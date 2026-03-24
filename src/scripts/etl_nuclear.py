#!/usr/bin/env python3
"""ETL: FAS Nuclear Warhead Counts - Load warhead estimates for all nations.

Source: Federation of American Scientists (FAS) Nuclear Notebook
URL: https://fas.org/initiative/status-world-nuclear-forces/

Sets `nuclear_warheads` and `nuclear_status` for all 195 Nation nodes based on
latest FAS estimates.

- 9 nuclear-armed states get their specific counts and status.
- The remaining 186 nations are set to 0 warheads and "none" status.

This script uses a single transaction to update all nations and attach
provenance records.

Task: task-P3-03-nuclear
Agent: Sentinel
"""

import logging
import os
from datetime import datetime, timezone

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-P3.3] %(message)s")
log = logging.getLogger("etl_nuclear")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

# Data from FAS, status of world nuclear forces.
# DPRK/PRK and ISR estimates are less certain.
NUCLEAR_DATA = {
    # Declared nuclear-weapon states under NPT
    "RUS": {"warheads": 5977, "status": "declared"},
    "USA": {"warheads": 5550, "status": "declared"},
    "CHN": {"warheads": 500, "status": "declared"},
    "FRA": {"warheads": 290, "status": "declared"},
    "GBR": {"warheads": 225, "status": "declared"},
    # Non-NPT nuclear powers
    "PAK": {"warheads": 170, "status": "declared"},
    "IND": {"warheads": 164, "status": "declared"},
    "ISR": {"warheads": 90, "status": "undeclared"},
    # NPT-withdrawn nuclear power
    "PRK": {"warheads": 50, "status": "declared"},
}

DEFAULT_DATA = {"warheads": 0, "status": "none"}
PROPERTIES_SET = ["nuclear_warheads", "nuclear_status"]

def load_to_neo4j(nuclear_map: dict):
    """Load nuclear warhead counts to Neo4j Nation nodes."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-3.3"
    
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # 1. Create the ImportBatch node for provenance
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id,
                        timestamp: datetime(),
                        agent: "Sentinel",
                        method: "scripted_import",
                        record_count: $count,
                        notes: "FAS Nuclear Notebook warhead estimates",
                        confidence: "medium",
                        requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "fas-nuclear"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(nuclear_map))
                
                # 2. Update all Nation nodes in a single query
                result = tx.run("""
                    WITH $nuclear_map AS nuclear_map
                    MATCH (n:Nation)
                    WITH n, COALESCE(nuclear_map[n.iso3], $default_data) AS data
                    SET n.nuclear_warheads = data.warheads,
                        n.nuclear_status = data.status
                    WITH n
                    MATCH (ib:ImportBatch {id: $batch_id})
                    MERGE (n)-[p:PROVENANCE]->(ib)
                    SET p.properties = $props
                    RETURN count(n) AS updated_count
                """, nuclear_map=nuclear_map, default_data=DEFAULT_DATA,
                       batch_id=batch_id, props=PROPERTIES_SET)
                
                summary = result.single()
                updated_count = summary["updated_count"] if summary else 0
                
                tx.commit()
                
        log.info(f"Committed nuclear data for {updated_count} nations, batch={batch_id}")
        return updated_count, batch_id
    finally:
        driver.close()


def main():
    log.info("=== ETL P3.3: FAS Nuclear Warhead Counts ===")
    
    # Load to Neo4j
    updated, batch_id = load_to_neo4j(NUCLEAR_DATA)
    
    log.info(f"=== DONE: {updated} nations updated with nuclear data, batch={batch_id} ===")
    return updated, batch_id


if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} nations updated with nuclear data, batch={batch_id}")
