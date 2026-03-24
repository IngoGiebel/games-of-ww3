
import os
import sys
from neo4j import GraphDatabase, exceptions
from datetime import datetime

# Hardcoded list of alliances and their members
# Sources: Wikipedia, CIA World Factbook, official organization websites
ALLIANCES = {
    "NATO": {
        "members": ["ALB", "BEL", "BGR", "CAN", "HRV", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "ISL", "ITA", "LVA", "LTU", "LUX", "MNE", "NLD", "MKD", "NOR", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE", "TUR", "GBR", "USA"],
        "type": "Military"
    },
    "BRICS": {
        "members": ["BRA", "RUS", "IND", "CHN", "ZAF", "EGY", "ETH", "IRN", "SAU", "ARE"],
        "type": "Economic"
    },
    "SCO": {  # Shanghai Cooperation Organisation
        "members": ["CHN", "IND", "IRN", "KAZ", "KGZ", "PAK", "RUS", "TJK", "UZB"],
        "type": "Political-Economic-Security"
    },
    "G20": {
        "members": ["ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IND", "IDN", "ITA", "JPN", "MEX", "RUS", "SAU", "ZAF", "KOR", "TUR", "GBR", "USA", "EU", "AFU"], # AFU = African Union
        "type": "Economic"
    },
    "EU": { # European Union - Supranational
        "members": ["AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"],
        "type": "Supranational"
    },
    "ASEAN": { # Association of Southeast Asian Nations
        "members": ["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "VNM"],
        "type": "Political-Economic"
    },
    "AU": { # African Union
        "members": ["DZA", "AGO", "BEN", "BWA", "BFA", "BDI", "CPV", "CMR", "CAF", "TCD", "COM", "COD", "COG", "CIV", "DJI", "EGY", "GNQ", "ERI", "SWZ", "ETH", "GAB", "GMB", "GHA", "GIN", "GNB", "KEN", "LSO", "LBR", "LBY", "MDG", "MWI", "MLI", "MRT", "MUS", "MAR", "MOZ", "NAM", "NER", "NGA", "RWA", "STP", "SEN", "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN", "TZA", "TGO", "TUN", "UGA", "ESH", "ZMB", "ZWE"],
        "type": "Political-Economic"
    },
    "AUKUS": {
        "members": ["AUS", "GBR", "USA"],
        "type": "Military"
    },
    "QUAD": { # Quadrilateral Security Dialogue
        "members": ["USA", "IND", "AUS", "JPN"],
        "type": "Strategic Forum"
    },
    "OPEC": {
        "members": ["DZA", "AGO", "COG", "GNQ", "GAB", "IRN", "IRQ", "KWT", "LBY", "NGA", "SAU", "ARE", "VEN"],
        "type": "Economic Cartel"
    },
    "OPEC+": {
        "members": ["DZA", "AGO", "COG", "GNQ", "GAB", "IRN", "IRQ", "KWT", "LBY", "NGA", "SAU", "ARE", "VEN", "AZE", "BHR", "BRN", "KAZ", "MYS", "MEX", "OMN", "RUS", "SSD", "SDN"],
        "type": "Economic Cartel"
    },
    "CSTO": { # Collective Security Treaty Organization
        "members": ["ARM", "BLR", "KAZ", "KGZ", "RUS", "TJK"],
        "type": "Military"
    },
    "GCC": { # Gulf Cooperation Council
        "members": ["BHR", "KWT", "OMN", "QAT", "SAU", "ARE"],
        "type": "Political-Economic"
    },
    "MERCOSUR": {
        "members": ["ARG", "BOL", "BRA", "PRY", "URY", "VEN"],
        "type": "Economic"
    },
    "ECOWAS": { # Economic Community of West African States
        "members": ["BEN", "BFA", "CPV", "CIV", "GMB", "GHA", "GIN", "GNB", "LBR", "NER", "NGA", "SEN", "SLE", "TGO"],
        "type": "Political-Economic"
    },
    "CIS": { # Commonwealth of Independent States
        "members": ["ARM", "AZE", "BLR", "KAZ", "KGZ", "MDA", "RUS", "TJK", "UZB"],
        "type": "Political-Economic"
    },
    "Arab League": {
        "members": ["DZA", "BHR", "COM", "DJI", "EGY", "IRQ", "JOR", "KWT", "LBN", "LBY", "MRT", "MAR", "OMN", "PSE", "QAT", "SAU", "SOM", "SDN", "SYR", "TUN", "ARE", "YEM"],
        "type": "Political"
    },
    "Five Eyes": {
        "members": ["USA", "GBR", "CAN", "AUS", "NZL"],
        "type": "Intelligence"
    },
    "G7": {
        "members": ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR", "USA", "EU"],
        "type": "Economic"
    },
    "Pacific Islands Forum": {
        "members": ["AUS", "COK", "FJI", "PYF", "KIR", "NCL", "NRU", "NZL", "NIU", "PLW", "PNG", "MHL", "FSM", "SLB", "TON", "TUV", "VUT", "WSM"],
        "type": "Political"
    }
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

    def load_alliances(self, alliances_data):
        query = """
        UNWIND $alliances as alliance_data
        // Merge the Alliance node and link to the ImportBatch
        MERGE (a:Alliance {name: alliance_data.name})
        ON CREATE SET a.type = alliance_data.type, a.created_at = datetime()
        ON MATCH SET a.type = alliance_data.type, a.updated_at = datetime()
        WITH a, alliance_data, $batch_id as batch_id
        MATCH (b:ImportBatch) WHERE id(b) = batch_id
        MERGE (a)-[:PROVENANCE]->(b)

        // Process members
        WITH a, alliance_data, batch_id
        UNWIND alliance_data.members as member_code
        OPTIONAL MATCH (n:Nation {id: member_code})
        WITH a, n, member_code, batch_id
        // Create the membership relationship if the nation was found
        FOREACH (_ IN CASE WHEN n IS NOT NULL THEN [1] ELSE [] END |
            MERGE (n)-[r:MEMBER_OF]->(a)
            ON CREATE SET
                r.start_date = date('1900-01-01'),
                r.created_at = datetime(),
                r.provenance_id = batch_id
        )
        // Log missing nations
        WITH n, member_code
        FOREACH (_ IN CASE WHEN n IS NULL THEN [1] ELSE [] END |
            MERGE (l:LogEntry {
                level: 'WARNING',
                message: 'Nation not found during alliance import',
                nation_code: member_code
            })
        )
        """
        self.tx.run(query, alliances=alliances_data, batch_id=self.batch_id)


def main():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not all([uri, user, password]):
        print("FATAL: Missing Neo4j connection details in environment.", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    script_name = os.path.basename(__file__)
    source_name = "cia-factbook"

    try:
        with ImportBatch(driver, script_name, source_name) as batch:
            print(f"INFO: Acquired transaction and ImportBatch ID: {batch.batch_id}")
            alliance_list = [
                {"name": name, "type": data["type"], "members": data["members"]}
                for name, data in ALLIANCES.items()
            ]
            batch.load_alliances(alliance_list)
            print(f"INFO: Staged {len(alliance_list)} alliances for commit.")
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
