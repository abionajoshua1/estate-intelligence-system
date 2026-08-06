'''from .neo4j import run_query

def get_dashboard_stats():
    residents_query = """
    MATCH (r:Resident)
    RETURN count(r) AS residents
    """

    properties_query = """
    MATCH (p:Property)
    RETURN count(p) AS properties
    """

    complaints_query = """
    MATCH (c:Complaint)
    RETURN count(c) AS complaints
    """

    open_complaints_query = """
    MATCH (c:Complaint {status:'open'})
    RETURN count(c) AS open_complaints
    """

    residents = run_query(residents_query)[0]["residents"]
    properties = run_query(properties_query)[0]["properties"]
    complaints = run_query(complaints_query)[0]["complaints"]
    open_complaints = run_query(open_complaints_query)[0]["open_complaints"]

    return {
        "residents": residents,
        "properties": properties,
        "complaints": complaints,
        "open_complaints": open_complaints,
    }'''

from .neo4j import run_query


def get_dashboard_stats():
    queries = {
        "residents": "MATCH (r:Resident) RETURN count(r) AS count",
        "properties": "MATCH (p:Property) RETURN count(p) AS count",
        "complaints": "MATCH (c:Complaint) RETURN count(c) AS count",
        "estates": "MATCH (e:Estate) RETURN count(e) AS count",
    }

    result = {}

    for key, query in queries.items():
        data = run_query(query)
        result[key] = data[0]["count"] if data else 0

    return result