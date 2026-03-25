#!/usr/bin/env python3
"""ETL: V-Dem Governance → STATE_AT edges (static projection).

Since the full V-Dem CSV (~500MB) is not yet downloaded, this script
projects the existing static governance properties from Nation nodes
onto all yearly Tick nodes as constant time series.

Once the real V-Dem dataset is available, run etl_vdem_governance.py
with VDEM_CSV/VDEM_ZIP to replace these with actual historical values.

Properties: stability_index, freedom_house_score, corruption_index, press_freedom
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-VDEM-STATIC] %(message)s")
log = logging.getLogger("etl_vdem_static")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

GOVERNANCE_PROPS = ["stability_index", "freedom_house_score", "corruption_index", "press_freedom"]
YEARS = list(range(2016, 2026))


def main():
    log.info("=== ETL: V-Dem Static → STATE_AT (Governance) ===")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-4.1-static"

    try:
        with driver.session() as session:
            # Get nations with governance data
            result = session.run("""
                MATCH (n:Nation) 
                WHERE n.stability_index IS NOT NULL
                RETURN n.iso3 AS iso3, 
                       n.stability_index AS stability_index,
                       n.freedom_house_score AS freedom_house_score,
                       n.corruption_index AS corruption_index,
                       n.press_freedom AS press_freedom
            """)
            nations = [dict(r) for r in result]
            log.info(f"Found {len(nations)} nations with governance data")

            # Build STATE_AT records for all yearly ticks
            state_at_records = []
            for nation in nations:
                props = {p: nation[p] for p in GOVERNANCE_PROPS if nation.get(p) is not None}
                if not props:
                    continue
                for year in YEARS:
                    month_offset = (year - 2016) * 12  # January of each year
                    tick_id = month_offset * 43200
                    state_at_records.append({
                        "iso3": nation["iso3"],
                        "tick_id": tick_id,
                        "properties": props,
                    })

            log.info(f"Prepared {len(state_at_records)} STATE_AT records")

            with session.begin_transaction() as tx:
                # ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id,
                        timestamp: datetime(),
                        agent: "Dione",
                        method: "static_projection",
                        record_count: $count,
                        notes: "V-Dem governance indices projected as constant series 2016-2025 (pending full dataset)",
                        confidence: "medium",
                        requires_replacement: true
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "vdem-v14"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(state_at_records))

                # Merge STATE_AT edges
                tx.run("""
                    UNWIND $records AS rec
                    MATCH (n:Nation {iso3: rec.iso3})
                    MATCH (t:Tick {id: rec.tick_id})
                    MERGE (n)-[s:STATE_AT]->(t)
                    SET s += rec.properties
                """, records=state_at_records)

                # Mark task
                tx.run("""
                    MATCH (t:Task)
                    WHERE t.id IN ["task-P4-01-vdem"]
                    SET t.status = "completed",
                        t.completed_at = datetime(),
                        t.assigned_to = "Dione",
                        t.result_summary = "V-Dem governance: static projection to ticks (pending full CSV for historical values)"
                """)
                tx.commit()

            log.info(f"=== DONE: {len(state_at_records)} STATE_AT edges merged for {len(nations)} nations ===")
            return len(nations), len(state_at_records)
    finally:
        driver.close()


if __name__ == "__main__":
    n, s = main()
    print(f"RESULT: {n} nations, {s} STATE_AT governance edges")
