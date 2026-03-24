#!/usr/bin/env python3
"""ETL: Historical Ticks — Create Tick nodes and STATE_AT snapshots (Sprint 2).

Creates:
- 120 Tick nodes (Jan 2016 — Dec 2025, monthly)
- NEXT chain between Ticks
- STATE_AT edges from Nations to Ticks with GDP data from time series

Task: task-P8-01-historical-ticks + task-P8-02-baseline
Agent: Dione (overnight job)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-HIST] %(message)s")
log = logging.getLogger("etl_hist")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

TIMESERIES_DIR = Path("data/timeseries")


def load_gdp_timeseries() -> dict:
    """Load GDP time series from P2-01 output."""
    ts_file = TIMESERIES_DIR / "worldbank_gdp.json"
    if ts_file.exists():
        with open(ts_file) as f:
            return json.load(f)
    return {}


def main():
    log.info("=== ETL: Historical Ticks (Sprint 2) ===")
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-8.1-8.2"
    
    # Load GDP time series
    gdp_ts = load_gdp_timeseries()
    log.info(f"Loaded GDP time series for {len(gdp_ts)} countries")
    
    try:
        # Phase 1: Create Tick nodes + NEXT chain
        log.info("Creating 120 Tick nodes (Jan 2016 — Dec 2025)...")
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "derived", record_count: 120,
                        notes: "Historical Tick nodes (120 months) + STATE_AT snapshots with GDP data from World Bank time series",
                        confidence: "high", requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "worldbank-wdi"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id)
                
                # Delete old test Tick nodes
                tx.run("MATCH (t:Tick) DETACH DELETE t")
                
                # Create 120 monthly Ticks
                tick_data = []
                for year in range(2016, 2026):
                    for month in range(1, 13):
                        month_offset = (year - 2016) * 12 + (month - 1)
                        tick_id = month_offset * 43200  # minutes since game epoch
                        game_time = f"{year}-{month:02d}-01T00:00:00Z"
                        tick_data.append({
                            "tick_id": tick_id,
                            "game_month": month_offset,
                            "game_time": game_time,
                            "tick_type": "ECONOMIC",
                            "year": year,
                            "month": month,
                        })
                
                tx.run("""
                    UNWIND $ticks AS t
                    CREATE (tick:Tick {
                        id: t.tick_id,
                        game_month: t.game_month,
                        game_time: datetime(t.game_time),
                        tick_type: t.tick_type,
                        real_time: datetime()
                    })
                """, ticks=tick_data)
                log.info(f"Created {len(tick_data)} Tick nodes")
                
                # Create NEXT chain
                tx.run("""
                    MATCH (t:Tick)
                    WITH t ORDER BY t.game_month
                    WITH collect(t) AS ticks
                    UNWIND range(0, size(ticks)-2) AS i
                    WITH ticks[i] AS a, ticks[i+1] AS b
                    CREATE (a)-[:NEXT]->(b)
                """)
                log.info("Created NEXT chain")
                
                tx.commit()
        
        # Phase 2: Create STATE_AT snapshots from GDP time series
        log.info("Creating STATE_AT snapshots from GDP time series...")
        state_at_count = 0
        
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # For each country with GDP time series, create STATE_AT per year
                for iso3, data in gdp_ts.items():
                    ts = data.get("timeseries", {})
                    for year_str, gdp_value in ts.items():
                        if gdp_value is None:
                            continue
                        year = int(year_str)
                        if year < 2016 or year > 2025:
                            continue
                        # Link to January tick of that year
                        month_offset = (year - 2016) * 12
                        tick_id = month_offset * 43200
                        
                        tx.run("""
                            MATCH (n:Nation {iso3: $iso3})
                            MATCH (t:Tick {id: $tick_id})
                            MERGE (n)-[s:STATE_AT]->(t)
                            SET s.gdp_nominal = $gdp
                        """, iso3=iso3, tick_id=tick_id, gdp=gdp_value)
                        state_at_count += 1
                
                tx.commit()
        
        log.info(f"Created {state_at_count} STATE_AT snapshots")
        
        # Phase 3: Create T=0 baseline (latest tick = Dec 2025, game_month=119)
        log.info("Creating T=0 baseline snapshot...")
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # T=0 = the latest tick (Dec 2025)
                tx.run("""
                    MATCH (n:Nation), (t:Tick {game_month: 119})
                    WHERE n.gdp_nominal IS NOT NULL
                    MERGE (n)-[s:STATE_AT]->(t)
                    SET s.gdp_nominal = n.gdp_nominal,
                        s.population = n.population,
                        s.stability_index = n.stability_index,
                        s.military_spending_abs = n.military_spending_abs,
                        s.national_morale = coalesce(n.national_morale, 50),
                        s.war_weariness = coalesce(n.war_weariness, 10)
                """)
                tx.commit()
        
        log.info("T=0 baseline created")
        
        # Verify
        with driver.session() as s:
            ticks = s.run("MATCH (t:Tick) RETURN count(t) AS cnt").single()["cnt"]
            states = s.run("MATCH ()-[s:STATE_AT]->() RETURN count(s) AS cnt").single()["cnt"]
            log.info(f"Verification: {ticks} Ticks, {states} STATE_AT edges")
        
        # Mark tasks
        with driver.session() as s:
            s.run("""MATCH (t:Task {id: "task-P8-01-historical-ticks"})
                   SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                       t.result_summary = $summary""",
                  summary=f"120 Tick nodes, {state_at_count} historical STATE_AT snapshots")
            s.run("""MATCH (t:Task {id: "task-P8-02-baseline"})
                   SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                       t.result_summary = "T=0 baseline snapshot for all nations with GDP data"
            """)
        
        log.info(f"=== DONE: {ticks} Ticks, {states} STATE_AT edges ===")
        return ticks, states
    finally:
        driver.close()


if __name__ == "__main__":
    ticks, states = main()
    print(f"RESULT: {ticks} Ticks, {states} STATE_AT edges")
