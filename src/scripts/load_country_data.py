#!/usr/bin/env python3
"""Load country data from JSON files and instantiate Country models.

Usage:
    python src/scripts/load_country_data.py [--data-dir data/countries] [--country USA]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gww3.models.country import (
    Alliance,
    AllianceType,
    Country,
    Economy,
    Geography,
    GovernmentType,
    Military,
    NuclearCapability,
    NuclearDoctrine,
    Resources,
    TradeRelationship,
)


def load_country(filepath: Path) -> Country:
    """Load a single country from a JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    geo_data = data["geography"]
    geography = Geography(
        land_area_km2=geo_data["land_area_km2"],
        coastline_km=geo_data["coastline_km"],
        borders=geo_data.get("borders", []),
        num_regions=geo_data.get("num_regions", 1),
        terrain_defense_modifier=geo_data.get("terrain_defense_modifier", 1.0),
        strategic_chokepoints=geo_data.get("strategic_chokepoints", []),
    )

    econ_data = data["economy"]
    economy = Economy(
        gdp_billion_usd=econ_data["gdp_billion_usd"],
        gdp_growth_rate=econ_data["gdp_growth_rate"],
        gdp_per_capita_usd=econ_data["gdp_per_capita_usd"],
        government_debt_pct_gdp=econ_data["government_debt_pct_gdp"],
        inflation_rate=econ_data["inflation_rate"],
        unemployment_rate=econ_data["unemployment_rate"],
        trade_openness=econ_data["trade_openness"],
        credit_rating_score=econ_data["credit_rating_score"],
        rd_expenditure_pct_gdp=econ_data["rd_expenditure_pct_gdp"],
        fdi_billion_usd=econ_data["fdi_billion_usd"],
        budget_military=econ_data.get("budget_military", 0),
        budget_infrastructure=econ_data.get("budget_infrastructure", 0),
        budget_social=econ_data.get("budget_social", 0),
        budget_rd=econ_data.get("budget_rd", 0),
    )

    nuc_data = data["military"].get("nuclear", {})
    nuclear = NuclearCapability(
        total_warheads=nuc_data.get("total_warheads", 0),
        deployed_strategic=nuc_data.get("deployed_strategic", 0),
        deployed_nonstrategic=nuc_data.get("deployed_nonstrategic", 0),
        stockpiled_reserve=nuc_data.get("stockpiled_reserve", 0),
        icbm_launchers=nuc_data.get("icbm_launchers", 0),
        slbm_launchers=nuc_data.get("slbm_launchers", 0),
        strategic_bombers=nuc_data.get("strategic_bombers", 0),
        doctrine=NuclearDoctrine(nuc_data.get("doctrine", "none")),
        has_second_strike=nuc_data.get("has_second_strike", False),
        max_range_km=nuc_data.get("max_range_km", 0),
    )

    mil_data = data["military"]
    military = Military(
        active_personnel=mil_data["active_personnel"],
        reserve_personnel=mil_data["reserve_personnel"],
        paramilitary=mil_data.get("paramilitary", 0),
        tanks=mil_data.get("tanks", 0),
        armored_vehicles=mil_data.get("armored_vehicles", 0),
        artillery=mil_data.get("artillery", 0),
        fighter_aircraft=mil_data.get("fighter_aircraft", 0),
        attack_aircraft=mil_data.get("attack_aircraft", 0),
        transport_aircraft=mil_data.get("transport_aircraft", 0),
        helicopters_attack=mil_data.get("helicopters_attack", 0),
        helicopters_total=mil_data.get("helicopters_total", 0),
        aircraft_carriers=mil_data.get("aircraft_carriers", 0),
        submarines=mil_data.get("submarines", 0),
        destroyers=mil_data.get("destroyers", 0),
        frigates=mil_data.get("frigates", 0),
        patrol_vessels=mil_data.get("patrol_vessels", 0),
        defense_budget_billion_usd=mil_data.get("defense_budget_billion_usd", 0),
        defense_budget_pct_gdp=mil_data.get("defense_budget_pct_gdp", 0),
        technology_level=mil_data.get("technology_level", 50),
        logistics_capacity=mil_data.get("logistics_capacity", 50),
        morale=mil_data.get("morale", 70),
        nuclear=nuclear,
    )

    res_data = data.get("resources", {})
    resources = Resources(
        oil_production_bpd=res_data.get("oil_production_bpd", 0),
        oil_reserves_billion_bbl=res_data.get("oil_reserves_billion_bbl", 0),
        natural_gas_bcm=res_data.get("natural_gas_bcm", 0),
        coal_mt=res_data.get("coal_mt", 0),
        uranium_tonnes=res_data.get("uranium_tonnes", 0),
        rare_earth_tonnes=res_data.get("rare_earth_tonnes", 0),
        steel_mt=res_data.get("steel_mt", 0),
        semiconductor_capability=res_data.get("semiconductor_capability", 0),
        food_self_sufficiency=res_data.get("food_self_sufficiency", 0.5),
        renewable_energy_pct=res_data.get("renewable_energy_pct", 0),
    )

    alliances = [
        Alliance(
            name=a["name"],
            alliance_type=AllianceType(a["alliance_type"]),
            mutual_defense=a.get("mutual_defense", False),
            year_joined=a.get("year_joined", 0),
        )
        for a in data.get("alliances", [])
    ]

    trade_partners = [
        TradeRelationship(
            partner_iso3=t["partner_iso3"],
            exports_billion_usd=t["exports_billion_usd"],
            imports_billion_usd=t["imports_billion_usd"],
            trade_balance=t.get("trade_balance", 0),
            key_exports=t.get("key_exports", []),
            key_imports=t.get("key_imports", []),
            dependency_score=t.get("dependency_score", 0),
        )
        for t in data.get("trade_partners", [])
    ]

    return Country(
        iso3=data["iso3"],
        name=data["name"],
        official_name=data["official_name"],
        government=GovernmentType(data["government"]),
        head_of_state=data.get("head_of_state", ""),
        population=data.get("population", 0),
        capital=data.get("capital", ""),
        geography=geography,
        economy=economy,
        military=military,
        resources=resources,
        alliances=alliances,
        trade_partners=trade_partners,
    )


def load_all_countries(data_dir: Path) -> list[Country]:
    """Load all country JSON files from a directory."""
    countries = []
    for filepath in sorted(data_dir.glob("*.json")):
        try:
            country = load_country(filepath)
            countries.append(country)
            print(f"  ✓ {country.iso3} — {country.name} (GDP: ${country.economy.gdp_billion_usd:,.0f}B)")
        except Exception as e:
            print(f"  ✗ {filepath.name} — Error: {e}", file=sys.stderr)
    return countries


def main() -> None:
    parser = argparse.ArgumentParser(description="Load GWW3 country data")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/countries"),
        help="Directory containing country JSON files",
    )
    parser.add_argument(
        "--country",
        type=str,
        default=None,
        help="Load a single country by ISO3 code",
    )
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Error: Data directory not found: {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading country data from {args.data_dir}/\n")

    if args.country:
        filepath = args.data_dir / f"{args.country}.json"
        if not filepath.exists():
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
        country = load_country(filepath)
        print(f"Loaded: {country.name}")
        print(f"  GDP: ${country.economy.gdp_billion_usd:,.0f}B")
        print(f"  Military: {country.military.active_personnel:.0f}k active")
        print(f"  Nuclear: {country.military.nuclear.total_warheads} warheads")
        print(f"  Power Index: {country.power_index:.0f}")
    else:
        countries = load_all_countries(args.data_dir)
        print(f"\nLoaded {len(countries)} countries.")

        # Print power rankings
        print("\n📊 Power Rankings:")
        ranked = sorted(countries, key=lambda c: c.power_index, reverse=True)
        for i, c in enumerate(ranked, 1):
            nuke = "☢️" if c.has_nuclear_weapons else "  "
            print(f"  {i}. {nuke} {c.name:<20} Power: {c.power_index:>7.0f}  GDP: ${c.economy.gdp_billion_usd:>8,.0f}B")


if __name__ == "__main__":
    main()
