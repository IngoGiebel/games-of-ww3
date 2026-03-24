"""Tests for normalization module."""
import pytest
from gww3.data.normalization import (
    normalize_value, normalize_record,
    _millions_to_abs, _vdem_to_100,
    PROPERTY_SPECS, GAME_CRITICAL_PROPERTIES,
)


def test_sipri_millions_to_absolute():
    """SIPRI reports military spending in millions USD."""
    assert _millions_to_abs(980) == 980_000_000
    assert _millions_to_abs(5.2) == 5_200_000


def test_vdem_to_100_scale():
    """V-Dem 0-1 floats → 0-100 integers."""
    assert _vdem_to_100(0.78) == 78
    assert _vdem_to_100(0.0) == 0
    assert _vdem_to_100(1.0) == 100
    assert _vdem_to_100(0.555) == 56  # rounds


def test_normalize_military_spending():
    """Military spending normalization from SIPRI millions."""
    val = normalize_value("military_spending_abs", 98.7)
    assert val == 98_700_000


def test_normalize_stability_index():
    """V-Dem stability index normalization."""
    val = normalize_value("stability_index", 0.72)
    assert val == 72


def test_normalize_gdp():
    """GDP should be kept as-is (already in USD)."""
    val = normalize_value("gdp_nominal", 4_700_000_000_000)
    assert val == 4_700_000_000_000.0


def test_normalize_none_returns_none():
    """None values pass through."""
    assert normalize_value("gdp_nominal", None) is None


def test_normalize_record():
    """Full record normalization."""
    raw = {
        "iso3": "DEU",
        "gdp_nominal": "4700000000000",
        "stability_index": 0.78,
        "military_spending_abs": 98.7,  # SIPRI millions
        "population": "84000000",
    }
    result = normalize_record(raw)
    assert result["gdp_nominal"] == 4_700_000_000_000.0
    assert result["stability_index"] == 78
    assert result["military_spending_abs"] == 98_700_000.0
    assert result["population"] == 84_000_000
    assert result["iso3"] == "DEU"  # string, no conversion


def test_game_critical_properties_defined():
    """Ensure game-critical properties are identified."""
    assert "gdp_nominal" in GAME_CRITICAL_PROPERTIES
    assert "population" in GAME_CRITICAL_PROPERTIES
    assert "stability_index" in GAME_CRITICAL_PROPERTIES
    assert "national_morale" in GAME_CRITICAL_PROPERTIES
    assert "military_spending_abs" in GAME_CRITICAL_PROPERTIES


def test_unknown_property_raises():
    """Unknown properties should raise KeyError."""
    with pytest.raises(KeyError):
        normalize_value("nonexistent_property", 42)
