#!/usr/bin/env python3
"""ETL: World Bank GDP — Load 10-year GDP time series for all nations.

Source: World Bank WDI API (api.worldbank.org)
Indicator: NY.GDP.MKTP.CD (GDP in current USD)
Period: 2016-2025 (10 years)

Task: task-P2-01-wb-gdp
Agent: Dione
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-P2.1] %(message)s")
log = logging.getLogger("etl_wb_gdp")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

WB_API = "https://api.worldbank.org/v2"
INDICATOR = "NY.GDP.MKTP.CD"
DATE_RANGE = "2016:2025"
PER_PAGE = 500


def fetch_worldbank_indicator(indicator, date_range):
    all_records = []
    page = 1
    while True:
        for attempt in range(3):
            try:
                resp = requests.get(f"{WB_API}/country/all/indicator/{indicator}",
                    params={"format": "json", "per_page": PER_PAGE, "date": date_range, "page": page},
                    timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.RequestException, json.JSONDecodeError) as e:
                log.warning(f"Page {page} attempt {attempt+1}/3: {e}")
                if attempt < 2: time.sleep(5 * (attempt + 1))
                else: raise
        if len(data) < 2 or not data[1]: break
        all_records.extend(data[1])
        log.info(f"Page {page}/{data[0].get('pages',1)}: {len(data[1])} records")
        if page >= data[0].get("pages", 1): break
        page += 1
        time.sleep(0.5)
    return all_records


def transform_records(raw):
    nations = {}
    for r in raw:
        iso3 = r.get("countryiso3code", "")
        if not iso3 or len(iso3) != 3: continue
        year, value = int(r["date"]), r.get("value")
        if iso3 not in nations:
            nations[iso3] = {"timeseries": {}, "latest_gdp": None, "latest_year": None}
        if value is not None:
            value = float(value)
            nations[iso3]["timeseries"][year] = value
            if nations[iso3]["latest_year"] is None or year > nations[iso3]["latest_year"]:
                nations[iso3]["latest_gdp"] = value
                nations[iso3]["latest_year"] = year
    return nations


def compute_cagr(ts):
    years = sorted(ts.keys())
    if len(years) < 2: return None
    f, l = ts[years[0]], ts[years[-1]]
    if not f or f <= 0: return None
    n = years[-1] - years[0]
    return round(((l/f)**(1/n) - 1) * 100, 2) if n > 0 else None


def load_to_neo4j(nations_data):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-2.1a"
    records = []
    for iso3, d in nations_data.items():
        if d["latest_gdp"] is None: continue
        cagr = compute_cagr(d["timeseries"])
        props = {"gdp_nominal": d["latest_gdp"], "gdp_nominal_year": d["latest_year"]}
        if cagr is not None: props["gdp_10yr_cagr"] = cagr
        records.append({"iso3": iso3, "properties": props, "prop_names": list(props.keys())})
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("""
                    CREATE (ib:ImportBatch {id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "api_import", record_count: $count,
                        notes: "World Bank WDI: NY.GDP.MKTP.CD (GDP current USD) 2016-2025",
                        confidence: "high", requires_replacement: false})
                    WITH ib MATCH (ds:DataSource {id: "worldbank-wdi"}) MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(records))
                result = tx.run("""
                    UNWIND $records AS rec MATCH (n:Nation {iso3: rec.iso3})
                    SET n += rec.properties WITH n, rec
                    MATCH (ib:ImportBatch {id: $batch_id})
                    MERGE (n)-[p:PROVENANCE]->(ib) SET p.properties = rec.prop_names
                    RETURN count(n) AS updated
                """, records=records, batch_id=batch_id)
                updated = result.single()["updated"]
                tx.commit()
        log.info(f"Committed {updated} nations, batch={batch_id}")
        return updated, batch_id
    finally:
        driver.close()


def save_timeseries(nations_data):
    ts = {iso3: {"indicator": INDICATOR, "timeseries": {str(k):v for k,v in sorted(d["timeseries"].items())},
           "latest_year": d["latest_year"], "latest_value": d["latest_gdp"], "cagr_10yr": compute_cagr(d["timeseries"])}
          for iso3, d in nations_data.items() if d["timeseries"]}
    Path("data/timeseries").mkdir(parents=True, exist_ok=True)
    with open("data/timeseries/worldbank_gdp.json", "w") as f: json.dump(ts, f, indent=2)
    log.info(f"Saved time series for {len(ts)} nations")


def main():
    log.info("=== ETL P2.1: World Bank GDP (10-year) ===")
    raw = fetch_worldbank_indicator(INDICATOR, DATE_RANGE)
    log.info(f"Fetched {len(raw)} raw records")
    nations = transform_records(raw)
    has_data = sum(1 for v in nations.values() if v["latest_gdp"] is not None)
    log.info(f"Transformed: {len(nations)} countries, {has_data} with GDP data")
    save_timeseries(nations)
    updated, batch_id = load_to_neo4j(nations)
    log.info(f"=== DONE: {updated} nations with GDP, batch={batch_id} ===")
    return updated, batch_id

if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} nations with GDP data, batch={batch_id}")
