import re

FORBIDDEN_KEYWORDS = [
    "CREATE",
    "MERGE",
    "DELETE",
    "DETACH",
    "SET",
    "REMOVE",
    "DROP",
    "CALL",
    "LOAD CSV",
]

ALLOWED_START = [
    "MATCH",
    "OPTIONAL MATCH",
]

def is_safe_cypher(query: str) -> bool:
    """
    Returns True only if the query appears to be read-only.
    """

    query = query.strip().upper()

    # Must begin with a read-only clause
    if not any(query.startswith(keyword) for keyword in ALLOWED_START):
        return False

    # Reject dangerous keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", query):
            return False

    return True