"""Tests for imputation module."""
import pytest
from gww3.data.imputation import (
    impute_value, build_imputation_context, impute_record,
    ImputationContext,
)


def _make_context():
    """Build a test context with known averages covering all non-nullable numeric properties."""
    _base = {
        "gdp_nominal": 3e12, "gdp_growth": 1.5, "gdp_per_capita": 40000, "gdp_10yr_cagr": 1.2,
        "inflation_rate": 3.0, "unemployment": 5.0, "debt_to_gdp": 70.0, "forex_reserves": 200e9,
        "population": 80_000_000, "urbanization": 75.0, "internet_penetration": 85.0,
        "military_spending_abs": 50e9, "military_spending_pct_gdp": 1.8,
        "manpower_active": 200_000, "manpower_reserve": 100_000, "nuclear_warheads": 0,
        "stability_index": 70, "freedom_house_score": 80, "corruption_index": 70, "press_freedom": 75,
        "national_morale": 60, "war_weariness": 10,
    }
    records = [
        {"iso3": "DEU", "sub_region": "Western Europe", "income_group": "HIC",
         **_base, "gdp_nominal": 4.7e12, "population": 84_000_000, "stability_index": 78},
        {"iso3": "FRA", "sub_region": "Western Europe", "income_group": "HIC",
         **_base, "gdp_nominal": 3.1e12, "population": 66_000_000, "stability_index": 70},
        {"iso3": "BRA", "sub_region": "South America", "income_group": "UMC",
         **_base, "gdp_nominal": 2.3e12, "population": 216_000_000, "stability_index": 50},
        {"iso3": "IND", "sub_region": "Southern Asia", "income_group": "LMC",
         **_base, "gdp_nominal": 4.1e12, "population": 1_420_000_000, "stability_index": 55},
    ]
    return build_imputation_context(records)


def test_temporal_backfill():
    """Priority 1: Use latest available year."""
    ctx = ImputationContext()
    result = impute_value(
        "gdp_nominal", "Western Europe", "HIC",
        historical_values={2022: 4.5e12, 2023: 4.6e12},
        context=ctx,
    )
    assert result is not None
    assert result.value == 4.6e12  # Latest year (2023)
    assert result.method == "temporal_backfill"
    assert result.source_year == 2023


def test_regional_average():
    """Priority 2: Regional average when no historical data."""
    ctx = _make_context()
    result = impute_value(
        "gdp_nominal", "Western Europe", "HIC",
        historical_values=None,
        context=ctx,
    )
    assert result is not None
    assert result.method == "regional_avg"
    # Average of DEU (4.7T) and FRA (3.1T) = 3.9T
    assert abs(result.value - 3.9e12) < 1e9


def test_income_group_fallback():
    """Priority 3: Income group when region has no data."""
    ctx = _make_context()
    result = impute_value(
        "gdp_nominal", "Unknown Region", "HIC",
        historical_values=None,
        context=ctx,
    )
    assert result is not None
    assert result.method == "income_group_avg"


def test_global_median_fallback():
    """Priority 4: Global median as last resort."""
    ctx = _make_context()
    result = impute_value(
        "gdp_nominal", "Unknown Region", "Unknown",
        historical_values=None,
        context=ctx,
    )
    assert result is not None
    assert result.method == "global_median"


def test_nullable_property_returns_none():
    """Gini is nullable — should return None if no data available."""
    ctx = ImputationContext()  # Empty context
    result = impute_value(
        "gini", "Unknown", "Unknown",
        historical_values=None,
        context=ctx,
    )
    assert result is None


def test_non_nullable_raises():
    """Non-nullable property with no data should raise ValueError."""
    ctx = ImputationContext()  # Empty context
    with pytest.raises(ValueError, match="Cannot impute non-nullable"):
        impute_value(
            "gdp_nominal", "Unknown", "Unknown",
            historical_values=None,
            context=ctx,
        )


def test_imputation_metadata():
    """ImputationResult should provide metadata dict."""
    ctx = ImputationContext()
    result = impute_value(
        "gdp_nominal", "Western Europe", "HIC",
        historical_values={2022: 4.5e12},
        context=ctx,
    )
    meta = result.metadata
    assert meta["imputation_method"] == "temporal_backfill"
    assert meta["data_confidence"] == "estimated"
    assert meta["imputation_source_year"] == 2022


def test_impute_record_fills_gaps():
    """impute_record should fill all None values."""
    ctx = _make_context()
    record = {
        "iso3": "AUT",
        "sub_region": "Western Europe",
        "income_group": "HIC",
        "gdp_nominal": None,
        "population": 9_000_000,
        "stability_index": None,
    }
    completed, imputations = impute_record(record, ctx)
    assert completed["gdp_nominal"] is not None
    assert completed["population"] == 9_000_000  # Not imputed (already has value)
    assert completed["stability_index"] is not None
    assert len(imputations) >= 2  # At least gdp + stability were imputed
