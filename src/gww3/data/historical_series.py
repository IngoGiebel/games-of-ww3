"""Helpers for 10-year historical time series used in Sprint 2."""

from __future__ import annotations

from statistics import pstdev

YEAR_START = 2016
YEAR_END = 2025
YEARS = tuple(range(YEAR_START, YEAR_END + 1))


def normalize_series(series: dict[int | str, float | int | None]) -> dict[int, float]:
    """Return a sorted year->float mapping limited to the Sprint 2 year range."""
    normalized: dict[int, float] = {}
    for year_raw, value in series.items():
        if value is None:
            continue
        year = int(year_raw)
        if YEAR_START <= year <= YEAR_END:
            normalized[year] = float(value)
    return dict(sorted(normalized.items()))


def series_points(series: dict[int | str, float | int | None]) -> list[tuple[int, float]]:
    """Return sorted (year, value) points."""
    return list(normalize_series(series).items())


def compute_cagr(series: dict[int | str, float | int | None]) -> float | None:
    """Compound annual growth rate in percent."""
    points = series_points(series)
    if len(points) < 2:
        return None
    start_year, start_value = points[0]
    end_year, end_value = points[-1]
    if start_value <= 0 or end_value <= 0 or end_year <= start_year:
        return None
    return round((((end_value / start_value) ** (1 / (end_year - start_year))) - 1) * 100, 4)


def compute_trend_slope(series: dict[int | str, float | int | None]) -> float | None:
    """Linear regression slope per year."""
    points = series_points(series)
    n = len(points)
    if n < 2:
        return None

    xs = [year for year, _ in points]
    ys = [value for _, value in points]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def compute_volatility(series: dict[int | str, float | int | None]) -> float | None:
    """Population std-dev of year-over-year percentage changes."""
    points = series_points(series)
    if len(points) < 3:
        return None

    deltas: list[float] = []
    for (_, previous), (_, current) in zip(points, points[1:]):
        if previous == 0:
            continue
        deltas.append(((current - previous) / abs(previous)) * 100)
    if len(deltas) < 2:
        return None
    return round(pstdev(deltas), 4)


def max_abs_yoy_change(series: dict[int | str, float | int | None]) -> float | None:
    """Largest absolute year-over-year percentage change."""
    points = series_points(series)
    if len(points) < 2:
        return None
    max_change: float | None = None
    for (_, previous), (_, current) in zip(points, points[1:]):
        if previous == 0:
            continue
        change = abs(((current - previous) / abs(previous)) * 100)
        max_change = change if max_change is None else max(max_change, change)
    return round(max_change, 4) if max_change is not None else None


def compute_metrics(series: dict[int | str, float | int | None]) -> dict[str, float | int | None]:
    """Convenience bundle used by the ETL scripts."""
    points = series_points(series)
    if not points:
        return {
            "points": 0,
            "start_year": None,
            "end_year": None,
            "latest_value": None,
            "cagr_pct": None,
            "trend_slope": None,
            "volatility_pct": None,
            "max_abs_yoy_change_pct": None,
        }

    return {
        "points": len(points),
        "start_year": points[0][0],
        "end_year": points[-1][0],
        "latest_value": round(points[-1][1], 4),
        "cagr_pct": compute_cagr(series),
        "trend_slope": compute_trend_slope(series),
        "volatility_pct": compute_volatility(series),
        "max_abs_yoy_change_pct": max_abs_yoy_change(series),
    }


TEMPORAL_LIMITS: dict[str, dict[str, float | int]] = {
    "gdp_nominal": {"max_relative_yoy_pct": 60.0, "min_points": 8},
    "population": {"max_relative_yoy_pct": 8.0, "min_points": 10},
    "urbanization": {"max_absolute_delta": 12.0, "min_points": 8},
    "internet_penetration": {"max_absolute_delta": 30.0, "min_points": 8},
    "inflation_rate": {"max_absolute_delta": 500.0, "min_points": 8},
    "unemployment": {"max_absolute_delta": 20.0, "min_points": 8},
    "gini": {"max_absolute_delta": 10.0, "min_points": 4},
    "debt_to_gdp": {"max_absolute_delta": 80.0, "min_points": 6},
    "forex_reserves": {"max_relative_yoy_pct": 100.0, "min_points": 6},
    "military_spending_abs": {"max_relative_yoy_pct": 150.0, "min_points": 6},
    "military_spending_pct_gdp": {"max_absolute_delta": 8.0, "min_points": 4},
    "stability_index": {"max_absolute_delta": 20.0, "min_points": 8},
    "freedom_house_score": {"max_absolute_delta": 20.0, "min_points": 8},
    "corruption_index": {"max_absolute_delta": 20.0, "min_points": 8},
    "press_freedom": {"max_absolute_delta": 25.0, "min_points": 8},
}


def validate_temporal_series(
    property_name: str,
    series: dict[int | str, float | int | None],
) -> list[str]:
    """Return temporal consistency issues for a single yearly series."""
    points = series_points(series)
    limits = TEMPORAL_LIMITS.get(property_name, {})
    min_points = int(limits.get("min_points", 0))
    issues: list[str] = []

    if min_points and len(points) < min_points:
        issues.append(f"{property_name}: sparse series ({len(points)} points)")

    years_present = {year for year, _ in points}
    missing = [year for year in YEARS if year not in years_present]
    if missing and len(points) >= min_points:
        issues.append(f"{property_name}: missing years {missing}")

    max_rel = limits.get("max_relative_yoy_pct")
    max_abs = limits.get("max_absolute_delta")
    for (prev_year, previous), (year, current) in zip(points, points[1:]):
        if year - prev_year != 1:
            issues.append(f"{property_name}: gap between {prev_year} and {year}")
            continue

        delta = current - previous
        if max_abs is not None and abs(delta) > float(max_abs):
            issues.append(
                f"{property_name}: absolute jump {delta:.2f} from {prev_year} to {year}"
            )

        if previous != 0 and max_rel is not None:
            rel = abs((delta / abs(previous)) * 100)
            if rel > float(max_rel):
                issues.append(
                    f"{property_name}: relative jump {rel:.2f}% from {prev_year} to {year}"
                )

    return issues
