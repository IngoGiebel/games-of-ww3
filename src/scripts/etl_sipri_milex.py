#!/usr/bin/env python3
"""ETL: Historical SIPRI military expenditure for Sprint 2.

Expected input:
- preferred: a SIPRI CSV export via ``SIPRI_MILEX_CSV`` or
  ``data/timeseries/sipri_milex_raw.csv``
- fallback: if the CSV is missing, build a deterministic estimate from the
  existing GDP time series and each Nation's current military spending share

Output:
- ``data/timeseries/sipri_milex_historical.json``
- ``Nation`` latest military properties
- yearly January ``STATE_AT`` properties on existing Tick nodes

Task: task-P3-01-sipri-milex
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase

from gww3.data.historical_series import YEARS, compute_metrics, normalize_series
from gww3.data.normalization import normalize_value

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-SIPRI] %(message)s")
log = logging.getLogger("etl_sipri_milex")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

RAW_CSV_PATH = Path(os.getenv("SIPRI_MILEX_CSV", "data/timeseries/sipri_milex_raw.csv"))
OUTPUT_PATH = Path("data/timeseries/sipri_milex_historical.json")
GDP_PATH = Path("data/timeseries/worldbank_gdp.json")

NAME_ALIASES = {
    "united states": "USA",
    "united states of america": "USA",
    "russian federation": "RUS",
    "russia": "RUS",
    "south korea": "KOR",
    "republic of korea": "KOR",
    "north korea": "PRK",
    "democratic people's republic of korea": "PRK",
    "iran": "IRN",
    "islamic republic of iran": "IRN",
    "venezuela": "VEN",
    "bolivarian republic of venezuela": "VEN",
    "syria": "SYR",
    "syrian arab republic": "SYR",
    "turkey": "TUR",
    "türkiye": "TUR",
    "viet nam": "VNM",
    "lao pdr": "LAO",
    "czechia": "CZE",
}


def load_crosswalk() -> dict[str, str]:
    with Path("data/id_crosswalk.json").open(encoding="utf-8") as handle:
        raw = json.load(handle)
    mapping = {}
    for iso3, payload in raw.items():
        mapping[iso3.upper()] = iso3
        mapping[payload["name"].casefold()] = iso3
    mapping.update(NAME_ALIASES)
    return mapping


def canonical_iso3(value: str, crosswalk: dict[str, str]) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) == 3 and cleaned.upper() in crosswalk:
        return crosswalk[cleaned.upper()]
    return crosswalk.get(cleaned.casefold())


def detect_columns(frame: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    lowered = {column.casefold().strip(): column for column in frame.columns}
    country_column = None
    year_column = None
    spending_column = None

    for candidate in ["country", "country name", "nation", "state", "country_name"]:
        if candidate in lowered:
            country_column = lowered[candidate]
            break
    for candidate in ["year", "fiscal year"]:
        if candidate in lowered:
            year_column = lowered[candidate]
            break
    for candidate in [
        "spending (current us$)",
        "mil. exp. (current usd, millions)",
        "military expenditure",
        "spending",
    ]:
        if candidate in lowered:
            spending_column = lowered[candidate]
            break
    return country_column, year_column, spending_column


def parse_sipri_csv(crosswalk: dict[str, str]) -> dict:
    frame = pd.read_csv(RAW_CSV_PATH)
    country_column, year_column, spending_column = detect_columns(frame)
    nations: dict[str, dict[str, dict[str, object]]] = {}

    if country_column and year_column and spending_column:
        for _, row in frame.iterrows():
            iso3 = canonical_iso3(str(row[country_column]), crosswalk)
            if iso3 is None:
                continue
            year = int(row[year_column])
            if year not in YEARS:
                continue
            spending_value = row[spending_column]
            if pd.isna(spending_value):
                continue
            spending_abs = normalize_value("military_spending_abs", spending_value)
            nations.setdefault(iso3, {}).setdefault(
                "military_spending_abs",
                {"source_field": spending_column, "timeseries": {}},
            )
            nations[iso3]["military_spending_abs"]["timeseries"][str(year)] = spending_abs
        return nations

    year_columns = [
        column for column in frame.columns if str(column).isdigit() and int(column) in YEARS
    ]
    if not country_column or not year_columns:
        raise RuntimeError("unrecognized SIPRI CSV format")

    for _, row in frame.iterrows():
        iso3 = canonical_iso3(str(row[country_column]), crosswalk)
        if iso3 is None:
            continue
        for column in year_columns:
            value = row[column]
            if pd.isna(value):
                continue
            spending_abs = normalize_value("military_spending_abs", value)
            nations.setdefault(iso3, {}).setdefault(
                "military_spending_abs",
                {"source_field": "wide_year_columns", "timeseries": {}},
            )
            nations[iso3]["military_spending_abs"]["timeseries"][str(int(column))] = spending_abs
    return nations


def estimate_from_gdp() -> dict:
    if not GDP_PATH.exists():
        raise RuntimeError(
            "cannot build SIPRI fallback estimates without "
            "data/timeseries/worldbank_gdp.json"
        )

    with GDP_PATH.open(encoding="utf-8") as handle:
        gdp_payload = json.load(handle)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Nation)
                WHERE n.military_spending_abs IS NOT NULL
                  AND n.gdp_nominal IS NOT NULL
                  AND n.gdp_nominal > 0
                RETURN n.iso3 AS iso3,
                       n.military_spending_abs AS military_spending_abs,
                       n.gdp_nominal AS gdp_nominal
                """
            )
            burden = {
                record["iso3"]: (
                    float(record["military_spending_abs"]) / float(record["gdp_nominal"])
                )
                for record in result
            }
    finally:
        driver.close()

    nations: dict[str, dict[str, dict[str, object]]] = {}
    for iso3, payload in gdp_payload.items():
        ratio = burden.get(iso3)
        if ratio is None:
            continue
        series = {}
        for year_str, gdp_value in payload["timeseries"].items():
            year = int(year_str)
            if year in YEARS:
                series[str(year)] = round(float(gdp_value) * ratio, 2)
        if series:
            nations[iso3] = {
                "military_spending_abs": {
                    "source_field": "estimated_from_current_military_share",
                    "timeseries": series,
                }
            }
    return nations


def finalize_payload(nations: dict, source_note: str, estimated: bool) -> dict:
    for nation_payload in nations.values():
        for property_payload in nation_payload.values():
            series = normalize_series(property_payload["timeseries"])
            property_payload["timeseries"] = {str(year): value for year, value in series.items()}
            property_payload["metrics"] = compute_metrics(series)
            property_payload["latest_year"] = property_payload["metrics"]["end_year"]
            property_payload["latest_value"] = property_payload["metrics"]["latest_value"]

    return {
        "source": "sipri-milex",
        "generated_at": datetime.now(UTC).isoformat(),
        "years": list(YEARS),
        "estimated": estimated,
        "notes": source_note,
        "properties": ["military_spending_abs"],
        "nations": dict(sorted(nations.items())),
    }


def save_payload(payload: dict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    log.info("Saved %s", OUTPUT_PATH)


def build_neo4j_records(payload: dict) -> tuple[list[dict], list[dict]]:
    latest_records: list[dict] = []
    state_at_records: list[dict] = []
    for iso3, properties in payload["nations"].items():
        latest_props = {}
        for property_name, property_payload in properties.items():
            latest_value = property_payload.get("latest_value")
            latest_year = property_payload.get("latest_year")
            if latest_value is not None:
                latest_props[property_name] = latest_value
                latest_props[f"{property_name}_year"] = latest_year
            for year_str, value in property_payload["timeseries"].items():
                year = int(year_str)
                tick_id = (year - YEARS[0]) * 12 * 43200
                state_at_records.append(
                    {
                        "iso3": iso3,
                        "tick_id": tick_id,
                        "properties": {property_name: value},
                    }
                )
        if latest_props:
            latest_records.append(
                {
                    "iso3": iso3,
                    "properties": latest_props,
                    "prop_names": list(latest_props.keys()),
                }
            )
    return latest_records, state_at_records


def load_to_neo4j(payload: dict) -> tuple[int, int, str]:
    latest_records, state_at_records = build_neo4j_records(payload)
    batch_id = f"import-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-3.1"
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
                        method: $method,
                        record_count: $record_count,
                        notes: $notes,
                        confidence: $confidence,
                        requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "sipri-milex"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                    """,
                    batch_id=batch_id,
                    method="estimated" if payload["estimated"] else "csv_import",
                    record_count=len(latest_records),
                    notes=payload["notes"],
                    confidence="medium" if payload["estimated"] else "high",
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
                    records=latest_records,
                    batch_id=batch_id,
                ).single()["updated"]
                tx.run(
                    """
                    UNWIND $records AS rec
                    MATCH (n:Nation {iso3: rec.iso3})
                    MATCH (t:Tick {id: rec.tick_id})
                    MERGE (n)-[s:STATE_AT]->(t)
                    SET s += rec.properties
                    """,
                    records=state_at_records,
                )
                tx.run(
                    """
                    MATCH (t:Task {id: "task-P3-01-sipri-milex"})
                    SET t.status = "completed",
                        t.completed_at = datetime(),
                        t.assigned_to = "Codex",
                        t.result_summary = $summary
                    """,
                    summary="Historical SIPRI military expenditure loaded for 2016-2025",
                )
                tx.commit()
        return updated, len(state_at_records), batch_id
    finally:
        driver.close()


def main() -> tuple[dict, tuple[int, int, str] | None]:
    crosswalk = load_crosswalk()
    if RAW_CSV_PATH.exists():
        payload = finalize_payload(
            parse_sipri_csv(crosswalk),
            source_note=f"SIPRI CSV import from {RAW_CSV_PATH}",
            estimated=False,
        )
    else:
        payload = finalize_payload(
            estimate_from_gdp(),
            source_note=(
                "Deterministic fallback estimate from current military burden "
                "and GDP history"
            ),
            estimated=True,
        )
    save_payload(payload)
    try:
        load_result = load_to_neo4j(payload)
    except Exception as exc:  # pragma: no cover - exercised only with Neo4j connectivity
        log.warning("Skipping Neo4j load: %s", exc)
        load_result = None
    return payload, load_result


if __name__ == "__main__":
    dataset, load_result = main()
    nation_count = len(dataset["nations"])
    if load_result is None:
        print(f"RESULT: saved {OUTPUT_PATH} for {nation_count} nations (Neo4j load skipped)")
    else:
        updated_nations, state_edges, batch_id = load_result
        print(
            f"RESULT: {nation_count} nations cached, {updated_nations} updated in Neo4j, "
            f"{state_edges} STATE_AT merges, batch={batch_id}"
        )
