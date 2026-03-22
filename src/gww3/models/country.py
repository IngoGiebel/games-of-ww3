"""Country model — the central data structure for a nation-state in GWW3.

All monetary values are in current USD (billions).
Military personnel counts are in thousands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NuclearDoctrine(Enum):
    """Nuclear weapons employment policy."""

    NONE = "none"  # No nuclear weapons
    NO_FIRST_USE = "no_first_use"  # Will not strike first
    FIRST_USE = "first_use"  # Reserves right to first use
    AMBIGUOUS = "ambiguous"  # Deliberately unclear


class GovernmentType(Enum):
    """Simplified government classification affecting game mechanics."""

    DEMOCRACY = "democracy"
    AUTHORITARIAN = "authoritarian"
    HYBRID = "hybrid"
    THEOCRACY = "theocracy"
    MILITARY_JUNTA = "military_junta"


class AllianceType(Enum):
    """Type of international alliance or partnership."""

    MILITARY = "military"  # NATO, CSTO — mutual defense
    ECONOMIC = "economic"  # EU single market, RCEP
    INTELLIGENCE = "intelligence"  # Five Eyes
    POLITICAL = "political"  # SCO, Arab League
    BILATERAL = "bilateral"  # Country-to-country agreements


@dataclass
class Geography:
    """Physical and territorial attributes."""

    land_area_km2: float  # Total land area
    coastline_km: float  # Coastline length (0 = landlocked)
    borders: list[str] = field(default_factory=list)  # ISO3 codes of bordering nations
    num_regions: int = 1  # Controllable territorial divisions
    terrain_defense_modifier: float = 1.0  # Geographic defense advantage (0.5–2.0)
    strategic_chokepoints: list[str] = field(default_factory=list)  # e.g., "Bosphorus", "Suez"


@dataclass
class Economy:
    """Economic indicators and capabilities."""

    gdp_billion_usd: float  # Nominal GDP in billions USD
    gdp_growth_rate: float  # Annual growth rate (e.g., 0.025 = 2.5%)
    gdp_per_capita_usd: float  # GDP per capita
    government_debt_pct_gdp: float  # Government debt as % of GDP
    inflation_rate: float  # Annual inflation (e.g., 0.03 = 3%)
    unemployment_rate: float  # Unemployment rate
    trade_openness: float  # Trade (% of GDP)
    credit_rating_score: float  # Normalized 0–100 (AAA=100, D=0)
    rd_expenditure_pct_gdp: float  # R&D spending as % of GDP
    fdi_billion_usd: float  # Foreign direct investment inflows

    # Budget allocation (sums to 1.0)
    budget_military: float = 0.0  # % of GDP to military
    budget_infrastructure: float = 0.0
    budget_social: float = 0.0
    budget_rd: float = 0.0


@dataclass
class NuclearCapability:
    """Nuclear weapons inventory and delivery systems."""

    total_warheads: int = 0  # Total inventory (deployed + stockpiled + retired)
    deployed_strategic: int = 0  # Active, ready-to-launch strategic warheads
    deployed_nonstrategic: int = 0  # Tactical nuclear weapons
    stockpiled_reserve: int = 0  # In reserve storage
    icbm_launchers: int = 0  # Land-based intercontinental ballistic missiles
    slbm_launchers: int = 0  # Submarine-launched ballistic missiles
    strategic_bombers: int = 0  # Nuclear-capable bombers
    doctrine: NuclearDoctrine = NuclearDoctrine.NONE
    has_second_strike: bool = False  # Survivable retaliatory capability
    max_range_km: int = 0  # Maximum delivery range


@dataclass
class Military:
    """Conventional military forces and capabilities."""

    # Personnel (thousands)
    active_personnel: float  # Active duty military
    reserve_personnel: float  # Trained reserves
    paramilitary: float = 0.0  # Paramilitary forces

    # Equipment counts
    tanks: int = 0
    armored_vehicles: int = 0
    artillery: int = 0
    fighter_aircraft: int = 0
    attack_aircraft: int = 0
    transport_aircraft: int = 0
    helicopters_attack: int = 0
    helicopters_total: int = 0
    aircraft_carriers: int = 0
    submarines: int = 0
    destroyers: int = 0
    frigates: int = 0
    patrol_vessels: int = 0

    # Capabilities
    defense_budget_billion_usd: float = 0.0
    defense_budget_pct_gdp: float = 0.0
    technology_level: float = 50.0  # 0–100 composite tech score
    logistics_capacity: float = 50.0  # 0–100 logistics/projection capability
    morale: float = 70.0  # 0–100 troop morale

    # Computed
    nuclear: NuclearCapability = field(default_factory=NuclearCapability)


@dataclass
class Resources:
    """Natural resource endowments and production."""

    oil_production_bpd: float = 0.0  # Barrels per day
    oil_reserves_billion_bbl: float = 0.0  # Proven reserves
    natural_gas_bcm: float = 0.0  # Annual production (billion cubic meters)
    coal_mt: float = 0.0  # Annual production (million tonnes)
    uranium_tonnes: float = 0.0  # Annual production
    rare_earth_tonnes: float = 0.0  # Annual production
    steel_mt: float = 0.0  # Annual production (million tonnes)
    semiconductor_capability: float = 0.0  # 0–100 score
    food_self_sufficiency: float = 0.5  # 0–1.0 (1.0 = fully self-sufficient)
    renewable_energy_pct: float = 0.0  # Renewable share of energy mix


@dataclass
class TradeRelationship:
    """Bilateral trade relationship between two nations."""

    partner_iso3: str  # Trading partner country code
    exports_billion_usd: float  # Annual exports to partner
    imports_billion_usd: float  # Annual imports from partner
    trade_balance: float = 0.0  # exports - imports
    key_exports: list[str] = field(default_factory=list)  # Main export commodities
    key_imports: list[str] = field(default_factory=list)  # Main import commodities
    dependency_score: float = 0.0  # 0–1, how dependent this nation is on this partner


@dataclass
class Alliance:
    """Alliance or partnership membership."""

    name: str  # e.g., "NATO", "CSTO", "Five Eyes"
    alliance_type: AllianceType
    members: list[str] = field(default_factory=list)  # ISO3 codes
    mutual_defense: bool = False  # Article 5 / collective defense
    year_joined: int = 0


@dataclass
class Country:
    """Complete nation-state model for GWW3.

    This is the root entity representing a playable (or NPC) nation
    in the simulation. It aggregates all sub-models into a single
    coherent state object.
    """

    # Identity
    iso3: str  # ISO 3166-1 alpha-3 code (e.g., "USA", "CHN")
    name: str  # Common name (e.g., "United States")
    official_name: str  # Official name
    government: GovernmentType
    head_of_state: str = ""
    population: int = 0  # Total population
    capital: str = ""

    # Sub-models
    geography: Geography = field(default_factory=lambda: Geography(0, 0))
    economy: Economy = field(
        default_factory=lambda: Economy(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    )
    military: Military = field(default_factory=lambda: Military(0, 0))
    resources: Resources = field(default_factory=Resources)

    # Relationships (populated from Neo4j)
    alliances: list[Alliance] = field(default_factory=list)
    trade_partners: list[TradeRelationship] = field(default_factory=list)

    # Game state (changes during play)
    diplomatic_capital: float = 100.0  # Spendable diplomatic influence
    stability: float = 80.0  # 0–100, domestic stability
    war_weariness: float = 0.0  # 0–100, accumulated war fatigue
    global_reputation: float = 50.0  # 0–100, international standing
    is_player_controlled: bool = False

    @property
    def has_nuclear_weapons(self) -> bool:
        """Whether this nation possesses nuclear weapons."""
        return self.military.nuclear.total_warheads > 0

    @property
    def has_second_strike(self) -> bool:
        """Whether this nation can survive a first strike and retaliate."""
        return self.military.nuclear.has_second_strike

    @property
    def military_spending_pct_gdp(self) -> float:
        """Military expenditure as percentage of GDP."""
        if self.economy.gdp_billion_usd == 0:
            return 0.0
        return self.military.defense_budget_billion_usd / self.economy.gdp_billion_usd * 100

    @property
    def power_index(self) -> float:
        """Composite national power score (0–1000).

        Weighted combination of economic, military, and soft power indicators.
        """
        econ_score = min(self.economy.gdp_billion_usd / 30, 300)  # Max 300 for ~$30T GDP
        mil_score = min(self.military.technology_level * 3, 300)  # Max 300
        nuke_score = 200 if self.has_second_strike else (100 if self.has_nuclear_weapons else 0)
        soft_score = min(self.global_reputation + self.diplomatic_capital, 200)  # Max 200
        return econ_score + mil_score + nuke_score + soft_score
