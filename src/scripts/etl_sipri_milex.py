
import os
import sys
from neo4j import GraphDatabase, exceptions
from datetime import datetime

#
# Placeholder data. Assumes SIPRI data in constant USD millions.
# TODO: Replace with real SIPRI data.
#
TOP_50_SPENDERS = {
    "United States of America": 916000,
    "People's Republic of China": 296000,
    "Russian Federation": 109000,
    "Republic of India": 83600,
    "Kingdom of Saudi Arabia": 75800,
    "United Kingdom of Great Britain and Northern Ireland": 74900,
    "Federal Republic of Germany": 66800,
    "Ukraine": 64800,
    "French Republic": 61300,
    "Japan": 50200,
    "Republic of Korea": 47900,
    "Italian Republic": 35500,
    "Commonwealth of Australia": 32300,
    "Canada": 28700,
    "State of Israel": 27500,
    "Kingdom of Spain": 23700,
    "Republic of Poland": 22900,
    "Federative Republic of Brazil": 22300,
    "Republic of Turkey": 18900,
    "Kingdom of the Netherlands": 18500,
    "State of Qatar": 17400,
    "Republic of Singapore": 16900,
    "Taiwan": 16600,  # Note: May not be in the database
    "People's Democratic Republic of Algeria": 15900,
    "United Mexican States": 14800,
    "Republic of Colombia": 14500,
    "Islamic Republic of Iran": 13400,
    "Islamic Republic of Pakistan": 12500,
    "Republic of Indonesia": 11800,
    "State of Kuwait": 11500,
    "Kingdom of Sweden": 11200,
    "Kingdom of Norway": 10900,
    "Swiss Confederation": 10500,
    "Sultanate of Oman": 10200,
    "Kingdom of Belgium": 9800,
    "Hellenic Republic": 9500,
    "Kingdom of Denmark": 9200,
    "Republic of Finland": 8900,
    "Republic of Austria": 8600,
    "Kingdom of Thailand": 8200,
    "Romania": 7900,
    "Republic of Chile": 7600,
    "Czech Republic": 7300,
    "Bolivarian Republic of Venezuela": 7000,
    "Kingdom of Morocco": 6800,
    "Republic of the Philippines": 6500,
    "People's Republic of Bangladesh": 6200,
    "Hungary": 5900
}

class ImportBatch:
    def __init__(self, driver, script_name, source):
        self.driver = driver
        self.script_name = script_name
        self.source = source
        self.tx = None
        self.batch_id = None

    def __enter__(self):
        self.tx = self.driver.session().begin_transaction()
        try:
            # MERGE the ImportBatch node
            result = self.tx.run(
                """
                MERGE (b:ImportBatch {script: $script, source: $source})
                ON CREATE SET b.created_at = datetime(), b.updated_at = datetime()
                ON MATCH SET b.updated_at = datetime()
                RETURN id(b) as id
                """,
                script=self.script_name,
                source=self.source
            )
            self.batch_id = result.single()["id"]
            return self
        except Exception:
            self.tx.rollback()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.tx:
            if exc_type is None:
                self.tx.commit()
            else:
                self.tx.rollback()

    def load_milex(self, milex_data):
        query = """
        UNWIND $milex_data as data
        MATCH (b:ImportBatch) WHERE id(b) = data.batch_id
        OPTIONAL MATCH (n:Nation {name: data.country})
        WITH n, data, b
        CALL {
            WITH n, data, b
            FOREACH (_ IN CASE WHEN n IS NOT NULL THEN [1] ELSE [] END |
                MERGE (m:MilitaryExpenditure {year: data.year, nation_name: n.name})
                ON CREATE SET
                    m.usd = data.spending,
                    m.created_at = datetime()
                ON MATCH SET
                    m.usd = data.spending,
                    m.updated_at = datetime()
                MERGE (m)-[:PROVENANCE]->(b)
                MERGE (n)-[:HAS_MILEX]->(m)
            )
            FOREACH (_ IN CASE WHEN n IS NULL THEN [1] ELSE [] END |
                MERGE (l:LogEntry {
                    level: 'WARNING',
                    message: 'Nation not found during SIPRI MILEX import',
                    nation_code: data.country
                })
                MERGE (l)-[:PROVENANCE]->(b)
            )
        }
        RETURN count(n) as found_nations
        """
        self.tx.run(query, milex_data=milex_data)


def validate_record(spending):
    if spending is None or spending < 0:
        return False
    return True


def main():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not all([uri, user, password]):
        print("FATAL: Missing Neo4j connection details in environment.", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    script_name = os.path.basename(__file__)
    source_name = "sipri-2023-placeholder"

    try:
        with ImportBatch(driver, script_name, source_name) as batch:
            print(f"INFO: Acquired transaction and ImportBatch ID: {batch.batch_id}")
            milex_data = []
            for country, spending_m in TOP_50_SPENDERS.items():
                if validate_record(spending_m):
                    milex_data.append(
                        {
                            "country": country,
                            "year": 2023,
                            "spending": int(spending_m * 1_000_000),
                            "batch_id": batch.batch_id,
                        }
                    )
            batch.load_milex(milex_data)
            print(f"INFO: Staged {len(milex_data)} military expenditure records for commit.")
        print("INFO: Transaction committed successfully.")

    except exceptions.ServiceUnavailable as e:
        print(f"FATAL: Neo4j connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: An error occurred during the transaction: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        driver.close()
        print("INFO: Database connection closed.")


if __name__ == "__main__":
    main()
