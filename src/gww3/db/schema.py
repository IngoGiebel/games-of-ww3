"""Neo4j Schema Definition for Games of World War 3.

This module defines the graph schema: node labels, relationship types,
constraints, and indexes. Run `initialize_schema()` against a Neo4j
instance to set up all constraints and indexes.

Design Principle: Edges > Properties.
Power is defined by network position, not isolated attributes.
"""

from __future__ import annotations

# ──────────────────────────────────────────────
# Node Labels
# ──────────────────────────────────────────────

NODE_LABELS = [
    # Core entities
    "Nation",           # Sovereign state (~195)
    "NonStateActor",    # Insurgencies, PMCs, cartels, terrorist orgs
    "DomesticFaction",  # Internal power groups (military, oligarchs, opposition...)

    # Geographic & Infrastructure
    "Region",           # Sub-national regions / territories
    "Chokepoint",       # Suez, Malacca, Hormuz, Panama, Bosphorus, GIUK Gap
    "Pipeline",         # Energy pipelines (Nord Stream, Druzhba, etc.)
    "Port",
    "Airport",
    "MilitaryBase",
    "SubseaCable",      # Internet backbone

    # Economic
    "Commodity",        # Oil, Gas, Wheat, Semiconductors, Rare Earths, ...
    "Currency",
    "CentralBank",
    "SovereignBond",

    # Military
    "MilitaryUnit",     # Divisions, fleets, squadrons
    "OrbitalNetwork",   # GPS, recon satellites

    # Temporal
    "Tick",             # Time node — forms a linked list
    "Event",            # Discrete occurrences (war declaration, election, disaster)
    "ActionIntent",     # Queued agent decision awaiting execution

    # Game
    "Game",             # A game instance
    "Player",           # Human or AI player
    "AgentRole",        # Strategist, General, Economist, Diplomat, Propagandist, Spymaster
]

# ──────────────────────────────────────────────
# Relationship Types
# ──────────────────────────────────────────────

RELATIONSHIP_TYPES = {
    # Geopolitical
    "BORDERS":          "(Nation)-[:BORDERS {length_km, terrain, disputed}]->(Nation)",
    "ALLIED_WITH":      "(Nation)-[:ALLIED_WITH {type, strength, treaty, since}]->(Nation)",
    "AT_WAR_WITH":      "(Nation)-[:AT_WAR_WITH {type, intensity, since, casus_belli}]->(Nation)",
    "SANCTIONS":        "(Nation)-[:SANCTIONS {target_sectors, since, severity}]->(Nation)",
    "SECRET_TREATY":    "(Nation)-[:SECRET_TREATY {type, terms}]->(Nation)",
    "MEMBER_OF":        "(Nation)-[:MEMBER_OF {since, role}]->(Alliance)",

    # Economic
    "EXPORTS":          "(Nation)-[:EXPORTS {commodity, volume, value, criticality}]->(Nation)",
    "IMPORTS":          "(Nation)-[:IMPORTS {commodity, volume, dependency_score}]->(Nation)",
    "USES_CURRENCY":    "(Nation)-[:USES_CURRENCY]->(Currency)",
    "OWNS_BOND":        "(Nation)-[:OWNS_BOND {amount, yield_pct}]->(Nation)",
    "DEPENDS_ON":       "(Nation)-[:DEPENDS_ON {criticality}]->(Commodity)",

    # Military & Logistics
    "DEPLOYED_AT":      "(MilitaryUnit)-[:DEPLOYED_AT]->(Region|MilitaryBase)",
    "SUPPLY_ROUTE":     "(Nation)-[:SUPPLY_ROUTE {distance, friction, vulnerability}]->(Nation)",
    "CONTROLS":         "(Nation)-[:CONTROLS]->(Region)",
    "BLOCKADES":        "(Nation|NonStateActor)-[:BLOCKADES]->(Chokepoint)",
    "COMMANDS":         "(Nation)-[:COMMANDS]->(MilitaryUnit)",

    # Internal politics
    "DEPENDS_ON_FACTION": "(Nation)-[:DEPENDS_ON_FACTION {approval}]->(DomesticFaction)",
    "LOBBIES":          "(DomesticFaction)-[:LOBBIES {influence, demands}]->(Nation)",
    "SUPPORTS":         "(Nation)-[:SUPPORTS {type, amount}]->(NonStateActor)",

    # Intelligence & Belief
    "BELIEVES":         "(AgentRole)-[:BELIEVES {value, confidence}]->(target)",

    # Temporal
    "NEXT":             "(Tick)-[:NEXT]->(Tick)",
    "STATE_AT":         "(Entity)-[:STATE_AT {properties...}]->(Tick)",
    "OCCURRED_AT":      "(Event)-[:OCCURRED_AT]->(Tick)",
    "SCHEDULED_FOR":    "(ActionIntent)-[:SCHEDULED_FOR]->(Tick)",
    "ISSUED_BY":        "(ActionIntent)-[:ISSUED_BY]->(Nation)",

    # Game
    "PLAYS":            "(Player)-[:PLAYS]->(Nation)",
    "ADVISES":          "(AgentRole)-[:ADVISES]->(Nation)",
    "PART_OF":          "(Nation)-[:PART_OF]->(Game)",
}

# ──────────────────────────────────────────────
# Constraints & Indexes (Cypher statements)
# ──────────────────────────────────────────────

SCHEMA_CONSTRAINTS = [
    # Uniqueness
    "CREATE CONSTRAINT nation_iso3 IF NOT EXISTS FOR (n:Nation) REQUIRE n.iso3 IS UNIQUE",
    "CREATE CONSTRAINT nation_name IF NOT EXISTS FOR (n:Nation) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT commodity_type IF NOT EXISTS FOR (c:Commodity) REQUIRE c.type IS UNIQUE",
    "CREATE CONSTRAINT currency_code IF NOT EXISTS FOR (c:Currency) REQUIRE c.code IS UNIQUE",
    "CREATE CONSTRAINT tick_id IF NOT EXISTS FOR (t:Tick) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT game_id IF NOT EXISTS FOR (g:Game) REQUIRE g.id IS UNIQUE",
    "CREATE CONSTRAINT player_id IF NOT EXISTS FOR (p:Player) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT chokepoint_name IF NOT EXISTS FOR (c:Chokepoint) REQUIRE c.name IS UNIQUE",

    # Indexes for common queries
    "CREATE INDEX nation_cow_code IF NOT EXISTS FOR (n:Nation) ON (n.cow_code)",
    "CREATE INDEX nation_un_m49 IF NOT EXISTS FOR (n:Nation) ON (n.un_m49)",
    "CREATE INDEX tick_game_time IF NOT EXISTS FOR (t:Tick) ON (t.game_time)",
    "CREATE INDEX event_type IF NOT EXISTS FOR (e:Event) ON (e.type)",
    "CREATE INDEX military_unit_nation IF NOT EXISTS FOR (u:MilitaryUnit) ON (u.nation_iso3)",
]


async def initialize_schema(driver) -> list[str]:
    """Apply all constraints and indexes to the Neo4j database.

    Args:
        driver: neo4j.AsyncDriver instance

    Returns:
        List of applied constraint/index names
    """
    applied = []
    async with driver.session() as session:
        for stmt in SCHEMA_CONSTRAINTS:
            await session.run(stmt)
            applied.append(stmt.split("IF NOT EXISTS")[0].strip())
    return applied
