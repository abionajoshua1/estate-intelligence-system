import re


def normalize_cypher(cypher: str) -> str:
    """
    Fix common LLM mistakes before sending Cypher to Neo4j.
    """

    replacements = {
        '"active"': '"Active"',
        "'active'": "'Active'",

        '"inactive"': '"Inactive"',
        "'inactive'": "'Inactive'",

        '"available"': '"Available"',
        "'available'": "'Available'",

        '"occupied"': '"Occupied"',
        "'occupied'": "'Occupied'",

        '"pending"': '"Pending"',
        "'pending'": "'Pending'",

        '"resolved"': '"Resolved"',
        "'resolved'": "'Resolved'",

        '"in progress"': '"In Progress"',
        "'in progress'": "'In Progress'",
    }

    for wrong, correct in replacements.items():
        cypher = cypher.replace(wrong, correct)

    return cypher