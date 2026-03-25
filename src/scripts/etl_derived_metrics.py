#!/usr/bin/env python3
"""Compute derived metrics for historical Sprint 2 time series."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from neo4j import GraphDatabase

from gww3.data.historical_series import compute_metrics, normalize_series

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-DERIVED] %(message)s")
log = logging.getLogger("etl_derived_metrics")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

TIMESERIES_FILES = [
    Path("data/timeseries/worldbank_gdp.json"),
    Path("data/timeseries/worldbank_historical.json"),
    Path("data/timeseries/sipri_milex_historical.json"),
    Path("data/timeseries/vdem_historical.json"),
]
OUTPUT_PATH = Path("data/timeseries/derived_metrics.json")


def iter_payloads() -> list[tuple[Path, dict]]:
    payloads: list[tuple[Path, dict]] = []
    for path in TIMESERIES_FILES:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            payloads.append((path, json.load(handle)))
    return payloads


def build_metrics_payload() -> dict:
    nations: dict[str, dict[str, dict[str, float | int | None]]] = {}

    for path, payload in iter_payloads():
        if "nations" in payload:
            nation_items = payload["nations"].items()
        else:
            nation_items = payload.items()

        for iso3, nation_payload in nation_items:
            if "nations" in payload:
                for property_name, property_payload in nation_payload.items():
                    series = normalize_series(property_payload.get("timeseries", {}))
                    if series:
                        nations.setdefault(iso3, {})[property_name] = compute_metrics(series)
            else:
                series = normalize_series(nation_payload.get("timeseries", {}))
                if series:
                    nations.setdefault(iso3, {})["gdp_nominal"] = compute_metrics(series)

    return {
        "source": "derived",
        "generated_at": datetime.now(UTC).isoformat(),
        "nations": dict(sorted(nations.items())),
    }


def save_payload(payload: dict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    log.info("Saved %s", OUTPUT_PATH)


def build_neo4j_records(payload: dict) -> list[dict]:
    records: list[dict] = []
    for iso3, property_metrics in payload["nations"].items():
        props = {}
        for property_name, metrics in property_metrics.items():
            if metrics.get("cagr_pct") is not None:
                props[f"{property_name}_cagr"] = metrics["cagr_pct"]
            if metrics.get("trend_slope") is not None:
                props[f"{property_name}_trend_slope"] = metrics["trend_slope"]
            if metrics.get("volatility_pct") is not None:
                props[f"{property_name}_volatility"] = metrics["volatility_pct"]
            if metrics.get("max_abs_yoy_change_pct") is not None:
                props[f"{property_name}_max_abs_yoy_change_pct"] = metrics["max_abs_yoy_change_pct"]
        if props:
            records.append({"iso3": iso3, "properties": props, "prop_names": list(props.keys())})
    return records


def load_to_neo4j(payload: dict) -> tuple[int, str]:
    records = build_neo4j_records(payload)
    batch_id = f"import-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-2.4"
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
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
                        notes: "Derived historical metrics: CAGR, trend slope, "
                               "volatility, max yearly jump",
                        confidence: "high",
                        requires_replacement: false
                    })
                    """,
                    batch_id=batch_id,
                    record_count=len(records),
                )
                updated = tx.run(
                    """
                    UNWIND $records AS rec
                    MATCH (n:Nation {iso3: rec.iso3})
                    SET n += rec.properties
                    WITH n, rec
                    MATCH (ib:ImportBatch {id: $batch_id})
                    MERGE (n)-[p:PROVENANCE]->(ib)
                    SET p.properties = rec.prop_names
                    RETURN count(n) AS updated
                    """,
                    records=records,
                    batch_id=batch_id,
                ).single()["updated"]
                tx.run(
                    """
                    MATCH (t:Task {id: "task-P2-08-cagr"})
                    SET t.status = "completed",
                        t.completed_at = datetime(),
                        t.assigned_to = "Codex",
                        t.result_summary = "Historical derived metrics computed"
                    """
                )
                tx.commit()
        return updated, batch_id
    finally:
        driver.close()


def main() -> tuple[dict, tuple[int, str] | None]:
    payload = build_metrics_payload()
    save_payload(payload)
    try:
        load_result = load_to_neo4j(payload)
    except Exception as exc:  # pragma: no cover - exercised only with Neo4j connectivity
        log.warning("Skipping Neo4j load: %s", exc)
        load_result = None
    return payload, load_result


if __name__ == "__main__":
    payload, load_result = main()
    nation_count = len(payload["nations"])
    if load_result is None:
        print(f"RESULT: saved {OUTPUT_PATH} for {nation_count} nations (Neo4j load skipped)")
    else:
        updated, batch_id = load_result
        print(
            f"RESULT: {nation_count} nations cached, {updated} updated in Neo4j, "
            f"batch={batch_id}"
        )
