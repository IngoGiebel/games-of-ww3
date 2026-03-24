#!/usr/bin/env python3
"""ETL: Chokepoints — Maritime chokepoints with transit data.

Task: task-P6-01-chokepoints
Agent: Dione
"""

import logging
import os
from datetime import datetime, timezone

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-CP] %(message)s")
log = logging.getLogger("etl_cp")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

CHOKEPOINTS = [
    {"name": "Strait of Hormuz", "type": "maritime", "oil_transit_mbpd": 21.0,
     "total_trade_pct": 0.25, "controlling_nations": ["IRN", "OMN"],
     "alternative_routes": ["Cape of Good Hope"], "vulnerability": "critical"},
    {"name": "Strait of Malacca", "type": "maritime", "oil_transit_mbpd": 16.0,
     "total_trade_pct": 0.30, "controlling_nations": ["MYS", "IDN", "SGP"],
     "alternative_routes": ["Lombok Strait", "Sunda Strait"], "vulnerability": "critical"},
    {"name": "Suez Canal", "type": "canal", "oil_transit_mbpd": 5.5,
     "total_trade_pct": 0.12, "controlling_nations": ["EGY"],
     "alternative_routes": ["Cape of Good Hope"], "vulnerability": "high"},
    {"name": "Bab el-Mandeb", "type": "maritime", "oil_transit_mbpd": 6.2,
     "total_trade_pct": 0.10, "controlling_nations": ["YEM", "DJI", "ERI"],
     "alternative_routes": ["Cape of Good Hope"], "vulnerability": "critical"},
    {"name": "Panama Canal", "type": "canal", "oil_transit_mbpd": 0.9,
     "total_trade_pct": 0.05, "controlling_nations": ["PAN"],
     "alternative_routes": ["Strait of Magellan", "Cape Horn"], "vulnerability": "moderate"},
    {"name": "Bosphorus", "type": "maritime", "oil_transit_mbpd": 3.0,
     "total_trade_pct": 0.03, "controlling_nations": ["TUR"],
     "alternative_routes": [], "vulnerability": "high"},
    {"name": "GIUK Gap", "type": "maritime", "oil_transit_mbpd": 0.0,
     "total_trade_pct": 0.08, "controlling_nations": ["GBR", "ISL", "NOR"],
     "alternative_routes": [], "vulnerability": "moderate"},
    {"name": "Taiwan Strait", "type": "maritime", "oil_transit_mbpd": 5.0,
     "total_trade_pct": 0.20, "controlling_nations": ["CHN", "TWN"],
     "alternative_routes": ["Pacific routing via Philippines"], "vulnerability": "critical"},
    {"name": "Cape of Good Hope", "type": "maritime", "oil_transit_mbpd": 0.0,
     "total_trade_pct": 0.05, "controlling_nations": ["ZAF"],
     "alternative_routes": [], "vulnerability": "low"},
    {"name": "Danish Straits", "type": "maritime", "oil_transit_mbpd": 3.2,
     "total_trade_pct": 0.02, "controlling_nations": ["DNK"],
     "alternative_routes": ["Kiel Canal"], "vulnerability": "moderate"},
]


def main():
    log.info("=== ETL P6.1: Chokepoints ===")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-6.1"

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "static_mapping", record_count: $count,
                        notes: "Maritime chokepoints with EIA oil transit data + strategic assessment",
                        confidence: "high", requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "eia-energy"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(CHOKEPOINTS))

                for cp in CHOKEPOINTS:
                    controllers = cp.pop("controlling_nations")
                    tx.run("""
                        MERGE (c:Chokepoint {name: $name})
                        SET c += $props
                        WITH c
                        MATCH (ib:ImportBatch {id: $batch_id})
                        MERGE (c)-[:PROVENANCE]->(ib)
                    """, name=cp["name"], props=cp, batch_id=batch_id)

                    for iso3 in controllers:
                        tx.run("""
                            MATCH (n:Nation {iso3: $iso3})
                            MATCH (c:Chokepoint {name: $name})
                            MERGE (n)-[:CONTROLS]->(c)
                        """, iso3=iso3, name=cp["name"])

                tx.commit()

        log.info(f"Loaded {len(CHOKEPOINTS)} chokepoints, batch={batch_id}")

        with driver.session() as s:
            s.run("""MATCH (t:Task {id: "task-P6-01-chokepoints"})
                   SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                       t.result_summary = $summary""",
                  summary=f"{len(CHOKEPOINTS)} chokepoints with transit data + CONTROLS edges")

        return len(CHOKEPOINTS), batch_id
    finally:
        driver.close()


if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} chokepoints, batch={batch_id}")
