#!/usr/bin/env python3
"""ETL: World Bank — All indicators (demographics + macro) for Sprint 1.

Covers tasks P2-02 (demographics) and P2-03 (macro) in one script.
Also re-fetches P2-01 GDP data for completeness.

Source: World Bank WDI API
Period: Latest available year per nation
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-WB] %(message)s")
log = logging.getLogger("etl_wb")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

WB_API = "https://api.worldbank.org/v2"

# All indicators we need
INDICATORS = {
    # Demographics (P2-02)
    "SP.POP.TOTL": "population",
    "SP.URB.TOTL.IN.ZS": "urbanization",
    "IT.NET.USER.ZS": "internet_penetration",
    # Macro (P2-03)
    "FP.CPI.TOTL.ZG": "inflation_rate",
    "SL.UEM.TOTL.ZS": "unemployment",
    "SI.POV.GINI": "gini",
    "GC.DOD.TOTL.GD.ZS": "debt_to_gdp",
    "FI.RES.TOTL.CD": "forex_reserves",
    # GDP extras
    "NY.GDP.MKTP.KD.ZG": "gdp_growth",
    "NY.GDP.PCAP.CD": "gdp_per_capita",
}


def fetch_indicator(indicator, date_range="2020:2025"):
    """Fetch one indicator for all countries, return {iso3: {year: value}}."""
    all_records = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{WB_API}/country/all/indicator/{indicator}",
                params={"format": "json", "per_page": 500, "date": date_range, "page": page},
                timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning(f"Failed to fetch {indicator} page {page}: {e}")
            break

        if len(data) < 2 or not data[1]:
            break
        all_records.extend(data[1])
        if page >= data[0].get("pages", 1):
            break
        page += 1
        time.sleep(0.3)

    # Group by iso3, take latest non-null value
    result = {}
    for r in all_records:
        iso3 = r.get("countryiso3code", "")
        if not iso3 or len(iso3) != 3:
            continue
        value = r.get("value")
        year = int(r["date"])
        if value is not None:
            if iso3 not in result or year > result[iso3][1]:
                result[iso3] = (float(value), year)

    return {iso3: v[0] for iso3, v in result.items()}


def main():
    log.info("=== ETL: World Bank All Indicators ===")

    # Fetch all indicators
    all_data = {}  # {iso3: {prop_name: value}}
    for wb_code, prop_name in INDICATORS.items():
        log.info(f"Fetching {wb_code} → {prop_name}")
        values = fetch_indicator(wb_code)
        for iso3, val in values.items():
            all_data.setdefault(iso3, {})[prop_name] = val
        log.info(f"  Got {len(values)} countries")
        time.sleep(0.5)

    # Special: population should be integer
    for iso3, props in all_data.items():
        if "population" in props:
            props["population"] = int(props["population"])

    # Build records for Neo4j
    records = []
    for iso3, props in all_data.items():
        if props:
            records.append({
                "iso3": iso3,
                "properties": props,
                "prop_names": list(props.keys()),
            })

    log.info(f"Total: {len(records)} countries with data")

    # Load to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-2.2-2.3"

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "api_import", record_count: $count,
                        notes: "World Bank WDI: demographics (pop, urban, internet) + macro (inflation, unemployment, gini, debt, forex, gdp_growth, gdp_per_capita)",
                        confidence: "high", requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "worldbank-wdi"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(records))

                result = tx.run("""
                    UNWIND $records AS rec
                    MATCH (n:Nation {iso3: rec.iso3})
                    SET n += rec.properties
                    WITH n, rec
                    MATCH (ib:ImportBatch {id: $batch_id})
                    MERGE (n)-[p:PROVENANCE]->(ib)
                    SET p.properties = rec.prop_names
                    RETURN count(n) AS updated
                """, records=records, batch_id=batch_id)
                updated = result.single()["updated"]

                tx.commit()

        log.info(f"Updated {updated} nations, batch={batch_id}")

        # Verify
        with driver.session() as session:
            r = session.run("""
                MATCH (n:Nation)
                WHERE n.population IS NOT NULL AND n.inflation_rate IS NOT NULL
                RETURN count(n) AS complete
            """).single()
            log.info(f"Nations with both population + inflation: {r['complete']}")

        return updated, batch_id
    finally:
        driver.close()


if __name__ == "__main__":
    total, batch_id = main()

    # Mark both tasks complete
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        for task_id in ["task-P2-02-wb-demographics", "task-P2-03-wb-macro"]:
            s.run("""
                MATCH (t:Task {id: $id})
                SET t.status = "completed", t.completed_at = datetime(),
                    t.result_summary = $summary, t.assigned_to = "Dione"
            """, id=task_id, summary=f"{total} nations updated with WB data")
    driver.close()
    print(f"RESULT: {total} nations updated, batch={batch_id}")
