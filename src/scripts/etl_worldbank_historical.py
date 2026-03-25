#!/usr/bin/env python3
"""ETL: Historical World Bank indicators for Sprint 2.

Loads 2016-2025 yearly time series for:
- population
- urbanization
- internet penetration
- inflation
- unemployment
- gini
- debt to GDP
- forex reserves

The script writes a reproducible JSON cache to ``data/timeseries/`` and, when
Neo4j is reachable, merges yearly properties onto existing January Tick nodes
via ``STATE_AT`` relationships while also refreshing the latest Nation values.

Tasks:
- task-P2-02-wb-demographics
- task-P2-03-wb-macro
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import requests
from neo4j import GraphDatabase

from gww3.data.historical_series import YEARS, compute_metrics, normalize_series
from gww3.data.normalization import normalize_value

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-WB-HIST] %(message)s")
log = logging.getLogger("etl_worldbank_historical")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

WB_API = os.getenv("WORLD_BANK_API", "https://api.worldbank.org/v2")
DATE_RANGE = f"{YEARS[0]}:{YEARS[-1]}"
PER_PAGE = 500

INDICATORS = {
    "SP.POP.TOTL": "population",
    "SP.URB.TOTL.IN.ZS": "urbanization",
    "IT.NET.USER.ZS": "internet_penetration",
    "FP.CPI.TOTL.ZG": "inflation_rate",
    "SL.UEM.TOTL.ZS": "unemployment",
    "SI.POV.GINI": "gini",
    "GC.DOD.TOTL.GD.ZS": "debt_to_gdp",
    "FI.RES.TOTL.CD": "forex_reserves",
}

OUTPUT_PATH = Path("data/timeseries/worldbank_historical.json")


def fetch_indicator(indicator_code: str) -> list[dict]:
    records: list[dict] = []
    page = 1
    while True:
        payload = None
        for attempt in range(3):
            try:
                response = requests.get(
                    f"{WB_API}/country/all/indicator/{indicator_code}",
                    params={
                        "format": "json",
                        "date": DATE_RANGE,
                        "per_page": PER_PAGE,
                        "page": page,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except (requests.RequestException, json.JSONDecodeError) as exc:
                log.warning(
                    "%s page %s attempt %s failed: %s",
                    indicator_code,
                    page,
                    attempt + 1,
                    exc,
                )
                time.sleep(2 * (attempt + 1))
        if payload is None:
            raise RuntimeError(f"failed to fetch World Bank indicator {indicator_code}")

        if len(payload) < 2 or not payload[1]:
            break
        records.extend(payload[1])
        total_pages = payload[0].get("pages", 1)
        log.info("%s page %s/%s -> %s records", indicator_code, page, total_pages, len(payload[1]))
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.25)
    return records


def build_payload() -> dict:
    nations: dict[str, dict[str, dict[str, object]]] = {}

    for indicator_code, property_name in INDICATORS.items():
        raw_records = fetch_indicator(indicator_code)
        for record in raw_records:
            iso3 = record.get("countryiso3code", "")
            if len(iso3) != 3:
                continue
            raw_value = record.get("value")
            if raw_value is None:
                continue
            year = int(record["date"])
            if year not in YEARS:
                continue

            normalized = normalize_value(property_name, raw_value)
            nations.setdefault(iso3, {}).setdefault(
                property_name,
                {"indicator": indicator_code, "timeseries": {}},
            )
            nations[iso3][property_name]["timeseries"][str(year)] = normalized

    for nation_payload in nations.values():
        for property_payload in nation_payload.values():
            series = normalize_series(property_payload["timeseries"])
            property_payload["timeseries"] = {str(year): value for year, value in series.items()}
            property_payload["metrics"] = compute_metrics(series)
            property_payload["latest_year"] = property_payload["metrics"]["end_year"]
            property_payload["latest_value"] = property_payload["metrics"]["latest_value"]

    return {
        "source": "worldbank-wdi",
        "generated_at": datetime.now(UTC).isoformat(),
        "years": list(YEARS),
        "properties": list(INDICATORS.values()),
        "indicators": INDICATORS,
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
            if latest_year is not None:
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
    batch_id = f"import-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-2.1b-2.1c"
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
                        method: "api_import",
                        record_count: $record_count,
                        notes: "World Bank historical indicators 2016-2025 for demographics and "
                               "macroeconomic data",
                        confidence: "high",
                        requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "worldbank-wdi"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                    """,
                    batch_id=batch_id,
                    record_count=len(latest_records),
                )

                latest_result = tx.run(
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
                )
                updated_nations = latest_result.single()["updated"]

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
                    MATCH (t:Task)
                    WHERE t.id IN ["task-P2-02-wb-demographics", "task-P2-03-wb-macro"]
                    SET t.status = "completed",
                        t.completed_at = datetime(),
                        t.assigned_to = "Codex",
                        t.result_summary = "Historical World Bank indicators loaded for 2016-2025"
                    """
                )
                tx.commit()
        return updated_nations, len(state_at_records), batch_id
    finally:
        driver.close()


def main() -> tuple[dict, tuple[int, int, str] | None]:
    payload = build_payload()
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
