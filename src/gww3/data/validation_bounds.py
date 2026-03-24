"""Sanity Bounds Validation for GWW3.

Hard invariants that MUST hold for every data import.
If any bound is violated, the task is blocked and escalated to Dione.

These are absolute physical/logical limits, NOT game balance constraints.
A nation with GDP=0 is a data error. A nation with GDP=$100B being invaded
by a nation with GDP=$28T is a game design question, not a data error.

Bounds are intentionally loose to accommodate edge cases:
- Venezuela inflation can exceed 1,000,000%
- Vatican City population is ~800
- Tuvalu GDP is ~60M
- North Korea military spending is classified (use estimate)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Bound:
    """A validation bound for a property."""
    property_name: str
    min_value: float | None = None
    max_value: float | None = None
    description: str = ""
    severity: str = "block"  # block | warn
    
    def check(self, value: Any) -> str | None:
        """Check if a value satisfies this bound.
        
        Returns:
            None if valid, error message string if violated.
        """
        if value is None:
            return None  # Null checking is handled by imputation, not bounds
        
        try:
            num = float(value)
        except (TypeError, ValueError):
            return f"{self.property_name}: cannot convert '{value}' to number"
        
        if self.min_value is not None and num < self.min_value:
            return (
                f"{self.property_name}={num:,.0f} below minimum {self.min_value:,.0f}. "
                f"{self.description}"
            )
        if self.max_value is not None and num > self.max_value:
            return (
                f"{self.property_name}={num:,.0f} above maximum {self.max_value:,.0f}. "
                f"{self.description}"
            )
        return None


# ──────────────────────────────────────────────
# Absolute Bounds (physical/logical limits)
# ──────────────────────────────────────────────

ABSOLUTE_BOUNDS = [
    # Economics
    Bound("gdp_nominal", min_value=10_000_000, max_value=50_000_000_000_000,
          description="Smallest nations (Tuvalu) ~$60M, largest (USA) ~$28T"),
    Bound("gdp_growth", min_value=-50, max_value=100,
          description="Worst contractions ~-30% (war), fastest growth ~30% (post-war recovery)"),
    Bound("gdp_per_capita", min_value=100, max_value=200_000,
          description="Poorest (Burundi) ~$250, richest (Luxembourg) ~$130k"),
    Bound("inflation_rate", min_value=-20, max_value=10_000_000,
          description="Deflation floor -15%, hyperinflation (Venezuela 2018) ~1,000,000%"),
    Bound("unemployment", min_value=0, max_value=80,
          description="Near-zero possible (Qatar), max ~70% (conflict zones)"),
    Bound("gini", min_value=15, max_value=70,
          description="Most equal (Slovakia ~23), most unequal (South Africa ~63)"),
    Bound("debt_to_gdp", min_value=0, max_value=500,
          description="Some nations near 0%, Japan ~260%"),
    Bound("forex_reserves", min_value=0, max_value=5_000_000_000_000,
          description="China ~$3.2T is the global maximum"),

    # Demographics
    Bound("population", min_value=800, max_value=1_500_000_000,
          description="Vatican ~800, India/China ~1.4B"),
    Bound("urbanization", min_value=5, max_value=100,
          description="Burundi ~14%, Singapore 100%"),
    Bound("internet_penetration", min_value=0, max_value=100,
          description="0% theoretically possible (North Korea ~0.1%)"),

    # Military
    Bound("military_spending_abs", min_value=0, max_value=1_200_000_000_000,
          description="Some nations have no military (Iceland), USA ~$980B"),
    Bound("military_spending_pct_gdp", min_value=0, max_value=30,
          description="0% (no military), max ~20% (wartime/North Korea)"),
    Bound("manpower_active", min_value=0, max_value=3_000_000,
          description="0 (Iceland), China ~2M"),
    Bound("manpower_reserve", min_value=0, max_value=10_000_000,
          description="0 to South Korea ~3.1M"),
    Bound("nuclear_warheads", min_value=0, max_value=7_000,
          description="0 for most, Russia ~5,977"),

    # Governance (all 0-100 scale)
    Bound("stability_index", min_value=0, max_value=100,
          description="Game-normalized 0-100 scale"),
    Bound("freedom_house_score", min_value=0, max_value=100,
          description="Freedom House 0-100"),
    Bound("corruption_index", min_value=0, max_value=100,
          description="TI CPI 0-100"),
    Bound("press_freedom", min_value=0, max_value=100,
          description="RSF/V-Dem normalized 0-100"),

    # Game state (all 0-100 scale)
    Bound("national_morale", min_value=0, max_value=100),
    Bound("war_weariness", min_value=0, max_value=100),
]

# ──────────────────────────────────────────────
# Cross-Property Invariants
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class CrossPropertyInvariant:
    """A validation rule involving multiple properties."""
    name: str
    description: str
    severity: str = "block"
    
    def check(self, record: dict) -> str | None:
        """Override in subclass or use factory. Returns error message or None."""
        raise NotImplementedError


class MilitaryLessThanGDP(CrossPropertyInvariant):
    """Military spending cannot exceed GDP."""
    def check(self, record: dict) -> str | None:
        mil = record.get("military_spending_abs")
        gdp = record.get("gdp_nominal")
        if mil is not None and gdp is not None and float(mil) > float(gdp):
            return f"military_spending_abs ({mil:,.0f}) > gdp_nominal ({gdp:,.0f})"
        return None


class ManpowerLessThanPopulation(CrossPropertyInvariant):
    """Active military cannot exceed total population."""
    def check(self, record: dict) -> str | None:
        mp = record.get("manpower_active")
        pop = record.get("population")
        if mp is not None and pop is not None and int(mp) > int(pop):
            return f"manpower_active ({mp}) > population ({pop})"
        return None


class ReserveLessThanPopulation(CrossPropertyInvariant):
    """Reserve military cannot exceed total population."""
    def check(self, record: dict) -> str | None:
        res = record.get("manpower_reserve")
        pop = record.get("population")
        if res is not None and pop is not None and int(res) > int(pop):
            return f"manpower_reserve ({res}) > population ({pop})"
        return None


class MilitaryPctConsistent(CrossPropertyInvariant):
    """Military spending % should roughly match abs/GDP ratio."""
    def check(self, record: dict) -> str | None:
        mil = record.get("military_spending_abs")
        gdp = record.get("gdp_nominal")
        pct = record.get("military_spending_pct_gdp")
        if mil and gdp and pct and float(gdp) > 0:
            computed = (float(mil) / float(gdp)) * 100
            declared = float(pct)
            # Allow 50% relative tolerance (sources may use different GDP bases)
            if abs(computed - declared) > max(declared * 0.5, 1.0):
                return (
                    f"military_spending_pct_gdp ({declared:.1f}%) inconsistent with "
                    f"abs/GDP ratio ({computed:.1f}%)"
                )
        return None


CROSS_INVARIANTS = [
    MilitaryLessThanGDP("mil_lt_gdp", "Military spending must be less than GDP"),
    ManpowerLessThanPopulation("mp_lt_pop", "Active military must be less than population"),
    ReserveLessThanPopulation("res_lt_pop", "Reserve military must be less than population"),
    MilitaryPctConsistent("mil_pct_consistent", "Military % should match abs/GDP ratio", severity="warn"),
]


# ──────────────────────────────────────────────
# Validation API
# ──────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of validating a record."""
    passed: bool
    errors: list[str]     # blocking errors
    warnings: list[str]   # non-blocking warnings
    
    @property
    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} error(s): {'; '.join(self.errors)}")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s): {'; '.join(self.warnings)}")
        return " | ".join(parts) if parts else "OK"


def validate_record(record: dict) -> ValidationResult:
    """Validate a nation record against all bounds and invariants.
    
    Args:
        record: Dict of nation properties
        
    Returns:
        ValidationResult with pass/fail status and details
    """
    errors = []
    warnings = []
    
    # Check absolute bounds
    for bound in ABSOLUTE_BOUNDS:
        val = record.get(bound.property_name)
        if val is not None:
            msg = bound.check(val)
            if msg:
                if bound.severity == "block":
                    errors.append(msg)
                else:
                    warnings.append(msg)
    
    # Check cross-property invariants
    for invariant in CROSS_INVARIANTS:
        msg = invariant.check(record)
        if msg:
            if invariant.severity == "block":
                errors.append(msg)
            else:
                warnings.append(msg)
    
    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_batch(records: list[dict]) -> dict[str, ValidationResult]:
    """Validate a batch of nation records.
    
    Args:
        records: List of nation dicts (must have 'iso3' key)
        
    Returns:
        Dict of {iso3: ValidationResult}
    """
    results = {}
    for record in records:
        iso3 = record.get("iso3", "UNKNOWN")
        results[iso3] = validate_record(record)
    return results
