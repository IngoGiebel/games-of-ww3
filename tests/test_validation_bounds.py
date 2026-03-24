"""Tests for validation bounds module."""
import pytest
from gww3.data.validation_bounds import (
    validate_record, validate_batch, Bound,
    MilitaryLessThanGDP, ManpowerLessThanPopulation,
)


# ──────────────────────────────────────────────
# Valid Records
# ──────────────────────────────────────────────

VALID_USA = {
    "iso3": "USA",
    "gdp_nominal": 28_000_000_000_000,
    "gdp_growth": 2.5,
    "gdp_per_capita": 83_500,
    "inflation_rate": 3.2,
    "unemployment": 3.7,
    "gini": 39.7,
    "debt_to_gdp": 123.0,
    "forex_reserves": 245_000_000_000,
    "population": 335_000_000,
    "urbanization": 83.0,
    "internet_penetration": 92.0,
    "military_spending_abs": 980_000_000_000,
    "military_spending_pct_gdp": 3.5,
    "manpower_active": 1_400_000,
    "manpower_reserve": 800_000,
    "nuclear_warheads": 5550,
    "stability_index": 72,
    "freedom_house_score": 83,
    "corruption_index": 67,
    "press_freedom": 72,
    "national_morale": 65,
    "war_weariness": 15,
}

VALID_TUVALU = {
    "iso3": "TUV",
    "gdp_nominal": 60_000_000,
    "population": 11_000,
    "military_spending_abs": 0,
    "manpower_active": 0,
    "stability_index": 80,
}


def test_valid_usa_passes():
    result = validate_record(VALID_USA)
    assert result.passed, f"USA should pass: {result.summary}"
    assert len(result.errors) == 0


def test_valid_tuvalu_passes():
    result = validate_record(VALID_TUVALU)
    assert result.passed, f"Tuvalu should pass: {result.summary}"


# ──────────────────────────────────────────────
# Bound Violations
# ──────────────────────────────────────────────

def test_gdp_too_low():
    """GDP below $10M should fail."""
    record = {**VALID_TUVALU, "gdp_nominal": 5_000}
    result = validate_record(record)
    assert not result.passed
    assert any("gdp_nominal" in e for e in result.errors)


def test_gdp_too_high():
    """GDP above $50T should fail."""
    record = {**VALID_USA, "gdp_nominal": 60_000_000_000_000}
    result = validate_record(record)
    assert not result.passed
    assert any("gdp_nominal" in e for e in result.errors)


def test_negative_population():
    """Population must be positive."""
    record = {**VALID_USA, "population": -1}
    result = validate_record(record)
    assert not result.passed


def test_hyperinflation_allowed():
    """Venezuela-style hyperinflation should pass."""
    record = {**VALID_USA, "inflation_rate": 1_000_000}
    result = validate_record(record)
    assert result.passed


def test_nuclear_warheads_negative():
    """Nuclear warheads can't be negative."""
    record = {**VALID_USA, "nuclear_warheads": -5}
    result = validate_record(record)
    assert not result.passed


# ──────────────────────────────────────────────
# Cross-Property Invariants
# ──────────────────────────────────────────────

def test_military_exceeds_gdp():
    """Military spending cannot exceed GDP."""
    record = {**VALID_USA, "military_spending_abs": 30_000_000_000_000}
    result = validate_record(record)
    assert not result.passed
    assert any("military_spending_abs" in e for e in result.errors)


def test_manpower_exceeds_population():
    """Active military cannot exceed population."""
    record = {**VALID_TUVALU, "manpower_active": 1_000_000, "population": 11_000}
    result = validate_record(record)
    assert not result.passed
    assert any("manpower_active" in e for e in result.errors)


def test_mil_pct_inconsistency_warns():
    """Inconsistent military % vs abs/GDP triggers warning, not error."""
    record = {
        **VALID_USA,
        "military_spending_pct_gdp": 15.0,  # Way off from actual ~3.5%
    }
    result = validate_record(record)
    # This should warn, not block
    assert result.passed  # warnings don't block
    assert len(result.warnings) > 0


# ──────────────────────────────────────────────
# Batch Validation
# ──────────────────────────────────────────────

def test_batch_validation():
    batch = [VALID_USA, VALID_TUVALU]
    results = validate_batch(batch)
    assert "USA" in results
    assert "TUV" in results
    assert results["USA"].passed
    assert results["TUV"].passed


def test_batch_with_failure():
    bad_record = {**VALID_USA, "iso3": "BAD", "gdp_nominal": 1}
    batch = [VALID_USA, bad_record]
    results = validate_batch(batch)
    assert results["USA"].passed
    assert not results["BAD"].passed
