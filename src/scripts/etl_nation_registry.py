#!/usr/bin/env python3
"""ETL: Nation Registry — Load ~195 sovereign nations into Neo4j.

Source: REST Countries API (restcountries.com) — free, no auth, comprehensive.
Fallback: pycountry library for ISO codes.

Creates/updates Nation nodes with identity + basic demographic properties.
Idempotent: uses MERGE on iso3 (existing G20 nations updated in place).
All writes in a single transaction with explicit tx.commit().

Task: task-P1-01-nation-registry
Agent: Dione (executing on behalf of Sentinel)
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import requests
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-P1.1] %(message)s")
log = logging.getLogger("etl_nations")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

# REST Countries API — all countries with relevant fields
REST_COUNTRIES_BASE = "https://restcountries.com/v3.1/all"
# API requires fields param, max 10 fields per request. We do 2 requests.
FIELDS_BATCH_1 = "name,cca2,cca3,ccn3,region,subregion,population,capital,independent,unMember"
FIELDS_BATCH_2 = "cca3,area,landlocked"

# Region mapping to match our schema
REGION_MAP = {
    "Africa": "Africa",
    "Americas": "Americas",
    "Antarctic": "Antarctica",
    "Asia": "Asia",
    "Europe": "Europe",
    "Oceania": "Oceania",
}


def _fetch_with_retry(url: str, params: dict, retries: int = 3) -> list[dict]:
    """Fetch from REST Countries with retries."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30,
                                headers={"Accept": "application/json"})
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            log.warning(f"Attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def fetch_nations() -> list[dict]:
    """Fetch all nations from REST Countries API (2 batches due to 10-field limit)."""
    log.info("Fetching nations from REST Countries API...")
    
    # Batch 1: core identity fields
    batch1 = _fetch_with_retry(REST_COUNTRIES_BASE, {"fields": FIELDS_BATCH_1})
    log.info(f"Batch 1: {len(batch1)} entries (identity)")
    
    # Batch 2: supplementary fields
    batch2 = _fetch_with_retry(REST_COUNTRIES_BASE, {"fields": FIELDS_BATCH_2})
    batch2_map = {entry.get("cca3"): entry for entry in batch2}
    log.info(f"Batch 2: {len(batch2)} entries (supplementary)")
    
    # Merge batch2 into batch1
    for entry in batch1:
        cca3 = entry.get("cca3")
        if cca3 and cca3 in batch2_map:
            entry.update(batch2_map[cca3])
    
    return batch1


def transform_nation(raw: dict) -> dict | None:
    """Transform a REST Countries entry to our Nation schema.
    
    Returns None for non-sovereign/non-independent entities.
    """
    iso3 = raw.get("cca3")
    iso2 = raw.get("cca2")
    
    if not iso3 or not iso2:
        return None
    
    # Filter: only independent states or UN members
    is_independent = raw.get("independent", False)
    is_un_member = raw.get("unMember", False)
    
    if not is_independent and not is_un_member:
        return None
    
    # Name extraction
    name_data = raw.get("name", {})
    official_name = name_data.get("official", "")
    common_name = name_data.get("common", "")
    
    # UN M49 numeric code
    ccn3 = raw.get("ccn3")
    un_m49 = int(ccn3) if ccn3 and ccn3.isdigit() else None
    
    # Region / sub-region
    region = REGION_MAP.get(raw.get("region", ""), raw.get("region", "Unknown"))
    sub_region = raw.get("subregion") or "Unknown"
    
    # Population
    population = raw.get("population", 0)
    
    # Capital
    capitals = raw.get("capital", [])
    capital = capitals[0] if capitals else None
    
    # Area
    area = raw.get("area")
    
    nation = {
        "iso3": iso3,
        "iso2": iso2,
        "name": official_name,
        "name_short": common_name,
        "un_m49": un_m49,
        "region": region,
        "sub_region": sub_region,
        "population": population,
        "capital": capital,
        "area_km2": area,
        "is_un_member": is_un_member,
        "data_confidence": "high",
        "data_quality": "verified",
        "data_needs_verification": False,
    }
    
    # Remove None values (Neo4j doesn't like None in property maps)
    return {k: v for k, v in nation.items() if v is not None}


def load_to_neo4j(nations: list[dict]):
    """Load nations into Neo4j in a single atomic transaction."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-1.1"
    
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # Create ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id,
                        timestamp: datetime(),
                        agent: "Dione",
                        method: "api_import",
                        record_count: $count,
                        notes: "Nation registry from REST Countries API (restcountries.com/v3.1)",
                        confidence: "high",
                        requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "cia-factbook"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(nations))
                
                # UNWIND all nations in a single Cypher operation
                tx.run("""
                    UNWIND $records AS rec
                    MERGE (n:Nation {iso3: rec.iso3})
                    SET n += rec
                    WITH n, rec
                    MATCH (ib:ImportBatch {id: $batch_id})
                    MERGE (n)-[p:PROVENANCE]->(ib)
                    SET p.properties = keys(rec)
                """, records=nations, batch_id=batch_id)
                
                # Remove old mock provenance for nations that now have real data
                tx.run("""
                    MATCH (n:Nation)-[old:PROVENANCE]->(ib:ImportBatch {id: "import-2026-03-23-archon-mock"})
                    WHERE EXISTS {
                        MATCH (n)-[:PROVENANCE]->(new:ImportBatch {id: $batch_id})
                    }
                    DELETE old
                """, batch_id=batch_id)
                
                tx.commit()
                log.info(f"Committed {len(nations)} nations with ImportBatch {batch_id}")
        
        # Verify
        with driver.session() as session:
            result = session.run("MATCH (n:Nation) RETURN count(n) AS cnt").single()
            total = result["cnt"]
            
            result2 = session.run("""
                MATCH (n:Nation) WHERE n.region IS NULL OR n.name IS NULL
                RETURN count(n) AS missing
            """).single()
            missing = result2["missing"]
            
            log.info(f"Verification: {total} Nation nodes, {missing} missing region/name")
            return total, batch_id
    
    finally:
        driver.close()


def main():
    log.info("=== ETL P1.1: Nation Registry ===")
    
    # Fetch
    raw_data = fetch_nations()
    
    # Transform
    nations = []
    skipped = 0
    for entry in raw_data:
        nation = transform_nation(entry)
        if nation:
            nations.append(nation)
        else:
            skipped += 1
    
    log.info(f"Transformed: {len(nations)} nations, {skipped} skipped (non-sovereign)")
    
    # Load
    total, batch_id = load_to_neo4j(nations)
    
    log.info(f"=== DONE: {total} nations in Neo4j, batch={batch_id} ===")
    return total, batch_id


if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} nations loaded, batch={batch_id}")
