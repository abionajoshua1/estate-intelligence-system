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

def validate_ai_query_scope(
    query: str,
    parameters: dict,
    query_plan: dict,
) -> bool:
    """
    Validate that an AI-generated Cypher query respects
    the authenticated user's query scope.

    Admin/global queries may access all estates.

    Manager/resident current-estate queries must:
    - use the trusted estate_id
    - reference the trusted $estate_id parameter
    - not rely on a user-supplied estate name for authorization
    """

    query_plan = query_plan or {}
    parameters = parameters or {}

    query_scope = query_plan.get("scope")
    estate_id = query_plan.get("estate_id")

    # ----------------------------------------------------------
    # GLOBAL / ADMIN
    # ----------------------------------------------------------

    if query_scope in {"global", "all_estates"}:
        return True

    # ----------------------------------------------------------
    # CURRENT ESTATE
    # ----------------------------------------------------------

    if query_scope == "current_estate":
        if not estate_id:
            return False

        # The trusted estate_id must be supplied as a parameter.
        if parameters.get("estate_id") != estate_id:
            return False

        # Current-estate queries must reference the trusted
        # estate parameter.
        if not re.search(
            r"\$estate_id\b",
            query,
            re.IGNORECASE,
        ):
            return False

        return True

    # ----------------------------------------------------------
    # UNKNOWN SCOPE
    # ----------------------------------------------------------

    return False