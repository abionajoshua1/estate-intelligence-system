#from django import db
import email

from django import db
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings
from .neo4j_connection import Neo4jConnection

from .ai_service import (
    ask_llm, 
    detect_ai_intent, 
    generate_cypher,
    explain_results,
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_properties(request):

    query = """
    MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)

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

    db = Neo4jConnection()

    try:
        properties = db.query(query)
    finally:
        db.close()

    return Response(properties)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_property(request):

    data = request.data

    property_number = data.get("property_number", "").strip()
    estate_id = data.get("estate_id", "").strip()
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
    MATCH (e:Estate {estate_id:$estate_id})

    CREATE (p:Property{
        property_id:$property_id,
        property_number:$property_number,
        property_type:$property_type,
        bedrooms:$bedrooms,
        bathrooms:$bathrooms,
        status:$status,
        created_at:datetime()
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
def update_property(request, property_id):

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
    
    data = request.data
    
    estate_id = data.get("estate_id", "").strip()
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
        db.close()
        return Response(
            {
                "error": "Estate not found."
            },
            status=404,
        )
    
    
    update_query = """
    MATCH (p:Property {property_id:$property_id})
    MATCH (newEstate:Estate {estate_id:$estate_id})
    
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

    resident_id = data.get("resident_id", "").strip()
    property_id = data.get("property_id", "").strip()

    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    category = data.get("category", "").strip()
    priority = data.get("priority", "").strip()

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
        db.close()
        return Response(
            {
                "error": "Resident not found."
            },
            status=404,
        )
    
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
        db.close()
        return Response(
            {
                "error": "Property not found."
            },
            status=404,
        )
    
    last_complaint_query = """
    MATCH (c:Complaint)
    RETURN c.complaint_id AS complaint_id
    ORDER BY complaint_id DESC
    LIMIT 1
    """

    last = db.query(last_complaint_query)

    if last:
        current_id = last[0]["complaint_id"]
        number = int(current_id.replace("C", ""))
        new_id = f"C{number + 1:03d}"
    else:
        new_id = "C001"

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
        }
    )

    db.close()

    return Response(
{
    "message": "Complaint created successfully.",
    "complaint": complaint[0]
},
status=201
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_complaints(request):

    query = """
    MATCH (r:Resident)-[:RAISED]->(c:Complaint)-[:ABOUT]->(p:Property)

    RETURN
        c.complaint_id AS complaint_id,
        r.name AS resident_name,
        p.property_number AS property_number,
        c.title AS title,
        c.description AS description,
        c.category AS category,
        c.priority AS priority,
        c.status AS status,
        toString(c.created_at) AS created_at

    ORDER BY c.created_at DESC
    """

    db = Neo4jConnection()

    try:
        complaints = db.query(query)
    finally:
        db.close()

    return Response(complaints)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_complaint(request, complaint_id):

    db = Neo4jConnection()

    query = """
    MATCH (c:Complaint {complaint_id: $complaint_id})

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
        query,
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

    data = request.data
    
    status_value = request.data.get("status", "").strip()

    allowed_status = [
        "Open",
        "In Progress",
        "Resolved",
    ]

    if status_value not in allowed_status:
        db.close()
        return Response(
            {
                "error": "Invalid complaint status."
            },
            status=400,
        )
    
    update_query = """
    MATCH (c:Complaint {complaint_id: $complaint_id})

    SET c.status = $status
    
    FOREACH (_ IN CASE WHEN $status = "Resolved" THEN [1] ELSE [] END |
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

    db.close()

    return Response(
    {
        "message": "Complaint updated successfully.",
        "complaint": updated[0]
    },
    status=200,
    )
    
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
def assign_property_to_resident(request):
    
    print("Assign Property to Resident API called.")

    data = request.data

    resident_id = data.get("resident_id", "").strip()
    property_id = data.get("property_id", "").strip()

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
        
        remove_existing_occupant_query = """
        MATCH (:Resident)-[rel:LIVES_IN]->(p:Property {property_id:$property_id})
        DELETE rel
        """

        db.query(
            remove_existing_occupant_query,
            {
                "property_id": property_id,
            },
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

        # Check if complaint is already linked to a property
        existing_relationship = """
        MATCH (c:Complaint {complaint_id:$complaint_id})-[r:ABOUT]->(:Property)
        RETURN r
        LIMIT 1
        """

        existing = db.query(
            existing_relationship,
            {
                "complaint_id": complaint_id
            }
        )

        if existing:
            return Response(
                {
                    "error": "Complaint is already assigned to a property."
                },
                status=400,
            )

        # Create relationship
        assign_query = """
        MATCH (c:Complaint {complaint_id:$complaint_id})
        MATCH (p:Property {property_id:$property_id})

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
@permission_classes([IsAuthenticated])
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
        MATCH (c:Complaint {complaint_id:$complaint_id})
        MATCH (t:MaintenanceTeam {team_id:$team_id})

        CREATE (c)-[:ASSIGNED_TO]->(t)
        
        SET c.status = "In Progress"

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS complaint_title,
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

        return Response(
            {
                "message": "Complaint assigned successfully.",
                "assignment": assignment[0],
            },
            status=201,
        )

    finally:
        db.close()
        

@api_view(["GET"])
def test_ai(request):

    answer = ask_llm(
        "Say hello in one sentence."
    )

    return Response({
        "response": answer
    })
    
def format_results(question: str, data):

    if not data:
        return "No matching records were found."

    q = question.lower()

    # ======================
    # ESTATES
    # ======================
    if "estate" in q:

        lines = []

        for row in data:
            estate_id = row.get("estate_id")
            estate_name = row.get("name") or row.get("estate_name")

            if estate_name:
                if estate_id:
                    lines.append(f"• {estate_name} ({estate_id})")
                else:
                    lines.append(f"• {estate_name}")

        return "Estates found:\n\n" + "\n".join(lines)

    # ======================
    # PROPERTIES
    # ======================
    if "property" in q:

        lines = []

        for row in data:
            
            property_number = (
                row.get("property_number")
                or row.get("p.property_number")
            )
            
            property_type = {
                row.get("property_type")
                or row.get("p.property_type")
            }
            
            status = (
                row.get("status")
                or row.get("p.status")
            )
            
            lines.append(
                f"• {property_number} - {property_type} {status}"
            )

        return "Properties:\n\n" + "\n".join(lines)

    # ======================
    # RESIDENTS
    # ======================
    if "resident" in q:

        lines = []

        for row in data:
            
            resident = (
                row.get("resident_name")
                or row.get("name")
                or row.get("r.name")
            )
            
            resident_id = (
                row.get("resident_id")
                or row.get("r.resident_id")
            )
            
            if resident_id:
                lines.append(f"• {resident} ({resident_id})")
            else:
                lines.append(f"• {resident}")
                
        return "Residents:\n\n" + "\n".join(lines)

    # ======================
    # COMPLAINTS
    # ======================
    if "complaint" in q:

        lines = []

        for row in data:
            
            title = (
                row.get("title")
                or row.get("c.title")
            )
            
            priority = (
                row.get("priority")
                or row.get("c.priority")
                or "Not specified"
            )
            
            status = (
                row.get("status")
                or row.get("c.status")

            )
            
            complaint_id = (
                row.get("complaint_id")
                or row.get("c.complaint_id")
            )

            lines.append(
                f"• {complaint_id}: {title} | {priority} | {status}"
            )

        return "Complaints:\n\n" + "\n".join(lines)

    return str(data)


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

    cypher = generate_cypher(question)
    
    
    cypher = normalize_cypher(cypher)
    
    if cypher.strip() == 'RETURN "UNSUPPORTED_QUERY" AS error':
        return Response({
            "question": question,
            "response": "I'm sorry, I can only answer questions about the Estate Intelligence System database.",
            "data": [],
        })
        
    if not is_safe_cypher(cypher):
        return Response(
            {"error": "Unsafe Cypher generated."},
            status=400,
        )

    data = execute_cypher(cypher)
    
    print("=" * 80)
    print("QUERY RESULT:")
    print(data)
    print("=" * 80)

    answer = format_results(question, data)

    return Response({
        "question": question,
        "cypher": cypher,
        "response": answer,
        "data": data,
    })
    

from dashboard.permissions import (
    IsResident,
    IsManager,
    IsAdmin,
    IsManagerOrAdmin,
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