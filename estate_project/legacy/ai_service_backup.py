from groq import Groq
from django.conf import settings
from .schema import GRAPH_SCHEMA

import re


client = Groq(
    api_key=settings.GROQ_API_KEY
)

def detect_ai_intent(question: str):
    question = question.lower()

    if any(word in question for word in ["complaint", "complaints"]):
        if any(word in question for word in ["most", "highest", "top"]):
            return "top_residents"

    elif any(word in question for word in ["vacant", "empty", "available"]):
        return "vacant_properties"

    elif any(word in question for word in ["manager", "managers"]):
        return "estate_managers"

    elif any(word in question for word in ["maintenance", "team"]):
        return "maintenance_teams"

    elif any(word in question for word in ["resident", "residents"]):
        return "residents"

    return "general"

def ask_llm(prompt: str):

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
    return content or ""


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
    
    # ---------- RESIDENT BY PROPERTY ----------
    property_match = re.search(
        r"who lives in (.+)",
        question,
        re.IGNORECASE
    )

    if property_match:
        property_number = property_match.group(1).strip().rstrip("?").strip()

        print(">>> RESIDENT BY PROPERTY QUERY USED <<<")
        print(">>> PROPERTY:", property_number)

        return (
            f"""
    MATCH (r:Resident)-[:LIVES_IN]->(p:Property)
    WHERE p.property_number = $property_number

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


def explain_results(question: str, data):

    if data and len(data) == 1:
        row = data[0]

        if "resident_count" in row:
            return f"There are {row['resident_count']} registered residents."

    prompt = f"""
You are EstateGraph AI.

You MUST answer ONLY from the database results.

Rules:
- Never invent information.
- Never guess.
- Never summarize unrelated fields.
- If the user asks for estates, talk ONLY about estates.
- If the user asks for residents, talk ONLY about residents.
- If the user asks for complaints, talk ONLY about complaints.
- If the user asks for properties, talk ONLY about properties.
- Ignore fields unrelated to the user's question.
- If the database returned no records, reply:
  "No matching records were found."

User Question:
{question}

Database Results:
{data}

Return ONLY the final answer.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "You answer only from database results. Never hallucinate."
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content.strip()
