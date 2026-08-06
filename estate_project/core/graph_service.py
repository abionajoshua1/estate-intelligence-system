from .neo4j_connection import Neo4jConnection
from datetime import date, datetime
from neo4j.time import DateTime, Date, Time


def fetch_top_residents():

    db = Neo4jConnection()

    try:

        query = """
        MATCH (r:Resident)-[:RAISED]->(c:Complaint)

        RETURN
            r.name AS resident,
            COUNT(c) AS complaints

        ORDER BY complaints DESC
        """

        return db.query(query)

    finally:
        db.close()
        
def fetch_vacant_properties():

    db = Neo4jConnection()

    try:

        query = """
        MATCH (p:Property)

        WHERE p.status = "Available"

        RETURN
            p.property_number AS property_number,
            p.property_type AS property_type,
            p.bedrooms AS bedrooms,
            p.bathrooms AS bathrooms

        ORDER BY p.property_number
        """

        return db.query(query)

    finally:
        db.close()
        
def fetch_estate_managers():

    db = Neo4jConnection()

    try:

        query = """
        MATCH (m:Manager)

        RETURN
            m.name AS manager_name,
            m.email AS email,
            m.phone AS phone,
            m.status AS status

        ORDER BY m.name
        """

        return db.query(query)

    finally:
        db.close()
        
        
        
def fetch_maintenance_teams():

    db = Neo4jConnection()

    try:

        query = """
        MATCH (t:MaintenanceTeam)

        RETURN
            t.team_name AS team_name,
            t.specialization AS specialization,
            t.phone AS phone,
            t.email AS email

        ORDER BY t.team_name
        """

        return db.query(query)

    finally:
        db.close()
        
            
def fetch_all_residents():

    db = Neo4jConnection()

    try:

        query = """
        MATCH (r:Resident)

        RETURN
            r.name AS resident_name,
            r.gender AS gender,
            r.phone AS phone,
            r.email AS email,
            r.status AS status

        ORDER BY r.name
        """

        return db.query(query)

    finally:
        db.close()


def execute_cypher(query):
    db = Neo4jConnection()

    try:
        results = db.query(query)

        cleaned_results = []

        for record in results:
            cleaned_record = {}

            for key, value in record.items():

                if isinstance(value, (DateTime, Date, Time, datetime, date)):
                    cleaned_record[key] = str(value)

                else:
                    cleaned_record[key] = value

            cleaned_results.append(cleaned_record)

        return cleaned_results

    finally:
        db.close()