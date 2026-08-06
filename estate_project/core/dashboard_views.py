from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .neo4j_connection import Neo4jConnection

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .neo4j_connection import Neo4jConnection


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_overview(request):

    db = Neo4jConnection()

    try:

        resident_query = """
        MATCH (r:Resident)
        RETURN count(r) AS total_residents
        """

        resident_count = db.query(resident_query)
        total_residents = resident_count[0]["total_residents"]


        property_query = """
        MATCH (p:Property)
        RETURN count(p) AS total_properties
        """

        property_count = db.query(property_query)
        total_properties = property_count[0]["total_properties"]
        
        estate_query = """
        MATCH (e:Estate)
        RETURN count(e) AS total_estates
        """

        estate_count = db.query(estate_query)
        total_estates = estate_count[0]["total_estates"]


        available_query = """
        MATCH (p:Property)
        WHERE p.status = "Available"
        RETURN count(p) AS available_properties
        """

        available_count = db.query(available_query)
        available_properties = available_count[0]["available_properties"]


        occupied_query = """
        MATCH (p:Property)
        WHERE p.status = "Occupied"
        RETURN count(p) AS occupied_properties
        """

        occupied_count = db.query(occupied_query)
        occupied_properties = occupied_count[0]["occupied_properties"]


        maintenance_query = """
        MATCH (p:Property)
        WHERE p.status = "Maintenance"
        RETURN count(p) AS maintenance_properties
        """

        maintenance_count = db.query(maintenance_query)
        maintenance_properties = maintenance_count[0]["maintenance_properties"]


        complaint_query = """
        MATCH (c:Complaint)
        RETURN count(c) AS total_complaints
        """

        complaint_count = db.query(complaint_query)
        total_complaints = complaint_count[0]["total_complaints"]


        open_query = """
        MATCH (c:Complaint)
        WHERE c.status = "Open"
        RETURN count(c) AS open_complaints
        """

        open_count = db.query(open_query)
        open_complaints = open_count[0]["open_complaints"]


        in_progress_query = """
        MATCH (c:Complaint)
        WHERE c.status = "In Progress"
        RETURN count(c) AS in_progress_complaints
        """

        in_progress_count = db.query(in_progress_query)
        in_progress_complaints = in_progress_count[0]["in_progress_complaints"]


        resolved_query = """
        MATCH (c:Complaint)
        WHERE c.status = "Resolved"
        RETURN count(c) AS resolved_complaints
        """

        resolved_count = db.query(resolved_query)
        resolved_complaints = resolved_count[0]["resolved_complaints"]


        return Response({
            "total_residents": total_residents,
            "total_properties": total_properties,
            "available_properties": available_properties,
            "occupied_properties": occupied_properties,
            "maintenance_properties": maintenance_properties,
            "total_estates": total_estates,
            "total_complaints": total_complaints,
            "open_complaints": open_complaints,
            "in_progress_complaints": in_progress_complaints,
            "resolved_complaints": resolved_complaints,
        })

    finally:
        db.close()
        
        
        
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def complaints_by_category(request):

    db = Neo4jConnection()

    try:

        query = """
        MATCH (c:Complaint)

        RETURN
            c.category AS category,
            count(c) AS total

        ORDER BY total DESC
        """

        result = db.query(query)

        return Response(result)

    finally:
        db.close()
        
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def properties_by_status(request):

    db = Neo4jConnection()

    try:

        query = """
        MATCH (p:Property)

        RETURN
            p.status AS status,
            count(p) AS total

        ORDER BY total DESC
        """

        result = db.query(query)

        return Response(result)

    finally:
        db.close()
        
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def residents_with_most_complaints(request):

    db = Neo4jConnection()

    try:

        query = """
        MATCH (r:Resident)-[:RAISED]->(c:Complaint)

        RETURN
            r.resident_id AS resident_id,
            r.name AS resident_name,
            count(c) AS total_complaints

        ORDER BY total_complaints DESC
        """

        result = db.query(query)

        return Response(result)

    finally:
        db.close()
        
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def properties_with_most_complaints(request):

    db = Neo4jConnection()

    try:

        query = """
        MATCH (c:Complaint)-[:ABOUT]->(p:Property)

        RETURN
            p.property_id AS property_id,
            p.property_number AS property_number,
            p.property_type AS property_type,
            count(c) AS total_complaints

        ORDER BY total_complaints DESC
        """

        result = db.query(query)

        return Response(result)

    finally:
        db.close()
        
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recent_complaint_activity(request):

    db = Neo4jConnection()

    try:

        query = """
        MATCH (r:Resident)-[:RAISED]->(c:Complaint)-[:ABOUT]->(p:Property)

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS title,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            r.name AS resident_name,
            p.property_number AS property_number,
            toString(c.created_at) AS created_at

        ORDER BY c.created_at DESC
        LIMIT 5
        """

        result = db.query(query)

        return Response(result)

    finally:
        db.close()