#!/usr/bin/env python3
"""Sprint 2 temporal validation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from neo4j import GraphDatabase

from gww3.data.historical_series import validate_temporal_series

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VALIDATE-S2] %(message)s")
log = logging.getLogger("validate_sprint2")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

TIMESERIES_FILES = [
    Path("data/timeseries/worldbank_gdp.json"),
    Path("data/timeseries/worldbank_historical.json"),
    Path("data/timeseries/sipri_milex_historical.json"),
    Path("data/timeseries/vdem_historical.json"),
]
OUTPUT_PATH = Path("data/validation_report_sprint2.json")


def validate_timeseries_files() -> dict:
    report = {"files": {}, "issues": [], "nations": {}}

    for path in TIMESERIES_FILES:
        if not path.exists():
            report["files"][str(path)] = {"present": False}
            report["issues"].append(f"missing file: {path}")
            continue

        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        if "nations" in payload:
            nation_items = payload["nations"].items()
        else:
            nation_items = payload.items()

        property_count = 0
        for iso3, nation_payload in nation_items:
            if "nations" in payload:
                for property_name, property_payload in nation_payload.items():
                    property_count += 1
                    issues = validate_temporal_series(
                        property_name,
                        property_payload.get("timeseries", {}),
                    )
                    if issues:
                        report["nations"].setdefault(iso3, {}).setdefault(
                            property_name,
                            [],
                        ).extend(issues)
            else:
                property_count += 1
                issues = validate_temporal_series(
                    "gdp_nominal",
                    nation_payload.get("timeseries", {}),
                )
                if issues:
                    report["nations"].setdefault(iso3, {}).setdefault(
                        "gdp_nominal",
                        [],
                    ).extend(issues)

        report["files"][str(path)] = {"present": True, "property_count": property_count}

    report["issue_count"] = sum(
        len(property_issues)
        for nation_payload in report["nations"].values()
        for property_issues in nation_payload.values()
    ) + len(report["issues"])
    return report


def validate_neo4j() -> dict:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            return {
                "tick_count": session.run("MATCH (t:Tick) RETURN count(t) AS c").single()["c"],
                "state_at_count": session.run(
                    "MATCH (:Nation)-[s:STATE_AT]->(:Tick) RETURN count(s) AS c"
                ).single()["c"],
                "baseline_complete": session.run(
                    """
                    MATCH (n:Nation)-[s:STATE_AT]->(t:Tick {game_month: 119})
                    WHERE s.gdp_nominal IS NOT NULL
                      AND s.population IS NOT NULL
                      AND s.military_spending_abs IS NOT NULL
                      AND s.stability_index IS NOT NULL
                    RETURN count(DISTINCT n) AS c
                    """
                ).single()["c"],
            }
    finally:
        driver.close()


def main() -> dict:
    report = validate_timeseries_files()
    try:
        report["neo4j"] = validate_neo4j()
    except Exception as exc:  # pragma: no cover - exercised only with Neo4j connectivity
        report["neo4j"] = {"error": str(exc)}
        report["issues"].append(f"neo4j validation skipped: {exc}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    log.info("Saved %s", OUTPUT_PATH)
    return report


if __name__ == "__main__":
    report = main()
    print(f"RESULT: issue_count={report['issue_count']}")
