from groq import Groq
from django.conf import settings
from .schema import GRAPH_SCHEMA

import re


client = Groq(
    api_key=settings.GROQ_API_KEY
)

def detect_ai_intent(question: str):
    """
    Layer 1: Natural Language Understanding.

    Converts the user's natural-language question into a structured
    semantic representation.

    This layer does NOT:
    - generate Cypher
    - access Neo4j
    - perform calculations
    - make operational decisions

    It only determines what the user means.
    """

    prompt = f"""
You are the Natural Language Understanding component
of an Estate Intelligence System.

Your job is to understand the meaning of the user's question.

DO NOT generate Cypher.
DO NOT answer the question.
DO NOT access the database.

Return ONLY valid JSON.

==================================================
SUPPORTED INTENTS
==================================================

operational_priorities
resident_property
residents_by_property
resident_by_estate
resident_count
estates
vacant_properties
estate_managers
maintenance_teams
open_complaints
pending_maintenance
properties_needing_attention
top_residents
top_properties
top_maintenance_teams
estate_overview
current_estate_state
property_manager
general

==================================================
SEMANTIC RULES
==================================================

Understand meaning rather than exact wording.

Semantically equivalent expressions must map
to the same intent.

For example:

"How many complaints are currently open?"
"How many complaints are unresolved?"
"How many complaints are still outstanding?"
"How many complaints haven't been resolved?"

All refer to:

intent = open_complaints
entity = complaint
filter status = Open

--------------------------------------------------

"What should I focus on today?"
"What needs my attention?"
"What should I handle first?"
"Which complaints should the manager deal with first?"
"What are the most urgent issues right now?"

All refer to:

intent = operational_priorities

--------------------------------------------------

"Who lives in Greenfield Estate?"
"Which residents are in Greenfield Estate?"
"Tell me the people living in Greenfield Estate."

All refer to residents associated with that estate.

--------------------------------------------------

CONTEXTUAL LOCATION REFERENCES:

When the authenticated user has a current estate
context, contextual location words refer to that
estate.

Examples include:

"Who lives here?"
"Who lives in this estate?"
"Who lives in my estate?"
"Who lives in the current estate?"
"Which residents are here?"
"List the residents here."
"Who lives where I live?"

When these questions are asking for residents,
they MUST be interpreted as:

intent = residents_by_estate

entity = resident

operation = list

The word "here", "this estate", "my estate",
"current estate", or "where I live" does NOT
represent a literal estate name.

Do not classify these questions as:

intent = general

The actual estate identity will be supplied later
by the authenticated user's estate context during
query planning.


--------------------------------------------------

IMPORTANT INTENT: RESIDENT PROPERTY LOOKUP

Questions asking where a specific resident lives MUST use:

intent = resident_property

entity = resident

operation = find

Extract the resident's name into:

"resident_name"

Examples:

"Where does John Doe live?"

MUST produce:

{{
    "intent": "resident_property",
    "entity": "resident",
    "operation": "find",
    "filters": {{
        "resident_name": "John Doe"
    }},
    "semantic_query": "Find the property and estate where John Doe lives"
}}

"Which property does John Doe live in?"

MUST produce:

{{
    "intent": "resident_property",
    "entity": "resident",
    "operation": "find",
    "filters": {{
        "resident_name": "John Doe"
    }},
    "semantic_query": "Find the property where John Doe lives"
}}

"What estate does John Doe live in?"

MUST produce:

{{
    "intent": "resident_property",
    "entity": "resident",
    "operation": "find",
    "filters": {{
        "resident_name": "John Doe"
    }},
    "semantic_query": "Find the estate where John Doe lives"
}}

Do NOT use:

resident_by_estate

residents_by_estate

residents_by_property

general

for these questions.

--------------------------------------------------

"Show me all electrical complaints."
"Which complaints are electrical?"
"Are there any complaints about electrical issues?"

All refer to:

entity = complaint
category = Electrical

==================================================
ENTITY VALUES
==================================================

Use one of:

estate
resident
property
complaint
maintenance_team
manager
system

==================================================
OPERATIONS
==================================================

Use one of:

count
list
find
rank
overview
status
prioritize

==================================================
FILTERS
==================================================

Extract meaningful filters when they are explicitly
or semantically implied by the question.

Possible filters include:

estate_name
resident_name
property_number
property_type
complaint_category
complaint_status
complaint_priority
maintenance_team
manager_name

For example:

"unresolved complaints"

means:

"complaint_status": "Open"

"electrical complaints"

means:

"complaint_category": "Electrical"

==================================================
OUTPUT FORMAT
==================================================

Return exactly this structure:

{{
    "intent": "...",
    "entity": "...",
    "operation": "...",
    "filters": {{}},
    "semantic_query": "..."
}}

The semantic_query should be a short normalized
description of what the user means.

==================================================
IMPORTANT
==================================================

Do not invent information.

If a value cannot be determined from the question,
leave it out of filters.

If the question is unrelated or genuinely ambiguous,
use:

"intent": "general"

==================================================
USER QUESTION
==================================================

{question}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict Natural Language "
                        "Understanding system. "
                        "Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
        )

        content = (
            response.choices[0].message.content
            or ""
        ).strip()

        print("=" * 80)
        print(">>> RAW SEMANTIC UNDERSTANDING <<<")
        print(content)
        print("=" * 80)

        # Remove accidental markdown fences if the model
        # adds them despite the instruction.
        content = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            content,
            flags=re.IGNORECASE,
        ).strip()

        import json

        understanding = json.loads(content)

        # --------------------------------------------------
        # Validate structure
        # --------------------------------------------------

        if not isinstance(understanding, dict):
            raise ValueError(
                "Semantic understanding must be a JSON object."
            )

        allowed_intents = {
            "operational_priorities",
            "resident_property",
            "residents_by_property",
            "residents_by_estate",
            "resident_count",
            "estates",
            "vacant_properties",
            "estate_managers",
            "maintenance_teams",
            "open_complaints",
            "pending_maintenance",
            "properties_needing_attention",
            "top_residents",
            "top_properties",
            "top_maintenance_teams",
            "estate_overview",
            "current_estate_state",
            "property_manager",
            "general",
        }

        allowed_entities = {
            "estate",
            "resident",
            "property",
            "complaint",
            "maintenance_team",
            "manager",
            "system",
        }

        allowed_operations = {
            "count",
            "list",
            "find",
            "rank",
            "overview",
            "status",
            "prioritize",
        }

        intent = understanding.get("intent", "general")
        entity = understanding.get("entity", "system")
        operation = understanding.get("operation", "find")
        filters = understanding.get("filters", {})
        semantic_query = understanding.get(
            "semantic_query",
            question,
        )

        if intent not in allowed_intents:
            intent = "general"

        if entity not in allowed_entities:
            entity = "system"

        if operation not in allowed_operations:
            operation = "find"

        if not isinstance(filters, dict):
            filters = {}

        result = {
            "intent": intent,
            "entity": entity,
            "operation": operation,
            "filters": filters,
            "semantic_query": semantic_query,
        }

        print("=" * 80)
        print(">>> SEMANTIC UNDERSTANDING <<<")
        print(result)
        print("=" * 80)

        return result

    except PermissionError as exc:
        print("=" * 80)
        print(">>> AI QUERY ACCESS DENIED <<<")
        print(repr(exc))
        print("=" * 80)

        return Response(
            {
                "error": str(exc),
            },
            status=403,
        )

    except Exception as exc:
        print("=" * 80)
        print(">>> AI QUERY ERROR <<<")
        print(repr(exc))
        print("=" * 80)

        return Response(
            {
                "error": "Unable to process the request right now.",
            },
            status=500,
        )
    

def ask_llm(prompt: str):
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": """
You are EstateGraph AI.

You answer questions about estates and housing.
Be concise and accurate.
"""
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        return (content or "").strip()

    except Exception as exc:
        print(">>> LLM ERROR:", exc)
        return ""


def generate_cypher(question: str, context=None, semantic_understanding=None,):

    context = context or {}
    
    semantic_understanding = semantic_understanding or {}

    intent = semantic_understanding.get("intent", "general")
    entity = semantic_understanding.get("entity", "system")
    operation = semantic_understanding.get("operation", "find")
    filters = semantic_understanding.get("filters", {})
    semantic_query = semantic_understanding.get(
        "semantic_query",
        question,
    )

    user_role = context.get("role")
    current_estate_id = context.get("estate_id")
    current_estate_name = context.get("estate_name")
    scope = context.get("scope")

    query_plan = context.get("query_plan") or {}

    query_scope = query_plan.get(
        "scope",
        scope
    )

    plan_estate_id = query_plan.get(
        "estate_id",
        current_estate_id
    )

    plan_estate_name = query_plan.get(
        "estate_name",
        current_estate_name
    )

    print(">>> QUERY CONTEXT <<<")
    print({
        "role": user_role,
        "estate_id": current_estate_id,
        "estate_name": current_estate_name,
        "scope": scope,
    })

    print(">>> QUERY PLAN CONTEXT <<<")
    print({
        "scope": query_scope,
        "estate_id": plan_estate_id,
        "estate_name": plan_estate_name,
    })

    q = question.lower().strip()
    
        # ==========================================================
    # ESTATE MANAGER
    #
    # Examples:
    # Who manages Greenfield Estate?
    # Who is the manager of Greenfield Estate?
    # Which estates have managers?
    # ==========================================================

    if intent == "estate_managers":

        estate_name = filters.get("estate_name")

        # ------------------------------------------------------
        # Specific estate
        # ------------------------------------------------------
        if estate_name:

            print(">>> ESTATE MANAGER QUERY USED <<<")
            print(">>> ESTATE:", estate_name)

            return (
                """
                MATCH (e:Estate)-[:HAS_MANAGER]->(m:Manager)

                WHERE toLower(trim(e.name)) =
                      toLower(trim($estate_name))

                RETURN
                    e.estate_id AS estate_id,
                    e.name AS estate_name,
                    m.manager_id AS manager_id,
                    m.name AS manager_name

                ORDER BY m.name
                """.strip(),
                {
                    "estate_name": estate_name
                },
            )

        # ------------------------------------------------------
        # All estates with managers
        # ------------------------------------------------------

        print(">>> ALL ESTATE MANAGERS QUERY USED <<<")

        return (
            """
            MATCH (e:Estate)-[:HAS_MANAGER]->(m:Manager)

            RETURN
                e.estate_id AS estate_id,
                e.name AS estate_name,
                m.manager_id AS manager_id,
                m.name AS manager_name

            ORDER BY e.name, m.name
            """.strip(),
            {},
        )

    # ==========================================================
    # RESIDENT PROPERTY
    #
    # Examples:
    # Where does John Doe live?
    # Where does Tunde live?
    # ==========================================================

    resident_property_match = re.search(
        r"where does (.+?) live\??$",
        question,
        re.IGNORECASE
    )

    if resident_property_match:

        resident_name = (
            resident_property_match.group(1)
            .strip()
            .rstrip("?.!")
            .strip()
        )

        print(">>> RESIDENT PROPERTY QUERY USED <<<")
        print(">>> RESIDENT:", resident_name)

        return (
            """
            MATCH (r:Resident)-[:LIVES_IN]->(p:Property)
                  <-[:HAS_PROPERTY]-(e:Estate)

            WHERE toLower(trim(r.name)) =
                  toLower(trim($resident_name))

            RETURN
                r.resident_id AS resident_id,
                r.name AS name,
                p.property_id AS property_id,
                p.property_number AS property_number,
                p.property_type AS property_type,
                e.estate_id AS estate_id,
                e.name AS estate_name

            ORDER BY r.name
            """.strip(),

            {
                "resident_name": resident_name
            },
        )


    # ==========================================================
    # RESIDENTS BY PROPERTY
    #
    # Examples:
    # Who lives in P001?
    # Who lives in property P001?
    # Who lives in A101?
    # Who lives in B201?
    # ==========================================================

    property_match = re.search(
        r"who lives in (?:property\s+)?(.+?)\??$",
        question,
        re.IGNORECASE
    )

    if property_match:

        property_identifier = (
            property_match.group(1)
            .strip()
            .rstrip("?.!")
            .strip()
        )

        # ------------------------------------------------------
        # Only treat actual property identifiers as properties.
        #
        # Examples:
        # P001
        # P002
        # A101
        # A102
        # B201
        # C301
        # TEST-001
        # ------------------------------------------------------

        if re.fullmatch(
            r"(?:P\d+|[A-Z]\d{3}|TEST-\d+)",
            property_identifier,
            re.IGNORECASE
        ):

            print(">>> RESIDENT BY PROPERTY QUERY USED <<<")
            print(
                ">>> PROPERTY IDENTIFIER:",
                property_identifier
            )

            return (
                """
                MATCH (r:Resident)-[:LIVES_IN]->(p:Property)

                WHERE
                    toLower(trim(p.property_id)) =
                    toLower(trim($property_number))

                    OR

                    toLower(trim(p.property_number)) =
                    toLower(trim($property_number))

                RETURN
                    r.resident_id AS resident_id,
                    r.name AS name,
                    p.property_id AS property_id,
                    p.property_number AS property_number,
                    p.property_type AS property_type

                ORDER BY r.name
                """.strip(),

                {
                    "property_number": property_identifier
                },
            )


    # ==========================================================
    # RESIDENTS BY ESTATE
    #
    # Examples:
    # Who lives in Greenfield Estate?
    # Who lives at Greenfield Estate?
    # Who lives in this estate?
    # Who lives here?
    # Which residents are in my estate?
    # List residents in this estate
    #
    # This handler relies on semantic intent + trusted
    # authenticated estate context.
    # ==========================================================

    if semantic_understanding.get("intent") == "residents_by_estate":

        print(">>> RESIDENTS BY ESTATE QUERY USED <<<")
        print(">>> QUERY SCOPE:", query_scope)
        print(">>> ESTATE ID:", plan_estate_id)
        print(">>> ESTATE NAME:", plan_estate_name)

        # ======================================================
        # CURRENT ESTATE SCOPE
        #
        # Resident asking:
        # "Who lives here?"
        # "Who lives in this estate?"
        # "Who lives in my estate?"
        #
        # The estate comes from authenticated user context.
        # ======================================================

        if query_scope == "current_estate":

            if not plan_estate_id:
                print(">>> MISSING ESTATE ID <<<")

                return 'RETURN "ESTATE_CONTEXT_REQUIRED" AS error'

            print(
                ">>> RESIDENTS BY CURRENT ESTATE "
                "QUERY USED <<<"
            )

            print(
                ">>> ESTATE ID:",
                plan_estate_id
            )

            print(
                ">>> ESTATE NAME:",
                plan_estate_name
            )

            return (
                """
                MATCH (r:Resident)-[:LIVES_IN]->(p:Property)
                    <-[:HAS_PROPERTY]-(e:Estate)

                WHERE e.estate_id = $estate_id

                RETURN
                    r.resident_id AS resident_id,
                    r.name AS name,
                    r.gender AS gender,
                    r.phone AS phone,
                    r.email AS email,
                    r.status AS status,
                    e.estate_id AS estate_id,
                    e.name AS estate_name

                ORDER BY r.name
                """.strip(),

                {
                    "estate_id": plan_estate_id
                },
            )

        # ======================================================
        # GLOBAL / ADMIN SCOPE
        #
        # Admin can explicitly query a named estate.
        #
        # Example:
        # "Who lives in Voera Estate?"
        # ======================================================

        if query_scope in {"global", "all_estates"}:

            estate_name = None

            if isinstance(semantic_understanding, dict):

                filters = semantic_understanding.get(
                    "filters",
                    {}
                )

                if isinstance(filters, dict):

                    estate_name = filters.get(
                        "estate_name"
                    )

            if not estate_name:
                estate_name = plan_estate_name

            if not estate_name:

                print(
                    ">>> ESTATE NAME REQUIRED FOR "
                    "GLOBAL ESTATE QUERY <<<"
                )

                return 'RETURN "ESTATE_CONTEXT_REQUIRED" AS error'

            print(
                ">>> ADMIN ESTATE QUERY <<<"
            )

            print(
                ">>> ESTATE NAME:",
                estate_name
            )

            return (
                """
                MATCH (r:Resident)-[:LIVES_IN]->(p:Property)
                    <-[:HAS_PROPERTY]-(e:Estate)

                WHERE toLower(trim(e.name)) =
                      toLower(trim($estate_name))

                RETURN
                    r.resident_id AS resident_id,
                    r.name AS name,
                    r.gender AS gender,
                    r.phone AS phone,
                    r.email AS email,
                    r.status AS status,
                    e.estate_id AS estate_id,
                    e.name AS estate_name

                ORDER BY r.name
                """.strip(),

                {
                    "estate_name": estate_name
                },
            )

        # ======================================================
        # UNKNOWN SCOPE
        # ======================================================

        print(
            ">>> UNSUPPORTED ESTATE QUERY SCOPE <<<"
        )

        return 'RETURN "UNSUPPORTED_QUERY" AS error'

    # ==========================================================
    # DOMAIN GUARD
    #
    # Prevent unrelated questions from reaching the LLM.
    # ==========================================================

    if not any(word in q for word in [
        "estate",
        "property",
        "properties",
        "resident",
        "residents",
        "complaint",
        "complaints",
        "maintenance",
        "overview",
        "priority",
        "priorities",
        "today",
        "pending",
        "open",
        "manager",
        "team",
        "teams",
    ]):

        print(">>> UNSUPPORTED QUERY <<<")

        return 'RETURN "UNSUPPORTED_QUERY" AS error'


    # ==========================================================
    # RESIDENT COUNT
    # ==========================================================

    if (
        "how many residents" in q
        or "resident count" in q
    ):

        print(">>> HARDCODED RESIDENT COUNT QUERY USED <<<")

        return """
        MATCH (r:Resident)

        RETURN
            COUNT(r) AS resident_count
        """.strip()


    # ==========================================================
    # ESTATES
    # ==========================================================

    if (
        "show all estates" in q
        or "list all estates" in q
        or "list every estate" in q
    ):

        print(">>> ESTATE LIST QUERY USED <<<")
        print(">>> QUERY SCOPE:", query_scope)
        print(">>> ESTATE ID:", plan_estate_id)
        print(">>> ESTATE NAME:", plan_estate_name)

        # ------------------------------------------------------
        # Admin / Developer - All Estates
        # ------------------------------------------------------

        if query_scope in ("global", "all_estates"):

            print(">>> GLOBAL ESTATE LIST QUERY USED <<<")

            return """
            MATCH (e:Estate)

            RETURN
                e.estate_id AS estate_id,
                e.name AS name

            ORDER BY e.name
            """.strip()

        # ------------------------------------------------------
        # Manager / Resident - Current Estate Only
        # ------------------------------------------------------

        if query_scope == "current_estate":

            if not plan_estate_id:
                print(">>> MISSING ESTATE ID <<<")

                return 'RETURN "ESTATE_CONTEXT_REQUIRED" AS error'

            print(">>> CURRENT ESTATE LIST QUERY USED <<<")

            return (
                """
                MATCH (e:Estate)

                WHERE e.estate_id = $estate_id

                RETURN
                    e.estate_id AS estate_id,
                    e.name AS name
                """.strip(),

                {
                    "estate_id": plan_estate_id
                },
            )

        print(">>> UNSUPPORTED ESTATE QUERY SCOPE <<<")

        return 'RETURN "UNSUPPORTED_QUERY" AS error'
    
    # ==========================================================
    # ESTATE RANKING
    # ==========================================================
    #
    # Examples:
    # Which estate has the most complaints?
    # Which estate has the highest number of complaints?
    # Which estates have the most complaints?
    #
    # Ranking is controlled by semantic understanding:
    #   intent    = estate_overview
    #   entity    = estate
    #   operation = rank
    #
    # Access scope is authoritative.
    # ==========================================================

    if (
        intent == "estate_overview"
        and entity == "estate"
        and operation == "rank"
    ):

        print(">>> ESTATE RANKING QUERY USED <<<")
        print(">>> QUERY SCOPE:", query_scope)
        print(">>> ESTATE ID:", plan_estate_id)
        print(">>> ESTATE NAME:", plan_estate_name)

        # ------------------------------------------------------
        # Resident / Manager - Current Estate
        # ------------------------------------------------------

        if query_scope == "current_estate":

            if not plan_estate_id:
                print(">>> MISSING ESTATE ID FOR ESTATE RANKING <<<")

                return 'RETURN "ESTATE_CONTEXT_REQUIRED" AS error'

            print(">>> ESTATE RANKING - SCOPED QUERY <<<")

            return (
                """
                MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)
                WHERE e.estate_id = $estate_id

                OPTIONAL MATCH (c:Complaint)-[:ABOUT]->(p)

                RETURN
                    e.estate_id AS estate_id,
                    e.name AS estate_name,
                    COUNT(DISTINCT c) AS complaint_count
                """.strip(),
                {
                    "estate_id": plan_estate_id
                },
            )

        # ------------------------------------------------------
        # Admin / Developer - Global Scope
        # ------------------------------------------------------

        if query_scope in ("global", "all_estates"):

            print(">>> ESTATE RANKING - GLOBAL QUERY <<<")

            return """
            MATCH (e:Estate)
            OPTIONAL MATCH (e)-[:HAS_PROPERTY]->(p:Property)
            OPTIONAL MATCH (c:Complaint)-[:ABOUT]->(p)

            RETURN
                e.estate_id AS estate_id,
                e.name AS estate_name,
                COUNT(DISTINCT c) AS complaint_count

            ORDER BY complaint_count DESC
            """.strip()

        # ------------------------------------------------------
        # Unsupported Scope
        # ------------------------------------------------------

        print(">>> UNSUPPORTED ESTATE RANKING SCOPE <<<")

        return 'RETURN "UNSUPPORTED_QUERY" AS error'
    

    # ==========================================================
    # ESTATE OVERVIEW
    # ==========================================================

    if (
        "estate overview" in q
        or "overview of the estate" in q
        or "overview of estate" in q
        or "give me an overview" in q
        or "estate situation" in q
    ):

        print(">>> ESTATE OVERVIEW QUERY USED <<<")
        print(">>> QUERY SCOPE:", query_scope)
        print(">>> ESTATE ID:", plan_estate_id)
        print(">>> ESTATE NAME:", plan_estate_name)

        # ------------------------------------------------------
        # Resident / Manager - Current Estate
        # ------------------------------------------------------

        if query_scope == "current_estate":

            if not plan_estate_id:
                print(">>> MISSING ESTATE ID <<<")

                return 'RETURN "ESTATE_CONTEXT_REQUIRED" AS error'

            print(">>> ESTATE OVERVIEW - SCOPED QUERY <<<")

            return (
                """
                MATCH (e:Estate)
                WHERE e.estate_id = $estate_id

                OPTIONAL MATCH (e)-[:HAS_PROPERTY]->(p:Property)

                WITH
                    e,
                    count(p) AS total_properties,
                    count(
                        CASE
                            WHEN p.status = "Available"
                            THEN 1
                        END
                    ) AS available_properties,
                    count(
                        CASE
                            WHEN p.status = "Occupied"
                            THEN 1
                        END
                    ) AS occupied_properties,
                    count(
                        CASE
                            WHEN p.status = "Maintenance"
                            THEN 1
                        END
                    ) AS maintenance_properties

                OPTIONAL MATCH (r:Resident)-[:LIVES_IN]->(p2:Property)
                    <-[:HAS_PROPERTY]-(e)

                WITH
                    e,
                    total_properties,
                    available_properties,
                    occupied_properties,
                    maintenance_properties,
                    count(DISTINCT r) AS total_residents

                OPTIONAL MATCH (c:Complaint)-[:ABOUT]->(p3:Property)
                    <-[:HAS_PROPERTY]-(e)

                RETURN
                    total_residents AS total_residents,
                    total_properties AS total_properties,
                    available_properties AS available_properties,
                    occupied_properties AS occupied_properties,
                    maintenance_properties AS maintenance_properties,

                    count(DISTINCT c) AS total_complaints,

                    count(
                        DISTINCT CASE
                            WHEN c.status = "Open"
                            THEN c
                        END
                    ) AS open_complaints,

                    count(
                        DISTINCT CASE
                            WHEN c.status = "In Progress"
                            THEN c
                        END
                    ) AS in_progress_complaints,

                    count(
                        DISTINCT CASE
                            WHEN c.status = "Resolved"
                            THEN c
                        END
                    ) AS resolved_complaints
                """.strip(),
                {
                    "estate_id": plan_estate_id
                },
            )

        # ------------------------------------------------------
        # Admin / Developer - Global Overview
        # ------------------------------------------------------

        if query_scope in ("global", "all_estates"):

            print(">>> ESTATE OVERVIEW - GLOBAL QUERY <<<")

            return """
            OPTIONAL MATCH (r:Resident)

            WITH
                count(DISTINCT r) AS total_residents

            OPTIONAL MATCH (p:Property)

            WITH
                total_residents,
                count(DISTINCT p) AS total_properties,

                count(
                    DISTINCT CASE
                        WHEN p.status = "Available"
                        THEN p
                    END
                ) AS available_properties,

                count(
                    DISTINCT CASE
                        WHEN p.status = "Occupied"
                        THEN p
                    END
                ) AS occupied_properties,

                count(
                    DISTINCT CASE
                        WHEN p.status = "Maintenance"
                        THEN p
                    END
                ) AS maintenance_properties

            OPTIONAL MATCH (c:Complaint)

            RETURN
                total_residents AS total_residents,
                total_properties AS total_properties,
                available_properties AS available_properties,
                occupied_properties AS occupied_properties,
                maintenance_properties AS maintenance_properties,

                count(DISTINCT c) AS total_complaints,

                count(
                    DISTINCT CASE
                        WHEN c.status = "Open"
                        THEN c
                    END
                ) AS open_complaints,

                count(
                    DISTINCT CASE
                        WHEN c.status = "In Progress"
                        THEN c
                    END
                ) AS in_progress_complaints,

                count(
                    DISTINCT CASE
                        WHEN c.status = "Resolved"
                        THEN c
                    END
                ) AS resolved_complaints
            """.strip()


    # ==========================================================
    # CURRENT ESTATE STATE
    # ==========================================================

    if (
        intent == "current_estate_state"
        and entity == "estate"
        and operation == "overview"
    ):

        print(">>> CURRENT ESTATE STATE QUERY USED <<<")
        print(">>> QUERY SCOPE:", query_scope)
        print(">>> ESTATE ID:", plan_estate_id)
        print(">>> ESTATE NAME:", plan_estate_name)

        # ------------------------------------------------------
        # Resident / Manager - Current Estate
        # ------------------------------------------------------

        if query_scope == "current_estate":

            if not plan_estate_id:
                print(">>> MISSING ESTATE ID <<<")

                return 'RETURN "UNSUPPORTED_QUERY" AS error'

            print(">>> CURRENT ESTATE STATE - SCOPED QUERY <<<")

            return (
                """
                MATCH (e:Estate)
                WHERE e.estate_id = $estate_id

                OPTIONAL MATCH (e)-[:HAS_PROPERTY]->(p:Property)

                WITH
                    e,
                    count(DISTINCT p) AS total_properties,

                    count(
                        DISTINCT CASE
                            WHEN p.status = "Available"
                            THEN p
                        END
                    ) AS available_properties,

                    count(
                        DISTINCT CASE
                            WHEN p.status = "Occupied"
                            THEN p
                        END
                    ) AS occupied_properties,

                    count(
                        DISTINCT CASE
                            WHEN p.status = "Maintenance"
                            THEN p
                        END
                    ) AS maintenance_properties

                OPTIONAL MATCH (r:Resident)-[:LIVES_IN]->(p2:Property)
                    <-[:HAS_PROPERTY]-(e)

                WITH
                    e,
                    total_properties,
                    available_properties,
                    occupied_properties,
                    maintenance_properties,
                    count(DISTINCT r) AS total_residents

                OPTIONAL MATCH (c:Complaint)-[:ABOUT]->(p3:Property)
                    <-[:HAS_PROPERTY]-(e)

                RETURN
                    e.estate_id AS estate_id,
                    e.name AS estate_name,

                    total_residents AS total_residents,
                    total_properties AS total_properties,
                    available_properties AS available_properties,
                    occupied_properties AS occupied_properties,
                    maintenance_properties AS maintenance_properties,

                    count(DISTINCT c) AS total_complaints,

                    count(
                        DISTINCT CASE
                            WHEN c.status = "Open"
                            THEN c
                        END
                    ) AS open_complaints,

                    count(
                        DISTINCT CASE
                            WHEN c.status = "In Progress"
                            THEN c
                        END
                    ) AS in_progress_complaints,

                    count(
                        DISTINCT CASE
                            WHEN c.status = "Resolved"
                            THEN c
                        END
                    ) AS resolved_complaints
                """.strip(),

                {
                    "estate_id": plan_estate_id
                },
            )

        # ------------------------------------------------------
        # Admin / Developer - All Estates
        # ------------------------------------------------------

        if query_scope in ("global", "all_estates"):

            print(">>> GLOBAL ESTATE STATE QUERY USED <<<")

            return """
            MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)

            RETURN
                e.estate_id AS estate_id,
                e.name AS estate_name,
                p.property_id AS property_id,
                p.property_number AS property_number,
                p.property_type AS property_type,
                p.status AS property_status

            ORDER BY
                e.name,
                p.property_number
            """.strip()


    # ==========================================================
    # PROPERTIES NEEDING ATTENTION
    # ==========================================================

    if (
        "what properties need attention" in q
        or "which properties need attention" in q
        or "properties that need attention" in q
        or "properties needing attention" in q
    ):

        print(">>> PROPERTIES NEEDING ATTENTION QUERY USED <<<")

        return """
        MATCH (p:Property)<-[:ABOUT]-(c:Complaint)

        WHERE c.status IN ["Open", "In Progress"]

        RETURN
            p.property_id AS property_id,
            p.property_number AS property_number,
            p.property_type AS property_type,
            p.status AS status,
            COUNT(c) AS complaint_count

        ORDER BY
            complaint_count DESC,
            p.property_number
        """.strip()


    # ==========================================================
    # PENDING MAINTENANCE
    # ==========================================================

    if (
        "pending maintenance" in q
        or "maintenance issues are pending" in q
        or "maintenance issue is pending" in q
        or "maintenance is pending" in q
        or "pending maintenance issues" in q
        or "pending maintenance problem" in q
        or "pending maintenance problems" in q
        or "maintenance problems are still open" in q
        or "maintenance issues are still open" in q
        or (
            "maintenance" in q
            and "pending" in q
        )
    ):

        print(">>> PENDING MAINTENANCE QUERY USED <<<")

        return """
        MATCH (c:Complaint)-[:ASSIGNED_TO]->(t:MaintenanceTeam)

        WHERE c.status = "Open"

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS title,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            t.team_name AS team

        ORDER BY complaint_id
        """.strip()


    # ==========================================================
    # OPEN COMPLAINTS
    # ==========================================================

    if (
        (
            "open complaints" in q
            or "complaints that are open" in q
            or "currently open complaints" in q
            or "unresolved complaints" in q
            or "unresolved complaint" in q
            or "outstanding complaints" in q
            or "outstanding complaint" in q
        )
        and "assigned" not in q
        and "maintenance team" not in q
    ):

        print(">>> OPEN COMPLAINTS QUERY USED <<<")

        return """
        MATCH (c:Complaint)

        WHERE c.status = "Open"

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS title,
            c.category AS category,
            c.priority AS priority,
            c.status AS status

        ORDER BY complaint_id
        """.strip()


    # ==========================================================
    # TODAY'S PRIORITIES
    # ==========================================================

    if (
        "today's priorities" in q
        or "todays priorities" in q
        or "current priorities" in q
        or "issues that need attention" in q
        or "what should i deal with first" in q
        or "what should i focus on today" in q
        or "focus on today" in q
        or "what needs attention today" in q
    ):

        print(">>> PRIORITIES QUERY USED <<<")

        return """
        MATCH (c:Complaint)

        WHERE c.status IN ["Open", "In Progress"]

        OPTIONAL MATCH (c)-[:ASSIGNED_TO]->(t:MaintenanceTeam)

        RETURN
            c.complaint_id AS complaint_id,
            c.title AS title,
            c.category AS category,
            c.priority AS priority,
            c.status AS status,
            t.team_name AS team

        ORDER BY

            CASE c.priority
                WHEN "High" THEN 1
                WHEN "Medium" THEN 2
                WHEN "Low" THEN 3
                ELSE 4
            END,

            CASE c.status
                WHEN "Open" THEN 1
                WHEN "In Progress" THEN 2
                ELSE 3
            END
        """.strip()


    # ==========================================================
    # MANAGER INSIGHTS
    # ==========================================================

    # ----------------------------------------------------------
    # Residents with the most complaints
    # ----------------------------------------------------------

    if (
        "residents" in q
        and "most complaints" in q
    ):

        print(">>> TOP RESIDENTS QUERY USED <<<")

        return """
        MATCH (r:Resident)-[:RAISED]->(c:Complaint)

        RETURN
            r.name AS resident,
            COUNT(c) AS complaint_count

        ORDER BY complaint_count DESC
        """.strip()


    # ----------------------------------------------------------
    # Properties with the most complaints
    # ----------------------------------------------------------

    if (
        "properties" in q
        and "most complaints" in q
    ):

        print(">>> TOP PROPERTIES QUERY USED <<<")

        return """
        MATCH (c:Complaint)-[:ABOUT]->(p:Property)

        RETURN
            p.property_number AS property_number,
            COUNT(c) AS complaint_count

        ORDER BY complaint_count DESC
        """.strip()


    # ----------------------------------------------------------
    # Maintenance teams handling the most complaints
    # ----------------------------------------------------------

    if (
        "maintenance teams" in q
        and "most complaints" in q
    ):

        print(">>> TOP MAINTENANCE TEAMS QUERY USED <<<")

        return """
        MATCH (c:Complaint)-[:ASSIGNED_TO]->(t:MaintenanceTeam)

        RETURN
            t.team_name AS team,
            COUNT(c) AS complaint_count

        ORDER BY complaint_count DESC
        """.strip()
        
    # ==========================================================
    # PROPERTY MANAGER
    #
    # Example:
    # Who manages the property where John Doe lives?
    # ==========================================================

    manager_match = re.search(
        r"property where (.+?) lives\??$",
        question,
        re.IGNORECASE
    )

    if manager_match and "who manages" in q:

        resident_name = (
            manager_match.group(1)
            .strip()
            .rstrip("?.!")
            .strip()
        )

        print(">>> PROPERTY MANAGER QUERY USED <<<")
        print(">>> RESIDENT:", resident_name)

        return (
            """
            MATCH (r:Resident {name: $resident_name})
                -[:LIVES_IN]->(p:Property)
                <-[:HAS_PROPERTY]-(e:Estate)
                -[:HAS_MANAGER]->(m:Manager)

            RETURN
                m.manager_id AS manager_id,
                m.name AS manager_name
            """.strip(),

            {
                "resident_name": resident_name
            },
        )
        
    # ==========================================================
    # ESTATE MANAGER
    #
    # Examples:
    # Who manages Greenfield Estate?
    # Who is the manager of Greenfield Estate?
    # Which manager manages Greenfield Estate?
    # ==========================================================

    estate_manager_match = re.search(
        r"(?:who manages|who is the manager of|which manager manages)"
        r"\s+(.+?)\??$",
        question,
        re.IGNORECASE
    )

    if estate_manager_match:

        estate_name = (
            estate_manager_match.group(1)
            .strip()
            .rstrip("?.!")
            .strip()
        )

        print(">>> ESTATE MANAGER QUERY USED <<<")
        print(">>> ESTATE:", estate_name)

        return (
            """
            MATCH (e:Estate)-[:HAS_MANAGER]->(m:Manager)

            WHERE toLower(trim(e.name)) =
                toLower(trim($estate_name))

            RETURN
                m.manager_id AS manager_id,
                m.name AS manager_name,
                e.estate_id AS estate_id,
                e.name AS estate_name

            ORDER BY manager_name
            """.strip(),
            {
                "estate_name": estate_name
            },
        )



    # ==========================================================
    # LLM FALLBACK
    # ==========================================================

    prompt = f"""
You are an expert Neo4j Cypher generator.

Your task is to convert natural language into Cypher.

==================================================
DATABASE SCHEMA
==================================================

{GRAPH_SCHEMA}

==================================================
RULES
==================================================

1. Return ONLY Cypher.

2. Never explain anything.

3. Never use markdown.

4. Never use code fences.

5. Never use CREATE.

6. Never use DELETE.

7. Never use MERGE.

8. Never use SET.

9. Never use REMOVE.

10. Never use DROP.

11. Use ONLY labels, relationships and properties
    that exist in the provided schema.

12. Traverse relationships whenever necessary.

13. Every expression inside RETURN must have
    an alias using AS.

Correct:

RETURN
r.resident_id AS resident_id,
r.name AS name,
r.status AS status

Incorrect:

RETURN
r.resident_id,
r.name,
r.status

14. Alias names MUST NEVER contain dots.

Correct:

AS resident_id
AS property_number
AS complaint_id
AS complaints

Incorrect:

AS r.name
AS p.property_number
AS c.title

15. Prefer MATCH over OPTIONAL MATCH.

16. If the answer cannot be generated from the schema,
    return:

RETURN "UNSUPPORTED_QUERY" AS error

17. QUERY SCOPE AND ACCESS CONTROL

The QUERY CONTEXT supplied with this prompt is authoritative.

If scope is "current_estate":
- The query MUST only return data belonging to the authenticated estate.
- Use the supplied estate_id parameter to constrain estate-owned data.
- Never query all estates, residents, properties, complaints, or maintenance
  records without applying the authenticated estate restriction.
- Never allow the user's requested estate name to override the authenticated
  estate_id.
- Do not invent or change the estate_id.

For estate-owned properties, prefer:

MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)
WHERE e.estate_id = $estate_id

Then apply additional filters.

For example, for available properties:

MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)
WHERE e.estate_id = $estate_id
  AND p.status = "Available"

RETURN
p.property_number AS property_number,
p.property_type AS property_type,
p.status AS status

==================================================
EXAMPLES
==================================================

Question:
How many residents are registered?

Cypher:

MATCH (r:Resident)

RETURN
COUNT(r) AS resident_count


Question:
Which residents live in Greenfield Estate?

Cypher:

MATCH (r:Resident)-[:LIVES_IN]->(p:Property)
      <-[:HAS_PROPERTY]-(e:Estate)

WHERE e.name = "Greenfield Estate"

RETURN
r.resident_id AS resident_id,
r.name AS name

ORDER BY r.name


Question:
Which resident has reported the most complaints?

Cypher:

MATCH (r:Resident)-[:RAISED]->(c:Complaint)

RETURN
r.name AS resident,
COUNT(c) AS complaints

ORDER BY complaints DESC

LIMIT 1


Question:
Who manages the property where John Doe lives?

Cypher:

MATCH (r:Resident {{name:"John Doe"}})
      -[:LIVES_IN]->(p:Property)
      -[:MANAGED_BY]->(m:Manager)

RETURN
m.manager_id AS manager_id,
m.name AS manager_name


Question:
Which team is handling Tunde's complaint?

Cypher:

MATCH (r:Resident {{name:"Tunde"}})
      -[:RAISED]->(c:Complaint)
      -[:ASSIGNED_TO]->(t:MaintenanceTeam)

RETURN
t.team_name AS team


Question:
Which properties are available?

Cypher:

MATCH (p:Property)

WHERE p.status = "Available"

RETURN
p.property_number AS property_number,
p.property_type AS property_type,
p.status AS status


Question:
List every resident.

Cypher:

MATCH (r:Resident)

RETURN
r.resident_id AS resident_id,
r.name AS name,
r.gender AS gender,
r.phone AS phone,
r.email AS email,
r.status AS status

ORDER BY r.name


Question:
List every estate.

Cypher:

MATCH (e:Estate)

RETURN
e.estate_id AS estate_id,
e.name AS name

ORDER BY e.name


Question:
Show all complaints.

Cypher:

MATCH (c:Complaint)

RETURN
c.complaint_id AS complaint_id,
c.title AS title,
c.priority AS priority,
c.status AS status

ORDER BY complaint_id

==================================================
USER QUESTION
==================================================

{question}
"""

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict Neo4j Cypher "
                        "generation system. "
                        "Return only valid Cypher."
                    ),
                },

                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            temperature=0,
        )

        cypher = (
            response.choices[0].message.content
            or ""
        ).strip()

        # ------------------------------------------------------
        # Remove accidental markdown code fences.
        # ------------------------------------------------------

        cypher = re.sub(
            r"^```(?:cypher|neo4j)?\s*|\s*```$",
            "",
            cypher,
            flags=re.IGNORECASE,
        ).strip()

        print("=" * 80)
        print(">>> AI GENERATED CYPHER <<<")
        print(cypher)
        print("=" * 80)

        return cypher

    except Exception as exc:

        print("=" * 80)
        print(">>> CYPHER GENERATION ERROR <<<")
        print(repr(exc))
        print("=" * 80)

        return 'RETURN "UNSUPPORTED_QUERY" AS error'

def analyze_results(question: str, data, intent=None, operation=None, entity=None):   
        
    """
    Deterministic semantic reasoning layer.

    Responsibilities:
    1. Interpret structured Neo4j results.
    2. Produce a direct human-readable answer.
    3. Provide supporting insights and reasoning.
    4. Never invent information that is not present in Neo4j results.

    Pipeline position:

        Natural Language
              ↓
        Semantic Understanding
              ↓
        Cypher Generation
              ↓
        Neo4j
              ↓
        Structured Results
              ↓
        analyze_results()
              ↓
        Human-readable Answer
    """

    # ==========================================================
    # NO DATA
    # ==========================================================

    if not data:

        return {
            "analysis": "No matching records were found.",
            "insights": [],
            "reasoning": [
                "Neo4j returned no records for the interpreted query."
            ],
            "actions": [],
            "data": [],
        }

    q = str(question or "").strip().lower()
    
    # ==========================================================
    # DETERMINISTIC OUTPUT CONTAINERS
    # ==========================================================
    #
    # Shared across reasoning branches.
    # ==========================================================

    insights = []
    reasoning = []
    actions = []
    

    # ==========================================================
    # HELPER FUNCTIONS
    # ==========================================================

    def pluralize(word, count):
        if count == 1:
            return word

        irregular_plurals = {
            "property": "properties",
            "facility": "facilities",
            "category": "categories",
            "activity": "activities",
            "complaint": "complaints",
            "resident": "residents",
            "estate": "estates",
            "manager": "managers",
            "team": "teams",
            "record": "records",
        }

        return irregular_plurals.get(
            word.lower(),
            f"{word}s"
        )

    def join_names(names):
        names = [str(name) for name in names if name]

        if not names:
            return ""

        if len(names) == 1:
            return names[0]

        if len(names) == 2:
            return f"{names[0]} and {names[1]}"

        return f"{', '.join(names[:-1])}, and {names[-1]}"

    def get_first_value(row, *keys):
        for key in keys:
            value = row.get(key)

            if value is not None and str(value).strip():
                return value

        return None

    # ==========================================================
    # DETERMINISTIC REASONING ENGINE
    #
    # Interprets measurable signals already returned by Neo4j.
    #
    # IMPORTANT:
    # - Uses only available structured data.
    # - Does not query Neo4j.
    # - Does not call the LLM.
    # - Does not invent missing information.
    # - Produces semantic assessments from measurable values.
    # ==========================================================

    def deterministic_reasoning(row):
        reasoning = []
        insights = []
        actions = []

        # ------------------------------------------------------
        # OCCUPANCY ANALYSIS
        # ------------------------------------------------------

        total_properties = int(
            row.get("total_properties") or 0
        )

        occupied_properties = int(
            row.get("occupied_properties") or 0
        )

        available_properties = int(
            row.get("available_properties") or 0
        )

        maintenance_properties = int(
            row.get("maintenance_properties") or 0
        )

        if total_properties > 0:

            occupancy_rate = (
                occupied_properties / total_properties
            ) * 100

            if occupancy_rate >= 100:
                occupancy_status = "full occupancy"

            elif occupancy_rate >= 80:
                occupancy_status = "high occupancy"

            elif occupancy_rate > 50:
                occupancy_status = "moderate occupancy"

            elif occupancy_rate > 0:
                occupancy_status = "low occupancy"

            else:
                occupancy_status = "no occupancy"

            reasoning.append(
                f"Property occupancy is {occupancy_rate:.0f}% "
                f"({occupied_properties} of "
                f"{total_properties} properties occupied)."
            )

            insights.append(
                f"The estate has {occupancy_status}."
            )

        # ------------------------------------------------------
        # COMPLAINT WORKLOAD ANALYSIS
        # ------------------------------------------------------

        total_complaints = int(
            row.get("total_complaints") or 0
        )

        open_complaints = int(
            row.get("open_complaints") or 0
        )

        in_progress_complaints = int(
            row.get("in_progress_complaints") or 0
        )

        resolved_complaints = int(
            row.get("resolved_complaints") or 0
        )
                

        active_complaints = (
            open_complaints +
            in_progress_complaints
        )

        if total_complaints > 0:

            active_rate = (
                active_complaints /
                total_complaints
            ) * 100

            resolution_rate = (
                resolved_complaints /
                total_complaints
            ) * 100

            reasoning.append(
                f"{active_complaints} of "
                f"{total_complaints} complaints "
                f"remain active "
                f"({active_rate:.0f}%)."
            )

            if active_rate >= 75:
                complaint_status = "high"

            elif active_rate >= 50:
                complaint_status = "moderate"

            elif active_rate > 0:
                complaint_status = "low"

            else:
                complaint_status = "no active"

            insights.append(
                f"The estate has a {complaint_status} "
                f"active complaint workload."
            )

            insights.append(
                f"{resolution_rate:.0f}% of complaints "
                f"have been resolved."
            )

            if active_complaints > 0:

                actions.append({
                    "type": "attention",
                    "reason": (
                        "Active complaints should be reviewed "
                        "and resolved."
                    ),
                    "count": active_complaints,
                })

        # ------------------------------------------------------
        # PROPERTY MAINTENANCE STATE
        #
        # This deliberately refers only to properties whose
        # status is explicitly marked as Maintenance.
        # It does NOT claim that there are no maintenance
        # complaints.
        # ------------------------------------------------------

        if total_properties > 0:

            if maintenance_properties > 0:

                maintenance_rate = (
                    maintenance_properties /
                    total_properties
                ) * 100

                reasoning.append(
                    f"{maintenance_properties} of "
                    f"{total_properties} properties "
                    f"are marked as under maintenance "
                    f"({maintenance_rate:.0f}%)."
                )

                insights.append(
                    f"{maintenance_properties} "
                    f"{pluralize('property', maintenance_properties)} "
                    f"are currently under maintenance."
                )

            else:

                reasoning.append(
                    "No properties are currently marked "
                    "as being under maintenance."
                )

        # ------------------------------------------------------
        # ESTATE HEALTH / STATUS
        #
        # This is a deterministic classification based only
        # on measurable occupancy and complaint workload.
        # ------------------------------------------------------

        estate_status = "stable"

        if (
            total_complaints > 0
            and active_complaints / total_complaints >= 0.75
        ):
            estate_status = "needs attention"

        elif (
            total_properties > 0
            and occupied_properties / total_properties >= 0.80
            and active_complaints > 0
        ):
            estate_status = "needs monitoring"

        elif active_complaints == 0:
            estate_status = "stable"

        insights.append(
            f"Overall estate status: {estate_status}."
        )

        reasoning.append(
            "The overall estate status was determined "
            "from the available occupancy and complaint "
            "workload indicators."
        )

        # ------------------------------------------------------
        # ESTATE-LEVEL ACTION
        # ------------------------------------------------------

        if estate_status == "needs attention":

            actions.append({
                "type": "priority",
                "reason": (
                    "The proportion of active complaints "
                    "is high and should be addressed."
                ),
                "count": active_complaints,
            })

        elif estate_status == "needs monitoring":

            actions.append({
                "type": "monitor",
                "reason": (
                    "The estate has high occupancy with "
                    "active complaints and should be monitored."
                ),
                "count": active_complaints,
            })

        return {
            "insights": insights,
            "reasoning": reasoning,
            "actions": actions,
            "estate_status": estate_status,
        }
    
    # ==========================================================
    # CURRENT ESTATE STATE
    # ==========================================================
    
    if intent == "current_estate_state" and len(data) == 1:

        row = data[0]

        deterministic = deterministic_reasoning(row)

        total_residents = int(
            row.get("total_residents") or 0
        )

        total_properties = int(
            row.get("total_properties") or 0
        )

        available_properties = int(
            row.get("available_properties") or 0
        )

        occupied_properties = int(
            row.get("occupied_properties") or 0
        )

        maintenance_properties = int(
            row.get("maintenance_properties") or 0
        )

        total_complaints = int(
            row.get("total_complaints") or 0
        )

        open_complaints = int(
            row.get("open_complaints") or 0
        )

        in_progress_complaints = int(
            row.get("in_progress_complaints") or 0
        )

        resolved_complaints = int(
            row.get("resolved_complaints") or 0
        )

        insights = deterministic["insights"]
        reasoning = deterministic["reasoning"]
        actions = deterministic["actions"]
        estate_status = deterministic["estate_status"]

        estate_name = get_first_value(
            row,
            "estate_name",
            "estate",
        )

        if estate_name:
            opening = f"{estate_name} currently has"
        else:
            opening = "The estate currently has"

        analysis = (
            f"{opening} {total_residents} "
            f"{pluralize('resident', total_residents)} across "
            f"{total_properties} "
            f"{pluralize('property', total_properties)}. "
            f"{occupied_properties} "
            f"{pluralize('property', occupied_properties)} "
            f"are occupied, "
            f"{available_properties} "
            f"{pluralize('property', available_properties)} "
            f"are available, and "
            f"{maintenance_properties} "
            f"{pluralize('property', maintenance_properties)} "
            f"are under maintenance. "
            f"There are {total_complaints} "
            f"{pluralize('complaint', total_complaints)}, "
            f"with {open_complaints} open, "
            f"{in_progress_complaints} in progress, "
            f"and {resolved_complaints} resolved. "
            f"Overall estate status: {estate_status}."
        )

        return {
            "analysis": analysis,
            "insights": insights,
            "reasoning": reasoning,
            "actions": actions,
            "estate_status": estate_status,
            "data": data,
        }

    # ==========================================================
    # RESIDENT -> PROPERTY
    #
    # Example:
    # Where does John Doe live?
    # ==========================================================

    if intent == "resident_property":

        row = data[0]

        resident_name = get_first_value(
            row,
            "name",
            "resident",
            "resident_name",
        )

        property_number = get_first_value(
            row,
            "property_number",
            "property",
        )

        property_type = get_first_value(
            row,
            "property_type",
        )

        estate_name = get_first_value(
            row,
            "estate_name",
            "estate",
        )

        if not property_number:

            return {
                "analysis": (
                    f"The property where "
                    f"{resident_name or 'the resident'} lives "
                    "could not be identified."
                ),
                "insights": [],
                "reasoning": [
                    "The resident was found, but no property identifier "
                    "was returned by Neo4j."
                ],
                "actions": [],
                "data": data,
            }

        analysis = (
            f"{resident_name or 'The resident'} lives in "
            f"property {property_number}"
        )

        if property_type:
            analysis += f", a {str(property_type).lower()}"

        if estate_name:
            analysis += f" in {estate_name}"

        analysis += "."

        return {
            "analysis": analysis,
            "insights": [],
            "reasoning": [
                "The resident's property was identified by following "
                "the LIVES_IN relationship from the Resident node "
                "to the Property node."
            ],
            "actions": [],
            "data": data,
        }

    # ==========================================================
    # PROPERTY -> RESIDENTS
    #
    # Examples:
    # Who lives in P001?
    # Who lives in A101?
    # Who lives in property P001?
    # ==========================================================

    if intent == "residents_by_property":

        names = [
            get_first_value(
                row,
                "name",
                "resident",
                "resident_name",
            )
            for row in data
        ]

        names = [
            name for name in names
            if name
        ]

        property_number = get_first_value(
            data[0],
            "property_number",
            "property",
        )

        if names:

            if len(names) == 1:

                analysis = (
                    f"{names[0]} lives in property "
                    f"{property_number or 'the specified property'}."
                )

            else:

                analysis = (
                    f"{join_names(names)} live in property "
                    f"{property_number or 'the specified property'}."
                )

        else:

            analysis = (
                f"No residents were found for property "
                f"{property_number or 'the specified property'}."
            )

        return {
            "analysis": analysis,
            "insights": [
                f"{len(names)} resident(s) are associated with "
                "the specified property."
            ],
            "reasoning": [
                "The residents were identified by following the "
                "LIVES_IN relationship between Resident and Property nodes."
            ],
            "actions": [],
            "data": data,
        }

    # ----------------------------------------------------------
    # RESIDENTS -> ESTATE
    #
    # Examples:
    # Who lives in Greenfield Estate?
    # Which residents are in Greenfield Estate?
    # ----------------------------------------------------------

    if intent == "residents_by_estate":

        names = [
            row.get("name")
            for row in data
            if row.get("name")
        ]

        estate_name = (
            data[0].get("estate_name")
            if data
            else None
        )

        if names:

            if len(names) == 1:
                analysis = (
                    f"{names[0]} lives in "
                    f"{estate_name or 'the specified estate'}."
                )

            elif len(names) == 2:
                analysis = (
                    f"{names[0]} and {names[1]} live in "
                    f"{estate_name or 'the specified estate'}."
                )

            else:
                analysis = (
                    f"{', '.join(names[:-1])}, and {names[-1]} "
                    f"live in "
                    f"{estate_name or 'the specified estate'}."
                )

        else:
            analysis = (
                f"No residents were found in "
                f"{estate_name or 'the specified estate'}."
            )

        return {
            "analysis": analysis,
            "insights": [
                f"{len(names)} resident(s) were found in "
                f"{estate_name or 'the specified estate'}."
            ],
            "reasoning": [
                "The residents were identified by traversing "
                "Resident → LIVES_IN → Property → HAS_PROPERTY → Estate."
            ],
            "actions": [],
            "data": data,
        }
        
        # ==========================================================
    # ESTATES
    #
    # Examples:
    # List all estates
    # Show all estates
    # List every estate
    # ==========================================================

    if intent == "estates":

        estate_names = [
            get_first_value(
                row,
                "name",
                "estate_name",
                "estate",
            )
            for row in data
        ]

        estate_names = [
            name
            for name in estate_names
            if name
        ]

        estate_names = list(dict.fromkeys(estate_names))

        if not estate_names:

            return {
                "analysis": "No estates were found.",
                "insights": [],
                "reasoning": [
                    "Neo4j returned estate records, but no estate names "
                    "could be extracted from the returned data."
                ],
                "actions": [],
                "data": data,
            }

        if len(estate_names) == 1:

            analysis = (
                f"There is 1 estate: "
                f"{estate_names[0]}."
            )

        elif len(estate_names) == 2:

            analysis = (
                f"There are 2 estates: "
                f"{estate_names[0]} and {estate_names[1]}."
            )

        else:

            analysis = (
                f"There are {len(estate_names)} estates: "
                f"{join_names(estate_names)}."
            )

        return {
            "analysis": analysis,
            "insights": [
                f"{len(estate_names)} estate(s) were found."
            ],
            "reasoning": [
                "The estates were retrieved directly from the Estate "
                "nodes returned by Neo4j."
            ],
            "actions": [],
            "data": data,
        }
        
    # ==========================================================
    # ESTATE MANAGERS
    #
    # Examples:
    # Who manages Greenfield Estate?
    # Which managers are assigned to Greenfield Estate?
    # ==========================================================

    if intent == "estate_managers":

        managers = [
            get_first_value(
                row,
                "manager_name",
                "manager",
                "name",
            )
            for row in data
        ]

        managers = [
            manager for manager in managers
            if manager
        ]

        managers = list(dict.fromkeys(managers))

        if managers:

            estate_name = get_first_value(
                data[0],
                "estate_name",
                "estate",
            )

            if len(managers) == 1:

                manager_name = managers[0]

                return {
                    "analysis": (
                        f"{manager_name} manages "
                        f"{estate_name or 'the estate'}."
                    ),
                    "insights": [
                        f"The assigned manager is {manager_name}."
                    ],
                    "reasoning": [
                        "The manager was identified through the "
                        "Estate → HAS_MANAGER → Manager relationship."
                    ],
                    "actions": [],
                    "data": data,
                }

            return {
                "analysis": (
                    f"{', '.join(managers)} manage "
                    f"{estate_name or 'the estate'}."
                ),
                "insights": [
                    f"{len(managers)} managers are assigned."
                ],
                "reasoning": [
                    "The managers were identified through the "
                    "Estate → HAS_MANAGER → Manager relationship."
                ],
                "actions": [],
                "data": data,
            }

        return {
            "analysis": (
                f"No manager was found for "
                f"{semantic_understanding.get('filters', {}).get('estate_name', 'the estate')}."
            ),
            "insights": [],
            "reasoning": [
                "Neo4j returned no manager records for the specified estate."
            ],
            "actions": [],
            "data": data,
        }


    # ==========================================================
    # PROPERTY MANAGER
    #
    # Example:
    # Who manages the property where John Doe lives?
    # ==========================================================

    if intent == "property_manager":

        managers = [
            get_first_value(
                row,
                "manager_name",
                "manager",
                "name",
            )
            for row in data
        ]

        managers = [
            manager for manager in managers
            if manager
        ]

        managers = list(dict.fromkeys(managers))

        if managers:

            if len(managers) == 1:

                analysis = (
                    f"{managers[0]} manages the property "
                    f"where the resident lives."
                )

            else:

                analysis = (
                    f"The property is managed by "
                    f"{join_names(managers)}."
                )

        else:

            analysis = (
                "No property manager was found for "
                "the specified resident."
            )

        return {
            "analysis": analysis,
            "insights": [],
            "reasoning": [
                "The manager was identified by following the resident's "
                "LIVES_IN relationship to the Property and then following "
                "the property's management relationship to the Manager."
            ],
            "actions": [],
            "data": data,
        }
        
    # ==========================================================
    # TOP ESTATES BY COMPLAINTS
    # ==========================================================
    #
    # Examples:
    # Which estate has the most complaints?
    # Which estates have the most complaints?
    # Which estate has the highest number of complaints?
    # ==========================================================

    if (
        intent == "estate_overview"
        and operation == "rank"
        and entity == "estate"
    ):

        complaint_rows = [
            row
            for row in data
            if row.get("complaint_count") is not None
        ]

        if complaint_rows:

            highest_count = max(
                int(row.get("complaint_count", 0))
                for row in complaint_rows
            )

            highest = [
                row
                for row in complaint_rows
                if int(row.get("complaint_count", 0))
                == highest_count
            ]

            estates = [
                get_first_value(
                    row,
                    "estate_name",
                    "estate",
                    "name",
                )
                for row in highest
            ]

            estates = [
                estate
                for estate in estates
                if estate
            ]

            if len(estates) == 1:

                analysis = (
                    f"{estates[0]} has the most complaints, "
                    f"with {highest_count} "
                    f"{pluralize('complaint', highest_count)}."
                )

            else:

                analysis = (
                    f"{join_names(estates)} have the most complaints, "
                    f"with {highest_count} "
                    f"{pluralize('complaint', highest_count)} each."
                )

            return {
                "analysis": analysis,
                "insights": [
                    f"The highest complaint count is {highest_count}."
                ],
                "reasoning": [
                    "Estate complaint totals were compared "
                    "deterministically using the records returned "
                    "by Neo4j."
                ],
                "actions": [],
                "data": highest,
            }

        return {
            "analysis": "No estate complaint records were found.",
            "insights": [],
            "reasoning": [
                "Neo4j returned no estate complaint totals."
            ],
            "actions": [],
            "data": [],
        }

    # ==========================================================
    # TOP RESIDENTS BY COMPLAINTS
    #
    # Example:
    # Which residents have the most complaints?
    # ==========================================================

    if intent == "top_residents":

        complaint_rows = [
            row
            for row in data
            if row.get("complaint_count") is not None
        ]

        if complaint_rows:

            highest_count = max(
                int(row.get("complaint_count", 0))
                for row in complaint_rows
            )

            highest = [
                row
                for row in complaint_rows
                if int(row.get("complaint_count", 0))
                == highest_count
            ]

            names = [
                row.get("resident")
                or row.get("name")
                or row.get("resident_name")
                for row in highest
            ]

            names = [
                name for name in names
                if name
            ]

            if len(names) == 1:

                analysis = (
                    f"{names[0]} has the most complaints, "
                    f"with {highest_count} "
                    f"{pluralize('complaint', highest_count)}."
                )

            else:

                analysis = (
                    f"{join_names(names)} have the most complaints, "
                    f"with {highest_count} "
                    f"{pluralize('complaint', highest_count)} each."
                )

            return {
                "analysis": analysis,
                "insights": [
                    f"The highest complaint count among residents "
                    f"is {highest_count}."
                ],
                "reasoning": [
                    "Resident complaint totals were compared using "
                    "the complaint counts returned by Neo4j."
                ],
                "actions": [],
                "top_records": highest,
                "data": data,
            }

    # ==========================================================
    # TOP PROPERTIES BY COMPLAINTS
    #
    # Example:
    # Which properties have the most complaints?
    # ==========================================================

    if intent == "top_properties":

        complaint_rows = [
            row
            for row in data
            if row.get("complaint_count") is not None
        ]

        if complaint_rows:

            highest_count = max(
                int(row.get("complaint_count", 0))
                for row in complaint_rows
            )

            highest = [
                row
                for row in complaint_rows
                if int(row.get("complaint_count", 0))
                == highest_count
            ]

            properties = [
                get_first_value(
                    row,
                    "property_number",
                    "property",
                    "property_name",
                )
                for row in highest
            ]

            properties = [
                property_name
                for property_name in properties
                if property_name
            ]

            if len(properties) == 1:

                analysis = (
                    f"Property {properties[0]} has the most complaints, "
                    f"with {highest_count} "
                    f"{pluralize('complaint', highest_count)}."
                )

            else:

                analysis = (
                    f"Properties {join_names(properties)} have the most "
                    f"complaints, with {highest_count} "
                    f"{pluralize('complaint', highest_count)} each."
                )

            return {
                "analysis": analysis,
                "insights": [
                    f"The highest complaint count among properties "
                    f"is {highest_count}."
                ],
                "reasoning": [
                    "Property complaint totals were compared using "
                    "the complaint counts returned by Neo4j."
                ],
                "actions": [],
                "top_records": highest,
                "data": data,
            }

    # ==========================================================
    # TOP MAINTENANCE TEAMS
    #
    # Example:
    # Which maintenance teams handle the most complaints?
    # ==========================================================

    if intent == "top_maintenance_teams":

        complaint_rows = [
            row
            for row in data
            if row.get("complaint_count") is not None
        ]

        if complaint_rows:

            highest_count = max(
                int(row.get("complaint_count", 0))
                for row in complaint_rows
            )

            highest = [
                row
                for row in complaint_rows
                if int(row.get("complaint_count", 0))
                == highest_count
            ]

            teams = [
                get_first_value(
                    row,
                    "team",
                    "team_name",
                    "maintenance_team",
                )
                for row in highest
            ]

            teams = [
                team
                for team in teams
                if team
            ]

            if len(teams) == 1:

                analysis = (
                    f"{teams[0]} handles the most complaints, "
                    f"with {highest_count} "
                    f"{pluralize('complaint', highest_count)}."
                )

            else:

                analysis = (
                    f"{join_names(teams)} handle the most complaints, "
                    f"with {highest_count} "
                    f"{pluralize('complaint', highest_count)} each."
                )

            return {
                "analysis": analysis,
                "insights": [
                    f"The highest complaint count among maintenance "
                    f"teams is {highest_count}."
                ],
                "reasoning": [
                    "Maintenance-team complaint totals were compared "
                    "using the complaint counts returned by Neo4j."
                ],
                "actions": [],
                "top_records": highest,
                "data": data,
            }

    # ==========================================================
    # OPEN COMPLAINT COUNT
    #
    # Example:
    # How many open complaints are there?
    # ==========================================================

    if intent == "open_complaints":

        count = 0

        if data:

            count = int(
                data[0].get(
                    "open_complaint_count",
                    0
                )
            )

        return {
            "analysis": (
                f"There {'is' if count == 1 else 'are'} "
                f"{count} open "
                f"{pluralize('complaint', count)}."
            ),
            "insights": [
                (
                    f"The system currently records "
                    f"{count} open "
                    f"{pluralize('complaint', count)}."
                )
            ],
            "reasoning": [
                "The count was obtained directly from complaints "
                "currently marked as open in Neo4j."
            ],
            "actions": [],
            "data": data,
        }

    # ==========================================================
    # OPERATIONAL PRIORITIES
    #
    # Example:
    # What are today's priorities?
    # ==========================================================

    if intent == "operational_priorities":

        open_complaints = []
        in_progress_complaints = []

        high_open = []
        medium_open = []
        low_open = []
        unprioritized_open = []

        assigned = []
        unassigned = []

        # ------------------------------------------------------
        # Inspect returned records
        # ------------------------------------------------------

        for row in data:

            status = str(
                row.get("status") or ""
            ).strip().lower()

            priority = str(
                row.get("priority") or ""
            ).strip().lower()

            team = row.get("team")

            if status == "open":

                open_complaints.append(row)

            elif status == "in progress":

                in_progress_complaints.append(row)

            # Priority applies to active complaints
            if status == "open":

                if priority == "high":
                    high_open.append(row)

                elif priority == "medium":
                    medium_open.append(row)

                elif priority == "low":
                    low_open.append(row)

                else:
                    unprioritized_open.append(row)

            # Assignment
            if status in {"open", "in progress"}:

                if team:
                    assigned.append(row)

                else:
                    unassigned.append(row)

        # ------------------------------------------------------
        # Assignment gaps
        # ------------------------------------------------------

        high_open_unassigned = [
            row
            for row in high_open
            if not row.get("team")
        ]

        medium_open_unassigned = [
            row
            for row in medium_open
            if not row.get("team")
        ]

        low_open_unassigned = [
            row
            for row in low_open
            if not row.get("team")
        ]

        # ------------------------------------------------------
        # Insights
        # ------------------------------------------------------

        insights = []

        if open_complaints:

            insights.append(
                f"{len(open_complaints)} open "
                f"{pluralize('complaint', len(open_complaints))} "
                "require attention."
            )

        if in_progress_complaints:

            insights.append(
                f"{len(in_progress_complaints)} "
                f"{pluralize('complaint', len(in_progress_complaints))} "
                "are currently in progress."
            )

        if high_open:

            insights.append(
                f"{len(high_open)} open "
                f"{pluralize('complaint', len(high_open))} "
                "are high priority."
            )

        if medium_open:

            insights.append(
                f"{len(medium_open)} open "
                f"{pluralize('complaint', len(medium_open))} "
                "are medium priority."
            )

        if low_open:

            insights.append(
                f"{len(low_open)} open "
                f"{pluralize('complaint', len(low_open))} "
                "are low priority."
            )

        if unprioritized_open:

            insights.append(
                f"{len(unprioritized_open)} open "
                f"{pluralize('complaint', len(unprioritized_open))} "
                "have no priority assigned."
            )

        if medium_open_unassigned:

            insights.append(
                f"{len(medium_open_unassigned)} medium-priority open "
                f"{pluralize('complaint', len(medium_open_unassigned))} "
                "have no maintenance team assigned."
            )

        if high_open_unassigned:

            insights.append(
                f"{len(high_open_unassigned)} high-priority open "
                f"{pluralize('complaint', len(high_open_unassigned))} "
                "have no maintenance team assigned."
            )

        if low_open_unassigned:

            insights.append(
                f"{len(low_open_unassigned)} low-priority open "
                f"{pluralize('complaint', len(low_open_unassigned))} "
                "have no maintenance team assigned."
            )

        # ------------------------------------------------------
        # Actions
        # ------------------------------------------------------

        actions = []

        def complaint_ids(rows):

            return [
                str(row.get("complaint_id"))
                for row in rows
                if row.get("complaint_id")
            ]

        high_ids = complaint_ids(high_open)
        high_unassigned_ids = complaint_ids(
            high_open_unassigned
        )

        medium_ids = complaint_ids(medium_open)
        medium_unassigned_ids = complaint_ids(
            medium_open_unassigned
        )

        low_ids = complaint_ids(low_open)
        unprioritized_ids = complaint_ids(
            unprioritized_open
        )

        if high_ids:

            actions.append({
                "type": "priority",
                "reason": (
                    "High-priority open complaints should be "
                    "addressed before lower-priority issues."
                ),
                "complaints": high_ids,
            })

        if high_unassigned_ids:

            actions.append({
                "type": "assignment",
                "reason": (
                    "These high-priority open complaints do not "
                    "currently have a maintenance team assigned."
                ),
                "complaints": high_unassigned_ids,
            })

        if medium_ids:

            actions.append({
                "type": "priority",
                "reason": (
                    "These medium-priority open complaints should "
                    "be reviewed after higher-priority issues."
                ),
                "complaints": medium_ids,
            })

        if medium_unassigned_ids:

            actions.append({
                "type": "assignment",
                "reason": (
                    "These medium-priority open complaints have "
                    "no maintenance team assigned."
                ),
                "complaints": medium_unassigned_ids,
            })

        if low_ids:

            actions.append({
                "type": "priority",
                "reason": (
                    "These low-priority open complaints remain "
                    "outstanding but are lower in priority."
                ),
                "complaints": low_ids,
            })

        if unprioritized_ids:

            actions.append({
                "type": "prioritization_review",
                "reason": (
                    "These open complaints have no priority "
                    "assigned and should be assessed."
                ),
                "complaints": unprioritized_ids,
            })

        # ------------------------------------------------------
        # Reasoning
        # ------------------------------------------------------

        reasoning = []

        if high_open:

            reasoning.append(
                f"{len(high_open)} open "
                f"{pluralize('complaint', len(high_open))} "
                "have high priority and therefore take precedence."
            )

        elif medium_open:

            reasoning.append(
                "No high-priority open complaints were found. "
                "The highest recorded priority among open complaints "
                "is medium."
            )

        elif low_open:

            reasoning.append(
                "No high- or medium-priority open complaints were found. "
                "The highest recorded priority among open complaints "
                "is low."
            )

        elif unprioritized_open:

            reasoning.append(
                "The open complaints have no recorded priority, "
                "so their urgency cannot be determined from the "
                "available data."
            )

        if high_open_unassigned:

            reasoning.append(
                f"{len(high_open_unassigned)} high-priority open "
                f"{pluralize('complaint', len(high_open_unassigned))} "
                "have no maintenance team assigned."
            )

        if medium_open_unassigned:

            reasoning.append(
                f"{len(medium_open_unassigned)} medium-priority open "
                f"{pluralize('complaint', len(medium_open_unassigned))} "
                "have no maintenance team assigned."
            )

        if unprioritized_open:

            reasoning.append(
                f"{len(unprioritized_open)} open "
                f"{pluralize('complaint', len(unprioritized_open))} "
                "have no recorded priority and require assessment."
            )

        if (
            open_complaints
            and not unassigned
        ):

            reasoning.append(
                "All currently active complaints have "
                "a maintenance team assigned."
            )

        # ------------------------------------------------------
        # Human-readable analysis
        # ------------------------------------------------------

        analysis_parts = []

        if open_complaints:

            count = len(open_complaints)

            analysis_parts.append(
                f"There {'is' if count == 1 else 'are'} "
                f"{count} open "
                f"{pluralize('complaint', count)}."
            )

        if high_open:

            count = len(high_open)

            analysis_parts.append(
                f"{count} "
                f"{'is' if count == 1 else 'are'} "
                "high priority."
            )

        if medium_open:

            count = len(medium_open)

            analysis_parts.append(
                f"{count} "
                f"{'is' if count == 1 else 'are'} "
                "medium priority."
            )

        if low_open:

            count = len(low_open)

            analysis_parts.append(
                f"{count} "
                f"{'is' if count == 1 else 'are'} "
                "low priority."
            )

        if unprioritized_open:

            count = len(unprioritized_open)

            analysis_parts.append(
                f"{count} "
                f"{'has' if count == 1 else 'have'} "
                "no priority assigned."
            )

        if medium_open_unassigned:

            count = len(medium_open_unassigned)

            analysis_parts.append(
                f"{count} medium-priority open "
                f"{pluralize('complaint', count)} "
                f"{'has' if count == 1 else 'have'} "
                "no maintenance team assigned."
            )

        if high_open_unassigned:

            count = len(high_open_unassigned)

            analysis_parts.append(
                f"{count} high-priority open "
                f"{pluralize('complaint', count)} "
                f"{'has' if count == 1 else 'have'} "
                "no maintenance team assigned."
            )

        if in_progress_complaints:

            count = len(in_progress_complaints)

            analysis_parts.append(
                f"{count} "
                f"{'is' if count == 1 else 'are'} "
                "currently in progress."
            )

        if not analysis_parts:

            analysis_parts.append(
                f"{len(data)} matching "
                f"{pluralize('record', len(data))} were retrieved, "
                "but no active operational priority information "
                "was identified."
            )

        analysis = " ".join(analysis_parts)

        return {
            "analysis": analysis,
            "insights": insights,
            "reasoning": reasoning,
            "actions": actions,
            "high_priority_count": len(high_open),
            "medium_priority_count": len(medium_open),
            "low_priority_count": len(low_open),
            "unprioritized_count": len(unprioritized_open),
            "open_count": len(open_complaints),
            "in_progress_count": len(in_progress_complaints),
            "assigned_count": len(assigned),
            "unassigned_count": len(unassigned),
            "data": data,
        }

    # ==========================================================
    # GENERAL COUNT QUERIES
    # ==========================================================

    # Handle common count aliases returned by Cypher.

    if len(data) == 1:

        row = data[0]

        count_fields = [
            key
            for key in row.keys()
            if key.endswith("_count")
        ]

        if len(count_fields) == 1:

            field = count_fields[0]
            count = int(row.get(field) or 0)

            entity_name = field.replace(
                "_count",
                ""
            ).replace(
                "_",
                " "
            )

            return {
                "analysis": (
                    f"There are {count} "
                    f"{pluralize(entity_name, count)}."
                ),
                "insights": [],
                "reasoning": [
                    "The count was obtained directly from "
                    "the aggregate result returned by Neo4j."
                ],
                "actions": [],
                "data": data,
            }
            
        # ==========================================================
    # ESTATE OVERVIEW
    #
    # Provides a deterministic summary of the current estate
    # state using aggregate values returned by Neo4j.
    # ==========================================================

    if intent == "estate_overview" and len(data) == 1:

        row = data[0]
        
        deterministic = deterministic_reasoning(row)

        total_residents = int(
            row.get("total_residents") or 0
        )

        total_properties = int(
            row.get("total_properties") or 0
        )

        available_properties = int(
            row.get("available_properties") or 0
        )

        occupied_properties = int(
            row.get("occupied_properties") or 0
        )

        maintenance_properties = int(
            row.get("maintenance_properties") or 0
        )

        total_complaints = int(
            row.get("total_complaints") or 0
        )

        open_complaints = int(
            row.get("open_complaints") or 0
        )

        in_progress_complaints = int(
            row.get("in_progress_complaints") or 0
        )

        resolved_complaints = int(
            row.get("resolved_complaints") or 0
        )

        # ------------------------------------------------------
        # Occupancy percentage
        # ------------------------------------------------------

        if total_properties > 0:
            occupancy_rate = (
                occupied_properties / total_properties
            ) * 100
        else:
            occupancy_rate = 0

        # ------------------------------------------------------
        # Resolution percentage
        # ------------------------------------------------------

        if total_complaints > 0:
            resolution_rate = (
                resolved_complaints / total_complaints
            ) * 100
        else:
            resolution_rate = 0
            
        # ------------------------------------------------------
        # Deterministic reasoning
        # ------------------------------------------------------

        insights = deterministic["insights"]
        reasoning = deterministic["reasoning"]
        actions = deterministic["actions"]
        estate_status = deterministic["estate_status"]

        # ------------------------------------------------------
        # Main analysis
        # ------------------------------------------------------

        analysis = (
            f"The estate currently has {total_residents} "
            f"{pluralize('resident', total_residents)} across "
            f"{total_properties} "
            f"{pluralize('property', total_properties)}. "
            f"{occupied_properties} "
            f"{pluralize('property', occupied_properties)} "
            f"are occupied, {available_properties} "
            f"{pluralize('property', available_properties)} "
            f"are available, and {maintenance_properties} "
            f"{pluralize('property', maintenance_properties)} "
            f"are under maintenance. "
            f"There are {total_complaints} "
            f"{pluralize('complaint', total_complaints)}, "
            f"with {open_complaints} open, "
            f"{in_progress_complaints} in progress, and "
            f"{resolved_complaints} resolved. "
            f"Overall estate status: {estate_status}."      
        )
        
        return {
            "analysis": analysis,
            "insights": insights,
            "reasoning": reasoning,
            "actions": actions,
            "estate_status": estate_status,
            "data": data,
        }
            
        # ------------------------------------------------------
        # Deterministic reasoning
        # ------------------------------------------------------

        insights = deterministic["insights"]
        reasoning = deterministic["reasoning"]
        actions = deterministic["actions"]
        estate_status = deterministic["estate_status"]

    # ==========================================================
    # GENERAL FALLBACK
    #
    # This should now be rare.
    # ==========================================================

    return {
        "analysis": (
            f"{len(data)} matching "
            f"{pluralize('record', len(data))} were retrieved."
        ),
        "insights": [],
        "reasoning": [
            "Neo4j returned structured records, but no "
            "specialized semantic response handler matched "
            "the interpreted intent."
        ],
        "actions": [],
        "data": data,
    }