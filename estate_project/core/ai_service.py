from groq import Groq
from django.conf import settings
from .schema import GRAPH_SCHEMA


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
        model="llama-3.3-70b-versatile",
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
    
    if "show all estates" in q or "list all estates" in q:
        print(">>> HARDCODED ESTATE QUERY USED <<<")
        return """
    MATCH (e:Estate)
    RETURN
    e.estate_id AS estate_id,
    e.name AS name
    ORDER BY e.name
    """.strip()

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

MATCH (r:Resident)-[:LIVES_IN]->(:Property)-[:PART_OF]->(e:Estate)

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
-[:MANAGED_BY]->
(m:Manager)

RETURN
m.name AS manager


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
        model="llama-3.3-70b-versatile",
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
    return (content or "").strip()


def explain_results(question: str, data):

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
        model="llama-3.3-70b-versatile",
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