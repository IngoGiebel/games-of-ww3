"""Tests for historical Sprint 2 time-series helpers."""

from gww3.data.historical_series import (
    compute_cagr,
    compute_metrics,
    compute_trend_slope,
    compute_volatility,
    normalize_series,
    validate_temporal_series,
)


def test_normalize_series_filters_none_and_out_of_range():
    series = {
        "2015": 1,
        "2016": 2,
        "2017": None,
        "2018": 3,
        "2026": 4,
    }
    assert normalize_series(series) == {2016: 2.0, 2018: 3.0}


def test_compute_cagr_positive_series():
    series = {2016: 100, 2020: 121}
    assert round(compute_cagr(series), 2) == 4.88


def test_compute_trend_slope():
    series = {2016: 10, 2017: 12, 2018: 14, 2019: 16}
    assert compute_trend_slope(series) == 2.0


def test_compute_volatility_from_yoy_changes():
    series = {2016: 100, 2017: 110, 2018: 99, 2019: 108.9}
    assert compute_volatility(series) is not None


def test_compute_metrics_bundle():
    metrics = compute_metrics({2016: 50, 2017: 60, 2018: 70})
    assert metrics["points"] == 3
    assert metrics["start_year"] == 2016
    assert metrics["end_year"] == 2018
    assert metrics["latest_value"] == 70.0
    assert metrics["trend_slope"] == 10.0


def test_validate_temporal_series_flags_large_population_jump():
    issues = validate_temporal_series(
        "population",
        {2016: 1_000_000, 2017: 1_500_000, 2018: 1_510_000},
    )
    assert any("relative jump" in issue for issue in issues)


def test_validate_temporal_series_allows_sparse_gini_without_gap_noise():
    issues = validate_temporal_series("gini", {2016: 40, 2019: 41, 2022: 42})
    assert any("sparse series" in issue for issue in issues)
