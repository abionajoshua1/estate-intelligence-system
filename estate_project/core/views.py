#from django import db
import email
import re

from django.contrib.auth.models import User

from django import db
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dashboard.permissions import (
    IsResident,
    IsManager,
    IsAdmin,
    IsManagerOrAdmin,
)

from dashboard.models import Profile, Notification
from dashboard.notification_service import create_notification


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings
from .neo4j_connection import Neo4jConnection

from .ai_service import (
    ask_llm, 
    detect_ai_intent, 
    generate_cypher,
    analyze_results,
    )

from .graph_service import (
    fetch_top_residents,
    fetch_vacant_properties,
    fetch_estate_managers,
    fetch_maintenance_teams,
    fetch_all_residents,
    execute_cypher,
)

from .cypher_guard import is_safe_cypher
from .cypher_normalizer import normalize_cypher

from rest_framework.views import APIView
from rest_framework.response import Response

from .authorization import (
    authorize_resource,
    get_authorization_context,
    is_global_access,
    authorize_estate,
    AuthorizationError,
)


# =========================
# INTENTS
# =========================
INTENT_SYNONYMS = {
    "residents": ["resident", "residents", "tenant", "tenants", "people living", "who lives"],
    "properties": ["property", "properties", "house", "apartments", "building", "units"],
    "complaints": ["complaint", "issues", "problem", "report"],
    "estate": ["estate", "overview", "summary", "compound"]
}


INTENT_QUERIES = {
    "residents": "MATCH (r:Resident) RETURN r.name AS name, r.resident_id AS id",
    "properties": "MATCH (p:Property) RETURN p.property_id AS id, p.type AS type",
    "complaints": "MATCH (r:Resident)-[:RAISED]->(c:Complaint) RETURN r.name AS resident, c.title AS complaint, c.status AS status",
    "estate": """
MATCH (e:Estate)
OPTIONAL MATCH (r:Resident)
OPTIONAL MATCH (p:Property)
OPTIONAL MATCH (c:Complaint)

RETURN
e.name AS estate,
count(DISTINCT r) AS residents,
count(DISTINCT p) AS properties,
count(DISTINCT c) AS complaints
"""
}

# =========================
# FORMAT RESPONSE
# =========================
def format_message(intent, rows):
    print("format_message() called with:", intent )
    if intent == "residents":
        names = [r["name"] for r in rows]
        return f"There are {len(names)} residents: {', '.join(names)}"

    if intent == "properties":
        return f"There are {len(rows)} properties registered"

    if intent == "complaints":
        return f"There are {len(rows)} complaints"

    if intent == "estate":
        estate = rows[0]

        residents = estate["residents"]
        properties = estate["properties"]
        complaints = estate["complaints"]

        insight = (
            f"{estate['estate']} has "
            f"{residents} resident(s), "
            f"{properties} property(s), and "
            f"{complaints} complaint(s)."
        )

        if complaints > residents:
            insight += (
                "Complaint volume is relatively high compared to the number of residents."
            )
        elif complaints == 0:
            insight += (
                "No complaints have been recorded, indicating smooth estate operations."
            )
        else:
            insight+= (
                "The estate appears to be operating within a normal complaint range."
            )

        print("Returning AI insight..")
        return insight

# =========================
# MAIN ENDPOINT
# =========================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_query_v2(request):

    question = request.data.get("question", "").strip()

    if not question:
        return Response(
            {"error": "Question cannot be empty."},
            status=400,
        )

    intent = detect_ai_intent(question)

    context = ""

    if intent == "top_residents":

        residents = fetch_top_residents()

        context = "Residents with complaint counts:\n\n"

        for resident in residents:
            context += (
                f"{resident['resident']} reported "
                f"{resident['complaints']} complaints.\n"
            )

    elif intent == "vacant_properties":

        properties = fetch_vacant_properties()

        context = "Vacant properties:\n\n"

        for property in properties:
            context += (
                f"Property {property['property_number']} "
                f"is a {property['property_type']} "
                f"with {property['bedrooms']} bedrooms "
                f"and {property['bathrooms']} bathrooms.\n"
            )

    elif intent == "estate_managers":

        managers = fetch_estate_managers()

        context = "Estate Managers:\n\n"

        for manager in managers:
            context += (
                f"{manager['manager_name']} "
                f"Email: {manager['email']} "
                f"Phone: {manager['phone']}.\n"
            )

    elif intent == "maintenance_teams":

        teams = fetch_maintenance_teams()

        context = "Maintenance Teams:\n\n"

        for team in teams:
            context += (
                f"{team['team_name']} "
                f"specializes in {team['specialization']}.\n"
            )

    elif intent == "residents":

        residents = fetch_all_residents()

        context = "Residents:\n\n"

        for resident in residents:
            context += (
                f"{resident['resident_name']} "
                f"({resident['gender']}) "
                f"Status: {resident['status']}.\n"
            )

    else:
        return Response({
            "intent": "general",
            "response": ask_llm(question),
        })

    prompt = f"""
You are an Estate Intelligence Assistant.

Answer ONLY using the estate information below.

If the answer is not contained in the information provided,
say you do not have enough estate data.

Estate Data:
{context}

User Question:
{question}
"""

    answer = ask_llm(prompt)

    return Response({
        "intent": intent,
        "response": answer,
    })
    
# =========================
# RESIDENT CRUD
# =========================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_residents(request):

    query = """
    MATCH (r:Resident)
    RETURN
        r.resident_id AS resident_id,
        r.name AS name,
        r.phone AS phone,
        r.email AS email,
        r.gender AS gender,
        r.status AS status,
        toString(r.registered_at) AS registered_at
    ORDER BY r.name
    """

    db = Neo4jConnection()

    try:
        residents = db.query(query)
    finally:
        db.close()

    return Response(residents)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_resident(request):

    data = request.data

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip().lower()
    gender = data.get("gender", "").strip()

    if not all([name, phone, email, gender]):
        return Response(
            {"error": "All fields are required."},
            status=400
        )

    allowed_genders = ["Male", "Female"]

    if gender not in allowed_genders:
        return Response(
            {
                "error": "Gender must be either 'Male' or 'Female'."
            },
            status=400,
        )
    

    # Create Neo4j connection
    db = Neo4jConnection()

    # Get the last resident ID
    last_resident_query = """
    MATCH (r:Resident)
    RETURN r.resident_id AS resident_id
    ORDER BY resident_id DESC
    LIMIT 1
    """

    last = db.query(last_resident_query)

    # Generate the next ID
    if last:
        current_id = last[0]["resident_id"]
        number = int(current_id.replace("R", ""))
        new_id = f"R{number + 1:03d}"
    else:
        new_id = "R001"

    check_email_query = """
    MATCH (r:Resident)
    WHERE toLower(r.email) = toLower($email)
    RETURN r
    LIMIT 1
    """

    existing = db.query(
        check_email_query,
        {
            "email": email
        }
    )

    if existing:
        db.close()
        return Response(
            {"error": "A resident with this email already exists."},
            status=400
        )
    
    check_phone_query = """
    MATCH (r:Resident)
    WHERE r.phone = $phone
    RETURN r
    LIMIT 1
    """

    existing_phone = db.query(
        check_phone_query,
        {
            "phone": phone
        }
    )
    
    if existing_phone:
        db.close()
        return Response(
            {"error": "A resident with this phone number already exists."},
            status=400
        )

    create_query = """
    CREATE (r:Resident {
        resident_id: $resident_id,
        name: $name,
        phone: $phone,
        email: $email,
        gender: $gender,
        status: "Active",
        registered_at: datetime()
    })

    
    RETURN
        r.resident_id AS resident_id,
        r.name AS name,
        r.phone AS phone,
        r.email AS email,
        r.gender AS gender,
        r.status AS status,
        toString(r.registered_at) AS registered_at
    """

    resident = db.query(
        create_query,
        {
            "resident_id": new_id,
            "name": name,
            "phone": phone,
            "email": email,
            "gender": gender
        }
    )

    db.close()

    return Response(
        {
            "message": "Resident created successfully",
            "resident": resident[0]
        },
        status=201,

    )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_resident(request, resident_id):

    db = Neo4jConnection()

    query = """
    MATCH (r:Resident {resident_id: $resident_id})

    RETURN
        r.resident_id AS resident_id,
        r.name AS name,
        r.phone AS phone,
        r.email AS email,
        r.gender AS gender,
        r.status AS status,
        toString(r.registered_at) AS registered_at
    """

    resident = db.query(
        query,
        {
            "resident_id": resident_id
        }
    )

    if not resident:
        db.close()
        return Response(
            {
                "error": "Resident not found."
            },
            status=404
        )

    data = request.data

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip().lower()
    gender = data.get("gender", "").strip()
    status_value = data.get("status", "").strip()

    if not all([name, phone, email, gender, status_value]):
        db.close()
        return Response(
            {
                "error": "All fields are required."
            },
            status=400,
        )

    allowed_genders = ["Male", "Female"]

    if gender not in allowed_genders:
        db.close()
        return Response(
            {
                "error": "Gender must be either 'Male' or 'Female'."
            },
            status=400,
        )

    allowed_status = ["Active", "Inactive"]

    if status_value not in allowed_status:
        db.close()
        return Response(
            {
                "error": "Status must be either 'Active' or 'Inactive'."
            },
            status=400,
        )

    check_email_query = """
    MATCH (r:Resident)
    WHERE toLower(r.email) = toLower($email)
    AND r.resident_id <> $resident_id
    RETURN r
    LIMIT 1
    """

    existing_email = db.query(
        check_email_query,
        {
            "email": email,
            "resident_id": resident_id,
        }
    )

    if existing_email:
        db.close()
        return Response(
            {
                "error": "Another resident already uses this email."
            },
            status=400,
        )
    
    check_phone_query = """
    MATCH (r:Resident)
    WHERE r.phone = $phone
    AND r.resident_id <> $resident_id
    RETURN r
    LIMIT 1
    """

    existing_phone = db.query(
        check_phone_query,
        {
            "phone": phone,
            "resident_id": resident_id,
        }
    )

    if existing_phone:
        db.close()
        return Response(
            {
                "error": "Another resident already uses this phone number."
            },
            status=400,
        )
    
    update_query = """
    MATCH (r:Resident {resident_id: $resident_id})

    SET
        r.name = $name,
        r.phone = $phone,
        r.email = $email,
        r.gender = $gender,
        r.status = $status

    RETURN
        r.resident_id AS resident_id,
        r.name AS name,
        r.phone AS phone,
        r.email AS email,
        r.gender AS gender,
        r.status AS status,
        toString(r.registered_at) AS registered_at
    """

    updated_resident = db.query(
        update_query,
        {
            "resident_id": resident_id,
            "name": name,
            "phone": phone,
            "email": email,
            "gender": gender,
            "status": status_value,
        }
    )

    db.close()

    return Response(
        {
            "message": "Resident updated sucessfully.",
            "resident": updated_resident[0]
        },
        status=200,
    )

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_resident(request, resident_id):

    db = Neo4jConnection()

    check_query = """
    MATCH (r:Resident {resident_id: $resident_id})
    RETURN r.resident_id AS resident_id,
           r.name AS name
    """

    resident = db.query(
        check_query,
        {
            "resident_id": resident_id
        }
    )

    if not resident:
        db.close()
        return Response(
            {
                "error": "Resident not found."
            },
            status=404,
        )

    delete_query = """
    MATCH (r:Resident {resident_id: $resident_id})
    DELETE r
    """

    db.query(
        delete_query,
        {
            "resident_id": resident_id
        }
    )

    db.close()

    return Response(
        {
            "message": "Resident deleted successfully.",
            "resident_id": resident_id
        },
        status=200,
    )
    
    
@api_view(["POST"])
@permission_classes([IsManagerOrAdmin])
def link_resident_account(request):

    user_id = request.data.get("user_id")
    resident_id = request.data.get("resident_id", "").strip()

    if not user_id or not resident_id:
        return Response(
            {
                "error": "User ID and Resident ID are required."
            },
            status=400,
        )

    # ----------------------------------------------------------
    # Get Django user
    # ----------------------------------------------------------

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {
                "error": "Django user not found."
            },
            status=404,
        )

    # ----------------------------------------------------------
    # Get user's profile
    # ----------------------------------------------------------

    profile, _ = Profile.objects.get_or_create(
        user=user
    )

    # ----------------------------------------------------------
    # Only resident accounts can be linked
    # ----------------------------------------------------------

    if profile.role != "resident":
        return Response(
            {
                "error": "Only resident accounts can be linked to resident records."
            },
            status=400,
        )

    # ----------------------------------------------------------
    # Verify Neo4j resident exists
    # ----------------------------------------------------------

    db = Neo4jConnection()

    try:

        resident_query = """
        MATCH (r:Resident {resident_id: $resident_id})
        RETURN
            r.resident_id AS resident_id,
            r.name AS resident_name
        LIMIT 1
        """

        resident = db.query(
            resident_query,
            {
                "resident_id": resident_id
            }
        )

        if not resident:
            return Response(
                {
                    "error": "Resident record not found."
                },
                status=404,
            )

        # ------------------------------------------------------
        # Prevent resident record from being linked to another
        # Django account
        # ------------------------------------------------------

        existing_link = Profile.objects.filter(
            resident_id=resident_id
        ).exclude(
            user=user
        ).first()

        if existing_link:
            return Response(
                {
                    "error": (
                        "This resident record is already linked "
                        "to another account."
                    )
                },
                status=400,
            )

        # ------------------------------------------------------
        # Link account
        # ------------------------------------------------------

        profile.resident_id = resident_id
        profile.save(update_fields=["resident_id"])

        return Response(
            {
                "message": "Resident account linked successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                },
                "resident": resident[0],
            },
            status=200,
        )

    finally:
        db.close()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_properties(request):

    try:
        context = get_authorization_context(request.user)
    except (AuthorizationError, ValueError) as exc:
        return Response(
            {"error": str(exc)},
            status=403,
        )

    if is_global_access(context):
        query = """
        MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)

        OPTIONAL MATCH (r:Resident)-[:LIVES_IN]->(p)

        RETURN
            p.property_id AS property_id,
            p.property_number AS property_number,
            p.property_type AS property_type,
            p.bedrooms AS bedrooms,
            p.bathrooms AS bathrooms,
            p.status AS status,

            e.estate_id AS estate_id,
            e.name AS estate_name,

            r.resident_id AS resident_id,
            r.name AS resident_name,

            toString(p.created_at) AS created_at

        ORDER BY e.name, p.property_number
        """

        parameters = {}

    else:
        query = """
        MATCH (e:Estate {estate_id: $estate_id})
              -[:HAS_PROPERTY]->(p:Property)

        OPTIONAL MATCH (r:Resident)-[:LIVES_IN]->(p)

        RETURN
            p.property_id AS property_id,
            p.property_number AS property_number,
            p.property_type AS property_type,
            p.bedrooms AS bedrooms,
            p.bathrooms AS bathrooms,
            p.status AS status,

            e.estate_id AS estate_id,
            e.name AS estate_name,

            r.resident_id AS resident_id,
            r.name AS resident_name,

            toString(p.created_at) AS created_at

        ORDER BY e.name, p.property_number
        """

        parameters = {
            "estate_id": context["estate_id"],
        }

    db = Neo4jConnection()

    try:
        properties = db.query(query, parameters)
    finally:
        db.close()

    return Response(properties)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_property(request):

    data = request.data

    estate_id = data.get("estate_id", "").strip()
    property_number = data.get("property_number", "").strip()
    property_type = data.get("property_type", "").strip()
    bedrooms = data.get("bedrooms")
    bathrooms = data.get("bathrooms")
    status_value = data.get("status", "").strip()

    # Authorization
    try:
        context = get_authorization_context(request.user)

        if context["role"] not in ["manager", "admin"]:
            return Response(
                {"error": "You are not authorized to create properties."},
                status=403,
            )

        authorize_estate(context, estate_id)

    except (AuthorizationError, ValueError) as exc:
        return Response(
            {"error": str(exc)},
            status=403,
        )

    if not all([
        estate_id,
        property_number,
        property_type,
        bedrooms,
        bathrooms,
        status_value,
    ]):
        return Response(
            {
                "error": "All fields are required."
            },
            status=400,
        )

    allowed_types = [
        "Apartment",
        "Duplex",
        "Bungalow",
        "Studio",
    ]

    if property_type not in allowed_types:
        return Response(
            {
                "error": "Invalid property type."
            },
            status=400,
        )

    allowed_status = [
        "Available",
        "Occupied",
        "Maintenance",
    ]

    if status_value not in allowed_status:
        return Response(
            {
                "error": "Invalid property status."
            },
            status=400,
        )

    db = Neo4jConnection()

    estate_query = """
    MATCH (e:Estate {estate_id: $estate_id})
    RETURN e
    LIMIT 1
    """

    estate = db.query(
        estate_query,
        {
            "estate_id": estate_id
        }
    )

    if not estate:
        db.close()
        return Response(
            {
                "error": "Estate not found."
            },
            status=404,
        )

    last_property_query = """
    MATCH (p:Property)
    RETURN p.property_id AS property_id
    ORDER BY property_id DESC
    LIMIT 1
    """

    last = db.query(last_property_query)

    if last:
        current_id = last[0]["property_id"]
        number = int(current_id.replace("P", ""))
        new_id = f"P{number + 1:03d}"
    else:
        new_id = "P001"

    check_property_number_query = """
    MATCH (p:Property)
    WHERE p.property_number = $property_number
    RETURN p
    LIMIT 1
    """

    existing_property = db.query(
        check_property_number_query,
        {
            "property_number": property_number
        }
    )

    if existing_property:
        db.close()
        return Response(
            {
                "error": "A property with this property number already exists."
            },
            status=400,
        )

    create_query = """
    MATCH (e:Estate {estate_id: $estate_id})
    CREATE (p:Property{
        property_id: $property_id,
        property_number: $property_number,
        property_type: $property_type,
        bedrooms: $bedrooms,
        bathrooms: $bathrooms,
        status: $status,
        created_at: datetime()
    })
    CREATE (e)-[:HAS_PROPERTY]->(p)
    RETURN
        p.property_id AS property_id,
        p.property_number AS property_number,
        p.property_type AS property_type,
        p.bedrooms AS bedrooms,
        p.bathrooms AS bathrooms,
        p.status AS status,
        e.estate_id AS estate_id,
        e.name AS estate_name,
        toString(p.created_at) AS created_at
    """

    property_node = db.query(
        create_query,
        {
            "property_id": new_id,
            "property_number": property_number,
            "property_type": property_type,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "status": status_value,
            "estate_id": estate_id,
        }
    )

    db.close()

    return Response(
        {
            "message": "Property created successfully.",
            "property": property_node[0]
        },
        status=201,
    )

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_property(request, property_id) -> Response:

    property_id = str(property_id).strip()

    # Authorization
    try:
        context = get_authorization_context(request.user)

        # Only managers and admins can update properties
        if context["role"] not in ["manager", "admin"]:
            return Response(
                {
                    "error": "You are not authorized to update properties."
                },
                status=403,
            )

        # Get requested update data
        data = request.data
        estate_id = data.get("estate_id", "").strip()

        # The existing property must belong to the user's
        # authorized estate.
        authorize_resource(
            context,
            "property",
            property_id,
        )

        # The target estate must also be within the user's
        # authorized scope.
        authorize_estate(
            context,
            estate_id,
        )

    except (AuthorizationError, ValueError) as exc:
        return Response(
            {"error": str(exc)},
            status=403,
        )

    db = Neo4jConnection()

    query = """
    MATCH (p:Property {property_id: $property_id})
    RETURN
        p.property_id AS property_id,
        p.property_number AS property_number,
        p.property_type AS property_type,
        p.bedrooms AS bedrooms,
        p.bathrooms AS bathrooms,
        p.status AS status,
        toString(p.created_at) AS created_at
    """

    property_node = db.query(
        query,
        {
            "property_id": property_id
        }
    )

    if not property_node:
        db.close()
        return Response(
            {
                "error": "Property not found."
            },
            status=404,
        )

    property_number = data.get("property_number", "").strip()
    property_type = data.get("property_type", "").strip()
    bedrooms = data.get("bedrooms")
    bathrooms = data.get("bathrooms")
    status_value = data.get("status", "").strip()

    if not all([
        estate_id,
        property_number,
        property_type,
        bedrooms,
        bathrooms,
        status_value,
    ]):
        db.close()
        return Response(
            {
                "error": "All fields are required."
            },
            status=400,
        )

    allowed_types = [
        "Apartment",
        "Duplex",
        "Bungalow",
        "Studio",
    ]

    if property_type not in allowed_types:
        db.close()
        return Response(
            {
                "error": "Invalid property type."
            },
            status=400,
        )

    allowed_status = [
        "Available",
        "Occupied",
        "Maintenance",
    ]

    if status_value not in allowed_status:
        db.close()
        return Response(
            {
                "error": "Invalid property status."
            },
            status=400,
        )

    check_property_number_query = """
    MATCH (p:Property)
    WHERE p.property_number = $property_number
    AND p.property_id <> $property_id
    RETURN p
    LIMIT 1
    """

    existing_property = db.query(
        check_property_number_query,
        {
            "property_number": property_number,
            "property_id": property_id,
        }
    )

    if existing_property:
        db.close()
        return Response(
            {
                "error": "Another property already uses this property number."
            },
            status=400,
        )

    estate_query = """
    MATCH (e:Estate {estate_id: $estate_id})
    RETURN e
    LIMIT 1
    """

    estate = db.query(
        estate_query,
        {
            "estate_id": estate_id
        }
    )

    if not estate:
        db.close()
        return Response(
            {
                "error": "Estate not found."
            },
            status=404,
        )

    update_query = """
    MATCH (p:Property {property_id: $property_id})
    MATCH (newEstate:Estate {estate_id: $estate_id})
    OPTIONAL MATCH (:Estate)-[r:HAS_PROPERTY]->(p)
    DELETE r
    MERGE (newEstate)-[:HAS_PROPERTY]->(p)
    SET
        p.property_number = $property_number,
        p.property_type = $property_type,
        p.bedrooms = $bedrooms,
        p.bathrooms = $bathrooms,
        p.status = $status
    RETURN
        p.property_id AS property_id,
        p.property_number AS property_number,
        p.property_type AS property_type,
        p.bedrooms AS bedrooms,
        p.bathrooms AS bathrooms,
        p.status AS status,
        newEstate.estate_id AS estate_id,
        newEstate.name AS estate_name,
        toString(p.created_at) AS created_at
    """

    updated_property = db.query(
        update_query,
        {
            "property_id": property_id,
            "estate_id": estate_id,
            "property_number": property_number,
            "property_type": property_type,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "status": status_value,
        }
    )

    db.close()

    return Response(
        {
            "message": "Property updated successfully.",
            "property": updated_property[0]
        }
    )

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_property(request, property_id):

    db = Neo4jConnection()

    query = """
    MATCH (p:Property {property_id: $property_id})

    RETURN
        p.property_id AS property_id
    """

    property_node = db.query(
        query,
        {
            "property_id": property_id
        }
    )

    if not property_node:
        db.close()
        return Response(
            {
                "error": "Property not found."
            },
            status=404,
        )
    
    delete_query = """
    MATCH (p:Property {property_id: $property_id})
    
    OPTIONAL MATCH (c:Complaint)-[:ABOUT]->(p)
    
    DETACH DELETE c, p
    """

    db.query(
        delete_query,
        {
            "property_id": property_id
        }
    )

    db.close()

    return Response(
    {
        "message": "Property deleted successfully."
    }
)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_complaint(request):

    data = request.data

    role = getattr(
        getattr(request.user, "profile", None),
        "role",
        None,
    )

    resident_id = data.get(
        "resident_id",
        ""
    ).strip()

    property_id = data.get(
        "property_id",
        ""
    ).strip()

    title = data.get(
        "title",
        ""
    ).strip()

    description = data.get(
        "description",
        ""
    ).strip()

    category = data.get(
        "category",
        ""
    ).strip()

    priority = data.get(
        "priority",
        ""
    ).strip()

    # Residents can only create complaints for themselves.
    # Managers/admins can select a resident.
    if role == "resident":

        resident_id = request.user.profile.resident_id

        if not resident_id:
            return Response(
                {
                    "error": (
                        "No resident profile is linked "
                        "to this account."
                    )
                },
                status=403,
            )

    # Validate required fields.
    if not all([
        resident_id,
        property_id,
        title,
        description,
        category,
        priority,
    ]):
        return Response(
            {
                "error": "All fields are required."
            },
            status=400,
        )

    allowed_categories = [
        "Electrical",
        "Plumbing",
        "Security",
        "Noise",
        "Cleaning",
        "Maintenance",
        "Other",
    ]

    if category not in allowed_categories:
        return Response(
            {
                "error": "Invalid complaint category."
            },
            status=400,
        )

    allowed_priorities = [
        "Low",
        "Medium",
        "High",
    ]

    if priority not in allowed_priorities:
        return Response(
            {
                "error": "Invalid complaint priority."
            },
            status=400,
        )

    db = Neo4jConnection()

    try:

        # ----------------------------------------------------------
        # Verify resident exists
        # ----------------------------------------------------------

        resident_query = """
        MATCH (r:Resident {resident_id: $resident_id})
        RETURN r
        LIMIT 1
        """

        resident = db.query(
            resident_query,
            {
                "resident_id": resident_id
            }
        )

        if not resident:
            return Response(
                {
                    "error": "Resident not found."
                },
                status=404,
            )

        # ----------------------------------------------------------
        # Verify property exists
        # ----------------------------------------------------------

        property_query = """
        MATCH (p:Property {property_id: $property_id})
        RETURN p
        LIMIT 1
        """

        property_node = db.query(
            property_query,
            {
                "property_id": property_id
            }
        )

        if not property_node:
            return Response(
                {
                    "error": "Property not found."
                },
                status=404,
            )

        # ----------------------------------------------------------
        # Generate complaint ID
        # ----------------------------------------------------------

        last_complaint_query = """
        MATCH (c:Complaint)
        RETURN c.complaint_id AS complaint_id
        ORDER BY complaint_id DESC
        LIMIT 1
        """

        last = db.query(
            last_complaint_query
        )

        if last:
            current_id = last[0]["complaint_id"]
            number = int(
                current_id.replace("C", "")
            )
            new_id = f"C{number + 1:03d}"
        else:
            new_id = "C001"

        # ----------------------------------------------------------
        # Create complaint
        # ----------------------------------------------------------

        create_query = """
        MATCH (r:Resident {resident_id: $resident_id})
        MATCH (p:Property {property_id: $property_id})

        CREATE (c:Complaint {
            complaint_id: $complaint_id,
            title: $title,
            description: $description,
            category: $category,
            priority: $priority,
            status: "Open",
            created_at: datetime()
        })

        CREATE (r)-[:RAISED]->(c)
        CREATE (c)-[:ABOUT]->(p)

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS title,
            c.description AS description,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            toString(c.created_at) AS created_at
        """

        complaint = db.query(
            create_query,
            {
                "resident_id": resident_id,
                "property_id": property_id,
                "complaint_id": new_id,
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "status": status,
            }
        )
        
        # ----------------------------------------------------------
        # Create notification for the resident
        # ----------------------------------------------------------

        if role == "resident":
            Notification.objects.create(
                user=request.user,
                title="Complaint Submitted",
                message=(
                    f'Your complaint "{title}" has been submitted '
                    f"successfully and is currently Open."
                ),
                notification_type="complaint",
            )

        return Response(
            {
                "message": "Complaint created successfully.",
                "complaint": complaint[0],
            },
            status=201,
        )

    finally:
        db.close()
        

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_complaints(request):
    try:
        page = int(request.query_params.get("page", 1))
    except ValueError:
        return Response(
            {"error": "Page must be a number."},
            status=400,
        )
    
    try:
        page_size = int(request.query_params.get("page_size", 10))
    except ValueError:
        return Response(
            {"error": "Page size must be a number."},
            status=400,
        )
    
    if page < 1:
        return Response(
            {"error": "Page must be at least 1."},
            status=400,
        )
        
    if page_size < 1:
        return Response(
            {"error": "Page size must be at least 1."},
            status=400,
        )
        
    if page_size > 100:
        return Response(
            {"error": "Page size cannot exceed 100."},
            status=400,
        )

    skip = (page - 1) * page_size

    role = getattr(
        getattr(request.user, "profile", None),
        "role",
        None,
    )
    
    status = request.query_params.get("status")
    priority = request.query_params.get("priority")
    category = request.query_params.get("category")
    
    where_clause = ""

    if status:
        where_clause = "WHERE c.status = $status"
        
    if priority:
        if where_clause:
            where_clause += " AND c.priority = $priority"
        else:
            where_clause = "WHERE c.priority = $priority"
            
    if category:
        if where_clause:
            where_clause += " AND c.category = $category"
        else:
            where_clause = "WHERE c.category = $category"

    if role in ["manager", "admin"]:
        query = f"""
        MATCH (r:Resident)-[:RAISED]->(c:Complaint)-[:ABOUT]->(p:Property)
        
        {where_clause}

        RETURN
            c.complaint_id AS complaint_id,
            r.resident_id AS resident_id,
            r.name AS resident_name,
            p.property_id AS property_id,
            p.property_number AS property_number,
            c.title AS title,
            c.description AS description,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            toString(c.created_at) AS created_at

        ORDER BY c.created_at DESC, c.complaint_id DESC
        SKIP $skip
        LIMIT $page_size + 1
        """

        parameters = {
            "skip": skip,
            "page_size": page_size,
            "status": status,
            "priority": priority,
            "category": category,
        }

    elif role == "resident":
        resident_id = request.user.profile.resident_id

        if not resident_id:
            return Response(
                {
                    "error": "No resident profile is linked to this account."
                },
                status=403,
            )

        query = f"""
        MATCH (r:Resident {resident_id: $resident_id})
            -[:RAISED]->(c:Complaint)-[:ABOUT]->(p:Property)
            
        {where_clause}

        RETURN
            c.complaint_id AS complaint_id,
            r.resident_id AS resident_id,
            r.name AS resident_name,
            p.property_id AS property_id,
            p.property_number AS property_number,
            c.title AS title,
            c.description AS description,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            toString(c.created_at) AS created_at

        ORDER BY c.created_at DESC, c.complaint_id DESC
        SKIP $skip
        LIMIT $page_size + 1
        """

        parameters = {
            "resident_id": resident_id,
            "skip": skip,
            "page_size": page_size,
            "status": status,
            "priority": priority,
            "category": category,
        }
    else:
        return Response(
            {"error": "Invalid user role."},
            status=403,
        )

    db = Neo4jConnection()

    try:
        complaints = db.query(
            query,
            parameters,
        )
        
        has_next = len(complaints) > page_size
        complaints = complaints[:page_size]
        
    finally:
        db.close()

    return Response({
        "page": page,
        "page_size": page_size,
        "has_next": has_next,
        "results": complaints,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def global_search(request):
    query_text = request.query_params.get("q", "").strip()

    if not query_text:
        return Response([])

    db = Neo4jConnection()

    query = """
    CALL {
        MATCH (r:Resident)
        WHERE
            toLower(coalesce(r.name, "")) CONTAINS toLower($q)
            OR toLower(coalesce(r.email, "")) CONTAINS toLower($q)
            OR toLower(coalesce(r.phone, "")) CONTAINS toLower($q)
            OR toLower(coalesce(r.resident_id, "")) CONTAINS toLower($q)

        OPTIONAL MATCH (r)-[:LIVES_IN]->(p:Property)
        OPTIONAL MATCH (e:Estate)-[:HAS_PROPERTY]->(p)

        RETURN
            "Resident" AS type,
            r.resident_id AS id,
            r.name AS title,
            coalesce(r.email, "") AS subtitle,
            coalesce(e.name, "") AS related_estate,
            coalesce(p.property_number, "") AS related_property,
            "" AS related_resident

        UNION ALL

        MATCH (p:Property)
        WHERE
            toLower(coalesce(p.property_number, "")) CONTAINS toLower($q)
            OR toLower(coalesce(p.property_type, "")) CONTAINS toLower($q)
            OR toLower(coalesce(p.property_id, "")) CONTAINS toLower($q)

        OPTIONAL MATCH (e:Estate)-[:HAS_PROPERTY]->(p)
        OPTIONAL MATCH (r:Resident)-[:LIVES_IN]->(p)

        RETURN
            "Property" AS type,
            p.property_id AS id,
            p.property_number AS title,
            p.property_type AS subtitle,
            coalesce(e.name, "") AS related_estate,
            "" AS related_property,
            coalesce(r.name, "") AS related_resident

        UNION ALL

        MATCH (c:Complaint)
        WHERE
            toLower(coalesce(c.title, "")) CONTAINS toLower($q)
            OR toLower(coalesce(c.category, "")) CONTAINS toLower($q)
            OR toLower(coalesce(c.description, "")) CONTAINS toLower($q)
            OR toLower(coalesce(c.complaint_id, "")) CONTAINS toLower($q)
            OR toLower(coalesce(c.status, "")) CONTAINS toLower($q)

        OPTIONAL MATCH (r:Resident)-[:RAISED]->(c)
        OPTIONAL MATCH (c)-[:ABOUT]->(p:Property)

        RETURN
            "Complaint" AS type,
            c.complaint_id AS id,
            c.title AS title,
            c.category AS subtitle,
            "" AS related_estate,
            coalesce(p.property_number, "") AS related_property,
            coalesce(r.name, "") AS related_resident

        UNION ALL

        MATCH (e:Estate)
        WHERE
            toLower(coalesce(e.name, "")) CONTAINS toLower($q)
            OR toLower(coalesce(e.estate_id, "")) CONTAINS toLower($q)
            OR toLower(coalesce(e.address, "")) CONTAINS toLower($q)
            OR toLower(coalesce(e.city, "")) CONTAINS toLower($q)
            OR toLower(coalesce(e.state, "")) CONTAINS toLower($q)

        RETURN
            "Estate" AS type,
            e.estate_id AS id,
            e.name AS title,
            coalesce(e.city, e.state, "") AS subtitle,
            "" AS related_estate,
            "" AS related_property,
            "" AS related_resident

        UNION ALL

        MATCH (m:Manager)
        WHERE
            toLower(coalesce(m.name, "")) CONTAINS toLower($q)
            OR toLower(coalesce(m.email, "")) CONTAINS toLower($q)
            OR toLower(coalesce(m.phone, "")) CONTAINS toLower($q)
            OR toLower(coalesce(m.manager_id, "")) CONTAINS toLower($q)

        OPTIONAL MATCH (e:Estate)-[:HAS_MANAGER]->(m)

        RETURN
            "Manager" AS type,
            m.manager_id AS id,
            m.name AS title,
            coalesce(m.email, "") AS subtitle,
            coalesce(e.name, "") AS related_estate,
            "" AS related_property,
            "" AS related_resident

        UNION ALL

        MATCH (t:MaintenanceTeam)
        WHERE
            toLower(coalesce(t.team_name, "")) CONTAINS toLower($q)
            OR toLower(coalesce(t.specialization, "")) CONTAINS toLower($q)
            OR toLower(coalesce(t.email, "")) CONTAINS toLower($q)
            OR toLower(coalesce(t.team_id, "")) CONTAINS toLower($q)

        OPTIONAL MATCH (e:Estate)-[:HAS_MAINTENANCE_TEAM]->(t)

        RETURN
            "MaintenanceTeam" AS type,
            t.team_id AS id,
            t.team_name AS title,
            coalesce(t.specialization, "") AS subtitle,
            coalesce(e.name, "") AS related_estate,
            "" AS related_property,
            "" AS related_resident
    }

    RETURN
        type,
        id,
        title,
        subtitle,
        related_estate,
        related_property,
        related_resident
    LIMIT 30
    """

    try:
        results = db.query(query, {"q": query_text})
    finally:
        db.close()

    return Response(results)



@api_view(["PUT"])
@permission_classes([IsManagerOrAdmin])
def update_complaint(request, complaint_id):

    db = Neo4jConnection()

    try:

        # ----------------------------------------------------------
        # Get complaint and resident who raised it
        # ----------------------------------------------------------

        query = """
        MATCH (r:Resident)-[:RAISED]->(c:Complaint {
            complaint_id: $complaint_id
        })

        RETURN
            r.resident_id AS resident_id,
            c.complaint_id AS complaint_id,
            c.title AS title,
            c.description AS description,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            toString(c.created_at) AS created_at
        """

        complaint = db.query(
            query,
            {
                "complaint_id": complaint_id
            }
        )

        if not complaint:
            return Response(
                {
                    "error": "Complaint not found."
                },
                status=404,
            )

        complaint_data = complaint[0]

        resident_id = complaint_data["resident_id"]
        title = complaint_data["title"]
        old_status = complaint_data["status"]

        # ----------------------------------------------------------
        # Validate new status
        # ----------------------------------------------------------

        status_value = request.data.get(
            "status",
            ""
        ).strip()

        allowed_status = [
            "Open",
            "In Progress",
            "Resolved",
        ]

        if status_value not in allowed_status:
            return Response(
                {
                    "error": "Invalid complaint status."
                },
                status=400,
            )

        # ----------------------------------------------------------
        # Update complaint in Neo4j
        # ----------------------------------------------------------

        update_query = """
        MATCH (c:Complaint {
            complaint_id: $complaint_id
        })

        SET c.status = $status

        FOREACH (
            _ IN CASE
                WHEN $status = "Resolved"
                THEN [1]
                ELSE []
            END |
            SET c.resolved_at = datetime()
        )

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS title,
            c.description AS description,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            toString(c.created_at) AS created_at,
            toString(c.resolved_at) AS resolved_at
        """

        updated = db.query(
            update_query,
            {
                "complaint_id": complaint_id,
                "status": status_value,
            }
        )

        # ----------------------------------------------------------
        # Create notification only when status actually changes
        # ----------------------------------------------------------

        if updated and old_status != status_value:

            notification_messages = {
                "Open": (
                    f'Your complaint "{title}" '
                    f'has been reopened and is currently Open.'
                ),
                "In Progress": (
                    f'Your complaint "{title}" '
                    f'is now In Progress.'
                ),
                "Resolved": (
                    f'Your complaint "{title}" '
                    f'has been marked as Resolved.'
                ),
            }

            notification_titles = {
                "Open": "Complaint Reopened",
                "In Progress": "Complaint Status Updated",
                "Resolved": "Complaint Resolved",
            }

            # Find the Django user linked to this Neo4j resident
            try:
                resident_profile = Profile.objects.get(
                    resident_id=resident_id
                )

                Notification.objects.create(
                    user=resident_profile.user,
                    title=notification_titles[status_value],
                    message=notification_messages[status_value],
                    notification_type="complaint",
                )

            except Profile.DoesNotExist:
                # The complaint remains successfully updated
                # even if its resident has no Django profile.
                pass

        return Response(
            {
                "message": "Complaint updated successfully.",
                "complaint": updated[0],
            },
            status=200,
        )

    finally:
        db.close()
    
@api_view(["DELETE"])
@permission_classes([IsManagerOrAdmin])
def delete_complaint(request, complaint_id):

    db = Neo4jConnection()

    check_query = """
    MATCH (c:Complaint {complaint_id: $complaint_id})
    RETURN c.complaint_id AS complaint_id
    """

    complaint = db.query(
        check_query,
        {
            "complaint_id": complaint_id
        }
    )

    if not complaint:
        db.close()
        return Response(
            {
                "error": "Complaint not found."
            },
            status=404,
        )

    delete_query = """
    MATCH (c:Complaint {complaint_id: $complaint_id})
    DETACH DELETE c
    """

    db.query(
        delete_query,
        {
            "complaint_id": complaint_id
        }
    )

    db.close()

    return Response(
        {
            "message": "Complaint deleted successfully."
        },
        status=200,
    )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_estates(request):

    query = """
    MATCH (e:Estate)

    OPTIONAL MATCH (e)-[:HAS_PROPERTY]->(p:Property)

    WITH
        e,
        COUNT(p) AS property_count,
        COUNT(CASE WHEN p.status = "Occupied" THEN 1 END) AS occupied_properties,
        COUNT(CASE WHEN p.status = "Available" THEN 1 END) AS available_properties,
        COUNT(CASE WHEN p.status = "Maintenance" THEN 1 END) AS maintenance_properties

    RETURN
        e.estate_id AS estate_id,
        e.name AS name,
        e.address AS address,
        e.city AS city,
        e.state AS state,
        e.status AS status,

        property_count,
        occupied_properties,
        available_properties,
        maintenance_properties,

        toString(e.created_at) AS created_at

    ORDER BY e.name
    """

    db = Neo4jConnection()

    try:
        estates = db.query(query)
    finally:
        db.close()

    return Response(estates)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_estate(request):

    data = request.data

    name = data.get("name", "").strip()
    address = data.get("address", "").strip()
    city = data.get("city", "").strip()
    state = data.get("state", "").strip()
    status_value = data.get("status", "").strip()

    if not all([
        name,
        address,
        city,
        state,
        status_value,
    ]):
        return Response(
            {
                "error": "All fields are required."
            },
            status=400,
        )

    allowed_status = [
        "Active",
        "Inactive",
    ]

    if status_value not in allowed_status:
        return Response(
            {
                "error": "Invalid estate status."
            },
            status=400,
        )

    db = Neo4jConnection()

    try:
        # Generate Estate ID
        last_estate_query = """
        MATCH (e:Estate)
        RETURN e.estate_id AS estate_id
        ORDER BY estate_id DESC
        LIMIT 1
        """

        last = db.query(last_estate_query)
        
        current_id = None

        if last and last[0]["estate_id"] is not None:
            current_id = last[0]["estate_id"]
            number = int(current_id.replace("E", ""))
            new_id = f"E{number + 1:03d}"
        else:
            new_id = "E001"
            
        # Check duplicate
        check_query = """
        MATCH (e:Estate)
        WHERE 
        (
            tolower(e.name) = tolower($name) AND
            tolower(e.city) = tolower($city)
        )
        OR
        tolower(e.address) = tolower($address)
        
        RETURN e
        LIMIT 1
        """

        existing = db.query(
            check_query,
            {
                "name": name,
                "city": city,
                "address": address
            }
        )

        if existing:
            return Response(
                {
                    "error": "An estate with this name already exists in this city."
                },
                status=400,
            )

        create_query = """
        CREATE (e:Estate {
            estate_id: $estate_id,
            name: $name,
            address: $address,
            city: $city,
            state: $state,
            status: $status,
            created_at: datetime()
        })

        RETURN
            e.estate_id AS estate_id,
            e.name AS name,
            e.address AS address,
            e.city AS city,
            e.state AS state,
            e.status AS status,
            toString(e.created_at) AS created_at
        """

        estate = db.query(
            create_query,
            {
                "estate_id": new_id,
                "name": name,
                "address": address,
                "city": city,
                "state": state,
                "status": status_value,
            },
        )

        return Response(
            {
                "message": "Estate created successfully.",
                "estate": estate[0],
            },
            status=201,
        )

    finally:
        db.close()
        
        
@api_view(["PUT"])
def update_estate(request, estate_id):

    db = Neo4jConnection()

    try:

        # Check estate exists
        estate_query = """
        MATCH (e:Estate {estate_id:$estate_id})
        RETURN e
        LIMIT 1
        """

        estate = db.query(
            estate_query,
            {
                "estate_id": estate_id,
            },
        )

        if not estate:
            return Response(
                {
                    "error": "Estate not found."
                },
                status=404,
            )

        data = request.data

        name = data.get("name", "").strip()
        address = data.get("address", "").strip()
        city = data.get("city", "").strip()
        state = data.get("state", "").strip()
        status_value = data.get("status", "").strip()

        if not all([
            name,
            address,
            city,
            state,
            status_value,
        ]):
            return Response(
                {
                    "error": "All fields are required."
                },
                status=400,
            )

        allowed_status = [
            "Active",
            "Inactive",
        ]

        if status_value not in allowed_status:
            return Response(
                {
                    "error": "Invalid estate status."
                },
                status=400,
            )

        # Prevent duplicate estate
        duplicate_query = """
        MATCH (e:Estate)
        WHERE
            e.estate_id <> $estate_id
            AND
            (
                (
                    toLower(e.name)=toLower($name)
                    AND
                    toLower(e.city)=toLower($city)
                )
                OR
                toLower(e.address)=toLower($address)
            )

        RETURN e
        LIMIT 1
        """

        duplicate = db.query(
            duplicate_query,
            {
                "estate_id": estate_id,
                "name": name,
                "city": city,
                "address": address,
            },
        )

        if duplicate:
            return Response(
                {
                    "error": "Another estate already uses this name or address."
                },
                status=400,
            )

        update_query = """
        MATCH (e:Estate {estate_id:$estate_id})

        SET
            e.name=$name,
            e.address=$address,
            e.city=$city,
            e.state=$state,
            e.status=$status

        RETURN
            e.estate_id AS estate_id,
            e.name AS name,
            e.address AS address,
            e.city AS city,
            e.state AS state,
            e.status AS status,
            toString(e.created_at) AS created_at
        """

        updated = db.query(
            update_query,
            {
                "estate_id": estate_id,
                "name": name,
                "address": address,
                "city": city,
                "state": state,
                "status": status_value,
            },
        )

        return Response(
            {
                "message": "Estate updated successfully.",
                "estate": updated[0],
            },
            status=200,
        )

    finally:
        db.close()
        
@api_view(["DELETE"])
def delete_estate(request, estate_id):

    db = Neo4jConnection()

    try:

        # Check estate exists
        estate = db.query(
            """
            MATCH (e:Estate {estate_id:$estate_id})
            RETURN e
            LIMIT 1
            """,
            {
                "estate_id": estate_id
            }
        )

        if not estate:
            return Response(
                {
                    "error": "Estate not found."
                },
                status=404,
            )

        # Check if estate still has properties
        properties = db.query(
            """
            MATCH (e:Estate {estate_id:$estate_id})-[:HAS_PROPERTY]->(p:Property)
            RETURN COUNT(p) AS property_count
            """,
            {
                "estate_id": estate_id
            }
        )

        if properties[0]["property_count"] > 0:
            return Response(
                {
                    "error": "Cannot delete an estate that still contains properties."
                },
                status=400,
            )

        db.query(
            """
            MATCH (e:Estate {estate_id:$estate_id})
            DETACH DELETE e
            """,
            {
                "estate_id": estate_id
            }
        )

        return Response(
            {
                "message": "Estate deleted successfully."
            },
            status=200,
        )

    finally:
        db.close()
        
        
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_manager(request):

    data = request.data

    estate_id = data.get("estate_id", "").strip()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    status_value = data.get("status", "").strip()

    if not all([
        estate_id,
        name,
        email,
        phone,
        status_value,
    ]):
        return Response(
            {
                "error": "All fields are required."
            },
            status=400,
        )

    allowed_status = [
        "Active",
        "Inactive",
    ]

    if status_value not in allowed_status:
        return Response(
            {
                "error": "Invalid manager status."
            },
            status=400,
        )

    db = Neo4jConnection()

    try:

        # Generate Manager ID
        last_manager_query = """
        MATCH (m:Manager)
        RETURN m.manager_id AS manager_id
        ORDER BY manager_id DESC
        LIMIT 1
        """

        last = db.query(last_manager_query)

        if last and last[0]["manager_id"] is not None:
            current_id = last[0]["manager_id"]
            number = int(current_id.replace("M", ""))
            new_id = f"M{number + 1:03d}"
        else:
            new_id = "M001"

        # Check Estate Exists
        estate_query = """
        MATCH (e:Estate {estate_id:$estate_id})
        RETURN e
        LIMIT 1
        """

        estate = db.query(
            estate_query,
            {
                "estate_id": estate_id
            }
        )

        if not estate:
            return Response(
                {
                    "error": "Estate not found."
                },
                status=404,
            )

        # Check if estate already has a manager
        existing_manager_query = """
        MATCH (e:Estate {estate_id:$estate_id})-[:HAS_MANAGER]->(m:Manager)
        RETURN m
        LIMIT 1
        """

        existing_manager = db.query(
            existing_manager_query,
            {
                "estate_id": estate_id
            }
        )

        if existing_manager:
            return Response(
                {
                    "error": "This estate already has a manager."
                },
                status=400,
            )

        # Check duplicate email
        duplicate_email_query = """
        MATCH (m:Manager)
        WHERE toLower(m.email) = toLower($email)
        RETURN m
        LIMIT 1
        """

        duplicate = db.query(
            duplicate_email_query,
            {
                "email": email
            }
        )

        if duplicate:
            return Response(
                {
                    "error": "Email already exists."
                },
                status=400,
            )

        # Create Manager
        create_manager_query = """
        MATCH (e:Estate {estate_id:$estate_id})

        CREATE (m:Manager {
            manager_id: $manager_id,
            name: $name,
            email: $email,
            phone: $phone,
            status: $status,
            created_at: datetime()
        })

        CREATE (e)-[:HAS_MANAGER]->(m)

        RETURN
            m.manager_id AS manager_id,
            m.name AS name,
            m.email AS email,
            m.phone AS phone,
            m.status AS status,
            e.estate_id AS estate_id,
            e.name AS estate_name,
            toString(m.created_at) AS created_at
        """

        manager = db.query(
            create_manager_query,
            {
                "estate_id": estate_id,
                "manager_id": new_id,
                "name": name,
                "email": email,
                "phone": phone,
                "status": status_value,
            },
        )

        return Response(
            {
                "message": "Manager created successfully.",
                "manager": manager[0],
            },
            status=201,
        )

    finally:
        db.close()
        
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_managers(request):

    query = """
    MATCH (e:Estate)-[:HAS_MANAGER]->(m:Manager)

    RETURN
        m.manager_id AS manager_id,
        m.name AS name,
        m.email AS email,
        m.phone AS phone,
        m.status AS status,
        e.estate_id AS estate_id,
        e.name AS estate_name,
        toString(m.created_at) AS created_at

    ORDER BY e.name, m.name
    """

    db = Neo4jConnection()

    try:
        managers = db.query(query)
    finally:
        db.close()

    return Response(managers)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_manager(request, manager_id):
    
    db = Neo4jConnection()
    
    try:
        
        # Check if manager exists
        check_query = """
        MATCH (m:Manager {manager_id:$manager_id})
        RETURN m
        LIMIT 1
        """

        manager = db.query(
            check_query,
            {
                "manager_id": manager_id
            }
        )

        if not manager:
            return Response(
                {
                    "error": "Manager not found."
                },
                status=404,
            )

        data = request.data

        estate_id = data.get("estate_id", "").strip()
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        status_value = data.get("status", "").strip()

        if not all([
            estate_id,
            name,
            email,
            phone,
            status_value,
        ]):
            return Response(
                {
                    "error": "All fields are required."
                },
                status=400,
            )
            
        
        estate_query = """
        MATCH (e:Estate {estate_id:$estate_id})
        RETURN e
        LIMIT 1
        """
        
        estate = db.query(
            estate_query,
            {
                "estate_id": estate_id
            }
        )
        
        if not estate:
            return Response(
                {
                    "error": "Estate not found."
                },
                status=404,
            )
            
        duplicate_email_query = """
        MATCH (m:Manager)
        WHERE toLower(m.email) = toLower($email)
        AND m.manager_id <> $manager_id
        RETURN m
        LIMIT 1
        """
        
        duplicate = db.query(
            duplicate_email_query,
            {
                "email": email,
                "manager_id": manager_id
            }
        )
        
        if duplicate:
            return Response(
                {
                    "error": "Email already exists."
                },
                status=400,
            )
            
        manage_check_query = """
        MATCH (e:Estate {estate_id:$estate_id})-[:HAS_MANAGER]->(m:Manager)
        WHERE m.manager_id <> $manager_id
        RETURN m
        LIMIT 1
        """
        
        existing = db.query(
            manage_check_query,
            {
                "estate_id": estate_id,
                "manager_id": manager_id
            }
        )
        
        if existing:
            return Response(
                {
                    "error": "This estate already has a manager."
                },
                status=400,
            )
            
        db.query(
            """
            MATCH (e:Estate {estate_id:$estate_id})
            MATCH (m:Manager {manager_id:$manager_id})
            
            CREATE (e)-[:HAS_MANAGER]->(m)
            """,
            {
                "estate_id": estate_id,
                "manager_id": manager_id
            }
        )
        
        update_query = """
        MATCH (m:Manager {manager_id:$manager_id})
        
        SET
            m.name = $name,
            m.email = $email,
            m.phone = $phone,
            m.status = $status
            
        RETURN
            m.manager_id AS manager_id,
            m.name AS name,
            m.email AS email,
            m.phone AS phone,
            m.status AS status,
            toString(m.created_at) AS created_at
        """
        
        updated = db.query(
            update_query,
            {
                "manager_id": manager_id,
                "name": name,
                "email": email,
                "phone": phone,
                "status": status_value
            }
        )
        
        return Response(
            {
                "message": "Manager updated successfully.",
                "manager": updated[0],
            },
        )
        
    finally:
        db.close()
        
        
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_manager(request, manager_id):

    db = Neo4jConnection()

    try:

        # Check manager exists
        query = """
        MATCH (m:Manager {manager_id:$manager_id})

        RETURN
            m.manager_id AS manager_id
        """

        manager = db.query(
            query,
            {
                "manager_id": manager_id
            }
        )

        if not manager:
            return Response(
                {
                    "error": "Manager not found."
                },
                status=404,
            )

        delete_query = """
        MATCH (m:Manager {manager_id:$manager_id})
        DETACH DELETE m
        """

        db.query(
            delete_query,
            {
                "manager_id": manager_id
            }
        )

        return Response(
            {
                "message": "Manager deleted successfully."
            }
        )

    finally:
        db.close()
        
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_maintenance_team(request):

    data = request.data

    estate_id = data.get("estate_id", "").strip()
    team_name = data.get("team_name", "").strip()
    specialization = data.get("specialization", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    status_value = data.get("status", "").strip()

    if not all([
        estate_id,
        team_name,
        specialization,
        phone,
        email,
        status_value,
    ]):
        return Response(
            {
                "error": "All fields are required."
            },
            status=400,
        )

    allowed_status = [
        "Active",
        "Inactive",
    ]

    if status_value not in allowed_status:
        return Response(
            {
                "error": "Invalid status."
            },
            status=400,
        )

    db = Neo4jConnection()

    try:
        
        last_team_query = """
        MATCH (t:MaintenanceTeam)
        RETURN t.team_id AS team_id
        ORDER BY team_id DESC
        LIMIT 1
        """

        last = db.query(last_team_query)

        if last and last[0]["team_id"] is not None:
            current_id = last[0]["team_id"]
            number = int(current_id.replace("T", ""))
            new_id = f"T{number + 1:03d}"
        else:
            new_id = "T001"
            
        estate_query = """
        MATCH (e:Estate {estate_id:$estate_id})
        RETURN e
        LIMIT 1
        """

        estate = db.query(
            estate_query,
            {
                "estate_id": estate_id
            }
        )

        if not estate:
            return Response(
                {
                    "error": "Estate not found."
                },
                status=404,
            )
   
        duplicate_team_query = """
        MATCH (e:Estate {estate_id:$estate_id})-[:HAS_MAINTENANCE_TEAM]->(t:MaintenanceTeam)
        WHERE toLower(t.team_name)=toLower($team_name)
        RETURN t
        LIMIT 1
        """

        duplicate_team = db.query(
            duplicate_team_query,
            {
                "estate_id": estate_id,
                "team_name": team_name,
            }
        )

        if duplicate_team:
            return Response(
                {
                    "error": "This estate already has a team with this name."
                },
                status=400,
            )
            
        duplicate_email_query = """
        MATCH (t:MaintenanceTeam)
        WHERE toLower(t.email)=toLower($email)
        RETURN t
        LIMIT 1
        """

        duplicate_email = db.query(
            duplicate_email_query,
            {
                "email": email
            }
        )

        if duplicate_email:
            return Response(
                {
                    "error": "Email already exists."
                },
                status=400,
            )
            
        create_query = """
        MATCH (e:Estate {estate_id:$estate_id})

        CREATE (t:MaintenanceTeam{
            team_id:$team_id,
            team_name:$team_name,
            specialization:$specialization,
            phone:$phone,
            email:$email,
            status:$status,
            created_at:datetime()
        })

        CREATE (e)-[:HAS_MAINTENANCE_TEAM]->(t)

        RETURN
            t.team_id AS team_id,
            t.team_name AS team_name,
            t.specialization AS specialization,
            t.phone AS phone,
            t.email AS email,
            t.status AS status,
            e.estate_id AS estate_id,
            e.name AS estate_name,
            toString(t.created_at) AS created_at
        """
        
        team = db.query(
            create_query,
            {
                "estate_id": estate_id,
                "team_id": new_id,
                "team_name": team_name,
                "specialization": specialization,
                "phone": phone,
                "email": email,
                "status": status_value,
            }
        )

        return Response(
            {
                "message": "Maintenance team created successfully.",
                "team": team[0],
            },
            status=201,
        )

    finally:
        db.close()
        

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_maintenance_teams(request):

    query = """
    MATCH (e:Estate)-[:HAS_MAINTENANCE_TEAM]->(t:MaintenanceTeam)

    RETURN
        t.team_id AS team_id,
        t.team_name AS team_name,
        t.specialization AS specialization,
        t.phone AS phone,
        t.email AS email,
        t.status AS status,

        e.estate_id AS estate_id,
        e.name AS estate_name,

        toString(t.created_at) AS created_at

    ORDER BY t.team_name
    """

    db = Neo4jConnection()

    try:
        teams = db.query(query)
    finally:
        db.close()

    return Response(teams)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_maintenance_team(request, team_id):

    query = """
    MATCH (e:Estate)-[:HAS_MAINTENANCE_TEAM]->(t:MaintenanceTeam {
        team_id:$team_id
    })

    RETURN
        t.team_id AS team_id,
        t.team_name AS team_name,
        t.specialization AS specialization,
        t.phone AS phone,
        t.email AS email,
        t.status AS status,

        e.estate_id AS estate_id,
        e.name AS estate_name,

        toString(t.created_at) AS created_at
    """

    db = Neo4jConnection()

    try:
        team = db.query(
            query,
            {
                "team_id": team_id
            }
        )
    finally:
        db.close()

    if not team:
        return Response(
            {
                "error": "Maintenance team not found."
            },
            status=404,
        )

    return Response(team[0])


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_maintenance_team(request, team_id):

    db = Neo4jConnection()

    try:

        # Check team exists
        query = """
        MATCH (t:MaintenanceTeam {team_id:$team_id})
        RETURN t
        LIMIT 1
        """

        team = db.query(
            query,
            {
                "team_id": team_id
            }
        )

        if not team:
            return Response(
                {
                    "error": "Maintenance team not found."
                },
                status=404,
            )

        data = request.data

        team_name = data.get("team_name", "").strip()
        specialization = data.get("specialization", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip()
        status_value = data.get("status", "").strip()

        if not all([
            team_name,
            specialization,
            phone,
            email,
            status_value,
        ]):
            return Response(
                {
                    "error": "All fields are required."
                },
                status=400,
            )

        allowed_status = [
            "Active",
            "Inactive",
        ]

        if status_value not in allowed_status:
            return Response(
                {
                    "error": "Invalid status."
                },
                status=400,
            )

        # Ensure email is unique
        duplicate_email_query = """
        MATCH (t:MaintenanceTeam)
        WHERE toLower(t.email)=toLower($email)
        AND t.team_id <> $team_id
        RETURN t
        LIMIT 1
        """
        
        duplicate_phone_query = """
        MATCH (t:MaintenanceTeam)
        WHERE t.phone = $phone
        AND t.team_id <> $team_id
        RETURN t
        LIMIT 1
        """

        duplicate_phone = db.query(
            duplicate_phone_query,
            {
                "phone": phone,
                "team_id": team_id,
            }
        )

        if duplicate_phone:
            return Response(
                {
                    "error": "Another maintenance team already uses this phone number."
                },
                status=400,
            )

        duplicate = db.query(
            duplicate_email_query,
            {
                "email": email,
                "team_id": team_id,
            }
        )

        if duplicate:
            return Response(
                {
                    "error": "Another maintenance team already uses this email."
                },
                status=400,
            )

        update_query = """
        MATCH (t:MaintenanceTeam {team_id:$team_id})

        SET
            t.team_name = $team_name,
            t.specialization = $specialization,
            t.phone = $phone,
            t.email = $email,
            t.status = $status

        RETURN
            t.team_id AS team_id,
            t.team_name AS team_name,
            t.specialization AS specialization,
            t.phone AS phone,
            t.email AS email,
            t.status AS status,
            toString(t.created_at) AS created_at
        """

        updated_team = db.query(
            update_query,
            {
                "team_id": team_id,
                "team_name": team_name,
                "specialization": specialization,
                "phone": phone,
                "email": email,
                "status": status_value,
            }
        )

        return Response(
            {
                "message": "Maintenance team updated successfully.",
                "team": updated_team[0],
            }
        )

    finally:
        db.close()
        
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_maintenance_team(request, team_id):

    db = Neo4jConnection()

    try:

        # Check if team exists
        query = """
        MATCH (t:MaintenanceTeam {team_id:$team_id})

        RETURN
            t.team_id AS team_id
        """

        team = db.query(
            query,
            {
                "team_id": team_id
            }
        )

        if not team:
            return Response(
                {
                    "error": "Maintenance team not found."
                },
                status=404,
            )

        delete_query = """
        MATCH (t:MaintenanceTeam {team_id:$team_id})
        DETACH DELETE t
        """

        db.query(
            delete_query,
            {
                "team_id": team_id
            }
        )

        return Response(
            {
                "message": "Maintenance team deleted successfully."
            }
        )

    finally:
        db.close()
        

@api_view(["POST"])
@permission_classes([IsManagerOrAdmin])
def assign_property_to_resident(request):

    print("Assign Property to Resident API called.")

    data = request.data

    resident_id = data.get("resident_id", "").strip()
    property_id = data.get("property_id", "").strip()

    print("ASSIGN DEBUG:")
    print("resident_id =", repr(resident_id))
    print("property_id =", repr(property_id))

    if not all([resident_id, property_id]):
        return Response(
            {
                "error": "Resident ID and Property ID are required."
            },
            status=400,
        )

    db = Neo4jConnection()

    try:

        # Check resident exists
        resident_query = """
        MATCH (r:Resident {resident_id:$resident_id})
        RETURN r
        LIMIT 1
        """

        resident = db.query(
            resident_query,
            {
                "resident_id": resident_id
            }
        )

        if not resident:
            return Response(
                {
                    "error": "Resident not found."
                },
                status=404,
            )

        # Check property exists
        property_query = """
        MATCH (p:Property {property_id:$property_id})
        RETURN p
        LIMIT 1
        """

        property_node = db.query(
            property_query,
            {
                "property_id": property_id
            }
        )

        if not property_node:
            return Response(
                {
                    "error": "Property not found."
                },
                status=404,
            )

        # Check if resident already occupies a property
        existing_relationship = """
        MATCH (r:Resident {resident_id:$resident_id})-[rel:LIVES_IN]->(:Property)
        RETURN rel
        LIMIT 1
        """

        existing = db.query(
            existing_relationship,
            {
                "resident_id": resident_id
            }
        )
        
        remove_old_property_query = """
        MATCH (r:Resident {resident_id:$resident_id})-[rel:LIVES_IN]->(:Property)
        DELETE rel
        """
        
        db.query(
            remove_old_property_query,
            {
                "resident_id": resident_id
            },
        )
        
        existing_occupant_query = """
        MATCH (r:Resident)-[:LIVES_IN]->(p:Property {property_id:$property_id})
        RETURN r.name AS resident_name
        LIMIT 1
        """

        existing_occupant = db.query(
            existing_occupant_query,
            {
                "property_id": property_id
            }
        )

        if existing_occupant:
            return Response(
                {
                    "error": f"Property is already occupied by {existing_occupant[0]['resident_name']}."
                },
                status=400,
            )
        

        # Create relationship
        assign_query = """
        MATCH (r:Resident {resident_id:$resident_id})
        MATCH (p:Property {property_id:$property_id})

        CREATE (r)-[:LIVES_IN]->(p)
        
        SET p.status = "Occupied"

        RETURN
            r.resident_id AS resident_id,
            r.name AS resident_name,
            p.property_id AS property_id,
            p.property_number AS property_number,
            p.status AS status
        """

        assignment = db.query(
            assign_query,
            {
                "resident_id": resident_id,
                "property_id": property_id,
            }
        )

        return Response(
            {
                "message": "Resident assigned to property successfully.",
                "assignment": assignment[0],
            },
            status=201,
        )

    finally:
        db.close()
        
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_property_to_complaint(request):

    data = request.data

    complaint_id = data.get("complaint_id", "").strip()
    property_id = data.get("property_id", "").strip()

    if not all([complaint_id, property_id]):
        return Response(
            {
                "error": "Complaint ID and Property ID are required."
            },
            status=400,
        )

    db = Neo4jConnection()

    try:

        # Check complaint exists
        complaint_query = """
        MATCH (c:Complaint {complaint_id:$complaint_id})
        RETURN c
        LIMIT 1
        """

        complaint = db.query(
            complaint_query,
            {
                "complaint_id": complaint_id
            }
        )

        if not complaint:
            return Response(
                {
                    "error": "Complaint not found."
                },
                status=404,
            )

        # Check property exists
        property_query = """
        MATCH (p:Property {property_id:$property_id})
        RETURN p
        LIMIT 1
        """

        property_node = db.query(
            property_query,
            {
                "property_id": property_id
            }
        )

        if not property_node:
            return Response(
                {
                    "error": "Property not found."
                },
                status=404,
            )
            
        # Create relationship
        assign_query = """
        MATCH (c:Complaint {complaint_id:$complaint_id})
        MATCH (p:Property {property_id:$property_id})

        OPTIONAL MATCH (c)-[old:ABOUT]->(:Property)
        DELETE old

        CREATE (c)-[:ABOUT]->(p)

        RETURN
            c.complaint_id AS complaint_id,
            p.property_id AS property_id,
            p.property_number AS property_number
        """

        assignment = db.query(
            assign_query,
            {
                "complaint_id": complaint_id,
                "property_id": property_id,
            }
        )

        return Response(
            {
                "message": "Complaint assigned to property successfully.",
                "assignment": assignment[0],
            },
            status=201,
        )

    finally:
        db.close()
        
@api_view(["POST"])
@permission_classes([IsManagerOrAdmin])
def assign_complaint_to_team(request):

    data = request.data

    complaint_id = data.get("complaint_id", "").strip()
    team_id = data.get("team_id", "").strip()

    if not all([complaint_id, team_id]):
        return Response(
            {
                "error": "Complaint ID and Team ID are required."
            },
            status=400,
        )

    db = Neo4jConnection()

    try:

        # Check complaint exists
        complaint_query = """
        MATCH (r:Resident)-[:RAISED]->(c:Complaint {complaint_id:$complaint_id})
        RETURN
            c.complaint_id AS complaint_id,
            c.title AS complaint_title,
            r.resident_id AS resident_id
        LIMIT 1
        """

        complaint = db.query(
            complaint_query,
            {
                "complaint_id": complaint_id
            }
        )

        if not complaint:
            return Response(
                {
                    "error": "Complaint not found."
                },
                status=404,
            )

        # Check maintenance team exists
        team_query = """
        MATCH (t:MaintenanceTeam {team_id:$team_id})
        RETURN t
        LIMIT 1
        """

        team = db.query(
            team_query,
            {
                "team_id": team_id
            }
        )

        if not team:
            return Response(
                {
                    "error": "Maintenance team not found."
                },
                status=404,
            )

        # Check complaint isn't already assigned
        existing_query = """
        MATCH (c:Complaint {complaint_id:$complaint_id})-[r:ASSIGNED_TO]->(:MaintenanceTeam)
        RETURN r
        LIMIT 1
        """

        existing = db.query(
            existing_query,
            {
                "complaint_id": complaint_id
            }
        )

        if existing:
            return Response(
                {
                    "error": "Complaint is already assigned to a maintenance team."
                },
                status=400,
            )

        # Create relationship
        assign_query = """
        MATCH (r:Resident)-[:RAISED]->(c:Complaint {complaint_id: $complaint_id})
        MATCH (t:MaintenanceTeam {team_id: $team_id})

        CREATE (c)-[:ASSIGNED_TO]->(t)
        SET c.status = "In Progress"

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS complaint_title,
            r.resident_id AS resident_id,
            t.team_id AS team_id,
            t.team_name AS team_name
        """

        assignment = db.query(
            assign_query,
            {
                "complaint_id": complaint_id,
                "team_id": team_id,
            }
        )
        

        if not assignment:
            return Response(
                {
                    "error": "Failed to assign complaint to maintenance team."
                },
                status=500,
            )

        # ----------------------------------------------------------
        # Create notification for the resident
        # ----------------------------------------------------------

        resident_id = assignment[0].get("resident_id")

        if resident_id:
            try:
                resident_profile = Profile.objects.get(
                    resident_id=resident_id
                )
                
                print("CREATING ASSIGNMENT NOTIFICATION FOR:", resident_profile.user)

                create_notification(
                    user=resident_profile.user,
                    title="Complaint Assigned",
                    message=(
                        f'Your complaint "{assignment[0]["complaint_title"]}" '
                        f'has been assigned to '
                        f'{assignment[0]["team_name"]} and is now In Progress.'
                    ),
                    notification_type="complaint",
                )

            except Profile.DoesNotExist as e:
                print("NOTIFICATION PROFILE ERROR:", e)

        return Response(
            {
                "message": "Complaint assigned successfully.",
                "assignment": assignment[0],
            },
            status=201,
        )

    finally:
        db.close()
        

    
def normalize_result(data):
    """Normalize Cypher result aliases into the application's internal schema."""

    aliases = {
        # Resident
        "resident_name": "name",

        # Estate
        "estate_name": "estate",

        # Property
        "property_status": "status",

        # Maintenance team
        "team_name": "team",
    }

    normalized = []

    for row in data:
        item = dict(row)

        for old_key, new_key in aliases.items():
            if old_key in item and new_key not in item:
                item[new_key] = item.pop(old_key)

        normalized.append(item)

    return normalized


def format_results(question: str, data):

    if not data:
        return "No matching records were found."

    data = normalize_result(data)
    row = data[0]

    # ==========================================================
    # FORMATTERS
    # ==========================================================

    def estate_overview(rows):
        r = rows[0]

        return (
            "Estate Overview:\n\n"
            f"• Residents: {r.get('total_residents', 0)}\n"
            f"• Properties: {r.get('total_properties', 0)}\n"
            f"• Available properties: {r.get('available_properties', 0)}\n"
            f"• Occupied properties: {r.get('occupied_properties', 0)}\n"
            f"• Properties under maintenance: {r.get('maintenance_properties', 0)}\n"
            f"• Total complaints: {r.get('total_complaints', 0)}\n"
            f"• Open complaints: {r.get('open_complaints', 0)}\n"
            f"• Complaints in progress: {r.get('in_progress_complaints', 0)}\n"
            f"• Resolved complaints: {r.get('resolved_complaints', 0)}"
        )

    def count_result(rows, field, singular, plural):
        count = rows[0].get(field, 0)

        return (
            f"There {'is' if count == 1 else 'are'} "
            f"{count} {singular if count == 1 else plural}."
        )

    def estates(rows):
        lines = ["Estates found:\n"]

        for item in rows:
            name = item.get("name") or "Unknown"
            estate_id = item.get("estate_id")

            if estate_id:
                lines.append(f"• {name} ({estate_id})")
            else:
                lines.append(f"• {name}")

        return "\n".join(lines)

    def residents(rows):
        lines = ["Residents:\n"]

        for item in rows:
            name = item.get("name") or "Unknown"
            resident_id = item.get("resident_id")

            if resident_id:
                lines.append(f"• {name} ({resident_id})")
            else:
                lines.append(f"• {name}")

        return "\n".join(lines)

    def residents_in_estate(rows):
        lines = ["Residents in Estate:\n"]

        for item in rows:
            name = item.get("name") or "Unknown"
            resident_id = item.get("resident_id") or "Unknown"
            estate = item.get("estate") or "Unknown"

            lines.append(
                f"• {name} ({resident_id}) - {estate}"
            )

        return "\n".join(lines)

    def residents_in_property(rows):
        lines = ["Residents in Property:\n"]

        for item in rows:
            name = item.get("name") or "Unknown"
            resident_id = item.get("resident_id") or "Unknown"
            property_number = item.get("property_number") or "Unknown"

            lines.append(
                f"• {name} ({resident_id}) - {property_number}"
            )

        return "\n".join(lines)
    
    def resident_location(rows):
        lines = ["Resident Location:\n"]

        for item in rows:
            name = item.get("name") or "Unknown"
            resident_id = item.get("resident_id") or "Unknown"
            property_number = item.get("property_number") or "Unknown"
            property_type = item.get("property_type") or "Unknown"
            estate = item.get("estate") or "Unknown"

            lines.append(
                f"• {name} ({resident_id}) - {property_number} | {property_type} | {estate}"
            )

        return "\n".join(lines)
    
    def properties(rows):
        lines = ["Properties:\n"]

        for item in rows:
            number = item.get("property_number") or "Unknown"
            property_type = item.get("property_type") or "Not specified"
            status = item.get("status") or "Unknown"

            lines.append(
                f"• {number} - {property_type} | {status}"
            )

        return "\n".join(lines)
    
    def properties_needing_attention(rows):
        lines = ["Properties Needing Attention:\n"]

        for item in rows:
            number = item.get("property_number") or "Unknown"
            property_type = item.get("property_type") or "Unknown"
            status = item.get("status") or "Unknown"
            count = item.get("complaint_count", 0)

            lines.append(
                f"• {number} - {property_type} | "
                f"{status} | {count} "
                f"{'complaint' if count == 1 else 'complaints'}"
            )

        return "\n".join(lines)
    

    def estate_property_status(rows):
        lines = ["Estate Property Status:\n"]

        for item in rows:
            estate = item.get("estate") or "Unknown"
            number = item.get("property_number") or "Unknown"
            property_type = item.get("property_type") or "Unknown"
            status = item.get("status") or "Unknown"

            lines.append(
                f"• {estate} - {number} | "
                f"{property_type} | {status}"
            )

        return "\n".join(lines)

    def complaints(rows):
        lines = ["Complaints:\n"]

        for item in rows:
            complaint_id = item.get("complaint_id") or "Unknown"
            title = item.get("title") or "Untitled complaint"
            priority = item.get("priority") or "Not specified"
            status = item.get("status") or "Unknown"

            lines.append(
                f"• {complaint_id}: "
                f"{title} | {priority} | {status}"
            )

        return "\n".join(lines)

    def maintenance_teams(rows):
        lines = ["Maintenance Teams:\n"]

        for item in rows:
            team = item.get("team") or "Unknown"
            specialization = (
                item.get("specialization")
                or "Not specified"
            )

            lines.append(
                f"• {team} | {specialization}"
            )

        return "\n".join(lines)

    def top_residents(rows):
        lines = ["Top Residents by Complaints:\n"]

        for i, item in enumerate(rows, 1):
            name = item.get("name") or "Unknown"
            count = item.get("complaint_count", 0)

            lines.append(
                f"{i}. {name} - {count} "
                f"{'complaint' if count == 1 else 'complaints'}"
            )

        return "\n".join(lines)

    def top_properties(rows):
        lines = ["Top Properties by Complaints:\n"]

        for i, item in enumerate(rows, 1):
            number = item.get("property_number") or "Unknown"
            count = item.get("complaint_count", 0)

            lines.append(
                f"{i}. {number} - {count} "
                f"{'complaint' if count == 1 else 'complaints'}"
            )

        return "\n".join(lines)

    def top_maintenance_teams(rows):
        lines = ["Maintenance Teams Handling Most Complaints:\n"]

        for i, item in enumerate(rows, 1):
            team = item.get("team") or "Unknown"
            count = item.get("complaint_count", 0)

            lines.append(
                f"{i}. {team} - {count} "
                f"{'complaint' if count == 1 else 'complaints'}"
            )

        return "\n".join(lines)

    def top_resident_single(rows):
        item = rows[0]

        name = item.get("name") or "Unknown"
        count = item.get("complaints", 0)

        return (
            f"{name} has reported "
            f"{count} "
            f"{'complaint' if count == 1 else 'complaints'}."
        )

    def top_team_single(rows):
        item = rows[0]

        team = item.get("team") or "Unknown"
        count = item.get("complaint_count", 0)

        return (
            f"{team} is handling "
            f"{count} "
            f"{'complaint' if count == 1 else 'complaints'}."
        )

    def manager(rows):
        lines = ["Property Manager:\n"]

        for item in rows:
            name = item.get("manager_name") or "Unknown"
            manager_id = item.get("manager_id") or "Unknown"

            lines.append(
                f"• {name} ({manager_id})"
            )

        return "\n".join(lines)
    
    

    # ==========================================================
    # RESULT TYPE REGISTRY
    # ==========================================================

    formatters = [
        (
            {"total_residents"},
            estate_overview,
        ),

        (
            {"resident_count"},
            lambda rows: count_result(
                rows,
                "resident_count",
                "registered resident",
                "registered residents",
            ),
        ),

        (
            {"complaint_count"},
            lambda rows: count_result(
                rows,
                "complaint_count",
                "registered complaint",
                "registered complaints",
            ),
        ),

        (
            {"open_complaints"},
            lambda rows: count_result(
                rows,
                "open_complaints",
                "open complaint",
                "open complaints",
            ),
        ),

        (
            {"complaints_in_progress"},
            lambda rows: count_result(
                rows,
                "complaints_in_progress",
                "complaint in progress",
                "complaints in progress",
            ),
        ),

        (
            {"resolved_complaints"},
            lambda rows: count_result(
                rows,
                "resolved_complaints",
                "resolved complaint",
                "resolved complaints",
            ),
        ),

        (
            {"estate_id", "estate", "property_id",
             "property_number", "property_type", "status"},
            estate_property_status,
        ),
        
         (
            {
                "resident_id",
                "name",
                "property_id",
                "property_number",
                "property_type",
                "estate_id",
                "estate",
            },
            resident_location,
        ),
         
        (
            {"resident_id", "name", "estate"},
            residents_in_estate,
        ),

        (
            {"resident_id", "name", "property_number"},
            residents_in_property,
        ),

        (
            {"resident", "complaint_count"},
            top_residents,
        ),

        (
            {"name", "complaints"},
            top_resident_single,
        ),

        (
            {"property_number", "complaint_count"},
            top_properties,
            
        ),
        
        (
            {
                "property_id",
                "property_number",
                "property_type",
                "status",
                "complaint_count",
            },
            properties_needing_attention,
        ),

        (
            {"team", "complaint_count"},
            top_maintenance_teams,
        ),

        (
            {"manager_id", "manager_name"},
            manager,
        ),

        (
            {"complaint_id", "title"},
            complaints,
        ),

        (
            {"team", "specialization"},
            maintenance_teams,
        ),

        (
            {"property_number", "property_type", "status"},
            properties,
        ),

        (
            {"resident_id", "name"},
            residents,
        ),

        (
            {"estate_id", "name"},
            estates,
        ),
    ]

    # ==========================================================
    # SCHEMA-BASED FORMAT SELECTION
    # ==========================================================

    result_keys = set(row.keys())

    matches = [
        (required_keys, formatter)
        for required_keys, formatter in formatters
        if required_keys.issubset(result_keys)
    ]

    if matches:
        _, formatter = max(
            matches,
            key=lambda item: len(item[0])
        )
        
        print(">>> FORMATTER USED:", formatter.__name__)
        return formatter(data)
    
    print(">>> NO FORMATTER MATCHED")
    print(">>> FORMAT_RESULTS QUESTION:", question)
    print(">>> FORMAT_RESULTS DATA:", data)

    return str(data)

def resolve_user_estate(user):
    """
    Resolve the authenticated user's estate context.

    Managers:
        User → Profile.manager_id → Manager → Estate

    Residents:
        User → Profile.resident_id → Resident → Property → Estate

    Admins:
        Global system access. No estate restriction.
    """

    profile = getattr(user, "profile", None)

    if not profile:
        raise ValueError("Authenticated user has no profile.")

    role = profile.role

    # ==========================================================
    # ADMIN / SOFTWARE DEVELOPER
    # ==========================================================

    if role == "admin":
        return {
            "role": "admin",
            "estate_id": None,
            "estate_name": None,
            "scope": "global",
        }

    # ==========================================================
    # MANAGER
    # ==========================================================

    if role == "manager":

        manager_id = profile.manager_id

        if not manager_id:
            raise ValueError(
                "Manager account is not linked to a manager record."
            )

        query = """
        MATCH (e:Estate)-[:HAS_MANAGER]->(m:Manager)
        WHERE m.manager_id = $manager_id

        RETURN
            e.estate_id AS estate_id,
            e.name AS estate_name

        LIMIT 1
        """

        result = execute_cypher(
            query,
            {"manager_id": manager_id},
        )

    # ==========================================================
    # RESIDENT
    # ==========================================================

    elif role == "resident":

        resident_id = profile.resident_id

        if not resident_id:
            raise ValueError(
                "Resident account is not linked to a resident record."
            )

        query = """
        MATCH (r:Resident)-[:LIVES_IN]->(p:Property)
              <-[:HAS_PROPERTY]-(e:Estate)

        WHERE r.resident_id = $resident_id

        RETURN
            e.estate_id AS estate_id,
            e.name AS estate_name

        LIMIT 1
        """

        result = execute_cypher(
            query,
            {"resident_id": resident_id},
        )

    else:
        return None

    if not result:
        raise ValueError(
            "No estate is associated with this account."
        )

    return {
        "role": role,
        "estate_id": result[0]["estate_id"],
        "estate_name": result[0]["estate_name"],
        "scope": "current_estate",
    }
    
    
def plan_query(question, understanding, user_context):
    """
    Layer 2: Intent & Query Planning.

    Combines semantic understanding from Layer 1 with
    trusted authenticated-user context.

    This layer does NOT:
    - access Neo4j
    - generate Cypher
    - execute queries
    - calculate results

    It determines the intended query scope and carries
    forward the constraints required by Layer 3.
    """

    intent = understanding.get("intent", "general")
    entity = understanding.get("entity", "system")
    operation = understanding.get("operation", "find")
    filters = understanding.get("filters", {})

    if not isinstance(filters, dict):
        filters = {}

    role = user_context.get("role") if user_context else None
    estate_id = user_context.get("estate_id") if user_context else None
    estate_name = user_context.get("estate_name") if user_context else None

    plan = {
        "intent": intent,
        "entity": entity,
        "operation": operation,
        "filters": filters,
        "scope": "global",
        "estate_id": None,
        "estate_name": None,
    }

    # ==========================================================
    # ADMIN / DEVELOPER
    # ==========================================================

    if role == "admin":

        plan["scope"] = "all_estates"

        # If the user explicitly names an estate,
        # preserve it as a query filter.
        if filters.get("estate_name"):
            plan["estate_name"] = filters["estate_name"]

        print(">>> QUERY PLAN: ADMIN / GLOBAL <<<")
        print(plan)

        return plan

    # ==========================================================
    # NON-ADMIN USERS
    #
    # Managers and residents are restricted to their
    # authenticated estate.
    # ==========================================================

    if role in ("manager", "resident"):

        if not estate_id:
            raise ValueError(
                "No estate context is available for this account."
            )

        requested_estate = filters.get("estate_name")

        # ----------------------------------------------------------
        # EXPLICIT ESTATE REQUEST
        #
        # Non-admin users may only query their authenticated estate.
        # ----------------------------------------------------------

        if requested_estate:

            if requested_estate.strip().lower() != estate_name.strip().lower():

                print(">>> ESTATE ACCESS VIOLATION <<<")
                print(">>> REQUESTED ESTATE:", requested_estate)
                print(">>> USER ESTATE:", estate_name)

                raise PermissionError(
                    "You are not authorized to access this estate."
                )

        # ----------------------------------------------------------
        # AUTHENTICATED ESTATE CONTEXT
        # ----------------------------------------------------------

        plan["scope"] = "current_estate"
        plan["estate_id"] = estate_id
        plan["estate_name"] = estate_name

        print(">>> QUERY PLAN: CURRENT ESTATE <<<")
        print(plan)

        return plan

    # ==========================================================
    # UNKNOWN / INVALID ROLE
    # ==========================================================

    raise ValueError(
        "Unable to determine a valid query scope for this account."
    )
    
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_query_v3(request):
    question = request.data.get("question", "").strip()

    print("=" * 80)
    print("QUESTION RECEIVED:")
    print(repr(question))
    print("=" * 80)

    if not question:
        return Response(
            {"error": "Question cannot be empty."},
            status=400,
        )

    try:
        understanding = detect_ai_intent(question)

        print("=" * 80)
        print("SEMANTIC UNDERSTANDING:")
        print(understanding)
        print("=" * 80)

        user_context = resolve_user_estate(request.user)

        print("=" * 80)
        print("USER CONTEXT:")
        print(user_context)
        print("=" * 80)

        query_plan = plan_query(
            question,
            understanding,
            user_context,
        )

        intent = understanding["intent"]
        

        if user_context is None:
            return Response(
                {
                    "error": (
                        "Your account is not associated "
                        "with an estate."
                    )
                },
                status=403,
            )

        print("=" * 80)
        print("USER ESTATE CONTEXT:")
        print(user_context)
        print("=" * 80)

        query_question = question

        if intent == "operational_priorities":
            query_question = "What should I focus on today?"

        generation_context = {
            **user_context,
            "query_plan": query_plan,
        }

        generated = generate_cypher(
            query_question,
            context=generation_context, 
            semantic_understanding=understanding,
        )

        if isinstance(generated, tuple):
            cypher, parameters = generated
        else:
            cypher = generated
            parameters = {}

        if not isinstance(cypher, str) or not cypher.strip():
            return Response(
                {"error": "Unable to generate a valid database query."},
                status=502,
            )

        cypher = normalize_cypher(cypher)

        if cypher.strip() == 'RETURN "UNSUPPORTED_QUERY" AS error':
            return Response({
                "question": question,
                "response": (
                    "I'm sorry, I can only answer questions about "
                    "the Estate Intelligence System database."
                ),
                "data": [],
            })

        if not is_safe_cypher(cypher):
            return Response(
                {"error": "Unsafe Cypher generated."},
                status=400,
            )

        data = execute_cypher(cypher, parameters)

        print("=" * 80)
        print("QUERY RESULT:")
        print(data)
        print("=" * 80)

        analysis = analyze_results(
            question,
            data,
            intent,
            understanding["operation"],
            understanding["entity"],
        )

        print("=" * 80)
        print("AI ANALYSIS:")
        print(analysis)
        print("=" * 80)

        answer = analysis["analysis"]

        return Response({
            "question": question,
            "cypher": cypher,
            "response": answer,
            "analysis": analysis,
            "data": data,
        })

    except PermissionError as exc:
        print("=" * 80)
        print(">>> AI QUERY ACCESS DENIED <<<")
        print(repr(exc))
        print("=" * 80)

        return Response(
            {
                "error": str(exc),
            },
            status=403,
        )

    except Exception as exc:
        print("=" * 80)
        print(">>> AI QUERY ERROR <<<")
        print(repr(exc))
        print("=" * 80)

        return Response(
            {
                "error": "Unable to process the request right now.",
            },
            status=500,
        )
        

class ResidentOnlyView(APIView):
    permission_classes = [IsResident]

    def get(self, request):
        return Response({
            "message": "Welcome Resident!"
        })


class ManagerOnlyView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        return Response({
            "message": "Welcome Estate Manager!"
        })


class AdminOnlyView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "message": "Welcome Developer!"
        })


class ManagerAdminView(APIView):
    permission_classes = [IsManagerOrAdmin]

    def get(self, request):
        return Response({
            "message": "Manager/Admin Dashboard"
        })