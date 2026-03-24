#!/usr/bin/env python3
"""Sprint 1 Validation — Check data completeness and consistency.

Task: task-P8-03-validation (Sprint 1 scope: current data only)
Agent: Dione
"""

import json
import logging
import os
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VALIDATE] %(message)s")
log = logging.getLogger("validate")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")


def run_checks(driver) -> dict:
    results = {}

    with driver.session() as s:
        # 1. Node counts
        for label in ["Nation", "Alliance", "Conflict", "NonStateActor", "DomesticFaction",
                       "Commodity", "Chokepoint", "DataSource", "ImportBatch", "Task"]:
            r = s.run(f"MATCH (n:{label}) RETURN count(n) AS cnt").single()
            results[f"count_{label}"] = r["cnt"]
            log.info(f"{label}: {r['cnt']}")

        # 2. Relationship counts
        for rel in ["BORDERS", "TRADES", "PRODUCES", "CONSUMES", "MEMBER_OF",
                     "ARMS_TRANSFER", "CONTROLS", "HAS_FACTION", "INVOLVED_IN", "PROVENANCE"]:
            r = s.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt").single()
            results[f"rel_{rel}"] = r["cnt"]
            log.info(f"{rel}: {r['cnt']}")

        # 3. Data completeness for G20
        g20 = ["USA", "CHN", "JPN", "DEU", "IND", "GBR", "FRA", "ITA", "BRA", "CAN",
               "RUS", "KOR", "AUS", "MEX", "IDN", "TUR", "SAU", "ARG", "ZAF"]
        critical_props = ["gdp_nominal", "population", "military_spending_abs",
                          "stability_index", "nuclear_warheads"]

        g20_complete = 0
        g20_issues = []
        for iso3 in g20:
            r = s.run("""
                MATCH (n:Nation {iso3: $iso3})
                RETURN n.gdp_nominal AS gdp, n.population AS pop,
                       n.military_spending_abs AS mil, n.stability_index AS stab,
                       n.nuclear_warheads AS nukes, n.name_short AS name
            """, iso3=iso3).single()
            missing = []
            for prop in critical_props:
                key = prop.split("_")[0] if prop != "nuclear_warheads" else "nukes"
                if prop == "gdp_nominal": key = "gdp"
                elif prop == "population": key = "pop"
                elif prop == "military_spending_abs": key = "mil"
                elif prop == "stability_index": key = "stab"
                elif prop == "nuclear_warheads": key = "nukes"
                if r[key] is None:
                    missing.append(prop)
            if missing:
                g20_issues.append(f"{iso3}: missing {', '.join(missing)}")
            else:
                g20_complete += 1

        results["g20_complete"] = f"{g20_complete}/{len(g20)}"
        results["g20_issues"] = g20_issues
        log.info(f"G20 completeness: {g20_complete}/{len(g20)}")
        for issue in g20_issues:
            log.warning(f"  ⚠️ {issue}")

        # 4. Nations with borders
        r = s.run("MATCH (n:Nation)-[:BORDERS]-() RETURN count(DISTINCT n) AS cnt").single()
        results["nations_with_borders"] = r["cnt"]

        # 5. Nations with alliances
        r = s.run("MATCH (n:Nation)-[:MEMBER_OF]->() RETURN count(DISTINCT n) AS cnt").single()
        results["nations_with_alliances"] = r["cnt"]

        # 6. Nations with factions
        r = s.run("MATCH (n:Nation)-[:HAS_FACTION]->() RETURN count(DISTINCT n) AS cnt").single()
        results["nations_with_factions"] = r["cnt"]

        # 7. Sanity: GDP vs military spending
        r = s.run("""
            MATCH (n:Nation)
            WHERE n.military_spending_abs > n.gdp_nominal AND n.gdp_nominal IS NOT NULL AND n.military_spending_abs IS NOT NULL
            RETURN n.iso3 AS iso3, n.military_spending_abs AS mil, n.gdp_nominal AS gdp
        """)
        violations = [dict(rec) for rec in r]
        results["sanity_mil_gt_gdp"] = len(violations)
        for v in violations:
            log.error(f"  ❌ {v['iso3']}: mil={v['mil']} > gdp={v['gdp']}")

    return results


def main():
    log.info("=== Sprint 1 Validation ===")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        results = run_checks(driver)

        # Save report
        os.makedirs("data", exist_ok=True)
        with open("data/validation_report_sprint1.json", "w") as f:
            json.dump(results, f, indent=2)
        log.info("Saved data/validation_report_sprint1.json")

        # Summary
        log.info("\n=== SUMMARY ===")
        log.info(f"Nations: {results['count_Nation']}")
        log.info(f"Alliances: {results['count_Alliance']}")
        log.info(f"Conflicts: {results['count_Conflict']}")
        log.info(f"NSAs: {results['count_NonStateActor']}")
        log.info(f"Factions: {results['count_DomesticFaction']}")
        log.info(f"Commodities: {results['count_Commodity']}")
        log.info(f"Chokepoints: {results['count_Chokepoint']}")
        log.info(f"G20 completeness: {results['g20_complete']}")
        log.info(f"Nations with borders: {results['nations_with_borders']}")
        log.info(f"Nations with alliances: {results['nations_with_alliances']}")
        log.info(f"Nations with factions: {results['nations_with_factions']}")
        log.info(f"Sanity violations (mil>gdp): {results['sanity_mil_gt_gdp']}")

        passed = results['sanity_mil_gt_gdp'] == 0 and results['count_Nation'] >= 195
        log.info(f"\n{'✅ VALIDATION PASSED' if passed else '❌ VALIDATION FAILED'}")

        # Mark task
        with driver.session() as s:
            s.run("""MATCH (t:Task {id: "task-P8-03-validation"})
                   SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                       t.result_summary = $summary""",
                  summary=f"Sprint 1 validation: {results['count_Nation']} nations, G20 {results['g20_complete']}, {results['sanity_mil_gt_gdp']} sanity violations")

        return results
    finally:
        driver.close()


if __name__ == "__main__":
    results = main()
