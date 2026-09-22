from .graph_service import execute_cypher


class AuthorizationError(Exception):
    """Raised when a user is not authorized to access a resource."""
    pass


def get_authorization_context(user):
    """
    Resolve the authenticated user's authorization context.

    Admins have global access.
    Managers and residents are restricted to their assigned estate.
    """

    from .views import resolve_user_estate

    context = resolve_user_estate(user)

    if not context:
        raise AuthorizationError(
            "Unable to determine authorization context."
        )

    return context


def is_global_access(context):
    """Return True when the user has global system access."""
    return context.get("scope") == "global"


def authorize_estate(context, estate_id):
    """
    Verify that the requested estate is within the
    user's authorized scope.
    """

    if is_global_access(context):
        return True

    authorized_estate_id = context.get("estate_id")

    if not authorized_estate_id:
        raise AuthorizationError(
            "User has no authorized estate."
        )

    if authorized_estate_id != estate_id:
        raise AuthorizationError(
            "You are not authorized to access this estate."
        )

    return True

def get_resource_estate(resource_type, resource_id):
    """
    Resolve the estate that owns a Neo4j resource.

    Returns the estate_id or None if the resource
    does not exist / cannot be associated with an estate.
    """

    queries = {
        "property": """
            MATCH (e:Estate)-[:HAS_PROPERTY]->(
                p:Property {property_id: $resource_id}
            )
            RETURN e.estate_id AS estate_id
            LIMIT 1
        """,

        "resident": """
            MATCH (r:Resident {resident_id: $resource_id})
                  -[:LIVES_IN]->(p:Property)
                  <-[:HAS_PROPERTY]-(e:Estate)
            RETURN e.estate_id AS estate_id
            LIMIT 1
        """,

        "manager": """
            MATCH (e:Estate)-[:HAS_MANAGER]->(
                m:Manager {manager_id: $resource_id}
            )
            RETURN e.estate_id AS estate_id
            LIMIT 1
        """,

        "maintenance_team": """
            MATCH (e:Estate)-[:HAS_MAINTENANCE_TEAM]->(
                t:MaintenanceTeam {team_id: $resource_id}
            )
            RETURN e.estate_id AS estate_id
            LIMIT 1
        """,

        "complaint": """
            MATCH (c:Complaint {complaint_id: $resource_id})
                  -[:ABOUT]->(p:Property)
                  <-[:HAS_PROPERTY]-(e:Estate)
            RETURN e.estate_id AS estate_id
            LIMIT 1
        """,
    }

    query = queries.get(resource_type)

    if not query:
        raise ValueError(
            f"Unsupported resource type: {resource_type}"
        )

    result = execute_cypher(
        query,
        {"resource_id": resource_id},
    )

    if not result:
        return None

    return result[0]["estate_id"]

def authorize_resource(context, resource_type, resource_id):
    """
    Verify that a resource belongs to the user's
    authorized estate.

    Admins have global access.
    Managers/residents are restricted to their estate.
    """

    if is_global_access(context):
        return True

    resource_estate_id = get_resource_estate(
        resource_type,
        resource_id,
    )

    if not resource_estate_id:
        raise AuthorizationError(
            "Resource does not belong to an estate."
        )

    return authorize_estate(
        context,
        resource_estate_id,
    )