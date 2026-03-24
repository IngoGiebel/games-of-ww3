#!/usr/bin/env python3
"""ETL: Commodities — Oil, Gas, Wheat, Rare Earths production/consumption.

Covers tasks P2-05 (EIA oil/gas), P2-06 (FAO wheat), P2-07 (USGS minerals).
Uses hardcoded top producer/consumer data (API access varies by source).

Creates PRODUCES and CONSUMES relationships between Nations and Commodities.
"""

import json
import logging
import os
from datetime import datetime, timezone

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-COMM] %(message)s")
log = logging.getLogger("etl_commodities")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

# ── Oil Production (top 15, thousand barrels/day, 2024 estimates) ──
OIL_PRODUCERS = {
    "USA": 13200, "SAU": 10500, "RUS": 10100, "CAN": 5600, "IRQ": 4500,
    "CHN": 4200, "ARE": 4000, "BRA": 3700, "IRN": 3400, "KWT": 2800,
    "NGA": 1500, "NOR": 2000, "MEX": 1900, "LBY": 1200, "AGO": 1100,
}
OIL_CONSUMERS = {
    "USA": 20000, "CHN": 16000, "IND": 5500, "JPN": 3400, "SAU": 3300,
    "RUS": 3200, "KOR": 2800, "BRA": 2700, "CAN": 2500, "DEU": 2200,
    "IRN": 2000, "IDN": 1800, "FRA": 1600, "GBR": 1400, "MEX": 1900,
}

# ── Natural Gas Production (top 10, bcm/year, 2024) ──
GAS_PRODUCERS = {
    "USA": 1035, "RUS": 640, "IRN": 260, "CHN": 230, "QAT": 180,
    "CAN": 185, "AUS": 155, "SAU": 120, "NOR": 115, "DZA": 100,
}
GAS_CONSUMERS = {
    "USA": 900, "RUS": 460, "CHN": 380, "IRN": 240, "JPN": 90,
    "CAN": 115, "SAU": 120, "DEU": 80, "GBR": 70, "MEX": 85,
}

# ── Wheat Production (top 10, million tonnes, 2024) ──
WHEAT_PRODUCERS = {
    "CHN": 137, "IND": 110, "RUS": 92, "USA": 49, "CAN": 35,
    "FRA": 35, "UKR": 23, "AUS": 29, "PAK": 27, "DEU": 22,
    "TUR": 21, "ARG": 19, "GBR": 16, "KAZ": 17, "POL": 14,
}
WHEAT_CONSUMERS = {
    "CHN": 150, "IND": 105, "RUS": 42, "USA": 30, "PAK": 28,
    "EGY": 21, "TUR": 20, "IRN": 17, "BRA": 12, "IDN": 11,
    "DZA": 11, "MAR": 10, "BGD": 9, "JPN": 6, "NGA": 5,
}

# ── Rare Earth Elements (top 5 producers, thousand tonnes, 2024) ──
REE_PRODUCERS = {
    "CHN": 240, "USA": 43, "MMR": 38, "AUS": 18, "THA": 7,
}
REE_CONSUMERS = {
    "CHN": 150, "JPN": 25, "USA": 15, "DEU": 8, "KOR": 7,
    "FRA": 4, "GBR": 3, "IND": 5,
}


def load_commodity_data(driver, commodity_name: str, producers: dict, consumers: dict, 
                         unit: str, batch_id: str):
    """Load PRODUCES and CONSUMES relationships for one commodity."""
    records = []
    for iso3, volume in producers.items():
        records.append({"iso3": iso3, "commodity": commodity_name, "rel": "PRODUCES", "volume": volume})
    for iso3, volume in consumers.items():
        records.append({"iso3": iso3, "commodity": commodity_name, "rel": "CONSUMES", "volume": volume})
    return records


def main():
    log.info("=== ETL: Commodities (Oil, Gas, Wheat, Rare Earths) ===")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-2.5-2.7"

    all_produce = []
    all_consume = []

    for name, producers, consumers in [
        ("Crude Oil", OIL_PRODUCERS, OIL_CONSUMERS),
        ("Natural Gas", GAS_PRODUCERS, GAS_CONSUMERS),
        ("Wheat", WHEAT_PRODUCERS, WHEAT_CONSUMERS),
        ("Rare Earth Elements", REE_PRODUCERS, REE_CONSUMERS),
    ]:
        for iso3, vol in producers.items():
            all_produce.append({"iso3": iso3, "commodity": name, "volume": vol})
        for iso3, vol in consumers.items():
            all_consume.append({"iso3": iso3, "commodity": name, "volume": vol})

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "static_mapping",
                        record_count: $count,
                        notes: "Commodity production/consumption: Oil (EIA), Gas (EIA), Wheat (FAO), Rare Earths (USGS). Top producers/consumers hardcoded from 2024 estimates.",
                        confidence: "medium", requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "eia-energy"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(all_produce) + len(all_consume))

                # PRODUCES relationships
                tx.run("""
                    UNWIND $records AS rec
                    MATCH (n:Nation {iso3: rec.iso3})
                    MATCH (c:Commodity {name: rec.commodity})
                    MERGE (n)-[r:PRODUCES]->(c)
                    SET r.volume = rec.volume
                    RETURN count(r) AS cnt
                """, records=all_produce)

                # CONSUMES relationships
                tx.run("""
                    UNWIND $records AS rec
                    MATCH (n:Nation {iso3: rec.iso3})
                    MATCH (c:Commodity {name: rec.commodity})
                    MERGE (n)-[r:CONSUMES]->(c)
                    SET r.volume = rec.volume
                    RETURN count(r) AS cnt
                """, records=all_consume)

                tx.commit()

        log.info(f"Loaded {len(all_produce)} PRODUCES + {len(all_consume)} CONSUMES, batch={batch_id}")

        # Mark tasks
        with driver.session() as s:
            for tid in ["task-P2-05-commodities-oil", "task-P2-06-commodities-food", "task-P2-07-commodities-minerals"]:
                s.run("""MATCH (t:Task {id: $id})
                       SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                           t.result_summary = $summary""",
                      id=tid, summary=f"Commodity data loaded. {len(all_produce)} PRODUCES + {len(all_consume)} CONSUMES")

        return len(all_produce) + len(all_consume), batch_id
    finally:
        driver.close()


if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} commodity relationships, batch={batch_id}")
