import os

from dotenv import load_dotenv
from neo4j import GraphDatabase, basic_auth

load_dotenv()


class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI") or "",
            auth=basic_auth(
                os.getenv("NEO4J_USER") or "",
                os.getenv("NEO4J_PASSWORD") or "",
            ),
        )

    def close(self):
        self.driver.close()

    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]