#!/usr/bin/env python3
"""Expand bilateral trade relationships in Neo4j.

This script:
1. Inspects the existing `TRADES_WITH` relationship structure.
2. Attempts to fetch top bilateral flows from the UN Comtrade public API.
3. Falls back to GDP-weighted seed estimates across known major trade corridors.
4. Creates missing `TRADES_WITH` edges without duplicating existing directed edges.

The default target is a final count of 320 directed relationships, which stays
inside the requested 200-500 range.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

ROOT = Path(__file__).resolve().parents[2]
WORLD_BANK_GDP_PATH = ROOT / "data" / "timeseries" / "worldbank_gdp.json"

DEFAULT_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
DEFAULT_USER = os.getenv("NEO4J_USER", "neo4j")
DEFAULT_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")
DEFAULT_TARGET_FINAL_COUNT = 320
DEFAULT_YEAR = 2024


@dataclass(frozen=True, slots=True)
class TradeEdge:
    exporter: str
    importer: str
    trade_value_usd: int
    year: int
    data_source: str


COUNTRY_REGION: dict[str, str] = {
    "USA": "north_america",
    "CAN": "north_america",
    "MEX": "north_america",
    "BRA": "south_america",
    "ARG": "south_america",
    "CHL": "south_america",
    "COL": "south_america",
    "PER": "south_america",
    "GBR": "europe",
    "DEU": "europe",
    "FRA": "europe",
    "ITA": "europe",
    "ESP": "europe",
    "NLD": "europe",
    "BEL": "europe",
    "POL": "europe",
    "CHE": "europe",
    "SWE": "europe",
    "IRL": "europe",
    "AUT": "europe",
    "CZE": "europe",
    "DNK": "europe",
    "NOR": "europe",
    "TUR": "europe",
    "RUS": "eurasia",
    "CHN": "east_asia",
    "JPN": "east_asia",
    "KOR": "east_asia",
    "HKG": "east_asia",
    "TWN": "east_asia",
    "IND": "south_asia",
    "PAK": "south_asia",
    "BGD": "south_asia",
    "IDN": "asean",
    "SGP": "asean",
    "THA": "asean",
    "MYS": "asean",
    "VNM": "asean",
    "PHL": "asean",
    "AUS": "oceania",
    "NZL": "oceania",
    "SAU": "middle_east",
    "ARE": "middle_east",
    "ISR": "middle_east",
    "EGY": "middle_east",
    "ZAF": "africa",
    "NGA": "africa",
}

REGIONAL_CLUSTERS: dict[str, list[str]] = {
    "north_america": ["USA", "CAN", "MEX"],
    "south_america": ["BRA", "ARG", "CHL", "COL", "PER"],
    "europe": ["DEU", "FRA", "GBR", "ITA", "ESP", "NLD", "BEL", "POL", "CHE", "SWE", "IRL", "AUT", "CZE", "DNK"],
    "east_asia": ["CHN", "JPN", "KOR", "HKG", "TWN"],
    "south_asia": ["IND", "PAK", "BGD"],
    "asean": ["IDN", "SGP", "THA", "MYS", "VNM", "PHL"],
    "middle_east": ["SAU", "ARE", "ISR", "EGY"],
    "africa": ["ZAF", "NGA"],
    "oceania": ["AUS", "NZL"],
}

MAJOR_CORRIDORS: list[tuple[str, str]] = [
    ("USA", "CHN"), ("USA", "DEU"), ("USA", "JPN"), ("USA", "KOR"),
    ("USA", "IND"), ("USA", "GBR"), ("USA", "FRA"), ("USA", "ITA"),
    ("USA", "NLD"), ("USA", "BEL"), ("USA", "IRL"), ("USA", "BRA"),
    ("USA", "AUS"), ("USA", "VNM"), ("USA", "THA"), ("USA", "SGP"),
    ("USA", "TWN"), ("USA", "IDN"), ("USA", "ARE"), ("USA", "SAU"),
    ("CHN", "DEU"), ("CHN", "GBR"), ("CHN", "FRA"), ("CHN", "ITA"),
    ("CHN", "ESP"), ("CHN", "NLD"), ("CHN", "BEL"), ("CHN", "POL"),
    ("CHN", "CHE"), ("CHN", "AUS"), ("CHN", "BRA"), ("CHN", "RUS"),
    ("CHN", "IND"), ("CHN", "SAU"), ("CHN", "ARE"), ("CHN", "ZAF"),
    ("CHN", "MEX"), ("CHN", "CAN"), ("CHN", "TUR"), ("CHN", "EGY"),
    ("JPN", "KOR"), ("JPN", "DEU"), ("JPN", "GBR"), ("JPN", "FRA"),
    ("JPN", "AUS"), ("JPN", "IND"), ("JPN", "IDN"), ("JPN", "THA"),
    ("JPN", "VNM"), ("JPN", "MYS"), ("JPN", "SGP"), ("JPN", "SAU"),
    ("KOR", "DEU"), ("KOR", "GBR"), ("KOR", "FRA"), ("KOR", "IND"),
    ("KOR", "VNM"), ("KOR", "MYS"), ("KOR", "SGP"), ("KOR", "ARE"),
    ("IND", "DEU"), ("IND", "GBR"), ("IND", "FRA"), ("IND", "ITA"),
    ("IND", "NLD"), ("IND", "BEL"), ("IND", "ARE"), ("IND", "SAU"),
    ("IND", "IDN"), ("IND", "SGP"), ("IND", "THA"), ("IND", "VNM"),
    ("DEU", "TUR"), ("DEU", "CZE"), ("DEU", "AUT"), ("DEU", "DNK"),
    ("DEU", "SWE"), ("DEU", "NOR"), ("DEU", "POL"), ("DEU", "CHE"),
    ("DEU", "NLD"), ("DEU", "BEL"), ("DEU", "IRL"), ("DEU", "MEX"),
    ("DEU", "CAN"), ("DEU", "BRA"), ("DEU", "AUS"), ("DEU", "RUS"),
    ("GBR", "IRL"), ("GBR", "NLD"), ("GBR", "BEL"), ("GBR", "CHE"),
    ("GBR", "AUT"), ("GBR", "DNK"), ("GBR", "SWE"), ("GBR", "TUR"),
    ("GBR", "SGP"), ("GBR", "ARE"), ("GBR", "SAU"), ("GBR", "ZAF"),
    ("FRA", "ESP"), ("FRA", "BEL"), ("FRA", "CHE"), ("FRA", "AUT"),
    ("FRA", "POL"), ("FRA", "TUR"), ("FRA", "BRA"), ("FRA", "ARE"),
    ("ITA", "ESP"), ("ITA", "POL"), ("ITA", "CHE"), ("ITA", "TUR"),
    ("ITA", "ARE"), ("ITA", "SAU"), ("ESP", "POL"), ("ESP", "BRA"),
    ("ESP", "ARG"), ("ESP", "CHL"), ("ESP", "COL"), ("ESP", "PER"),
    ("NLD", "BEL"), ("NLD", "CHE"), ("NLD", "POL"), ("NLD", "SGP"),
    ("NLD", "ARE"), ("BEL", "POL"), ("BEL", "CHE"), ("POL", "CZE"),
    ("POL", "AUT"), ("POL", "SWE"), ("CHE", "AUT"), ("SWE", "DNK"),
    ("SWE", "NOR"), ("CZE", "AUT"), ("DNK", "NOR"), ("BRA", "ARG"),
    ("BRA", "CHL"), ("BRA", "COL"), ("BRA", "PER"), ("BRA", "MEX"),
    ("BRA", "ARE"), ("BRA", "SAU"), ("MEX", "CAN"), ("MEX", "JPN"),
    ("MEX", "KOR"), ("MEX", "BRA"), ("CAN", "GBR"), ("CAN", "JPN"),
    ("CAN", "KOR"), ("CAN", "MEX"), ("AUS", "KOR"), ("AUS", "IND"),
    ("AUS", "SGP"), ("AUS", "MYS"), ("AUS", "NZL"), ("IDN", "SGP"),
    ("IDN", "THA"), ("IDN", "MYS"), ("IDN", "VNM"), ("IDN", "PHL"),
    ("SGP", "THA"), ("SGP", "MYS"), ("SGP", "VNM"), ("SGP", "PHL"),
    ("THA", "MYS"), ("THA", "VNM"), ("THA", "PHL"), ("MYS", "VNM"),
    ("MYS", "PHL"), ("VNM", "PHL"), ("SAU", "ARE"), ("SAU", "EGY"),
    ("SAU", "ZAF"), ("ARE", "EGY"), ("ARE", "ZAF"), ("EGY", "ZAF"),
]

PAIR_BONUS: dict[frozenset[str], float] = {
    frozenset(("USA", "CAN")): 3.0,
    frozenset(("USA", "MEX")): 3.3,
    frozenset(("USA", "CHN")): 2.2,
    frozenset(("USA", "JPN")): 1.8,
    frozenset(("USA", "DEU")): 1.8,
    frozenset(("CHN", "JPN")): 2.0,
    frozenset(("CHN", "KOR")): 2.1,
    frozenset(("CHN", "AUS")): 2.0,
    frozenset(("CHN", "RUS")): 1.9,
    frozenset(("CHN", "VNM")): 1.8,
    frozenset(("CHN", "MYS")): 1.7,
    frozenset(("CHN", "SGP")): 1.7,
    frozenset(("DEU", "FRA")): 1.8,
    frozenset(("DEU", "NLD")): 1.8,
    frozenset(("DEU", "BEL")): 1.7,
    frozenset(("DEU", "POL")): 1.7,
    frozenset(("DEU", "CZE")): 1.9,
    frozenset(("DEU", "AUT")): 1.8,
    frozenset(("FRA", "ESP")): 1.6,
    frozenset(("GBR", "IRL")): 1.9,
    frozenset(("NLD", "BEL")): 2.0,
    frozenset(("JPN", "KOR")): 1.7,
    frozenset(("JPN", "AUS")): 1.7,
    frozenset(("KOR", "VNM")): 1.7,
    frozenset(("IND", "ARE")): 1.9,
    frozenset(("IND", "SAU")): 1.7,
    frozenset(("BRA", "ARG")): 1.8,
    frozenset(("AUS", "NZL")): 1.8,
    frozenset(("SAU", "ARE")): 1.7,
}


def load_latest_gdp() -> dict[str, float]:
    with WORLD_BANK_GDP_PATH.open() as handle:
        raw = json.load(handle)

    gdp_by_iso3: dict[str, float] = {}
    for iso3, record in raw.items():
        if len(iso3) != 3:
            continue
        latest = record.get("latest_value")
        if isinstance(latest, (int, float)) and latest > 0:
            gdp_by_iso3[iso3] = float(latest)
    return gdp_by_iso3


def fetch_json(url: str, timeout: int = 30) -> dict | list | None:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "gww3-trade-fix/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = response.read().decode(charset)
            return json.loads(payload)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def extract_records(payload: dict | list | None) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    for key in ("data", "dataset", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [record for record in value if isinstance(record, dict)]
    return []


def first_str(record: dict, keys: Iterable[str]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return None


def first_number(record: dict, keys: Iterable[str]) -> float | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", ""))
            except ValueError:
                continue
    return None


def fetch_un_comtrade_pairs(valid_iso3: set[str], year: int, limit: int) -> list[TradeEdge]:
    base_urls = [
        "https://comtradeapi.un.org/data/v1/get/C/A/HS",
        "https://comtradeapi.worldbank.org/data/v1/get/C/A/HS",
    ]
    params = {
        "reporterCode": "all",
        "partnerCode": "all",
        "cmdCode": "TOTAL",
        "flowCode": "X",
        "period": str(year),
        "maxRecords": str(limit),
        "format": "json",
        "includeDesc": "false",
    }

    api_edges: dict[tuple[str, str], TradeEdge] = {}
    for base_url in base_urls:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        payload = fetch_json(url)
        for record in extract_records(payload):
            exporter = first_str(
                record,
                ("reporterISO", "reporterIso", "reporterCodeIsoAlpha3", "rt3ISO", "reporter"),
            )
            importer = first_str(
                record,
                ("partnerISO", "partnerIso", "partnerCodeIsoAlpha3", "pt3ISO", "partner"),
            )
            value = first_number(record, ("primaryValue", "tradeValue", "TradeValue", "value"))
            if exporter not in valid_iso3 or importer not in valid_iso3:
                continue
            if exporter == importer or value is None or value <= 0:
                continue
            key = (exporter, importer)
            edge = TradeEdge(
                exporter=exporter,
                importer=importer,
                trade_value_usd=int(value),
                year=year,
                data_source="un-comtrade-api",
            )
            if key not in api_edges or api_edges[key].trade_value_usd < edge.trade_value_usd:
                api_edges[key] = edge
        if api_edges:
            break
    return sorted(api_edges.values(), key=lambda edge: edge.trade_value_usd, reverse=True)


def region_affinity(exporter: str, importer: str) -> float:
    exporter_region = COUNTRY_REGION.get(exporter)
    importer_region = COUNTRY_REGION.get(importer)
    if exporter_region and exporter_region == importer_region:
        return 1.45

    linked_regions = {
        frozenset(("europe", "north_america")): 1.22,
        frozenset(("east_asia", "asean")): 1.35,
        frozenset(("east_asia", "oceania")): 1.25,
        frozenset(("east_asia", "north_america")): 1.16,
        frozenset(("east_asia", "europe")): 1.10,
        frozenset(("south_asia", "middle_east")): 1.28,
        frozenset(("south_america", "north_america")): 1.12,
        frozenset(("south_america", "europe")): 1.10,
        frozenset(("middle_east", "europe")): 1.12,
        frozenset(("africa", "europe")): 1.10,
    }
    return linked_regions.get(frozenset((exporter_region, importer_region)), 1.0)


def estimate_trade_value_usd(exporter: str, importer: str, gdp_by_iso3: dict[str, float]) -> int:
    gdp_exporter = gdp_by_iso3.get(exporter)
    gdp_importer = gdp_by_iso3.get(importer)
    if not gdp_exporter or not gdp_importer:
        return 0

    pair = frozenset((exporter, importer))
    base = 0.0092 * math.sqrt(gdp_exporter * gdp_importer)
    value = base * region_affinity(exporter, importer) * PAIR_BONUS.get(pair, 1.0)
    return int(max(value, 1_000_000_000))


def build_fallback_pairs(valid_iso3: set[str], gdp_by_iso3: dict[str, float], year: int) -> list[TradeEdge]:
    candidate_pairs: set[tuple[str, str]] = set()

    for cluster in REGIONAL_CLUSTERS.values():
        members = [iso3 for iso3 in cluster if iso3 in valid_iso3]
        for left, right in combinations(members, 2):
            candidate_pairs.add((left, right))

    for left, right in MAJOR_CORRIDORS:
        if left in valid_iso3 and right in valid_iso3:
            candidate_pairs.add((left, right))

    edges: list[TradeEdge] = []
    for left, right in candidate_pairs:
        estimated = estimate_trade_value_usd(left, right, gdp_by_iso3)
        if estimated <= 0:
            continue
        edges.append(
            TradeEdge(
                exporter=left,
                importer=right,
                trade_value_usd=estimated,
                year=year,
                data_source="seed:gdp-weighted-major-pairs",
            )
        )
        edges.append(
            TradeEdge(
                exporter=right,
                importer=left,
                trade_value_usd=estimated,
                year=year,
                data_source="seed:gdp-weighted-major-pairs",
            )
        )

    return sorted(edges, key=lambda edge: edge.trade_value_usd, reverse=True)


def inspect_database(driver) -> tuple[int, set[tuple[str, str]], list[str]]:
    with driver.session() as session:
        relationship_count = session.run(
            "MATCH ()-[r:TRADES_WITH]->() RETURN count(r) AS count"
        ).single()["count"]
        existing_pairs = {
            (record["exporter"], record["importer"])
            for record in session.run(
                """
                MATCH (a:Nation)-[:TRADES_WITH]->(b:Nation)
                RETURN a.iso3 AS exporter, b.iso3 AS importer
                """
            )
        }
        property_keys = session.run(
            """
            MATCH ()-[r:TRADES_WITH]->()
            UNWIND keys(r) AS key
            RETURN DISTINCT key
            ORDER BY key
            """
        ).value()
    return relationship_count, existing_pairs, property_keys


def fetch_valid_nations(driver) -> set[str]:
    with driver.session() as session:
        return {
            record["iso3"]
            for record in session.run(
                "MATCH (n:Nation) WHERE n.iso3 IS NOT NULL RETURN n.iso3 AS iso3"
            )
        }


def insert_trade_edges(driver, edges: list[TradeEdge]) -> int:
    payload = [
        {
            "exporter": edge.exporter,
            "importer": edge.importer,
            "trade_value_usd": edge.trade_value_usd,
            "year": edge.year,
            "data_source": edge.data_source,
        }
        for edge in edges
    ]
    if not payload:
        return 0

    query = """
    UNWIND $rows AS row
    MATCH (exporter:Nation {iso3: row.exporter})
    MATCH (importer:Nation {iso3: row.importer})
    MERGE (exporter)-[r:TRADES_WITH]->(importer)
    ON CREATE SET
        r.trade_value_usd = row.trade_value_usd,
        r.year = row.year,
        r.data_source = row.data_source
    RETURN count(r) AS merged_count
    """
    with driver.session() as session:
        session.run(query, rows=payload).consume()
    return len(payload)


def select_new_edges(
    api_edges: list[TradeEdge],
    fallback_edges: list[TradeEdge],
    existing_pairs: set[tuple[str, str]],
    target_new_edges: int,
) -> list[TradeEdge]:
    selected: list[TradeEdge] = []
    seen = set(existing_pairs)
    for edge in api_edges + fallback_edges:
        key = (edge.exporter, edge.importer)
        if key in seen:
            continue
        selected.append(edge)
        seen.add(key)
        if len(selected) >= target_new_edges:
            break
    return selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand bilateral TRADES_WITH pairs in Neo4j.")
    parser.add_argument("--neo4j-uri", default=DEFAULT_URI)
    parser.add_argument("--neo4j-user", default=DEFAULT_USER)
    parser.add_argument("--neo4j-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--target-final-count", type=int, default=DEFAULT_TARGET_FINAL_COUNT)
    parser.add_argument("--api-limit", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline-preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gdp_by_iso3 = load_latest_gdp()

    if args.offline_preview:
        valid_iso3 = set(COUNTRY_REGION) & set(gdp_by_iso3)
        fallback_edges = build_fallback_pairs(valid_iso3, gdp_by_iso3, args.year)
        print(f"Offline preview nations: {len(valid_iso3)}")
        print(f"Offline fallback candidate edges: {len(fallback_edges)}")
        print("Top 20 fallback edges:")
        for edge in fallback_edges[:20]:
            print(
                f"{edge.exporter}->{edge.importer} "
                f"${edge.trade_value_usd:,.0f} "
                f"{edge.year} {edge.data_source}"
            )
        return 0

    try:
        driver = GraphDatabase.driver(
            args.neo4j_uri,
            auth=(args.neo4j_user, args.neo4j_password),
        )
    except Exception as exc:
        print(f"FATAL: could not initialize Neo4j driver: {exc}", file=sys.stderr)
        return 1

    try:
        valid_iso3 = fetch_valid_nations(driver)
        if not valid_iso3:
            print("FATAL: no Nation nodes with iso3 found.", file=sys.stderr)
            return 1

        starting_count, existing_pairs, property_keys = inspect_database(driver)
        print(f"Existing TRADES_WITH count: {starting_count}")
        print(f"Existing property keys: {property_keys or ['<none>']}")
        print(f"Nation count with iso3: {len(valid_iso3)}")

        target_final_count = max(200, min(args.target_final_count, 500))
        target_new_edges = max(0, target_final_count - starting_count)
        print(f"Target final TRADES_WITH count: {target_final_count}")
        print(f"Need to add up to {target_new_edges} new directed edges.")

        api_edges = fetch_un_comtrade_pairs(valid_iso3, args.year, args.api_limit)
        print(f"UN Comtrade API candidate edges: {len(api_edges)}")

        fallback_edges = build_fallback_pairs(valid_iso3, gdp_by_iso3, args.year)
        print(f"Fallback candidate edges: {len(fallback_edges)}")

        selected_edges = select_new_edges(
            api_edges=api_edges,
            fallback_edges=fallback_edges,
            existing_pairs=existing_pairs,
            target_new_edges=target_new_edges,
        )

        api_selected = sum(1 for edge in selected_edges if edge.data_source == "un-comtrade-api")
        fallback_selected = len(selected_edges) - api_selected
        print(f"Selected new edges: {len(selected_edges)}")
        print(f"Selected from API: {api_selected}")
        print(f"Selected from fallback: {fallback_selected}")

        if args.dry_run:
            print("Dry run enabled; no database changes written.")
            return 0

        created_count = insert_trade_edges(driver, selected_edges)
        final_count, _, final_property_keys = inspect_database(driver)
        print(f"Inserted new TRADES_WITH edges: {created_count}")
        print(f"Final TRADES_WITH count: {final_count}")
        print(f"Final property keys: {final_property_keys or ['<none>']}")
        return 0

    except ServiceUnavailable as exc:
        print(f"FATAL: could not connect to Neo4j at {args.neo4j_uri}: {exc}", file=sys.stderr)
        return 1
    except Neo4jError as exc:
        print(f"FATAL: Neo4j query failed: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
