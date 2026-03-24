import os
import sys
from neo4j import GraphDatabase, exceptions

# Placeholder data for major arms transfers (2016-2025).
# Value is in millions of USD.
ARMS_DATA = [
    {"exporter": "USA", "importer": "SAU", "year": 2022, "value": 3500, "system": "F-15SA Fighter Jets", "status": "delivered"},
    {"exporter": "USA", "importer": "AUS", "year": 2024, "value": 2000, "system": "M1 Abrams Tanks", "status": "ordered"},
    {"exporter": "USA", "importer": "QAT", "year": 2021, "value": 1200, "system": "Patriot PAC-3 Missiles", "status": "delivered"},
    {"exporter": "USA", "importer": "JPN", "year": 2023, "value": 3300, "system": "F-35 Fighter Jets", "status": "ordered"},
    {"exporter": "RUS", "importer": "IND", "year": 2021, "value": 5430, "system": "S-400 Missile System", "status": "delivered"},
    {"exporter": "RUS", "importer": "EGY", "year": 2022, "value": 2000, "system": "Su-35 Fighter Jets", "status": "delivered"},
    {"exporter": "FRA", "importer": "IND", "year": 2020, "value": 8700, "system": "Rafale Fighter Jets", "status": "delivered"},
    {"exporter": "FRA", "importer": "QAT", "year": 2019, "value": 1100, "system": "NH90 Helicopters", "status": "delivered"},
    {"exporter": "DEU", "importer": "EGY", "year": 2021, "value": 2500, "system": "Type 209 Submarines", "status": "ordered"},
    {"exporter": "CHN", "importer": "PAK", "year": 2022, "value": 1500, "system": "Type 054A/P Frigates", "status": "delivered"},
    {"exporter": "GBR", "importer": "SAU", "year": 2018, "value": 5000, "system": "Typhoon Fighter Jets", "status": "ordered"},
    {"exporter": "ISR", "importer": "IND", "year": 2019, "value": 777, "system": "Barak-8 Missile Systems", "status": "delivered"},
    {"exporter": "KOR", "importer": "AUS", "year": 2023, "value": 700, "system": "K9 Thunder Howitzers", "status": "ordered"},
    {"exporter": "ITA", "importer": "EGY", "year": 2020, "value": 1200, "system": "FREMM Frigates", "status": "delivered"},
    {"exporter": "ESP", "importer": "SAU", "year": 2018, "value": 2200, "system": "Avante 2200 Corvettes", "status": "ordered"},
]

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

    def load_arms_deals(self, deal_data):
        query = """
        UNWIND $deal_data as data
        MATCH (b:ImportBatch) WHERE id(b) = data.batch_id
        MATCH (exporter:Nation {iso3: data.exporter})
        MATCH (importer:Nation {iso3: data.importer})

        MERGE (deal:ArmsDeal {exporter_iso3: data.exporter, importer_iso3: data.importer, system: data.system, year: data.year})
        ON CREATE SET
            deal.value_usd_mln = data.value,
            deal.status = data.status,
            deal.created_at = datetime()
        ON MATCH SET
            deal.value_usd_mln = data.value,
            deal.status = data.status,
            deal.updated_at = datetime()

        MERGE (exporter)-[:EXPORTED_ARMS]->(deal)
        MERGE (deal)-[:IMPORTED_ARMS]->(importer)
        MERGE (deal)-[:PROVENANCE]->(b)
        """
        self.tx.run(query, deal_data=deal_data)

def validate_record(record):
    required_keys = ["exporter", "importer", "year", "value", "system", "status"]
    for key in required_keys:
        if key not in record or record[key] is None:
            return False
    if not isinstance(record["value"], int) or record["value"] <= 0:
        return False
    if not isinstance(record["year"], int) or not (2016 <= record["year"] <= 2025):
        return False
    return True

def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        print("FATAL: NEO4J_PASSWORD environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    script_name = os.path.basename(__file__)
    source_name = "sipri-arms"

    try:
        with ImportBatch(driver, script_name, source_name) as batch:
            print(f"INFO: Acquired transaction and ImportBatch ID: {batch.batch_id}")
            
            deal_list = []
            for item in ARMS_DATA:
                if validate_record(item):
                    normalized_item = item.copy()
                    normalized_item["value"] = item["value"] * 1_000_000
                    normalized_item["batch_id"] = batch.batch_id
                    deal_list.append(normalized_item)
                else:
                    print(f"WARNING: Skipping invalid arms deal record: {item}", file=sys.stderr)

            if not deal_list:
                print("INFO: No valid arms deals to load.")
                return

            batch.load_arms_deals(deal_list)
            print(f"INFO: Staged {len(deal_list)} arms deals for commit.")
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
