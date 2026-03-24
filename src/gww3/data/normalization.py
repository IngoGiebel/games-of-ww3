"""Unit & Scale Normalization Registry for GWW3.

Every property in the database has a canonical unit and scale.
Import scripts MUST normalize to these standards before committing to Neo4j.

Design rationale:
- All monetary values in absolute USD (not millions, not PPP)
- All rates as percentages (5.9 means 5.9%, not 0.059)
- All indices scaled to 0-100 integers for game engine compatibility
- V-Dem 0-1 floats are multiplied by 100
- SIPRI reports in millions USD → multiply by 1_000_000

This module is imported by Sentinel's ETL scripts and by validation_bounds.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class PropertyDomain(Enum):
    """Categorization of property domains for source routing."""
    IDENTITY = "identity"
    DEMOGRAPHICS = "demographics"
    ECONOMICS = "economics"
    MILITARY = "military"
    GOVERNANCE = "governance"
    GAME_STATE = "game_state"
    PROVENANCE = "provenance"


@dataclass(frozen=True)
class PropertySpec:
    """Specification for a single Nation property."""
    name: str
    domain: PropertyDomain
    canonical_unit: str          # e.g., "USD", "percent", "integer", "float_0_100"
    description: str
    primary_source: str          # DataSource.id
    nullable: bool = False       # False = must be imputed if missing
    game_critical: bool = False  # True = engine crashes without this value
    
    # Normalization function: raw source value → canonical value
    # None means no conversion needed
    normalize: Callable[[Any], Any] | None = None


def _millions_to_abs(val: float | int) -> float:
    """SIPRI reports in millions USD → absolute USD."""
    return float(val) * 1_000_000


def _vdem_to_100(val: float) -> int:
    """V-Dem 0-1 float → 0-100 integer."""
    return round(float(val) * 100)


def _ensure_float(val: Any) -> float:
    """Coerce to float, handle string numbers."""
    if isinstance(val, str):
        val = val.replace(",", "").strip()
    return float(val)


def _ensure_int(val: Any) -> int:
    """Coerce to integer."""
    return int(round(float(val)))


# ──────────────────────────────────────────────
# Property Registry
# ──────────────────────────────────────────────

PROPERTY_SPECS: dict[str, PropertySpec] = {
    # ── Identity ──
    "iso3": PropertySpec("iso3", PropertyDomain.IDENTITY, "string", "ISO 3166-1 alpha-3", "cia-factbook"),
    "iso2": PropertySpec("iso2", PropertyDomain.IDENTITY, "string", "ISO 3166-1 alpha-2", "cia-factbook"),
    "name": PropertySpec("name", PropertyDomain.IDENTITY, "string", "Official full name", "cia-factbook"),
    "name_short": PropertySpec("name_short", PropertyDomain.IDENTITY, "string", "Common short name", "cia-factbook"),
    "cow_code": PropertySpec("cow_code", PropertyDomain.IDENTITY, "integer", "Correlates of War code", "cia-factbook", normalize=_ensure_int),
    "un_m49": PropertySpec("un_m49", PropertyDomain.IDENTITY, "integer", "UN M49 numeric code", "cia-factbook", normalize=_ensure_int),
    "vdem_id": PropertySpec("vdem_id", PropertyDomain.IDENTITY, "integer", "V-Dem country ID", "vdem", nullable=True, normalize=_ensure_int),
    "region": PropertySpec("region", PropertyDomain.IDENTITY, "string", "Geographic region", "cia-factbook"),
    "sub_region": PropertySpec("sub_region", PropertyDomain.IDENTITY, "string", "Geographic sub-region", "cia-factbook"),
    "government_type": PropertySpec("government_type", PropertyDomain.IDENTITY, "string", "Form of government", "cia-factbook"),
    "leader_name": PropertySpec("leader_name", PropertyDomain.IDENTITY, "string", "Head of state/government", "cia-factbook"),
    "leader_ideology": PropertySpec("leader_ideology", PropertyDomain.IDENTITY, "string", "Political ideology of leader", "cia-factbook"),

    # ── Demographics ──
    "population": PropertySpec("population", PropertyDomain.DEMOGRAPHICS, "integer", "Total population", "worldbank-wdi", game_critical=True, normalize=_ensure_int),
    "urbanization": PropertySpec("urbanization", PropertyDomain.DEMOGRAPHICS, "percent", "Urban population %", "worldbank-wdi", normalize=_ensure_float),
    "internet_penetration": PropertySpec("internet_penetration", PropertyDomain.DEMOGRAPHICS, "percent", "Internet users %", "worldbank-wdi", normalize=_ensure_float),

    # ── Economics ──
    "gdp_nominal": PropertySpec("gdp_nominal", PropertyDomain.ECONOMICS, "USD", "GDP in current USD", "worldbank-wdi", game_critical=True, normalize=_ensure_float),
    "gdp_growth": PropertySpec("gdp_growth", PropertyDomain.ECONOMICS, "percent", "Annual GDP growth %", "worldbank-wdi", normalize=_ensure_float),
    "gdp_per_capita": PropertySpec("gdp_per_capita", PropertyDomain.ECONOMICS, "USD", "GDP per capita in current USD", "worldbank-wdi", normalize=_ensure_float),
    "gdp_10yr_cagr": PropertySpec("gdp_10yr_cagr", PropertyDomain.ECONOMICS, "percent", "10-year compound annual growth rate %", "worldbank-wdi", normalize=_ensure_float),
    "inflation_rate": PropertySpec("inflation_rate", PropertyDomain.ECONOMICS, "percent", "Consumer price inflation %", "worldbank-wdi", normalize=_ensure_float),
    "unemployment": PropertySpec("unemployment", PropertyDomain.ECONOMICS, "percent", "Unemployment rate %", "worldbank-wdi", normalize=_ensure_float),
    "gini": PropertySpec("gini", PropertyDomain.ECONOMICS, "float_0_100", "Gini coefficient (0-100)", "worldbank-wdi", nullable=True, normalize=_ensure_float),
    "debt_to_gdp": PropertySpec("debt_to_gdp", PropertyDomain.ECONOMICS, "percent", "Government debt as % of GDP", "worldbank-wdi", normalize=_ensure_float),
    "forex_reserves": PropertySpec("forex_reserves", PropertyDomain.ECONOMICS, "USD", "Foreign exchange reserves in USD", "worldbank-wdi", normalize=_ensure_float),

    # ── Military ──
    "military_spending_abs": PropertySpec(
        "military_spending_abs", PropertyDomain.MILITARY, "USD",
        "Military expenditure in absolute USD",
        "sipri-milex", game_critical=True,
        normalize=_millions_to_abs,  # SIPRI reports in millions!
    ),
    "military_spending_pct_gdp": PropertySpec("military_spending_pct_gdp", PropertyDomain.MILITARY, "percent", "Military spending as % of GDP", "sipri-milex", normalize=_ensure_float),
    "manpower_active": PropertySpec("manpower_active", PropertyDomain.MILITARY, "integer", "Active military personnel", "iiss-milbal", normalize=_ensure_int),
    "manpower_reserve": PropertySpec("manpower_reserve", PropertyDomain.MILITARY, "integer", "Reserve military personnel", "iiss-milbal", normalize=_ensure_int),
    "nuclear_warheads": PropertySpec("nuclear_warheads", PropertyDomain.MILITARY, "integer", "Estimated nuclear warheads", "fas-nuclear", normalize=_ensure_int),
    "nuclear_status": PropertySpec("nuclear_status", PropertyDomain.MILITARY, "enum", "Nuclear capability status", "fas-nuclear"),

    # ── Governance ──
    "stability_index": PropertySpec("stability_index", PropertyDomain.GOVERNANCE, "float_0_100", "Political stability (0-100)", "vdem", game_critical=True, normalize=_vdem_to_100),
    "freedom_house_score": PropertySpec("freedom_house_score", PropertyDomain.GOVERNANCE, "float_0_100", "Freedom House score (0-100)", "vdem", normalize=_ensure_float),
    "corruption_index": PropertySpec("corruption_index", PropertyDomain.GOVERNANCE, "float_0_100", "Corruption Perceptions Index (0-100)", "vdem", normalize=_ensure_float),
    "press_freedom": PropertySpec("press_freedom", PropertyDomain.GOVERNANCE, "float_0_100", "Press freedom score (0-100)", "vdem", normalize=_ensure_float),

    # ── Game State ──
    "national_morale": PropertySpec("national_morale", PropertyDomain.GAME_STATE, "float_0_100", "National morale (0-100)", "archon-mock", game_critical=True, normalize=_ensure_float),
    "war_weariness": PropertySpec("war_weariness", PropertyDomain.GAME_STATE, "float_0_100", "War weariness (0-100)", "archon-mock", game_critical=True, normalize=_ensure_float),
}

# Quick lookups
GAME_CRITICAL_PROPERTIES = [name for name, spec in PROPERTY_SPECS.items() if spec.game_critical]
NULLABLE_PROPERTIES = [name for name, spec in PROPERTY_SPECS.items() if spec.nullable]
NON_NULLABLE_PROPERTIES = [name for name, spec in PROPERTY_SPECS.items() if not spec.nullable and spec.domain != PropertyDomain.PROVENANCE]


def normalize_value(property_name: str, raw_value: Any) -> Any:
    """Normalize a raw value to canonical form.
    
    Args:
        property_name: The property name (must exist in PROPERTY_SPECS)
        raw_value: The raw value from the data source
        
    Returns:
        Normalized value in canonical unit/scale
        
    Raises:
        KeyError: If property_name is not in the registry
        ValueError: If the value cannot be normalized
    """
    spec = PROPERTY_SPECS[property_name]
    if raw_value is None:
        return None
    if spec.normalize is not None:
        return spec.normalize(raw_value)
    return raw_value


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize all values in a record dict.
    
    Only processes keys that exist in PROPERTY_SPECS.
    Unknown keys are passed through unchanged.
    """
    result = {}
    for key, value in record.items():
        if key in PROPERTY_SPECS and value is not None:
            result[key] = normalize_value(key, value)
        else:
            result[key] = value
    return result


# ──────────────────────────────────────────────
# Source-specific normalization helpers
# ──────────────────────────────────────────────

# World Bank indicator codes → our property names
WORLDBANK_INDICATOR_MAP = {
    "NY.GDP.MKTP.CD": "gdp_nominal",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth",
    "NY.GDP.PCAP.CD": "gdp_per_capita",
    "SP.POP.TOTL": "population",
    "FP.CPI.TOTL.ZG": "inflation_rate",
    "SL.UEM.TOTL.ZS": "unemployment",
    "SI.POV.GINI": "gini",
    "GC.DOD.TOTL.GD.ZS": "debt_to_gdp",
    "FI.RES.TOTL.CD": "forex_reserves",
    "SP.URB.TOTL.IN.ZS": "urbanization",
    "IT.NET.USER.ZS": "internet_penetration",
}

# World Bank income groups (for imputation)
INCOME_GROUPS = {
    "HIC": "High income",
    "UMC": "Upper middle income",
    "LMC": "Lower middle income",
    "LIC": "Low income",
}
