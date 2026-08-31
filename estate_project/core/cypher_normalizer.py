import re


STATUS_VALUES = {
    "active": "Active",
    "inactive": "Inactive",
    "available": "Available",
    "occupied": "Occupied",
    "pending": "Pending",
    "resolved": "Resolved",
    "in progress": "In Progress",
    "open": "Open",
    "maintenance": "Maintenance",
}


def normalize_cypher(cypher: str) -> str:
    """
    Normalize known status literals produced by the LLM.

    Only quoted status values are changed. All other Cypher
    content is preserved.
    """

    if not isinstance(cypher, str):
        return cypher

    pattern = re.compile(
        r"""(["'])\s*(active|inactive|available|occupied|pending|resolved|in progress|open|maintenance)\s*\1""",
        re.IGNORECASE,
    )

    def replace_status(match):
        quote = match.group(1)
        value = STATUS_VALUES[match.group(2).lower()]
        return f"{quote}{value}{quote}"

    return pattern.sub(replace_status, cypher)