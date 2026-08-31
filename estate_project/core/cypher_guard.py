import re


# Cypher clauses that can modify, delete, or otherwise perform
# operations outside the read-only query scope of this application.
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
    "FOREACH",
    "START",
]

ALLOWED_START_PATTERN = re.compile(
    r"^(MATCH|OPTIONAL\s+MATCH)\b",
    re.IGNORECASE,
)


def is_safe_cypher(query: str) -> bool:
    """
    Returns True only for single, read-only Cypher statements
    beginning with MATCH or OPTIONAL MATCH.
    """

    if not isinstance(query, str):
        return False

    query = query.strip()

    if not query:
        return False

    # Reject multiple statements.
    if ";" in query.rstrip(";"):
        return False

    # Query must begin with a valid read-only clause.
    if not ALLOWED_START_PATTERN.match(query):
        return False

    upper_query = query.upper()

    # Reject dangerous Cypher clauses.
    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(pattern, upper_query):
            return False

    return True