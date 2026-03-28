#!/usr/bin/env python3
"""Consolidate military spending from MilitaryExpenditure into Nation nodes.

Workflow:
1. Inspect MilitaryExpenditure and HAS_MILEX structure.
2. For each Nation linked via HAS_MILEX, copy the latest available spending values
   to Nation.military_spending_abs and Nation.military_spending_pct_gdp.
3. For remaining Nations without military_spending_abs, derive the most recent
   value from STATE_AT relationships.
4. Print final coverage and a concise audit report.

The script never deletes MilitaryExpenditure nodes.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FIX-MILEX] %(message)s")
log = logging.getLogger("fix_milex_consolidation")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

ABS_KEYS = (
    "military_spending_abs",
    "spending_abs",
    "military_expenditure_abs",
    "military_expenditure",
    "expenditure",
    "spending",
    "value",
    "amount",
    "current_usd",
)

PCT_KEYS = (
    "military_spending_pct_gdp",
    "spending_pct_gdp",
    "military_expenditure_pct_gdp",
    "pct_gdp",
    "percent_gdp",
    "share_gdp",
    "gdp_share",
    "burden_share",
)

YEAR_KEYS = (
    "latest_year",
    "year",
    "as_of_year",
    "observation_year",
    "snapshot_year",
    "date_year",
)

MONTH_KEYS = (
    "month",
    "as_of_month",
    "observation_month",
    "snapshot_month",
)


@dataclass(frozen=True)
class MilexCandidate:
    iso3: str
    name: str
    abs_value: float | None
    pct_value: float | None
    year: int | None
    month: int | None


@dataclass(frozen=True)
class StateAtCandidate:
    iso3: str
    name: str
    abs_value: float | None
    pct_value: float | None
    year: int | None
    month: int | None
    game_month: int | None
    tick_id: int | None


def _first_number(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_int(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _pick_milex_candidate(record: dict[str, Any]) -> MilexCandidate:
    node_props = record["node_props"] or {}
    rel_props = record["rel_props"] or {}
    merged = {**node_props, **rel_props}
    return MilexCandidate(
        iso3=record["iso3"],
        name=record["name"],
        abs_value=_first_number(merged, ABS_KEYS),
        pct_value=_first_number(merged, PCT_KEYS),
        year=_first_int(merged, YEAR_KEYS),
        month=_first_int(merged, MONTH_KEYS),
    )


def _pick_state_at_candidate(record: dict[str, Any]) -> StateAtCandidate:
    rel_props = record["rel_props"] or {}
    return StateAtCandidate(
        iso3=record["iso3"],
        name=record["name"],
        abs_value=_first_number(rel_props, ("military_spending_abs",)),
        pct_value=_first_number(rel_props, ("military_spending_pct_gdp",)),
        year=_first_int(record, ("tick_year",)),
        month=_first_int(record, ("tick_month",)),
        game_month=_first_int(record, ("game_month",)),
        tick_id=_first_int(record, ("tick_id",)),
    )


def _milex_sort_key(candidate: MilexCandidate) -> tuple[int, int, int]:
    return (
        candidate.year if candidate.year is not None else -1,
        candidate.month if candidate.month is not None else -1,
        1 if candidate.abs_value is not None else 0,
    )


def _state_at_sort_key(candidate: StateAtCandidate) -> tuple[int, int, int, int]:
    return (
        candidate.year if candidate.year is not None else -1,
        candidate.month if candidate.month is not None else -1,
        candidate.game_month if candidate.game_month is not None else -1,
        candidate.tick_id if candidate.tick_id is not None else -1,
    )


def inspect_structure(session) -> dict[str, Any]:
    counts = session.run(
        """
        MATCH (n:Nation)
        OPTIONAL MATCH (m:MilitaryExpenditure)
        WITH count(DISTINCT n) AS nation_count, count(DISTINCT m) AS milex_count
        OPTIONAL MATCH (:Nation)-[r:HAS_MILEX]->(:MilitaryExpenditure)
        RETURN nation_count, milex_count, count(r) AS has_milex_count
        """
    ).single()

    node_keys = list(
        session.run(
            """
            MATCH (m:MilitaryExpenditure)
            UNWIND keys(m) AS key
            RETURN key, count(*) AS occurrences
            ORDER BY occurrences DESC, key
            """
        )
    )
    rel_keys = list(
        session.run(
            """
            MATCH (:Nation)-[r:HAS_MILEX]->(:MilitaryExpenditure)
            UNWIND keys(r) AS key
            RETURN key, count(*) AS occurrences
            ORDER BY occurrences DESC, key
            """
        )
    )
    samples = list(
        session.run(
            """
            MATCH (n:Nation)-[r:HAS_MILEX]->(m:MilitaryExpenditure)
            RETURN n.iso3 AS iso3,
                   n.name AS name,
                   properties(r) AS rel_props,
                   properties(m) AS node_props
            ORDER BY n.iso3
            LIMIT 5
            """
        )
    )

    return {
        "nation_count": counts["nation_count"],
        "milex_count": counts["milex_count"],
        "has_milex_count": counts["has_milex_count"],
        "node_keys": [(row["key"], row["occurrences"]) for row in node_keys],
        "rel_keys": [(row["key"], row["occurrences"]) for row in rel_keys],
        "samples": [
            {
                "iso3": row["iso3"],
                "name": row["name"],
                "rel_props": row["rel_props"],
                "node_props": row["node_props"],
            }
            for row in samples
        ],
    }


def consolidate_from_has_milex(session) -> dict[str, Any]:
    records = list(
        session.run(
            """
            MATCH (n:Nation)-[r:HAS_MILEX]->(m:MilitaryExpenditure)
            RETURN n.iso3 AS iso3,
                   n.name AS name,
                   properties(r) AS rel_props,
                   properties(m) AS node_props
            ORDER BY n.iso3
            """
        )
    )

    latest_by_nation: dict[str, MilexCandidate] = {}
    for row in records:
        candidate = _pick_milex_candidate(dict(row))
        if candidate.abs_value is None and candidate.pct_value is None:
            continue
        current = latest_by_nation.get(candidate.iso3)
        if current is None or _milex_sort_key(candidate) > _milex_sort_key(current):
            latest_by_nation[candidate.iso3] = candidate

    updates = []
    for candidate in latest_by_nation.values():
        properties: dict[str, Any] = {}
        if candidate.abs_value is not None:
            properties["military_spending_abs"] = candidate.abs_value
            if candidate.year is not None:
                properties["military_spending_abs_year"] = candidate.year
        if candidate.pct_value is not None:
            properties["military_spending_pct_gdp"] = candidate.pct_value
            if candidate.year is not None:
                properties["military_spending_pct_gdp_year"] = candidate.year
        if properties:
            updates.append(
                {
                    "iso3": candidate.iso3,
                    "name": candidate.name,
                    "properties": properties,
                }
            )

    updated = 0
    if updates:
        updated = session.run(
            """
            UNWIND $updates AS row
            MATCH (n:Nation {iso3: row.iso3})
            SET n += row.properties
            RETURN count(n) AS updated
            """,
            updates=updates,
        ).single()["updated"]

    return {
        "linked_candidates": len(records),
        "chosen_nations": len(latest_by_nation),
        "updated_nations": updated,
        "updates": updates,
    }


def backfill_from_state_at(session) -> dict[str, Any]:
    records = list(
        session.run(
            """
            MATCH (n:Nation)-[s:STATE_AT]->(t:Tick)
            WHERE n.military_spending_abs IS NULL
              AND (s.military_spending_abs IS NOT NULL
                   OR s.military_spending_pct_gdp IS NOT NULL)
            RETURN n.iso3 AS iso3,
                   n.name AS name,
                   properties(s) AS rel_props,
                   t.year AS tick_year,
                   t.month AS tick_month,
                   t.game_month AS game_month,
                   t.id AS tick_id
            ORDER BY n.iso3, t.year DESC, t.month DESC, t.game_month DESC, t.id DESC
            """
        )
    )

    latest_by_nation: dict[str, StateAtCandidate] = {}
    for row in records:
        candidate = _pick_state_at_candidate(dict(row))
        if candidate.abs_value is None:
            continue
        current = latest_by_nation.get(candidate.iso3)
        if current is None or _state_at_sort_key(candidate) > _state_at_sort_key(current):
            latest_by_nation[candidate.iso3] = candidate

    updates = []
    for candidate in latest_by_nation.values():
        properties: dict[str, Any] = {
            "military_spending_abs": candidate.abs_value,
        }
        if candidate.year is not None:
            properties["military_spending_abs_year"] = candidate.year
        if candidate.pct_value is not None:
            properties["military_spending_pct_gdp"] = candidate.pct_value
            if candidate.year is not None:
                properties["military_spending_pct_gdp_year"] = candidate.year
        updates.append(
            {
                "iso3": candidate.iso3,
                "name": candidate.name,
                "properties": properties,
            }
        )

    updated = 0
    if updates:
        updated = session.run(
            """
            UNWIND $updates AS row
            MATCH (n:Nation {iso3: row.iso3})
            WHERE n.military_spending_abs IS NULL
            SET n += row.properties
            RETURN count(n) AS updated
            """,
            updates=updates,
        ).single()["updated"]

    return {
        "state_candidates": len(records),
        "chosen_nations": len(latest_by_nation),
        "updated_nations": updated,
        "updates": updates,
    }


def final_coverage(session) -> dict[str, Any]:
    row = session.run(
        """
        MATCH (n:Nation)
        RETURN count(n) AS total_nations,
               count { (n) WHERE n.military_spending_abs IS NOT NULL } AS abs_covered,
               count { (n) WHERE n.military_spending_pct_gdp IS NOT NULL } AS pct_covered,
               count { (n) WHERE n.military_spending_abs IS NULL } AS abs_missing
        """
    ).single()
    missing = list(
        session.run(
            """
            MATCH (n:Nation)
            WHERE n.military_spending_abs IS NULL
            RETURN n.iso3 AS iso3, n.name AS name
            ORDER BY n.iso3
            LIMIT 25
            """
        )
    )
    return {
        "total_nations": row["total_nations"],
        "abs_covered": row["abs_covered"],
        "pct_covered": row["pct_covered"],
        "abs_missing": row["abs_missing"],
        "missing_sample": [{"iso3": r["iso3"], "name": r["name"]} for r in missing],
    }


def print_report(structure: dict[str, Any], has_milex: dict[str, Any], state_at: dict[str, Any], coverage: dict[str, Any]) -> None:
    print("=== Military Spending Consolidation Report ===")
    print(
        "Initial structure: "
        f"{structure['milex_count']} MilitaryExpenditure nodes, "
        f"{structure['has_milex_count']} HAS_MILEX edges, "
        f"{structure['nation_count']} Nation nodes"
    )
    print("MilitaryExpenditure property keys:")
    for key, occurrences in structure["node_keys"]:
        print(f"  - {key}: {occurrences}")
    print("HAS_MILEX property keys:")
    for key, occurrences in structure["rel_keys"]:
        print(f"  - {key}: {occurrences}")
    print("Sample linked records:")
    for sample in structure["samples"]:
        print(
            f"  - {sample['iso3']} {sample['name']}: "
            f"rel={sample['rel_props']} node={sample['node_props']}"
        )

    print(
        "HAS_MILEX consolidation: "
        f"{has_milex['linked_candidates']} linked records scanned, "
        f"{has_milex['chosen_nations']} nations selected, "
        f"{has_milex['updated_nations']} Nation nodes updated"
    )
    print(
        "STATE_AT backfill: "
        f"{state_at['state_candidates']} candidate snapshots scanned, "
        f"{state_at['chosen_nations']} nations selected, "
        f"{state_at['updated_nations']} Nation nodes updated"
    )
    print(
        "Final coverage: "
        f"{coverage['abs_covered']}/{coverage['total_nations']} with military_spending_abs, "
        f"{coverage['pct_covered']}/{coverage['total_nations']} with military_spending_pct_gdp, "
        f"{coverage['abs_missing']} still missing military_spending_abs"
    )
    if coverage["missing_sample"]:
        print("Remaining missing sample:")
        for row in coverage["missing_sample"]:
            print(f"  - {row['iso3']} {row['name']}")


def main() -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            structure = inspect_structure(session)
            has_milex = consolidate_from_has_milex(session)
            state_at = backfill_from_state_at(session)
            coverage = final_coverage(session)
        print_report(structure, has_milex, state_at, coverage)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
