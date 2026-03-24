#!/usr/bin/env python3
"""ETL: Borders — Create BORDERS relationships between nations.

Source: REST Countries API v3.1 (borders field gives ISO-3 codes of neighbors).
Creates bidirectional BORDERS relationships (A→B and B→A via MERGE).

Task: task-P1-03-borders
Agent: Dione
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import requests
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-P1.3] %(message)s")
log = logging.getLogger("etl_borders")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")


def fetch_borders() -> list[dict]:
    """Fetch border data from REST Countries API."""
    log.info("Fetching borders from REST Countries API...")
    
    for attempt in range(3):
        try:
            resp = requests.get(
                "https://restcountries.com/v3.1/all",
                params={"fields": "cca3,borders"},
                headers={"Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            log.warning(f"Attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    
    raise RuntimeError("Failed to fetch borders after 3 attempts")


def extract_border_pairs(raw_data: list[dict]) -> list[tuple[str, str]]:
    """Extract unique border pairs (A, B) where A < B to avoid duplicates."""
    pairs = set()
    for entry in raw_data:
        iso3 = entry.get("cca3")
        borders = entry.get("borders", [])
        if not iso3 or not borders:
            continue
        for neighbor in borders:
            pair = tuple(sorted([iso3, neighbor]))
            pairs.add(pair)
    
    return sorted(pairs)


def load_to_neo4j(pairs: list[tuple[str, str]]):
    """Create BORDERS relationships in Neo4j."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-1.3"
    
    # Convert pairs to records for UNWIND
    records = [{"a": a, "b": b} for a, b in pairs]
    
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # Create ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "api_import", record_count: $count,
                        notes: "Land borders from REST Countries API v3.1 (borders field)",
                        confidence: "high", requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "cia-factbook"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, count=len(records))
                
                # Create BORDERS relationships (bidirectional via 2 MERGEs)
                # Some border neighbors may not be in our Nation registry (e.g., territories)
                # Use OPTIONAL MATCH patterns to skip those gracefully
                result = tx.run("""
                    UNWIND $pairs AS pair
                    MATCH (a:Nation {iso3: pair.a})
                    MATCH (b:Nation {iso3: pair.b})
                    MERGE (a)-[:BORDERS]->(b)
                    MERGE (b)-[:BORDERS]->(a)
                    RETURN count(*) AS created
                """, pairs=records)
                created = result.single()["created"]
                
                tx.commit()
        
        # Verify
        with driver.session() as session:
            r = session.run("MATCH ()-[b:BORDERS]->() RETURN count(b) AS cnt").single()
            total_edges = r["cnt"]
            
            r2 = session.run("""
                MATCH (n:Nation)-[b:BORDERS]-() 
                WITH n, count(b) AS neighbors 
                RETURN count(n) AS nations_with_borders, avg(neighbors) AS avg_neighbors
            """).single()
        
        log.info(f"Committed {created} border pairs, {total_edges} total BORDERS edges")
        log.info(f"{r2['nations_with_borders']} nations with borders, avg {r2['avg_neighbors']:.1f} neighbors")
        return total_edges, batch_id
    
    finally:
        driver.close()


def main():
    log.info("=== ETL P1.3: Borders ===")
    
    raw = fetch_borders()
    pairs = extract_border_pairs(raw)
    log.info(f"Extracted {len(pairs)} unique border pairs")
    
    total_edges, batch_id = load_to_neo4j(pairs)
    log.info(f"=== DONE: {total_edges} BORDERS edges, batch={batch_id} ===")
    return total_edges, batch_id


if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} BORDERS edges, batch={batch_id}")
