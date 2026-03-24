"""Missing Data Imputation for GWW3.

The game engine uses deterministic math: null values cause TypeErrors.
Every property MUST have a value. Missing data is imputed, never left null.

Imputation Hierarchy (in priority order):
1. Latest available year from same source (e.g., WB 2022 if 2024 missing)
2. Regional average (same sub_region + same income group)
3. Income-group average (World Bank income classifications)
4. Global median

All imputed values are tagged:
  data_confidence: "estimated"
  imputation_method: "temporal_backfill" | "regional_avg" | "income_group_avg" | "global_median"
  imputation_source_year: 2022  (for temporal backfill)

Design rationale:
- Regional average is preferred over income-group because neighbors share geopolitical
  characteristics (borders, trade patterns, conflict exposure) beyond just wealth.
- Global median is the last resort — it's better than null but carries maximum uncertainty.
- Gini coefficient is the only nullable property (many nations don't measure it).
  Even Gini gets imputed if possible, but we accept null for tiny island states.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from gww3.data.normalization import PROPERTY_SPECS, NULLABLE_PROPERTIES


@dataclass
class ImputationResult:
    """Result of imputing a single value."""
    value: Any
    method: str              # temporal_backfill | regional_avg | income_group_avg | global_median
    confidence: str = "estimated"
    source_year: int | None = None  # For temporal backfill
    sample_size: int = 0     # How many nations contributed to the average
    
    @property
    def metadata(self) -> dict:
        """Return metadata dict for Neo4j property tagging."""
        result = {
            "imputation_method": self.method,
            "data_confidence": self.confidence,
        }
        if self.source_year:
            result["imputation_source_year"] = self.source_year
        return result


@dataclass
class ImputationContext:
    """Context needed for imputation decisions.
    
    Populated from Neo4j before running imputation on a batch.
    """
    # Regional averages: {(sub_region, income_group): {property: value}}
    regional_averages: dict[tuple[str, str], dict[str, float]] = field(default_factory=dict)
    
    # Income group averages: {income_group: {property: value}}
    income_group_averages: dict[str, dict[str, float]] = field(default_factory=dict)
    
    # Global medians: {property: value}
    global_medians: dict[str, float] = field(default_factory=dict)


def impute_value(
    property_name: str,
    sub_region: str,
    income_group: str,
    historical_values: dict[int, float] | None,
    context: ImputationContext,
) -> ImputationResult | None:
    """Impute a missing value using the hierarchy.
    
    Args:
        property_name: The property to impute
        sub_region: Nation's sub_region (e.g., "Western Europe")
        income_group: World Bank income group (e.g., "HIC")
        historical_values: {year: value} dict of prior years, if available
        context: Pre-computed averages for the entire dataset
        
    Returns:
        ImputationResult with value and metadata, or None if property is nullable
        and no imputation is possible
    """
    spec = PROPERTY_SPECS.get(property_name)
    
    # Strategy 1: Temporal backfill — use latest available year
    if historical_values:
        sorted_years = sorted(historical_values.keys(), reverse=True)
        for year in sorted_years:
            val = historical_values[year]
            if val is not None:
                return ImputationResult(
                    value=val,
                    method="temporal_backfill",
                    source_year=year,
                    sample_size=1,
                )
    
    # Strategy 2: Regional average (sub_region + income_group)
    regional_key = (sub_region, income_group)
    if regional_key in context.regional_averages:
        regional = context.regional_averages[regional_key]
        if property_name in regional:
            return ImputationResult(
                value=regional[property_name],
                method="regional_avg",
                sample_size=regional.get(f"_n_{property_name}", 0),
            )
    
    # Strategy 3: Income group average
    if income_group in context.income_group_averages:
        income = context.income_group_averages[income_group]
        if property_name in income:
            return ImputationResult(
                value=income[property_name],
                method="income_group_avg",
                sample_size=income.get(f"_n_{property_name}", 0),
            )
    
    # Strategy 4: Global median
    if property_name in context.global_medians:
        return ImputationResult(
            value=context.global_medians[property_name],
            method="global_median",
            sample_size=context.global_medians.get(f"_n_{property_name}", 0),
        )
    
    # If we get here and the property is nullable, return None (acceptable)
    if spec and spec.nullable:
        return None
    
    # Non-nullable property with no imputation possible — this is a problem
    raise ValueError(
        f"Cannot impute non-nullable property '{property_name}' for "
        f"region='{sub_region}', income='{income_group}'. "
        f"No historical, regional, income-group, or global data available."
    )


def build_imputation_context(nation_records: list[dict]) -> ImputationContext:
    """Build imputation context from a set of nation records.
    
    Call this BEFORE running imputation on the batch. It computes
    regional/income-group/global averages from the non-null values
    in the dataset.
    
    Args:
        nation_records: List of dicts with nation data (must include
                       'sub_region' and 'income_group' keys)
    
    Returns:
        ImputationContext with pre-computed averages
    """
    context = ImputationContext()
    
    # Collect values by grouping key
    regional_values: dict[tuple[str, str], dict[str, list[float]]] = {}
    income_values: dict[str, dict[str, list[float]]] = {}
    global_values: dict[str, list[float]] = {}
    
    numeric_properties = [
        name for name, spec in PROPERTY_SPECS.items()
        if spec.canonical_unit in ("USD", "percent", "integer", "float_0_100")
    ]
    
    for record in nation_records:
        sub_region = record.get("sub_region", "Unknown")
        income_group = record.get("income_group", "Unknown")
        regional_key = (sub_region, income_group)
        
        for prop in numeric_properties:
            val = record.get(prop)
            if val is not None:
                # Regional
                regional_values.setdefault(regional_key, {}).setdefault(prop, []).append(float(val))
                # Income group
                income_values.setdefault(income_group, {}).setdefault(prop, []).append(float(val))
                # Global
                global_values.setdefault(prop, []).append(float(val))
    
    # Compute averages
    for key, props in regional_values.items():
        context.regional_averages[key] = {}
        for prop, vals in props.items():
            context.regional_averages[key][prop] = statistics.mean(vals)
            context.regional_averages[key][f"_n_{prop}"] = len(vals)
    
    for group, props in income_values.items():
        context.income_group_averages[group] = {}
        for prop, vals in props.items():
            context.income_group_averages[group][prop] = statistics.mean(vals)
            context.income_group_averages[group][f"_n_{prop}"] = len(vals)
    
    for prop, vals in global_values.items():
        context.global_medians[prop] = statistics.median(vals)
        context.global_medians[f"_n_{prop}"] = len(vals)
    
    return context


def impute_record(
    record: dict[str, Any],
    context: ImputationContext,
    historical: dict[str, dict[int, float]] | None = None,
) -> tuple[dict[str, Any], list[ImputationResult]]:
    """Impute all missing values in a nation record.
    
    Args:
        record: Nation data dict (may contain None values)
        context: Pre-computed imputation context
        historical: {property_name: {year: value}} for temporal backfill
        
    Returns:
        Tuple of (completed record, list of ImputationResults for logging)
    """
    sub_region = record.get("sub_region", "Unknown")
    income_group = record.get("income_group", "Unknown")
    historical = historical or {}
    
    completed = dict(record)
    imputations = []
    
    # Only impute numeric properties from domains that make sense to average.
    # Identity fields (cow_code, un_m49, etc.) and string fields are not imputable.
    IMPUTABLE_DOMAINS = {"demographics", "economics", "military", "governance", "game_state"}
    numeric_properties = [
        name for name, spec in PROPERTY_SPECS.items()
        if spec.canonical_unit in ("USD", "percent", "integer", "float_0_100")
        and not spec.nullable
        and spec.domain.value in IMPUTABLE_DOMAINS
    ]
    
    for prop in numeric_properties:
        if completed.get(prop) is None:
            result = impute_value(
                property_name=prop,
                sub_region=sub_region,
                income_group=income_group,
                historical_values=historical.get(prop),
                context=context,
            )
            if result is not None:
                completed[prop] = result.value
                imputations.append(result)
    
    return completed, imputations
