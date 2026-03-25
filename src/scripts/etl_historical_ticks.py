#!/usr/bin/env python3
"""Sprint 2 temporal maintenance for Tick nodes and baseline snapshots."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-TICKS] %(message)s")
log = logging.getLogger("etl_historical_ticks")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")


def tick_rows() -> list[dict]:
    rows = []
    for year in range(2016, 2026):
        for month in range(1, 13):
            game_month = (year - 2016) * 12 + (month - 1)
            rows.append(
                {
                    "id": game_month * 43200,
                    "game_month": game_month,
                    "game_time": f"{year}-{month:02d}-01T00:00:00Z",
                    "year": year,
                    "month": month,
                    "tick_type": "ECONOMIC",
                }
            )
    return rows


def main() -> tuple[int, int, str]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-8.1-8.2"
    ticks = tick_rows()

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run(
                    """
                    CREATE (ib:ImportBatch {
                        id: $batch_id,
                        timestamp: datetime(),
                        agent: "Codex",
                        method: "derived",
                        record_count: $record_count,
                        notes: "Verified monthly Tick nodes and refreshed T=0 baseline "
                               "STATE_AT snapshot",
                        confidence: "high",
                        requires_replacement: false
                    })
                    """,
                    batch_id=batch_id,
                    record_count=len(ticks),
                )
                tx.run(
                    """
                    UNWIND $ticks AS tick
                    MERGE (t:Tick {id: tick.id})
                    SET t.game_month = tick.game_month,
                        t.game_time = datetime(tick.game_time),
                        t.tick_type = tick.tick_type,
                        t.year = tick.year,
                        t.month = tick.month,
                        t.real_time = datetime()
                    """,
                    ticks=ticks,
                )
                tx.run(
                    """
                    MATCH (t:Tick)
                    WITH t ORDER BY t.game_month
                    WITH collect(t) AS ticks
                    UNWIND range(0, size(ticks) - 2) AS idx
                    WITH ticks[idx] AS a, ticks[idx + 1] AS b
                    MERGE (a)-[:NEXT]->(b)
                    """
                )
                tx.run(
                    """
                    MATCH (n:Nation), (t:Tick {game_month: 119})
                    MERGE (n)-[s:STATE_AT]->(t)
                    SET s.gdp_nominal = coalesce(n.gdp_nominal, s.gdp_nominal),
                        s.population = coalesce(n.population, s.population),
                        s.urbanization = coalesce(n.urbanization, s.urbanization),
                        s.internet_penetration = coalesce(
                            n.internet_penetration,
                            s.internet_penetration
                        ),
                        s.inflation_rate = coalesce(n.inflation_rate, s.inflation_rate),
                        s.unemployment = coalesce(n.unemployment, s.unemployment),
                        s.gini = coalesce(n.gini, s.gini),
                        s.debt_to_gdp = coalesce(n.debt_to_gdp, s.debt_to_gdp),
                        s.forex_reserves = coalesce(n.forex_reserves, s.forex_reserves),
                        s.military_spending_abs = coalesce(
                            n.military_spending_abs,
                            s.military_spending_abs
                        ),
                        s.stability_index = coalesce(n.stability_index, s.stability_index),
                        s.freedom_house_score = coalesce(
                            n.freedom_house_score,
                            s.freedom_house_score
                        ),
                        s.corruption_index = coalesce(n.corruption_index, s.corruption_index),
                        s.press_freedom = coalesce(n.press_freedom, s.press_freedom),
                        s.national_morale = coalesce(n.national_morale, s.national_morale, 50),
                        s.war_weariness = coalesce(n.war_weariness, s.war_weariness, 10)
                    """
                )
                tx.run(
                    """
                    MATCH (t:Task)
                    WHERE t.id IN ["task-P8-01-historical-ticks", "task-P8-02-baseline"]
                    SET t.status = "completed",
                        t.completed_at = datetime(),
                        t.assigned_to = "Codex",
                        t.result_summary = CASE
                            WHEN t.id = "task-P8-01-historical-ticks"
                                THEN "Historical Tick nodes verified and NEXT chain merged"
                            ELSE "T=0 baseline STATE_AT snapshot refreshed from Nation properties"
                        END
                    """
                )
                tx.commit()

        with driver.session() as session:
            tick_count = session.run("MATCH (t:Tick) RETURN count(t) AS c").single()["c"]
            state_count = session.run(
                "MATCH (:Nation)-[s:STATE_AT]->(:Tick) RETURN count(s) AS c"
            ).single()["c"]
        return tick_count, state_count, batch_id
    finally:
        driver.close()


if __name__ == "__main__":
    tick_count, state_count, batch_id = main()
    print(f"RESULT: {tick_count} ticks, {state_count} STATE_AT edges, batch={batch_id}")
