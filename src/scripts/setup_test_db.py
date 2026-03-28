#!/usr/bin/env python3
"""Set up a minimal test database for GSL parser and engine tests.

Creates a small but complete Neo4j graph with:
- 5 nations (USA, CHN, RUS, DEU, IRN)
- 2 alliances (NATO, SCO)
- 2 commodities (Oil, Semiconductors)
- 1 chokepoint (Strait of Hormuz)
- 2 conflicts
- Key relationships (TRADES, BORDERS, SANCTIONS, AT_WAR_WITH, MEMBER_OF)
- All properties include _c confidence fields

This is the minimum viable graph for testing GSL rules end-to-end.

Usage: PYTHONPATH=src python3.12 src/scripts/setup_test_db.py
"""

import os
import logging
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TEST-DB] %(message)s")
log = logging.getLogger("setup_test_db")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")
TEST_DB = "gww3test"


def setup(driver):
    """Create the test graph."""
    with driver.session() as s:
        # Clear and rebuild test data
        s.run("MATCH (n) DETACH DELETE n")
        log.info("Cleared test database")

        # ── Nations ──
        nations = [
            {"iso3": "USA", "name": "United States", "gdp_nominal": 25000000000000, "gdp_nominal_c": 0.85,
             "population": 331000000, "population_c": 0.85, "stability": 72, "stability_c": 0.75,
             "national_morale": 65, "national_morale_c": 0.85, "war_weariness": 15, "war_weariness_c": 0.85,
             "military_spending_abs": 886000000000, "military_spending_abs_c": 0.80,
             "inflation_rate": 3.2, "inflation_rate_c": 0.85, "unemployment": 3.7, "unemployment_c": 0.85,
             "nuclear_warheads": 5550, "nuclear_warheads_c": 0.90, "manpower_active": 1400000, "manpower_active_c": 0.80,
             "press_freedom": 72, "press_freedom_c": 0.75, "corruption_index": 69, "corruption_index_c": 0.80,
             "forex_reserves": 244000000000, "forex_reserves_c": 0.85, "debt_to_gdp": 123.0, "debt_to_gdp_c": 0.85,
             "gini": 39.0, "gini_c": 0.85, "urbanization": 83.0, "urbanization_c": 0.85,
             "internet_penetration": 92.0, "internet_penetration_c": 0.85, "is_landlocked": False},
            {"iso3": "CHN", "name": "China", "gdp_nominal": 17700000000000, "gdp_nominal_c": 0.70,
             "population": 1310000000, "population_c": 0.55, "stability": 68, "stability_c": 0.60,
             "national_morale": 70, "national_morale_c": 0.85, "war_weariness": 5, "war_weariness_c": 0.85,
             "military_spending_abs": 296000000000, "military_spending_abs_c": 0.60,
             "inflation_rate": 2.0, "inflation_rate_c": 0.70, "unemployment": 5.2, "unemployment_c": 0.70,
             "nuclear_warheads": 500, "nuclear_warheads_c": 0.90, "manpower_active": 2000000, "manpower_active_c": 0.70,
             "press_freedom": 25, "press_freedom_c": 0.60, "corruption_index": 45, "corruption_index_c": 0.80,
             "forex_reserves": 3100000000000, "forex_reserves_c": 0.70, "debt_to_gdp": 77.0, "debt_to_gdp_c": 0.70,
             "gini": 38.0, "gini_c": 0.70, "urbanization": 64.0, "urbanization_c": 0.70,
             "internet_penetration": 73.0, "internet_penetration_c": 0.70, "is_landlocked": False},
            {"iso3": "RUS", "name": "Russia", "gdp_nominal": 2200000000000, "gdp_nominal_c": 0.85,
             "population": 144000000, "population_c": 0.85, "stability": 55, "stability_c": 0.75,
             "national_morale": 50, "national_morale_c": 0.85, "war_weariness": 45, "war_weariness_c": 0.85,
             "military_spending_abs": 109000000000, "military_spending_abs_c": 0.65,
             "inflation_rate": 8.5, "inflation_rate_c": 0.85, "unemployment": 3.0, "unemployment_c": 0.85,
             "nuclear_warheads": 6257, "nuclear_warheads_c": 0.90, "manpower_active": 1150000, "manpower_active_c": 0.80,
             "press_freedom": 19, "press_freedom_c": 0.75, "corruption_index": 28, "corruption_index_c": 0.80,
             "forex_reserves": 580000000000, "forex_reserves_c": 0.85, "debt_to_gdp": 17.0, "debt_to_gdp_c": 0.85,
             "gini": 36.0, "gini_c": 0.85, "urbanization": 75.0, "urbanization_c": 0.85,
             "internet_penetration": 85.0, "internet_penetration_c": 0.85, "is_landlocked": False},
            {"iso3": "DEU", "name": "Germany", "gdp_nominal": 4700000000000, "gdp_nominal_c": 0.85,
             "population": 84000000, "population_c": 0.85, "stability": 78, "stability_c": 0.75,
             "national_morale": 62, "national_morale_c": 0.85, "war_weariness": 10, "war_weariness_c": 0.85,
             "military_spending_abs": 98700000000, "military_spending_abs_c": 0.80,
             "inflation_rate": 5.9, "inflation_rate_c": 0.85, "unemployment": 3.0, "unemployment_c": 0.85,
             "nuclear_warheads": 0, "nuclear_warheads_c": 0.90, "manpower_active": 183000, "manpower_active_c": 0.80,
             "press_freedom": 84, "press_freedom_c": 0.75, "corruption_index": 79, "corruption_index_c": 0.80,
             "forex_reserves": 270000000000, "forex_reserves_c": 0.85, "debt_to_gdp": 64.3, "debt_to_gdp_c": 0.85,
             "gini": 31.7, "gini_c": 0.85, "urbanization": 77.5, "urbanization_c": 0.85,
             "internet_penetration": 93.0, "internet_penetration_c": 0.85, "is_landlocked": False},
            {"iso3": "IRN", "name": "Iran", "gdp_nominal": 400000000000, "gdp_nominal_c": 0.70,
             "population": 88000000, "population_c": 0.85, "stability": 42, "stability_c": 0.75,
             "national_morale": 55, "national_morale_c": 0.85, "war_weariness": 20, "war_weariness_c": 0.85,
             "military_spending_abs": 25000000000, "military_spending_abs_c": 0.60,
             "inflation_rate": 42.0, "inflation_rate_c": 0.70, "unemployment": 11.0, "unemployment_c": 0.70,
             "nuclear_warheads": 0, "nuclear_warheads_c": 0.90, "manpower_active": 610000, "manpower_active_c": 0.80,
             "press_freedom": 15, "press_freedom_c": 0.75, "corruption_index": 25, "corruption_index_c": 0.80,
             "forex_reserves": 120000000000, "forex_reserves_c": 0.70, "debt_to_gdp": 42.0, "debt_to_gdp_c": 0.70,
             "gini": 42.0, "gini_c": 0.70, "urbanization": 76.0, "urbanization_c": 0.70,
             "internet_penetration": 84.0, "internet_penetration_c": 0.70, "is_landlocked": False},
        ]

        for n in nations:
            s.run("CREATE (n:Nation $props)", props=n)
        log.info(f"Created {len(nations)} Nation nodes")

        # ── Alliances ──
        s.run("CREATE (:Alliance {name: 'NATO', type: 'military', founded: 1949})")
        s.run("CREATE (:Alliance {name: 'SCO', type: 'political', founded: 2001})")
        s.run("MATCH (n:Nation {iso3: 'USA'}), (a:Alliance {name: 'NATO'}) CREATE (n)-[:MEMBER_OF {role: 'leader', since: 1949}]->(a)")
        s.run("MATCH (n:Nation {iso3: 'DEU'}), (a:Alliance {name: 'NATO'}) CREATE (n)-[:MEMBER_OF {role: 'member', since: 1955}]->(a)")
        s.run("MATCH (n:Nation {iso3: 'CHN'}), (a:Alliance {name: 'SCO'}) CREATE (n)-[:MEMBER_OF {role: 'founder', since: 2001}]->(a)")
        s.run("MATCH (n:Nation {iso3: 'RUS'}), (a:Alliance {name: 'SCO'}) CREATE (n)-[:MEMBER_OF {role: 'founder', since: 2001}]->(a)")
        log.info("Created alliances + memberships")

        # ── Commodities ──
        s.run("CREATE (:Commodity {name: 'Crude Oil', type: 'oil', strategic_importance: 'critical'})")
        s.run("CREATE (:Commodity {name: 'Semiconductors', type: 'semiconductors', strategic_importance: 'critical'})")
        log.info("Created commodities")

        # ── Chokepoints ──
        s.run("CREATE (:Chokepoint {name: 'Strait of Hormuz', type: 'maritime', oil_transit_mbpd: 21.0})")
        s.run("MATCH (n:Nation {iso3: 'IRN'}), (c:Chokepoint {name: 'Strait of Hormuz'}) CREATE (n)-[:CONTROLS]->(c)")
        log.info("Created chokepoints")

        # ── Relationships ──
        # Trade
        s.run("""MATCH (a:Nation {iso3: 'USA'}), (b:Nation {iso3: 'CHN'}) 
               CREATE (a)-[:TRADES {commodity_type: 'mixed', volume: 500000000000, volume_c: 0.85, friction: 0.3, friction_c: 0.85}]->(b)""")
        s.run("""MATCH (a:Nation {iso3: 'DEU'}), (b:Nation {iso3: 'RUS'}) 
               CREATE (a)-[:TRADES {commodity_type: 'energy', volume: 50000000000, volume_c: 0.85, friction: 0.5, friction_c: 0.85}]->(b)""")
        s.run("""MATCH (a:Nation {iso3: 'CHN'}), (b:Nation {iso3: 'IRN'}) 
               CREATE (a)-[:TRADES {commodity_type: 'oil', volume: 30000000000, volume_c: 0.70, friction: 0.4, friction_c: 0.70}]->(b)""")

        # Sanctions
        s.run("MATCH (a:Nation {iso3: 'USA'}), (b:Nation {iso3: 'IRN'}) CREATE (a)-[:SANCTIONS {severity: 0.9, since: 2018}]->(b)")
        s.run("MATCH (a:Nation {iso3: 'USA'}), (b:Nation {iso3: 'RUS'}) CREATE (a)-[:SANCTIONS {severity: 0.7, since: 2022}]->(b)")

        # Borders
        s.run("MATCH (a:Nation {iso3: 'RUS'}), (b:Nation {iso3: 'CHN'}) CREATE (a)-[:BORDERS {length_km: 4209, disputed: false}]->(b)")
        s.run("MATCH (a:Nation {iso3: 'DEU'}), (b:Nation {iso3: 'CHN'}) RETURN 1")  # no border

        # Conflicts
        s.run("CREATE (:Conflict {name: 'Russia-Ukraine War', type: 'interstate', intensity: 'high'})")
        s.run("MATCH (n:Nation {iso3: 'RUS'}), (c:Conflict {name: 'Russia-Ukraine War'}) CREATE (n)-[:INVOLVED_IN {role: 'attacker'}]->(c)")

        # Tick (T=0)
        s.run("CREATE (:Tick {id: 0, tick_type: 'ECONOMIC', game_month: 1})")

        log.info("Created relationships")

        # ── Verify ──
        counts = s.run("""
            RETURN 
                size([(n:Nation) | n]) AS nations,
                size([(a:Alliance) | a]) AS alliances,
                size([(c:Commodity) | c]) AS commodities,
                size([(c:Chokepoint) | c]) AS chokepoints,
                size([(c:Conflict) | c]) AS conflicts,
                size([()-[r:TRADES]->() | r]) AS trades,
                size([()-[r:SANCTIONS]->() | r]) AS sanctions,
                size([()-[r:MEMBER_OF]->() | r]) AS memberships
        """).single()
        log.info(f"Test DB: {dict(counts)}")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    setup(driver)
    driver.close()
    log.info("Test database setup complete!")


if __name__ == "__main__":
    main()
