#!/usr/bin/env python3
"""ETL: Domestic Factions — Derive from governance data.

For Sprint 1: Create 2-3 generic factions per nation based on regime type.
Detailed factions with real party names will come in Sprint 3.

Task: task-P4-02-factions
Agent: Dione
"""

import logging
import os
from datetime import datetime, timezone

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-FAC] %(message)s")
log = logging.getLogger("etl_factions")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")


def main():
    log.info("=== ETL P4.2: Domestic Factions (generic) ===")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-4.2"

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "derived", record_count: 0,
                        notes: "Generic domestic factions derived from stability_index. 2-3 factions per nation. Sprint 3 will add real party names.",
                        confidence: "low", requires_replacement: true,
                        derivation_formula: "stability > 60: ruling_party(70) + opposition(50) + civil_society(40). stability 30-60: ruling_elite(80) + opposition_bloc(40) + military(60). stability < 30: regime(90) + security_forces(80) + underground_opposition(20)"
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "vdem"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id)

                # Delete old mock factions first
                tx.run("MATCH (f:DomesticFaction) DETACH DELETE f")

                # Democratic nations (stability > 60): ruling party + opposition + civil society
                tx.run("""
                    MATCH (n:Nation) WHERE n.stability_index > 60
                    CREATE (f1:DomesticFaction {name: n.name_short + " Ruling Coalition", ideology: "Centrist", influence: 70, loyalty_to_leader: 75, popular_support: 45})
                    CREATE (f2:DomesticFaction {name: n.name_short + " Opposition", ideology: "Reform", influence: 50, loyalty_to_leader: 30, popular_support: 35})
                    CREATE (f3:DomesticFaction {name: n.name_short + " Civil Society", ideology: "Liberal", influence: 40, loyalty_to_leader: 20, popular_support: 20})
                    CREATE (n)-[:HAS_FACTION]->(f1)
                    CREATE (n)-[:HAS_FACTION]->(f2)
                    CREATE (n)-[:HAS_FACTION]->(f3)
                """)

                # Hybrid regimes (stability 30-60): ruling elite + opposition bloc + military
                tx.run("""
                    MATCH (n:Nation) WHERE n.stability_index > 30 AND n.stability_index <= 60
                    CREATE (f1:DomesticFaction {name: n.name_short + " Ruling Elite", ideology: "Establishment", influence: 80, loyalty_to_leader: 85, popular_support: 35})
                    CREATE (f2:DomesticFaction {name: n.name_short + " Opposition Bloc", ideology: "Reform", influence: 40, loyalty_to_leader: 15, popular_support: 30})
                    CREATE (f3:DomesticFaction {name: n.name_short + " Military", ideology: "Nationalist", influence: 60, loyalty_to_leader: 70, popular_support: 15})
                    CREATE (n)-[:HAS_FACTION]->(f1)
                    CREATE (n)-[:HAS_FACTION]->(f2)
                    CREATE (n)-[:HAS_FACTION]->(f3)
                """)

                # Authoritarian (stability <= 30): regime + security forces + underground opposition
                tx.run("""
                    MATCH (n:Nation) WHERE n.stability_index <= 30 AND n.stability_index IS NOT NULL
                    CREATE (f1:DomesticFaction {name: n.name_short + " Regime", ideology: "Authoritarian", influence: 90, loyalty_to_leader: 95, popular_support: 25})
                    CREATE (f2:DomesticFaction {name: n.name_short + " Security Forces", ideology: "Loyalist", influence: 80, loyalty_to_leader: 90, popular_support: 10})
                    CREATE (f3:DomesticFaction {name: n.name_short + " Underground Opposition", ideology: "Dissident", influence: 20, loyalty_to_leader: 5, popular_support: 30})
                    CREATE (n)-[:HAS_FACTION]->(f1)
                    CREATE (n)-[:HAS_FACTION]->(f2)
                    CREATE (n)-[:HAS_FACTION]->(f3)
                """)

                # Nations without governance data: 2 generic factions
                tx.run("""
                    MATCH (n:Nation) WHERE n.stability_index IS NULL
                    AND NOT EXISTS { MATCH (n)-[:HAS_FACTION]->() }
                    CREATE (f1:DomesticFaction {name: n.name_short + " Government", ideology: "Status Quo", influence: 70, loyalty_to_leader: 70, popular_support: 40})
                    CREATE (f2:DomesticFaction {name: n.name_short + " Opposition", ideology: "Change", influence: 30, loyalty_to_leader: 20, popular_support: 30})
                    CREATE (n)-[:HAS_FACTION]->(f1)
                    CREATE (n)-[:HAS_FACTION]->(f2)
                """)

                tx.commit()

        # Count results
        with driver.session() as s:
            r = s.run("MATCH (f:DomesticFaction) RETURN count(f) AS cnt").single()
            faction_count = r["cnt"]
            r2 = s.run("MATCH (n:Nation)-[:HAS_FACTION]->() RETURN count(DISTINCT n) AS cnt").single()
            nation_count = r2["cnt"]

        log.info(f"Created {faction_count} factions for {nation_count} nations")

        with driver.session() as s:
            s.run("""MATCH (t:Task {id: "task-P4-02-factions"})
                   SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                       t.result_summary = $summary""",
                  summary=f"{faction_count} generic factions for {nation_count} nations (2-3 per nation)")

        return faction_count, batch_id
    finally:
        driver.close()


if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} factions, batch={batch_id}")
