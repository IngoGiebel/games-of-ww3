import os
import sys
from neo4j import GraphDatabase, exceptions

# Placeholder data for top bilateral trade pairs.
# Value is in billions of USD (approximate).
TRADE_DATA = [
    {"from": "USA", "to": "CHN", "value": 505, "commodity": "electronics", "friction": 0.6},
    {"from": "CHN", "to": "USA", "value": 148, "commodity": "general_goods", "friction": 0.6},
    {"from": "USA", "to": "MEX", "value": 307, "commodity": "vehicles", "friction": 0.2},
    {"from": "MEX", "to": "USA", "value": 401, "commodity": "vehicles", "friction": 0.2},
    {"from": "USA", "to": "CAN", "value": 309, "commodity": "oil", "friction": 0.1},
    {"from": "CAN", "to": "USA", "value": 331, "commodity": "vehicles", "friction": 0.1},
    {"from": "DEU", "to": "CHN", "value": 117, "commodity": "vehicles", "friction": 0.4},
    {"from": "CHN", "to": "DEU", "value": 180, "commodity": "machinery", "friction": 0.4},
    {"from": "DEU", "to": "FRA", "value": 130, "commodity": "vehicles", "friction": 0.1},
    {"from": "FRA", "to": "DEU", "value": 80, "commodity": "machinery", "friction": 0.1},
    {"from": "CHN", "to": "JPN", "value": 173, "commodity": "electronics", "friction": 0.3},
    {"from": "JPN", "to": "CHN", "value": 147, "commodity": "machinery", "friction": 0.3},
    {"from": "USA", "to": "DEU", "value": 89, "commodity": "vehicles", "friction": 0.2},
    {"from": "DEU", "to": "USA", "value": 156, "commodity": "vehicles", "friction": 0.2},
    {"from": "CHN", "to": "KOR", "value": 162, "commodity": "electronics", "friction": 0.2},
    {"from": "KOR", "to": "CHN", "value": 139, "commodity": "electronics", "friction": 0.2},
    {"from": "IND", "to": "USA", "value": 80, "commodity": "general_goods", "friction": 0.4},
    {"from": "USA", "to": "IND", "value": 45, "commodity": "machinery", "friction": 0.4},
    {"from": "RUS", "to": "CHN", "value": 73, "commodity": "oil", "friction": 0.5},
    {"from": "CHN", "to": "RUS", "value": 50, "commodity": "machinery", "friction": 0.5},
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

    def load_trades(self, trade_data):
        query = """
        UNWIND $trade_data as data
        MATCH (b:ImportBatch) WHERE id(b) = data.batch_id
        MATCH (n_from:Nation {iso3: data.from})
        MATCH (n_to:Nation {iso3: data.to})
        MERGE (n_from)-[r:TRADES {commodity_type: data.commodity}]->(n_to)
        ON CREATE SET
            r.value_usd = data.value,
            r.friction_pct = data.friction,
            r.year = 2023,
            r.created_at = datetime()
        ON MATCH SET
            r.value_usd = data.value,
            r.friction_pct = data.friction,
            r.updated_at = datetime()
        MERGE (r)-[:PROVENANCE]->(b)
        """
        self.tx.run(query, trade_data=trade_data)

def validate_record(record):
    if not all(k in record for k in ["from", "to", "value", "commodity", "friction"]):
        return False
    if record["value"] <= 0 or record["friction"] < 0 or record["friction"] > 1:
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
    source_name = "un-comtrade"

    try:
        with ImportBatch(driver, script_name, source_name) as batch:
            print(f"INFO: Acquired transaction and ImportBatch ID: {batch.batch_id}")
            
            trade_list = []
            for item in TRADE_DATA:
                if validate_record(item):
                    normalized_item = item.copy()
                    normalized_item["value"] = item["value"] * 1_000_000_000
                    normalized_item["friction"] = item["friction"] * 100
                    normalized_item["batch_id"] = batch.batch_id
                    trade_list.append(normalized_item)
                else:
                    print(f"WARNING: Skipping invalid trade record: {item}", file=sys.stderr)

            if not trade_list:
                print("INFO: No valid trade data to load.")
                return

            batch.load_trades(trade_list)
            print(f"INFO: Staged {len(trade_list)} trade relationships for commit.")
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
