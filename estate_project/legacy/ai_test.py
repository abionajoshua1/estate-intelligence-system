from ai_engine import generate_cypher
from core.neo4j_connection import Neo4jConnection


def run_test(question):
    print("\n========================")
    print("QUESTION:", question)
    print("------------------------")

    cypher = generate_cypher(question)
    print("CYPHER:", cypher)

    db = Neo4jConnection()
    result = db.query(cypher)
    db.close()

    print("RESULT:", result)


if __name__ == "__main__":
    questions = [
        "show all residents",
        "list all complaints",
        "show all properties"
    ]

    for q in questions:
        run_test(q)