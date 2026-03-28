"""Re-Derive Computations — Recalculate derived metrics after bias corrections.

Part of the GWW3 ETL pipeline (Sprint 3):
  Normalize → Bias Tag → Correction Overlay → **Re-Derive** → Validate → Neo4j

⚠️ This step is MANDATORY. Without it, derived metrics (gdp_per_capita, etc.)
   remain computed from uncorrected base values, producing silently corrupt data.
   See: Gemini Deep Think Final Review, Fix 3.

Operates on:
1. Live Nation node properties (Double-Write Hot Path)
2. Historical STATE_AT edges (inline re-derivation for all ticks)

Reference: docs/BIAS_FRAMEWORK.md Section 6.1, docs/DATA_MODEL_COMPLETE.md Section 7
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Formula → Cypher transpilation
# ──────────────────────────────────────────────

# Maps simple formula expressions to Cypher SET clauses.
# Only supports basic arithmetic: +, -, *, /
# For complex formulas (CAGR), use dedicated Cypher.

_FORMULA_TO_CYPHER: dict[str, dict] = {
    "gdp_per_capita": {
        "formula": "gdp_nominal / population",
        "cypher_node": "n.gdp_per_capita = n.gdp_nominal / n.population",
        "cypher_edge": "r.gdp_per_capita = r.gdp_nominal / r.population",
        "null_guard": "n.gdp_nominal IS NOT NULL AND n.population IS NOT NULL AND n.population > 0",
        "null_guard_edge": "r.gdp_nominal IS NOT NULL AND r.population IS NOT NULL AND r.population > 0",
        "c_rule": "CASE WHEN n.gdp_nominal_c < n.population_c THEN n.gdp_nominal_c ELSE n.population_c END",
        "c_rule_edge": "CASE WHEN r.gdp_nominal_c < r.population_c THEN r.gdp_nominal_c ELSE r.population_c END",
    },
    "military_spending_pct_gdp": {
        "formula": "military_spending_abs / gdp_nominal * 100",
        "cypher_node": "n.military_spending_pct_gdp = n.military_spending_abs / n.gdp_nominal * 100",
        "cypher_edge": "r.military_spending_pct_gdp = r.military_spending_abs / r.gdp_nominal * 100",
        "null_guard": "n.military_spending_abs IS NOT NULL AND n.gdp_nominal IS NOT NULL AND n.gdp_nominal > 0",
        "null_guard_edge": "r.military_spending_abs IS NOT NULL AND r.gdp_nominal IS NOT NULL AND r.gdp_nominal > 0",
        "c_rule": "CASE WHEN n.military_spending_abs_c < n.gdp_nominal_c THEN n.military_spending_abs_c ELSE n.gdp_nominal_c END",
        "c_rule_edge": "CASE WHEN r.military_spending_abs_c < r.gdp_nominal_c THEN r.military_spending_abs_c ELSE r.gdp_nominal_c END",
    },
}

# CAGR is special — requires access to historical data. Handled separately.


async def rederive_nation_nodes(driver) -> dict[str, int]:
    """Recalculate derived metrics on live Nation nodes.

    Returns dict of {metric_name: nations_updated}.
    """
    results = {}
    async with driver.session() as session:
        for metric_name, spec in _FORMULA_TO_CYPHER.items():
            query = f"""
                MATCH (n:Nation)
                WHERE {spec['null_guard']}
                SET {spec['cypher_node']},
                    n.{metric_name}_c = {spec['c_rule']}
                RETURN count(n) AS updated
            """
            result = await session.run(query)
            record = await result.single()
            count = record["updated"] if record else 0
            results[metric_name] = count
            logger.info(
                "Re-derive (Nation nodes): %s = %s → %d nations updated",
                metric_name, spec["formula"], count,
            )

    return results


async def rederive_historical_state_at(driver) -> dict[str, int]:
    """Recalculate derived metrics on ALL historical STATE_AT edges.

    This is the inline re-derivation that prevents corrupt historical analytics.
    Runs after bias corrections have been applied to STATE_AT via Cypher batch.
    """
    results = {}
    async with driver.session() as session:
        for metric_name, spec in _FORMULA_TO_CYPHER.items():
            query = f"""
                MATCH (n:Nation)-[r:STATE_AT]->(t:Tick)
                WHERE {spec['null_guard_edge']}
                SET {spec['cypher_edge']},
                    r.{metric_name}_c = {spec['c_rule_edge']}
                RETURN count(r) AS updated
            """
            result = await session.run(query)
            record = await result.single()
            count = record["updated"] if record else 0
            results[metric_name] = count
            logger.info(
                "Re-derive (STATE_AT edges): %s → %d edges updated",
                metric_name, count,
            )

    return results


async def apply_historical_corrections(driver, overrides_path: str | Path = "data/bias_overrides.json") -> int:
    """Apply entity_overrides corrections to ALL historical STATE_AT edges.

    This is the Cypher batch script from BIAS_FRAMEWORK.md Section 6.2:
    Sets corrected values + _c on historical edges, then re-derives dependent metrics.

    Returns total number of edges updated.
    """
    path = Path(overrides_path)
    with open(path) as f:
        overrides = json.load(f)

    total = 0
    entity_overrides = overrides.get("entity_overrides", {})

    async with driver.session() as session:
        for iso3, props in entity_overrides.items():
            for prop_name, correction in props.items():
                corrected_value = correction.get("corrected_value")
                c_source = correction["c_source"]

                if corrected_value is not None:
                    # Value + confidence on all historical STATE_AT edges
                    query = f"""
                        MATCH (n:Nation {{iso3: $iso3}})-[r:STATE_AT]->(t:Tick)
                        WHERE t.id <= 0
                        SET r.{prop_name} = $corrected_value,
                            r.{prop_name}_c = $c_source
                        RETURN count(r) AS updated
                    """
                    result = await session.run(
                        query, iso3=iso3, corrected_value=corrected_value, c_source=c_source,
                    )
                    record = await result.single()
                    count = record["updated"] if record else 0
                    total += count
                    logger.info(
                        "Historical correction: %s.%s = %s (c=%s) → %d STATE_AT edges",
                        iso3, prop_name, corrected_value, c_source, count,
                    )
                else:
                    # Confidence only on historical edges
                    query = f"""
                        MATCH (n:Nation {{iso3: $iso3}})-[r:STATE_AT]->(t:Tick)
                        WHERE t.id <= 0
                        SET r.{prop_name}_c = $c_source
                        RETURN count(r) AS updated
                    """
                    result = await session.run(
                        query, iso3=iso3, c_source=c_source,
                    )
                    record = await result.single()
                    count = record["updated"] if record else 0
                    total += count
                    logger.info(
                        "Historical confidence: %s.%s c=%s → %d STATE_AT edges",
                        iso3, prop_name, c_source, count,
                    )

    return total


async def rederive_metrics(
    driver,
    overrides_path: str | Path = "data/bias_overrides.json",
) -> dict:
    """Main entry point: recalculate all derived metrics.

    Pipeline position: runs AFTER bias tagger + correction overlay, BEFORE validation.

    Steps:
    1. Apply historical corrections to STATE_AT edges
    2. Re-derive on live Nation nodes
    3. Re-derive on historical STATE_AT edges

    Returns summary dict.
    """
    logger.info("=== Re-Derive: recalculating derived metrics ===")

    hist_corrections = await apply_historical_corrections(driver, overrides_path)
    node_results = await rederive_nation_nodes(driver)
    edge_results = await rederive_historical_state_at(driver)

    logger.info(
        "=== Re-Derive complete: %d historical corrections, %d node metrics, %d edge metrics ===",
        hist_corrections,
        sum(node_results.values()),
        sum(edge_results.values()),
    )

    return {
        "historical_corrections": hist_corrections,
        "nation_node_rederives": node_results,
        "state_at_rederives": edge_results,
    }
