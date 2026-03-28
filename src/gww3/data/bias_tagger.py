"""Bias Tagger — Apply confidence scores and corrections from bias_overrides.json.

Part of the GWW3 ETL pipeline (Sprint 3):
  Normalize → **Bias Tag** → **Correction Overlay** → Re-Derive → Validate → Neo4j

This module reads data/bias_overrides.json and:
1. Applies default c_source confidence values per data source to Nation properties
2. Applies entity-specific corrections (value adjustments + confidence downgrades)

Reference: docs/BIAS_FRAMEWORK.md Section 6.1, docs/DATA_MODEL_COMPLETE.md Section 3.8

Uses the Double-Write Pattern: modifies live Nation node properties directly.
Historical STATE_AT edges are updated separately by rederive.py.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Source → Property mapping
# ──────────────────────────────────────────────
# Which Nation properties come from which DataSource.
# Used to apply source_defaults.c_source as {prop}_c.

SOURCE_PROPERTY_MAP: dict[str, list[str]] = {
    "worldbank-wdi": [
        "gdp_nominal", "gdp_growth", "gdp_per_capita", "gdp_10yr_cagr",
        "inflation_rate", "unemployment", "gini", "debt_to_gdp",
        "forex_reserves", "population", "urbanization", "internet_penetration",
    ],
    "worldbank-wdi-low-capacity": [
        "gdp_nominal", "gdp_growth", "gdp_per_capita",
        "inflation_rate", "unemployment", "gini", "debt_to_gdp",
        "forex_reserves", "population", "urbanization",
    ],
    "freedom-house": [
        "freedom_house_score",
    ],
    "v-dem": [
        "stability_index", "press_freedom",
    ],
    "v-dem-contested": [
        "stability_index", "press_freedom",
    ],
    "acled": [],  # ACLED feeds Conflict/NonStateActor nodes, not Nation properties
    "acled-conflict-zone": [],
    "un-wpp": [
        "population",  # overwrites WB population for some nations
    ],
    "sipri-milex": [
        "military_spending_abs", "military_spending_pct_gdp",
        "manpower_active", "manpower_reserve",
    ],
    "global-firepower": [],  # Feeds MilitaryCapability nodes, not direct Nation props
}


def _load_overrides(overrides_path: str | Path) -> dict:
    """Load bias_overrides.json."""
    path = Path(overrides_path)
    if not path.exists():
        raise FileNotFoundError(f"Bias overrides file not found: {path}")
    with open(path) as f:
        return json.load(f)


async def apply_source_defaults(driver, overrides: dict) -> int:
    """Apply default c_source values from source_defaults to all Nation nodes.

    For each source, sets {prop}_c on the relevant properties.
    Sources with 'applies_to_iso3' only affect listed nations.

    Returns total number of property updates.
    """
    total_updates = 0
    source_defaults = overrides.get("source_defaults", {})

    async with driver.session() as session:
        for source_id, config in source_defaults.items():
            c_source = config["c_source"]
            props = SOURCE_PROPERTY_MAP.get(source_id, [])
            if not props:
                continue

            applies_to = config.get("applies_to_iso3")

            # Build SET clause for confidence fields
            set_parts = [f"n.{prop}_c = {c_source}" for prop in props]
            set_clause = ", ".join(set_parts)

            if applies_to:
                # Only apply to specific nations
                query = f"""
                    MATCH (n:Nation)
                    WHERE n.iso3 IN $iso3_list
                    SET {set_clause}
                    RETURN count(n) AS updated
                """
                result = await session.run(query, iso3_list=applies_to)
            else:
                # Apply to all nations
                query = f"""
                    MATCH (n:Nation)
                    SET {set_clause}
                    RETURN count(n) AS updated
                """
                result = await session.run(query)

            record = await result.single()
            count = record["updated"] if record else 0
            total_updates += count * len(props)
            logger.info(
                "Source '%s': set c=%s on %d properties for %d nations%s",
                source_id, c_source, len(props), count,
                f" (restricted to {len(applies_to)} iso3 codes)" if applies_to else "",
            )

    return total_updates


async def apply_entity_overrides(driver, overrides: dict) -> int:
    """Apply entity-specific corrections from entity_overrides.

    For each (iso3, property):
    - If corrected_value is not null: SET both the property and {prop}_c
    - If corrected_value is null: SET only {prop}_c (confidence downgrade)

    Returns total number of property updates.
    """
    total_updates = 0
    entity_overrides = overrides.get("entity_overrides", {})

    async with driver.session() as session:
        for iso3, props in entity_overrides.items():
            for prop_name, correction in props.items():
                c_source = correction["c_source"]
                corrected_value = correction.get("corrected_value")

                if corrected_value is not None:
                    # Value correction + confidence downgrade
                    query = f"""
                        MATCH (n:Nation {{iso3: $iso3}})
                        SET n.{prop_name} = $corrected_value,
                            n.{prop_name}_c = $c_source
                        RETURN n.name AS name
                    """
                    result = await session.run(
                        query,
                        iso3=iso3,
                        corrected_value=corrected_value,
                        c_source=c_source,
                    )
                    record = await result.single()
                    if record:
                        logger.info(
                            "%s (%s): %s corrected to %s, c=%s",
                            record["name"], iso3, prop_name, corrected_value, c_source,
                        )
                        total_updates += 2  # value + confidence
                else:
                    # Confidence downgrade only
                    query = f"""
                        MATCH (n:Nation {{iso3: $iso3}})
                        SET n.{prop_name}_c = $c_source
                        RETURN n.name AS name
                    """
                    result = await session.run(
                        query, iso3=iso3, c_source=c_source,
                    )
                    record = await result.single()
                    if record:
                        logger.info(
                            "%s (%s): %s confidence downgraded to c=%s",
                            record["name"], iso3, prop_name, c_source,
                        )
                        total_updates += 1

    return total_updates


async def apply_bias_tags(
    driver,
    overrides_path: str | Path = "data/bias_overrides.json",
) -> dict[str, int]:
    """Main entry point: apply all bias tags and corrections.

    Pipeline position: runs AFTER normalization, BEFORE re-derive.

    Returns dict with counts of updates applied.
    """
    overrides = _load_overrides(overrides_path)

    logger.info("=== Bias Tagger: applying bias_overrides.json ===")

    source_updates = await apply_source_defaults(driver, overrides)
    entity_updates = await apply_entity_overrides(driver, overrides)

    logger.info(
        "=== Bias Tagger complete: %d source defaults + %d entity overrides ===",
        source_updates, entity_updates,
    )

    return {
        "source_default_updates": source_updates,
        "entity_override_updates": entity_updates,
    }
