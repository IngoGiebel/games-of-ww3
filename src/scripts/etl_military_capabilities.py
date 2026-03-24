import os
import sys
from neo4j import GraphDatabase, exceptions

# Data provided in task-P3-02-capabilities
# Format: ISO3(manpower_active/manpower_reserve)
CAPABILITIES_DATA = {
    "CHN": {"active": 2035000, "reserve": 510000},
    "IND": {"active": 1455550, "reserve": 1155000},
    "USA": {"active": 1388100, "reserve": 845000},
    "PRK": {"active": 1280000, "reserve": 600000},
    "RUS": {"active": 1150000, "reserve": 2000000},
    "KOR": {"active": 555000, "reserve": 3100000},
    "PAK": {"active": 654000, "reserve": 550000},
    "IRN": {"active": 610000, "reserve": 350000},
    "VNM": {"active": 482000, "reserve": 5000000},
    "EGY": {"active": 438500, "reserve": 479000},
    "MMR": {"active": 406000, "reserve": 0},
    "IDN": {"active": 395500, "reserve": 400000},
    "THA": {"active": 360850, "reserve": 200000},
    "TUR": {"active": 355200, "reserve": 378700},
    "BRA": {"active": 366500, "reserve": 1340000},
    "COL": {"active": 293200, "reserve": 34950},
    "MEX": {"active": 277150, "reserve": 81500},
    "JPN": {"active": 247150, "reserve": 56000},
    "SAU": {"active": 227000, "reserve": 0},
    "DEU": {"active": 183400, "reserve": 30000},
    "FRA": {"active": 203250, "reserve": 35000},
    "GBR": {"active": 148500, "reserve": 37000},
    "ITA": {"active": 165500, "reserve": 18300},
    "ISR": {"active": 169500, "reserve": 465000},
    "UKR": {"active": 900000, "reserve": 250000},
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
                source=self.source,
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

    def load_capabilities(self, capabilities_data):
        query = """
        UNWIND $capabilities_data as data
        MATCH (b:ImportBatch) WHERE id(b) = data.batch_id
        OPTIONAL MATCH (n:Nation {iso3: data.iso3})
        WITH n, data, b
        CALL {
            WITH n, data, b
            FOREACH (_ IN CASE WHEN n IS NOT NULL THEN [1] ELSE [] END |
                MERGE (c:MilitaryCapability {nation_iso3: n.iso3, year: 2024})
                ON CREATE SET
                    c.manpower_active = data.active,
                    c.manpower_reserve = data.reserve,
                    c.created_at = datetime()
                ON MATCH SET
                    c.manpower_active = data.active,
                    c.manpower_reserve = data.reserve,
                    c.updated_at = datetime()
                MERGE (n)-[:HAS_CAPABILITY]->(c)
                MERGE (c)-[:PROVENANCE]->(b)
            )
            FOREACH (_ IN CASE WHEN n IS NULL THEN [1] ELSE [] END |
                MERGE (l:LogEntry {
                    level: 'WARNING',
                    message: 'Nation not found during military capability import',
                    nation_code: data.iso3
                })
                MERGE (l)-[:PROVENANCE]->(b)
            )
        }
        RETURN count(n) as found_nations
        """
        self.tx.run(query, capabilities_data=capabilities_data)


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        print("FATAL: NEO4J_PASSWORD environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    script_name = os.path.basename(__file__)
    source_name = "iiss-milbal"

    try:
        with ImportBatch(driver, script_name, source_name) as batch:
            print(f"INFO: Acquired transaction and ImportBatch ID: {batch.batch_id}")
            capabilities_list = []
            for iso3, data in CAPABILITIES_DATA.items():
                capabilities_list.append(
                    {
                        "iso3": iso3,
                        "active": data["active"],
                        "reserve": data["reserve"],
                        "batch_id": batch.batch_id,
                    }
                )
            batch.load_capabilities(capabilities_list)
            print(f"INFO: Staged {len(capabilities_list)} military capability records for commit.")
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
