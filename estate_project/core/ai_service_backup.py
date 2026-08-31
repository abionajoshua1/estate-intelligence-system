from groq import Groq
from django.conf import settings
from .schema import GRAPH_SCHEMA

import re


client = Groq(
    api_key=settings.GROQ_API_KEY
)

def detect_ai_intent(question: str):
    """
    Uses the LLM to understand the user's intended operation.

    The LLM classifies the natural-language question into a
    predefined estate-system intent. It does not generate
    Cypher and does not access the database.
    """

    prompt = f"""
You are the intent classification component of an Estate Intelligence System.

Your ONLY task is to determine what the user is asking for.

Return ONLY one of the following intent names:

operational_priorities
resident_property
residents_by_property
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

INTENT DEFINITIONS:

operational_priorities:
The user wants to know what should be handled, prioritized, focused on,
or given attention in the estate.

Examples:
"What should I focus on today?"
"What should I do today?"
"What needs my attention?"
"What should I handle first?"
"What are my priorities?"
"What needs to be dealt with?"

resident_property:
The user wants to know where a particular resident lives.

Examples:
"Where does John live?"
"Which property does John live in?"

residents_by_property:
The user wants to know who lives in a particular property.

Examples:
"Who lives in P001?"
"Who lives in Apartment 12?"

resident_count:
The user wants the number of residents.

estates:
The user wants to list or view estates.

vacant_properties:
The user wants available, vacant, or empty properties.

estate_managers:
The user wants information about estate managers.

maintenance_teams:
The user wants to list or view maintenance teams.

open_complaints:
The user wants to see complaints that are currently open or unresolved.

pending_maintenance:
The user wants to know about pending maintenance issues.

properties_needing_attention:
The user wants properties that require attention because of complaints or maintenance issues.

top_residents:
The user wants residents with the most complaints.

top_properties:
The user wants properties with the most complaints.

top_maintenance_teams:
The user wants maintenance teams handling the most complaints.

estate_overview:
The user wants a general numerical overview of the estate.

current_estate_state:
The user wants the current state/status of estate properties.

property_manager:
The user wants to know who manages the estate/property associated with a resident or property.

general:
Use this when the question does not clearly belong to any supported estate-system intent.

IMPORTANT RULES:

1. Understand meaning, not exact wording.
2. Treat semantically equivalent questions as the same intent.
3. Do not generate Cypher.
4. Do not explain your answer.
5. Return exactly ONE intent name.
6. If the question is ambiguous or unrelated to the estate system, return general.

USER QUESTION:

{question}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict intent classifier. "
                        "Return exactly one supported intent name "
                        "and nothing else."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
        )

        intent = (
            response.choices[0].message.content
            or "general"
        ).strip().lower()

        allowed_intents = {
            "operational_priorities",
            "resident_property",
            "residents_by_property",
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

        if intent not in allowed_intents:
            print(">>> UNKNOWN AI INTENT:", intent)
            return "general"

        print(">>> AI INTENT:", intent)

        return intent

    except Exception as exc:
        print(">>> INTENT CLASSIFICATION ERROR:", exc)
        return "general"
    

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


def generate_cypher(question: str):
    
    q = question.lower()
    
    # ---------- RESIDENT PROPERTY ----------
    resident_property_match = re.search(
        r"where does (.+?) live\??$",
        question,
        re.IGNORECASE
    )

    if resident_property_match:
        resident_name = resident_property_match.group(1).strip()

        print(">>> RESIDENT PROPERTY QUERY USED <<<")
        print(">>> RESIDENT:", resident_name)

        return (
            f"""
    MATCH (r:Resident {{name: $resident_name}})
        -[:LIVES_IN]->(p:Property)
        <-[:HAS_PROPERTY]-(e:Estate)

    RETURN
    r.resident_id AS resident_id,
    r.name AS name,
    p.property_id AS property_id,
    p.property_number AS property_number,
    p.property_type AS property_type,
    e.estate_id AS estate_id,
    e.name AS estate_name
    """.strip(),
            {"resident_name": resident_name},
        )
    
    # ---------- RESIDENTS BY ESTATE ----------
    estate_resident_match = re.search(
        r"(?:who lives in|who lives at|people living in|people who live in|residents in|residents of|which residents are in)\s+(.+?)\??$",
        question,
        re.IGNORECASE
    )

    if estate_resident_match:
        estate_name = estate_resident_match.group(1).strip().rstrip("?").strip()

        # Handle common shortened estate names
        if estate_name.lower() == "greenfield":
            estate_name = "Greenfield Estate"

        print(">>> RESIDENTS BY ESTATE QUERY USED <<<")
        print(">>> ESTATE:", estate_name)

        return (
            """
        MATCH (r:Resident)-[:LIVES_IN]->(p:Property)<-[:HAS_PROPERTY]-(e:Estate)
        WHERE toLower(e.name) = toLower($estate_name)

        RETURN
        r.resident_id AS resident_id,
        r.name AS name,
        r.gender AS gender,
        r.phone AS phone,
        r.email AS email,
        r.status AS status

        ORDER BY name
        """.strip(),
            {"estate_name": estate_name},
        )


    # ---------- RESIDENT BY PROPERTY ----------
    property_match = re.search(
        r"who lives in property\s+(.+?)\??$",
        question,
        re.IGNORECASE
    )

    if property_match:
        property_number = property_match.group(1).strip().rstrip("?").strip()

        print(">>> RESIDENT BY PROPERTY QUERY USED <<<")
        print(">>> PROPERTY:", property_number)

        return (
            """
        MATCH (r:Resident)-[:LIVES_IN]->(p:Property)
        WHERE toLower(p.property_number) = toLower($property_number)

        RETURN
        r.resident_id AS resident_id,
        r.name AS name,
        p.property_number AS property_number

        ORDER BY r.name
        """.strip(),
            {"property_number": property_number},
        )

    # ---------- DOMAIN GUARD ----------
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
    ]):
        print(">>> UNSUPPORTED QUERY <<<")
        return 'RETURN "UNSUPPORTED_QUERY" AS error'
    
    if "how many residents" in q or "resident count" in q:
        print(">>> HARDCODED RESIDENT COUNT QUERY USED <<<")
        return """
    MATCH (r:Resident)
    RETURN COUNT(r) AS resident_count
    """.strip()
    
    if (
        "show all estates" in q
        or "list all estates" in q
        or "list every estate" in q):
        
        print(">>> HARDCODED ESTATE QUERY USED <<<")
        return """
    MATCH (e:Estate)
    RETURN
    e.estate_id AS estate_id,
    e.name AS name
    ORDER BY e.name
    """.strip()
    
    if (
        "estate overview" in q
        or "overview of the estate" in q
        or "overview of estate" in q
        or "give me an overview" in q
        or "estate situation" in q
    ):
        print(">>> ESTATE OVERVIEW QUERY USED <<<")
        return """
    MATCH (r:Resident)
    WITH count(r) AS total_residents

    MATCH (p:Property)
    WITH total_residents,
         count(p) AS total_properties,
         count(CASE WHEN p.status = "Available" THEN 1 END) AS available_properties,
         count(CASE WHEN p.status = "Occupied" THEN 1 END) AS occupied_properties,
         count(CASE WHEN p.status = "Maintenance" THEN 1 END) AS maintenance_properties

    MATCH (c:Complaint)
    RETURN
    total_residents AS total_residents,
    total_properties AS total_properties,
    available_properties AS available_properties,
    occupied_properties AS occupied_properties,
    maintenance_properties AS maintenance_properties,
    count(c) AS total_complaints,
    count(CASE WHEN c.status = "Open" THEN 1 END) AS open_complaints,
    count(CASE WHEN c.status = "In Progress" THEN 1 END) AS in_progress_complaints,
    count(CASE WHEN c.status = "Resolved" THEN 1 END) AS resolved_complaints
    """.strip()
    
    
    
    # ---------- CURRENT ESTATE STATE ----------
    if (
        "current state of the estate" in q
        or "current state of estate" in q
        or "state of the estate" in q
        or "state of estate" in q
    ):
        print(">>> CURRENT ESTATE STATE QUERY USED <<<")

        return """
    MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)

    RETURN
    e.estate_id AS estate_id,
    e.name AS estate_name,
    p.property_id AS property_id,
    p.property_number AS property_number,
    p.property_type AS property_type,
    p.status AS property_status

    ORDER BY e.name, p.property_number
    """.strip()
    
        # ---------- PROPERTIES NEEDING ATTENTION ----------
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

    ORDER BY complaint_count DESC,
             p.property_number
    """.strip()


    
# ---------- PENDING MAINTENANCE ----------
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
        or ("maintenance" in q and "pending" in q)
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
    
    # ---------- OPEN COMPLAINTS ----------
    if (
        (
        "open complaints" in q
        or "complaints that are open" in q
        or "currently open complaints" in q
        or "unresolved complaints" in q
        or "unresolved complaint" in q
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
    
    # ---------- TODAY'S PRIORITIES ----------
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
    
    # ======================
    # MANAGER INSIGHTS
    # ======================

    # Residents with the most complaints
    if "residents" in q and "most complaints" in q:
        print(">>> TOP RESIDENTS QUERY USED <<<")
        return """
    MATCH (r:Resident)-[:RAISED]->(c:Complaint)
    RETURN
    r.name AS resident,
    COUNT(c) AS complaint_count
    ORDER BY complaint_count DESC
    """.strip()


    # Properties with the most complaints
# Properties with the most complaints
    if "properties" in q and "most complaints" in q:
        print(">>> TOP PROPERTIES QUERY USED <<<")

        return """
    MATCH (c:Complaint)-[:ABOUT]->(p:Property)

    RETURN
    p.property_number AS property_number,
    COUNT(c) AS complaint_count
    ORDER BY complaint_count DESC
    """.strip()


    # Maintenance teams handling the most complaints
    if "maintenance teams" in q and "most complaints" in q:
        print(">>> TOP MAINTENANCE TEAMS QUERY USED <<<")
        return """
    MATCH (c:Complaint)-[:ASSIGNED_TO]->(t:MaintenanceTeam)
    RETURN
    t.team_name AS team,
    COUNT(c) AS complaint_count
    ORDER BY complaint_count DESC
    """.strip()
    
    # ---------- PROPERTY MANAGER ----------
    manager_match = re.search(
        r"property where (.+?) lives",
        question,
        re.IGNORECASE
    )

    if manager_match and "who manages" in q:

        resident_name = manager_match.group(1).strip()

        print(">>> PROPERTY MANAGER QUERY USED <<<")
        print(">>> RESIDENT:", resident_name)

        return (
            f"""
        MATCH (r:Resident {{name: $resident_name}})
            -[:LIVES_IN]->(p:Property)
            <-[:HAS_PROPERTY]-(e:Estate)
            -[:HAS_MANAGER]->(m:Manager)

        RETURN
        m.manager_id AS manager_id,
        m.name AS manager_name
        """.strip(),
            {"resident_name": resident_name},
        )
                
        
    prompt = f"""
You are an expert Neo4j Cypher generator.

Your task is to convert natural language into Cypher.

=========================================
DATABASE SCHEMA
=========================================

{GRAPH_SCHEMA}

=========================================
RULES
=========================================

1. Return ONLY Cypher.
2. Never explain anything.
3. Never use markdown.
4. Never use ``` blocks.
5. Never use CREATE.
6. Never use DELETE.
7. Never use MERGE.
8. Never use SET.
9. Never use REMOVE.
10. Never use DROP.
11. Use ONLY labels, relationships and properties that exist in the provided schema. Never invent labels, relationship types or property names.
12. Traverse relationships whenever necessary.
13. Every expression inside RETURN MUST have an alias using AS.

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
16. If the answer cannot be generated from the schema, return:

RETURN "UNSUPPORTED_QUERY" AS error

=========================================
EXAMPLES
=========================================

Question:
How many residents are registered?

Cypher:

MATCH (r:Resident)

RETURN
COUNT(r) AS resident_count

Question:
Which residents live in Greenfield Estate?

Cypher:

MATCH (r:Resident)-[:LIVES_IN]->(p:Property)<-[:HAS_PROPERTY]-(e:Estate)

WHERE e.name = "Greenfield Estate"

RETURN
r.resident_id AS resident_id,
r.name AS name

ORDER BY name

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
-[:LIVES_IN]->
(p:Property)
<-[:HAS_PROPERTY]-
(e:Estate)
-[:HAS_MANAGER]->
(m:Manager)

RETURN
m.manager_id AS manager_id,
m.name AS manager_name


Question:
Which team is handling Tunde's complaint?

Cypher:

MATCH (r:Resident {{name:"Tunde"}})
-[:RAISED]->
(c:Complaint)
-[:ASSIGNED_TO]->
(t:MaintenanceTeam)

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

=========================================

Generate Cypher for:

{question}

"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": """
You are an expert Neo4j Cypher generator.

Only return valid Cypher.
Never explain.
Never use markdown.
Never use code fences.
Always alias every RETURN field using AS.
Never invent labels, properties or relationships.
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
    )

    content = response.choices[0].message.content
    
    print(">>> AI GENERATED CYPHER <<<")
    print(content)

    return (content or "").strip()

def analyze_results(question: str, data, intent=None):
    """
    Performs deterministic, evidence-based reasoning on Neo4j results.

    The function does not invent priorities, assignments, statuses,
    or other facts. It derives operational findings only from data
    returned by Neo4j.
    """

    if not data:
        return {
            "analysis": "No matching records were found.",
            "insights": [],
            "recommendations": [],
            "data": [],
        }

    q = question.lower()

    # ==========================================================
    # PRIORITY / ATTENTION REASONING
    # ==========================================================

    if intent == "operational_priorities":

        open_complaints = []
        in_progress_complaints = []

        high_priority = []
        medium_priority = []
        low_priority = []
        unprioritized = []

        assigned = []
        unassigned = []

        # ------------------------------------------------------
        # Inspect every database record
        # ------------------------------------------------------

        for row in data:

            status = str(row.get("status") or "").strip().lower()
            priority = str(row.get("priority") or "").strip().lower()
            team = row.get("team")

            # Status
            if status == "open":
                open_complaints.append(row)

            elif status == "in progress":
                in_progress_complaints.append(row)

            # Priority
            if priority == "high":
                high_priority.append(row)

            elif priority == "medium":
                medium_priority.append(row)

            elif priority == "low":
                low_priority.append(row)

            else:
                unprioritized.append(row)

            # --------------------------------------------------
            # Assignment status
            #
            # Only complaints that are still operationally active
            # should be considered for assignment gaps.
            # --------------------------------------------------

            if status in {"open", "in progress"}:
                if team:
                    assigned.append(row)
                else:
                    unassigned.append(row)

        # ------------------------------------------------------
        # Specific operational groups
        # ------------------------------------------------------

        high_open = [
            row for row in high_priority
            if str(row.get("status") or "").strip().lower() == "open"
        ]

        medium_open = [
            row for row in medium_priority
            if str(row.get("status") or "").strip().lower() == "open"
        ]

        low_open = [
            row for row in low_priority
            if str(row.get("status") or "").strip().lower() == "open"
        ]

        unprioritized_open = [
            row for row in unprioritized
            if str(row.get("status") or "").strip().lower() == "open"
        ]

        medium_open_unassigned = [
            row for row in medium_open
            if not row.get("team")
        ]

        high_open_unassigned = [
            row for row in high_open
            if not row.get("team")
        ]

        low_open_unassigned = [
            row for row in low_open
            if not row.get("team")
        ]

        # ======================================================
        # BUILD INSIGHTS
        # ======================================================

        insights = []

        if open_complaints:
            insights.append(
                f"{len(open_complaints)} open complaint(s) require attention."
            )

        if in_progress_complaints:
            insights.append(
                f"{len(in_progress_complaints)} complaint(s) are currently in progress."
            )

        if high_open:
            insights.append(
                f"{len(high_open)} open complaint(s) are high priority."
            )

        if medium_open:
            insights.append(
                f"{len(medium_open)} open complaint(s) are medium priority."
            )

        if low_open:
            insights.append(
                f"{len(low_open)} open complaint(s) are low priority."
            )

        if unprioritized_open:
            insights.append(
                f"{len(unprioritized_open)} open complaint(s) have no priority assigned."
            )

        if medium_open_unassigned:
            insights.append(
                f"{len(medium_open_unassigned)} medium-priority open complaint(s) "
                f"have no maintenance team assigned."
            )

        if high_open_unassigned:
            insights.append(
                f"{len(high_open_unassigned)} high-priority open complaint(s) "
                f"have no maintenance team assigned."
            )

        if low_open_unassigned:
            insights.append(
                f"{len(low_open_unassigned)} low-priority open complaint(s) "
                f"have no maintenance team assigned."
            )

        # ======================================================
        # BUILD SPECIFIC ACTIONS
        # ======================================================

        actions = []

        # ------------------------------------------------------
        # High priority
        # ------------------------------------------------------

        if high_open:

            ids = [
                str(row.get("complaint_id"))
                for row in high_open
                if row.get("complaint_id")
            ]

            if ids:
                actions.append({
                    "type": "priority",
                    "reason": (
                        "High-priority open complaints should be addressed "
                        "before lower-priority open complaints."
                    ),
                    "complaints": ids,
                })

        # ------------------------------------------------------
        # High-priority assignment gap
        # ------------------------------------------------------

        if high_open_unassigned:

            ids = [
                str(row.get("complaint_id"))
                for row in high_open_unassigned
                if row.get("complaint_id")
            ]

            if ids:
                actions.append({
                    "type": "assignment",
                    "reason": (
                        "These high-priority open complaints do not currently "
                        "have a maintenance team assigned."
                    ),
                    "complaints": ids,
                })

        # ------------------------------------------------------
        # Medium priority
        # ------------------------------------------------------

        if medium_open:

            ids = [
                str(row.get("complaint_id"))
                for row in medium_open
                if row.get("complaint_id")
            ]

            if ids:
                actions.append({
                    "type": "priority",
                    "reason": (
                        "These medium-priority open complaints should be "
                        "reviewed after any higher-priority issues."
                    ),
                    "complaints": ids,
                })

        # ------------------------------------------------------
        # Medium-priority assignment gap
        # ------------------------------------------------------

        if medium_open_unassigned:

            ids = [
                str(row.get("complaint_id"))
                for row in medium_open_unassigned
                if row.get("complaint_id")
            ]

            if ids:
                actions.append({
                    "type": "assignment",
                    "reason": (
                        "These medium-priority open complaints have no "
                        "maintenance team assigned and require assignment "
                        "before maintenance work can proceed."
                    ),
                    "complaints": ids,
                })

        # ------------------------------------------------------
        # Low priority
        # ------------------------------------------------------

        if low_open:

            ids = [
                str(row.get("complaint_id"))
                for row in low_open
                if row.get("complaint_id")
            ]

            if ids:
                actions.append({
                    "type": "priority",
                    "reason": (
                        "These low-priority open complaints remain outstanding "
                        "but are lower in priority than high- or medium-priority issues."
                    ),
                    "complaints": ids,
                })

        # ------------------------------------------------------
        # Missing priority
        # ------------------------------------------------------

        if unprioritized_open:

            ids = [
                str(row.get("complaint_id"))
                for row in unprioritized_open
                if row.get("complaint_id")
            ]

            if ids:
                actions.append({
                    "type": "prioritization_review",
                    "reason": (
                        "These open complaints do not have a priority assigned. "
                        "Their urgency should be assessed before assigning a priority."
                    ),
                    "complaints": ids,
                })

        # ======================================================
        # SPECIFIC COMPLAINT DETAILS
        # ======================================================

        complaint_details = []

        for row in open_complaints:

            complaint_id = row.get("complaint_id")

            if not complaint_id:
                continue

            complaint_details.append({
                "complaint_id": complaint_id,
                "title": row.get("title"),
                "category": row.get("category"),
                "priority": row.get("priority"),
                "status": row.get("status"),
                "team": row.get("team"),
            })

        # ======================================================
        # DETERMINE OVERALL REASONING
        # ======================================================

        reasoning = []

        if high_open:
            reasoning.append(
                f"{len(high_open)} open complaint(s) have high priority "
                "and therefore take precedence."
            )

        elif medium_open:
            reasoning.append(
                "No high-priority open complaints were found. "
                "The highest recorded priority among the open complaints is medium."
            )

        elif low_open:
            reasoning.append(
                "No high- or medium-priority open complaints were found. "
                "The highest recorded priority among the open complaints is low."
            )

        if not high_open and not medium_open and not low_open and unprioritized_open:
            reasoning.append(
                "The open complaints have no recorded priority, so their urgency "
                "cannot be determined from the available data."
            )

        if medium_open_unassigned:
            reasoning.append(
                f"{len(medium_open_unassigned)} medium-priority open complaint(s) "
                "have no maintenance team assigned, creating an assignment gap."
            )

        if high_open_unassigned:
            reasoning.append(
                f"{len(high_open_unassigned)} high-priority open complaint(s) "
                "have no maintenance team assigned."
            )

        if unprioritized_open:
            reasoning.append(
                f"{len(unprioritized_open)} open complaint(s) have no recorded "
                "priority and require assessment before their urgency can be determined."
            )

        if not unassigned and open_complaints:
            reasoning.append(
                "All currently active complaints have a maintenance team assigned."
            )

        # ======================================================
        # BUILD HUMAN-READABLE ANALYSIS
        # ======================================================

        analysis_parts = []

        if open_complaints:
            analysis_parts.append(
                f"There {'is' if len(open_complaints) == 1 else 'are'} "
                f"{len(open_complaints)} open complaint"
                f"{'' if len(open_complaints) == 1 else 's'}."
            )

        if high_open:
            analysis_parts.append(
                f"{len(high_open)} "
                f"{'is' if len(high_open) == 1 else 'are'} high priority."
            )

        if medium_open:
            analysis_parts.append(
                f"{len(medium_open)} "
                f"{'is' if len(medium_open) == 1 else 'are'} medium priority."
            )

        if low_open:
            analysis_parts.append(
                f"{len(low_open)} "
                f"{'is' if len(low_open) == 1 else 'are'} low priority."
            )

        if unprioritized_open:
            analysis_parts.append(
                f"{len(unprioritized_open)} "
                f"{'has' if len(unprioritized_open) == 1 else 'have'} "
                "no priority assigned."
            )

        if medium_open_unassigned:
            analysis_parts.append(
                f"{len(medium_open_unassigned)} medium-priority open "
                f"complaint"
                f"{'' if len(medium_open_unassigned) == 1 else 's'} "
                f"{'has' if len(medium_open_unassigned) == 1 else 'have'} "
                "no maintenance team assigned."
            )

        if high_open_unassigned:
            analysis_parts.append(
                f"{len(high_open_unassigned)} high-priority open "
                f"complaint"
                f"{'' if len(high_open_unassigned) == 1 else 's'} "
                f"{'has' if len(high_open_unassigned) == 1 else 'have'} "
                "no maintenance team assigned."
            )

        if in_progress_complaints:
            analysis_parts.append(
                f"{len(in_progress_complaints)} "
                f"{'is' if len(in_progress_complaints) == 1 else 'are'} "
                "currently in progress."
            )

        if not analysis_parts:
            analysis_parts.append(
                f"{len(data)} matching record(s) were retrieved, "
                "but no active operational priority information was identified."
            )

        analysis = " ".join(analysis_parts)

        # ======================================================
        # FINAL STRUCTURED RESULT
        # ======================================================

        return {
            "analysis": analysis,

            "insights": insights,

            "reasoning": reasoning,

            "actions": actions,

            "complaints": complaint_details,

            "high_priority_count": len(high_priority),
            "medium_priority_count": len(medium_priority),
            "low_priority_count": len(low_priority),
            "unprioritized_count": len(unprioritized),

            "open_count": len(open_complaints),
            "in_progress_count": len(in_progress_complaints),

            "assigned_count": len(assigned),
            "unassigned_count": len(unassigned),

            "data": data,
        }
        
    # ==========================================================
    # OPEN COMPLAINT COUNT
    # ==========================================================

    if intent == "open_complaints":

        count = 0

        if data:
            count = int(data[0].get("open_complaint_count", 0))

        return {
            "analysis": (
                f"There {'is' if count == 1 else 'are'} "
                f"{count} open complaint"
                f"{'' if count == 1 else 's'}."
            ),

            "insights": [
                (
                    f"The system currently records {count} open "
                    f"complaint"
                    f"{'' if count == 1 else 's'}."
                )
            ],

            "reasoning": [
                "The count was obtained directly from the complaints currently marked as open in Neo4j."
            ],

            "actions": [],

            "data": data,
        }
        
        
    # ==========================================================
    # MOST COMPLAINTS
    # ==========================================================

    if "most complaints" in q or "highest complaints" in q:

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
                if int(row.get("complaint_count", 0)) == highest_count
            ]

            # --------------------------------------------------
            # Build human-readable answer
            # --------------------------------------------------

            if len(highest) == 1:

                record = highest[0]

                estate_name = (
                    record.get("name")
                    or record.get("estate_name")
                    or record.get("estate")
                    or "the estate"
                )

                analysis = (
                    f"{estate_name} has the most complaints, "
                    f"with {highest_count} complaint"
                    f"{'' if highest_count == 1 else 's'}."
                )

            else:

                estate_names = [
                    str(
                        row.get("name")
                        or row.get("estate_name")
                        or row.get("estate")
                        or "Unknown estate"
                    )
                    for row in highest
                ]

                analysis = (
                    f"{', '.join(estate_names)} have the most complaints, "
                    f"with {highest_count} complaint"
                    f"{'' if highest_count == 1 else 's'} each."
                )

            return {
                "analysis": analysis,

                "insights": [
                    (
                        f"The highest complaint count among the returned "
                        f"estate records is {highest_count}."
                    )
                ],

                "reasoning": [
                    (
                        "The estates were compared using the complaint "
                        "counts returned by Neo4j."
                    )
                ],

                "actions": [],

                "top_records": highest,

                "data": data,
            }

    # ==========================================================
    # GENERAL ANALYSIS
    # ==========================================================

    return {
        "analysis": (
            f"{len(data)} matching record(s) were retrieved."
        ),
        "insights": [],
        "reasoning": [],
        "actions": [],
        "data": data,
    }