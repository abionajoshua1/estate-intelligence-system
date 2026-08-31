from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "Theuniverse1@")
)

try:
    with driver.session(database="neo4jcypher25") as session:
        result = session.run("RETURN 1 AS test")
        print(result.single()["test"])
finally:
    driver.close()