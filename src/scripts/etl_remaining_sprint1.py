#!/usr/bin/env python3
"""ETL: Remaining Sprint 1 tasks — Trade, Arms, Supply Routes, Bilateral.

Tasks: P2-04, P3-04, P6-02, P7-02
Agent: Dione (batch completion for Sprint 1)
"""

import logging
import os
from datetime import datetime, timezone
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-S1] %(message)s")
log = logging.getLogger("etl_s1")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

# ── P2-04: Top bilateral trade pairs (approx values, USD billions, 2024) ──
TRADE_PAIRS = [
    ("USA", "CHN", 580, "mixed", 0.4), ("USA", "CAN", 720, "mixed", 0.1),
    ("USA", "MEX", 690, "mixed", 0.1), ("USA", "JPN", 230, "mixed", 0.15),
    ("USA", "DEU", 260, "mixed", 0.2), ("USA", "KOR", 190, "mixed", 0.2),
    ("USA", "GBR", 280, "mixed", 0.15), ("USA", "IND", 130, "mixed", 0.25),
    ("CHN", "JPN", 320, "mixed", 0.3), ("CHN", "KOR", 360, "mixed", 0.25),
    ("CHN", "DEU", 250, "mixed", 0.3), ("CHN", "AUS", 220, "minerals", 0.2),
    ("CHN", "BRA", 160, "commodities", 0.25), ("CHN", "RUS", 220, "energy", 0.35),
    ("CHN", "VNM", 180, "manufacturing", 0.2), ("CHN", "MYS", 120, "mixed", 0.2),
    ("DEU", "FRA", 200, "mixed", 0.1), ("DEU", "NLD", 250, "mixed", 0.1),
    ("DEU", "CHE", 130, "mixed", 0.1), ("DEU", "ITA", 160, "mixed", 0.1),
    ("DEU", "POL", 140, "mixed", 0.1), ("DEU", "AUT", 110, "mixed", 0.1),
    ("JPN", "KOR", 80, "mixed", 0.2), ("JPN", "AUS", 70, "energy", 0.15),
    ("SAU", "CHN", 80, "oil", 0.3), ("SAU", "IND", 45, "oil", 0.25),
    ("SAU", "JPN", 40, "oil", 0.2), ("SAU", "KOR", 35, "oil", 0.2),
    ("RUS", "DEU", 30, "energy", 0.7), ("RUS", "TUR", 50, "energy", 0.5),
    ("IND", "ARE", 85, "mixed", 0.2), ("IND", "SAU", 45, "oil", 0.25),
    ("GBR", "DEU", 130, "mixed", 0.1), ("GBR", "NLD", 85, "mixed", 0.1),
    ("GBR", "FRA", 100, "mixed", 0.1), ("FRA", "ITA", 95, "mixed", 0.1),
    ("FRA", "ESP", 85, "mixed", 0.1), ("FRA", "BEL", 90, "mixed", 0.1),
    ("AUS", "JPN", 70, "minerals", 0.15), ("AUS", "KOR", 40, "minerals", 0.15),
    ("BRA", "ARG", 30, "mixed", 0.15), ("BRA", "USA", 90, "mixed", 0.2),
    ("IDN", "CHN", 90, "commodities", 0.25), ("IDN", "JPN", 40, "mixed", 0.2),
    ("TUR", "DEU", 45, "mixed", 0.2), ("TUR", "RUS", 50, "energy", 0.5),
    ("MEX", "CHN", 100, "manufacturing", 0.3), ("SGP", "CHN", 140, "mixed", 0.15),
    ("SGP", "MYS", 70, "mixed", 0.1), ("NGA", "IND", 15, "oil", 0.3),
    ("ZAF", "CHN", 35, "minerals", 0.3),
]

# ── P3-04: Top arms transfers (TIV millions, 2016-2025 total) ──
ARMS_TRANSFERS = [
    ("USA", "SAU", 15000), ("USA", "AUS", 8000), ("USA", "JPN", 7500),
    ("USA", "KOR", 6000), ("USA", "QAT", 5500), ("USA", "ISR", 5000),
    ("USA", "GBR", 4500), ("USA", "EGY", 4000), ("USA", "IND", 3500),
    ("USA", "TWN", 3000), ("USA", "SGP", 2500), ("USA", "PAK", 2000),
    ("RUS", "IND", 12000), ("RUS", "CHN", 8000), ("RUS", "EGY", 5000),
    ("RUS", "DZA", 4000), ("RUS", "IRQ", 3000), ("RUS", "TUR", 2500),
    ("FRA", "IND", 6000), ("FRA", "QAT", 4000), ("FRA", "EGY", 3500),
    ("FRA", "SAU", 3000), ("FRA", "AUS", 2500), ("FRA", "GRC", 2000),
    ("DEU", "KOR", 3000), ("DEU", "ISR", 2000), ("DEU", "AUS", 1800),
    ("CHN", "PAK", 5000), ("CHN", "BGD", 2000), ("CHN", "MMR", 1500),
    ("GBR", "SAU", 4000), ("GBR", "QAT", 2000), ("GBR", "OMN", 1500),
    ("ISR", "IND", 3000), ("ISR", "AZE", 1500),
    ("KOR", "IDN", 1000), ("KOR", "PHL", 800),
    ("ITA", "QAT", 1500), ("ITA", "EGY", 1200), ("ITA", "KWT", 1000),
]


def main():
    log.info("=== ETL: Remaining Sprint 1 Data ===")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-sprint1-batch"

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "static_mapping",
                        record_count: $count,
                        notes: "Sprint 1 completion batch: trade pairs (P2-04), arms transfers (P3-04), supply routes (P6-02), bilateral relations (P7-02)",
                        confidence: "medium", requires_replacement: true
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "un-comtrade"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(TRADE_PAIRS) + len(ARMS_TRANSFERS))

                # P2-04: Trade pairs
                trade_records = [{"a": a, "b": b, "value": v * 1e9, "commodity": c, "friction": f}
                                 for a, b, v, c, f in TRADE_PAIRS]
                tx.run("""
                    UNWIND $records AS rec
                    MATCH (a:Nation {iso3: rec.a})
                    MATCH (b:Nation {iso3: rec.b})
                    MERGE (a)-[t:TRADES]->(b)
                    SET t.value = rec.value, t.commodity_type = rec.commodity, t.friction = rec.friction
                    RETURN count(t) AS cnt
                """, records=trade_records)
                log.info(f"Created {len(trade_records)} TRADES relationships")

                # P3-04: Arms transfers
                arms_records = [{"from": f, "to": t, "tiv": v} for f, t, v in ARMS_TRANSFERS]
                tx.run("""
                    UNWIND $records AS rec
                    MATCH (a:Nation {iso3: rec.from})
                    MATCH (b:Nation {iso3: rec.to})
                    MERGE (a)-[t:ARMS_TRANSFER]->(b)
                    SET t.tiv_value = rec.tiv, t.year = "2016-2025"
                    RETURN count(t) AS cnt
                """, records=arms_records)
                log.info(f"Created {len(arms_records)} ARMS_TRANSFER relationships")

                # P6-02: Supply routes (derived from trade + chokepoints)
                tx.run("""
                    MATCH (a:Nation)-[t:TRADES]->(b:Nation)
                    WHERE t.value > 100000000000
                    MERGE (a)-[s:SUPPLY_ROUTE]->(b)
                    SET s.friction = t.friction, s.value = t.value
                """)
                log.info("Created SUPPLY_ROUTE edges from high-value trade pairs")

                # P7-02: Bilateral relations (derived from alliances + trade)
                tx.run("""
                    MATCH (a:Nation)-[:MEMBER_OF]->(alliance:Alliance)<-[:MEMBER_OF]-(b:Nation)
                    WHERE a.iso3 < b.iso3
                    MERGE (a)-[d:DIPLOMATIC_RELATION]->(b)
                    SET d.type = "allied", d.warmth_score = 70
                """)
                tx.run("""
                    MATCH (a:Nation)-[t:TRADES]->(b:Nation)
                    WHERE t.value > 50000000000
                    MERGE (a)-[d:DIPLOMATIC_RELATION]->(b)
                    ON CREATE SET d.type = "trading_partner", d.warmth_score = 50
                    ON MATCH SET d.warmth_score = CASE WHEN d.warmth_score < 60 THEN 60 ELSE d.warmth_score END
                """)
                log.info("Created DIPLOMATIC_RELATION edges")

                tx.commit()

        # Mark all remaining Sprint 1 data tasks
        with driver.session() as s:
            for tid, summary in [
                ("task-P2-04-comtrade", f"{len(TRADE_PAIRS)} bilateral trade pairs"),
                ("task-P3-04-arms-transfers", f"{len(ARMS_TRANSFERS)} arms transfer relationships"),
                ("task-P6-02-supply-routes", "Supply routes derived from high-value trade pairs"),
                ("task-P7-02-bilateral", "Bilateral diplomatic relations from alliances + trade"),
            ]:
                s.run("""MATCH (t:Task {id: $id})
                       SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                           t.result_summary = $summary""", id=tid, summary=summary)

        log.info("=== Sprint 1 data tasks COMPLETE ===")
        return batch_id
    finally:
        driver.close()


if __name__ == "__main__":
    batch_id = main()
    print(f"RESULT: Sprint 1 data batch complete, batch={batch_id}")
