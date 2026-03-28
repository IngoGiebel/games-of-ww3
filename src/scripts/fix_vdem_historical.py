#!/usr/bin/env python3
"""Fix missing historical V-Dem STATE_AT time series for 2016-2025.

Workflow:
1. Inspect current V-Dem properties already stored on ``STATE_AT`` edges.
2. Resolve a V-Dem v14 dataset from one of several sources:
   - explicit local file paths / URLs from env
   - GitHub release assets for ``vdeminstitute/vdemdata`` tag ``V14``
   - raw ``vdem.RData`` from the repo tag
   - existing local files in ``data/``
   - optional ``pip install vdemdata pyreadr`` fallback
3. Build yearly records for the five requested indicators:
   ``v2x_polyarchy``, ``v2x_liberal`` (from source column ``v2x_libdem``),
   ``v2x_partipdem``, ``v2x_delibdem``, ``v2x_egaldem``.
4. Upsert those properties on ``(:Nation)-[:STATE_AT]->(:Tick)`` for Jan 2016
   through Jan 2025.

The script is idempotent. It can run in constrained environments: if network
or Neo4j access is blocked, it logs a precise summary and exits without writing
to Neo4j.
"""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from neo4j import GraphDatabase

from gww3.data.historical_series import YEARS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FIX-VDEM-HIST] %(message)s")
log = logging.getLogger("fix_vdem_historical")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

DATA_DIR = Path("data")
TIMESERIES_DIR = DATA_DIR / "timeseries"
CROSSWALK_PATH = DATA_DIR / "id_crosswalk.json"
OUTPUT_JSON = TIMESERIES_DIR / "vdem_historical_v14.json"
OUTPUT_CSV = TIMESERIES_DIR / "vdem_historical_v14.csv"

GITHUB_RELEASE_API = "https://api.github.com/repos/vdeminstitute/vdemdata/releases/tags/V14"
RAW_RDATA_URLS = (
    "https://raw.githubusercontent.com/vdeminstitute/vdemdata/V14/data/vdem.RData",
    "https://github.com/vdeminstitute/vdemdata/raw/refs/tags/V14/data/vdem.RData",
)

SOURCE_COLUMNS = {
    "country_id",
    "country_text_id",
    "year",
    "v2x_polyarchy",
    "v2x_libdem",
    "v2x_partipdem",
    "v2x_delibdem",
    "v2x_egaldem",
}

TARGET_COLUMNS = {
    "v2x_polyarchy": "v2x_polyarchy",
    "v2x_libdem": "v2x_liberal",
    "v2x_partipdem": "v2x_partipdem",
    "v2x_delibdem": "v2x_delibdem",
    "v2x_egaldem": "v2x_egaldem",
}

STATE_AT_PROPERTIES = list(TARGET_COLUMNS.values())
TICK_ID_BY_YEAR = {year: (year - YEARS[0]) * 12 * 43200 for year in YEARS}


@dataclass
class DatasetResolution:
    source: str
    frame: pd.DataFrame
    cache_path: Path | None = None


def load_crosswalk() -> dict[str, dict[str, Any]]:
    with CROSSWALK_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def tick_id_for_year(year: int) -> int:
    return TICK_ID_BY_YEAR[year]


def is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def request_bytes(url: str, timeout: int = 120) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def frame_has_required_columns(frame: pd.DataFrame) -> bool:
    return SOURCE_COLUMNS.issubset(frame.columns)


def maybe_from_csv_bytes(raw: bytes) -> pd.DataFrame | None:
    try:
        frame = pd.read_csv(io.BytesIO(raw), low_memory=False)
    except Exception:
        return None
    return frame if frame_has_required_columns(frame) else None


def maybe_from_zip_bytes(raw: bytes) -> pd.DataFrame | None:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for member in archive.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                with archive.open(member) as handle:
                    frame = pd.read_csv(handle, low_memory=False)
                if frame_has_required_columns(frame):
                    return frame
    except zipfile.BadZipFile:
        return None
    return None


def maybe_load_rdata(path: Path) -> pd.DataFrame | None:
    try:
        import pyreadr  # type: ignore
    except ImportError:
        return None

    result = pyreadr.read_r(str(path))
    for frame in result.values():
        if isinstance(frame, pd.DataFrame) and frame_has_required_columns(frame):
            return frame
    return None


def install_optional_python_packages() -> bool:
    packages = ["vdemdata", "pyreadr"]
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *packages],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except Exception as exc:
        log.warning("Optional pip fallback failed: %s", exc)
        return False


def load_frame_from_path(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, low_memory=False)
        return frame if frame_has_required_columns(frame) else None
    if suffix == ".zip":
        return maybe_from_zip_bytes(path.read_bytes())
    if suffix in {".rdata", ".rda"}:
        return maybe_load_rdata(path)
    return None


def try_env_sources() -> DatasetResolution | None:
    env_sources = [os.getenv("VDEM_CSV"), os.getenv("VDEM_ZIP"), os.getenv("VDEM_RDATA")]
    for raw_source in env_sources:
        if not raw_source:
            continue
        if is_http_url(raw_source):
            log.info("Trying V-Dem dataset from URL: %s", raw_source)
            try:
                raw = request_bytes(raw_source)
                frame = maybe_from_csv_bytes(raw) or maybe_from_zip_bytes(raw)
                if frame is not None:
                    return DatasetResolution(source=raw_source, frame=frame)
            except Exception as exc:
                log.warning("Failed to load %s: %s", raw_source, exc)
            continue

        path = Path(raw_source)
        log.info("Trying V-Dem dataset from local path: %s", path)
        try:
            frame = load_frame_from_path(path)
        except Exception as exc:
            log.warning("Failed to load %s: %s", path, exc)
            continue
        if frame is not None:
            return DatasetResolution(source=str(path), frame=frame, cache_path=path)
    return None


def try_github_release_assets(cache_dir: Path) -> DatasetResolution | None:
    log.info("Trying GitHub release assets for V-Dem v14")
    response = requests.get(GITHUB_RELEASE_API, timeout=60)
    response.raise_for_status()
    payload = response.json()
    assets = payload.get("assets", [])
    preferred_urls: list[str] = []

    for asset in assets:
        url = asset.get("browser_download_url")
        name = str(asset.get("name", "")).lower()
        if not url:
            continue
        if name.endswith(".csv.zip") or name.endswith(".zip") or name.endswith(".csv"):
            preferred_urls.append(url)
    for url in preferred_urls:
        try:
            raw = request_bytes(url)
            frame = maybe_from_zip_bytes(raw) or maybe_from_csv_bytes(raw)
            if frame is None:
                continue
            cache_path = cache_dir / Path(url).name
            cache_path.write_bytes(raw)
            return DatasetResolution(source=url, frame=frame, cache_path=cache_path)
        except Exception as exc:
            log.warning("Failed GitHub asset %s: %s", url, exc)
    return None


def try_raw_rdata(cache_dir: Path) -> DatasetResolution | None:
    for url in RAW_RDATA_URLS:
        log.info("Trying raw RData fallback: %s", url)
        try:
            raw = request_bytes(url)
        except Exception as exc:
            log.warning("Failed raw RData download %s: %s", url, exc)
            continue

        cache_path = cache_dir / Path(url).name
        cache_path.write_bytes(raw)
        frame = maybe_load_rdata(cache_path)
        if frame is not None:
            return DatasetResolution(source=url, frame=frame, cache_path=cache_path)
    return None


def try_local_files() -> DatasetResolution | None:
    candidates = [
        OUTPUT_CSV,
        TIMESERIES_DIR / "vdem_historical.csv",
        TIMESERIES_DIR / "vdem_historical.zip",
        TIMESERIES_DIR / "vdem.RData",
        DATA_DIR / "vdem_historical.csv",
        DATA_DIR / "vdem_v14.csv",
        DATA_DIR / "vdem_v14.zip",
        Path("vdem.csv"),
        Path("vdem.zip"),
        Path("vdem.RData"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        log.info("Trying local fallback: %s", path)
        try:
            frame = load_frame_from_path(path)
        except Exception as exc:
            log.warning("Failed local fallback %s: %s", path, exc)
            continue
        if frame is not None:
            return DatasetResolution(source=str(path), frame=frame, cache_path=path)
    return None


def resolve_dataset() -> DatasetResolution:
    env_result = try_env_sources()
    if env_result is not None:
        return env_result

    cache_dir = TIMESERIES_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    for resolver in (try_github_release_assets, try_raw_rdata):
        try:
            result = resolver(cache_dir)
        except Exception as exc:
            log.warning("%s failed: %s", resolver.__name__, exc)
            result = None
        if result is not None:
            return result

    local_result = try_local_files()
    if local_result is not None:
        return local_result

    if install_optional_python_packages():
        raw_result = try_raw_rdata(cache_dir)
        if raw_result is not None:
            return raw_result
        local_result = try_local_files()
        if local_result is not None:
            return local_result

    raise RuntimeError(
        "Unable to resolve a V-Dem v14 dataset from env, GitHub, local files, or pip fallback"
    )


def resolve_iso3(row: pd.Series, crosswalk: dict[str, dict[str, Any]]) -> str | None:
    text_id = str(row.get("country_text_id", "")).strip().upper()
    if len(text_id) == 3 and text_id in crosswalk:
        return text_id

    country_id_raw = row.get("country_id")
    if pd.notna(country_id_raw):
        country_id = int(country_id_raw)
        for iso3, payload in crosswalk.items():
            if payload.get("vdem_id") == country_id:
                return iso3
    return None


def build_state_at_records(
    frame: pd.DataFrame,
    crosswalk: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    subset = frame.loc[frame["year"].isin(YEARS), list(SOURCE_COLUMNS)].copy()
    subset["country_id"] = pd.to_numeric(subset["country_id"], errors="coerce")

    unmatched_rows = 0
    records: list[dict[str, Any]] = []

    for _, row in subset.iterrows():
        iso3 = resolve_iso3(row, crosswalk)
        if iso3 is None:
            unmatched_rows += 1
            continue

        year = int(row["year"])
        props: dict[str, float] = {}
        for source_col, target_col in TARGET_COLUMNS.items():
            value = row.get(source_col)
            if pd.isna(value):
                continue
            props[target_col] = round(float(value), 6)
        if not props:
            continue

        records.append(
            {
                "iso3": iso3,
                "vdem_id": int(row["country_id"]) if pd.notna(row["country_id"]) else None,
                "year": year,
                "tick_id": tick_id_for_year(year),
                "properties": props,
            }
        )

    years_present = sorted({record["year"] for record in records})
    nations_present = sorted({record["iso3"] for record in records})
    summary = {
        "rows_in_year_window": int(len(subset)),
        "records_ready": len(records),
        "nations_ready": len(nations_present),
        "years_present": years_present,
        "unmatched_rows": unmatched_rows,
    }
    return records, summary


def save_records(records: list[dict[str, Any]], source: str) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        "source": source,
        "generated_at": datetime.now(UTC).isoformat(),
        "years": list(YEARS),
        "properties": STATE_AT_PROPERTIES,
        "records": records,
    }
    with OUTPUT_JSON.open("w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2, sort_keys=True)

    rows: list[dict[str, Any]] = []
    for record in records:
        row = {
            "iso3": record["iso3"],
            "vdem_id": record["vdem_id"],
            "year": record["year"],
            "tick_id": record["tick_id"],
        }
        row.update(record["properties"])
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUTPUT_CSV, index=False)


def inspect_existing_state_at() -> dict[str, Any]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            record = session.run(
                """
                MATCH (n:Nation)-[s:STATE_AT]->(t:Tick)
                WHERE any(prop IN $props WHERE s[prop] IS NOT NULL)
                RETURN
                    count(s) AS edge_count,
                    count(DISTINCT n) AS nation_count,
                    collect(DISTINCT t.year) AS years,
                    min(t.id) AS min_tick,
                    max(t.id) AS max_tick,
                    count(CASE WHEN s.v2x_polyarchy IS NOT NULL THEN 1 END) AS polyarchy_edges,
                    count(CASE WHEN s.v2x_liberal IS NOT NULL THEN 1 END) AS liberal_edges,
                    count(CASE WHEN s.v2x_partipdem IS NOT NULL THEN 1 END) AS participatory_edges,
                    count(CASE WHEN s.v2x_delibdem IS NOT NULL THEN 1 END) AS deliberative_edges,
                    count(CASE WHEN s.v2x_egaldem IS NOT NULL THEN 1 END) AS egalitarian_edges,
                    count(CASE WHEN s.stability_index IS NOT NULL THEN 1 END)
                        AS legacy_stability_edges,
                    count(CASE WHEN s.freedom_house_score IS NOT NULL THEN 1 END)
                        AS legacy_freedom_edges
                """,
                props=STATE_AT_PROPERTIES + ["stability_index", "freedom_house_score"],
            ).single()
            return record.data() if record is not None else {}
    finally:
        driver.close()


def load_to_neo4j(records: list[dict[str, Any]]) -> dict[str, Any]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-fix-vdem-historical"

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run(
                    """
                    CREATE (ib:ImportBatch {
                        id: $batch_id,
                        timestamp: datetime(),
                        agent: "Codex",
                        method: "historical_fix",
                        record_count: $count,
                        notes: "Backfill V-Dem v14 historical STATE_AT time series for 2016-2025",
                        confidence: "high",
                        requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource)
                    WHERE ds.id IN ["vdem", "vdem-v14"]
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                    """,
                    batch_id=batch_id,
                    count=len(records),
                )
                result = tx.run(
                    """
                    UNWIND $records AS rec
                    OPTIONAL MATCH (n_by_iso:Nation {iso3: rec.iso3})
                    OPTIONAL MATCH (n_by_vdem:Nation {vdem_id: rec.vdem_id})
                    WITH rec, coalesce(n_by_vdem, n_by_iso) AS nation
                    MATCH (t:Tick {id: rec.tick_id})
                    WHERE nation IS NOT NULL
                    MERGE (nation)-[s:STATE_AT]->(t)
                    SET s += rec.properties
                    RETURN count(s) AS merged_edges, count(DISTINCT nation) AS matched_nations
                    """,
                    records=records,
                ).single()
                tx.commit()

        return {
            "batch_id": batch_id,
            "merged_edges": result["merged_edges"] if result is not None else 0,
            "matched_nations": result["matched_nations"] if result is not None else 0,
        }
    finally:
        driver.close()


def main() -> int:
    inspection: dict[str, Any] | None
    try:
        inspection = inspect_existing_state_at()
        log.info("Existing STATE_AT V-Dem inspection: %s", inspection)
    except Exception as exc:
        inspection = None
        log.warning("Could not inspect existing STATE_AT V-Dem data: %s", exc)

    try:
        resolution = resolve_dataset()
    except Exception as exc:
        log.error("Dataset resolution failed: %s", exc)
        print(json.dumps({"inspection": inspection, "error": str(exc)}, indent=2))
        return 1

    log.info("Resolved dataset from %s", resolution.source)
    crosswalk = load_crosswalk()
    records, summary = build_state_at_records(resolution.frame, crosswalk)
    save_records(records, resolution.source)
    log.info("Prepared records summary: %s", summary)

    load_result: dict[str, Any] | None
    try:
        load_result = load_to_neo4j(records)
        log.info("Neo4j load summary: %s", load_result)
    except Exception as exc:
        load_result = None
        log.warning("Neo4j load skipped/failed: %s", exc)

    result = {
        "inspection": inspection,
        "dataset_source": resolution.source,
        "records_summary": summary,
        "cache_json": str(OUTPUT_JSON),
        "cache_csv": str(OUTPUT_CSV),
        "neo4j_load": load_result,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
