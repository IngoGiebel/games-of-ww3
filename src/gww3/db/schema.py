"""Neo4j Schema Definition for Games of World War 3.

This module defines the graph schema: node labels, relationship types,
constraints, and indexes. Run `initialize_schema()` against a Neo4j
instance to set up all constraints and indexes.

Design Principle: Edges > Properties.
Power is defined by network position, not isolated attributes.

Temporal Strategy (per Deep Think review):
- Current state lives directly on Entity nodes as properties.
- STATE_AT snapshots are created ONLY on Monthly (Economic) and Epoch (Annual) ticks.
- Intra-month changes are logged as lightweight (:Event) nodes with deltas.
- ALL properties use strictly monthly frequency — no mixing.
- This prevents graph explosion (525,600 Tick nodes/year would OOM).

ETL Strategy (per Deep Think review):
- Sentinel agents generate + execute deterministic Python scripts for bulk data.
- LLM context is NEVER used to parse structured API payloads row-by-row.
- LLM reasoning is reserved for unstructured text and fuzzy matching only.
- Agent context is cleared after every task to prevent memory bloat.

Data Strategy (per Deep Think review):
- Missing values are NEVER left as null — impute from regional/income-group averages.
- All imputed values tagged with data_confidence: "estimated".
- Hard sanity bounds are checked before every commit (see validation_bounds.py).
- 10-year historical data (2016-2025) loaded for trend analysis and CAGR.

Agent Output Strategy:
- Game agents output structured JSON (Pydantic-validated), NEVER raw Cypher.
- JSON actions map to predefined Python backend functions.
- This prevents schema hallucination and database corruption.
"""

from __future__ import annotations

# ──────────────────────────────────────────────
# Node Labels
# ──────────────────────────────────────────────

NODE_LABELS = [
    # Core entities
    "Nation",           # Sovereign state (~195). NOT supranational blocs (EU → Alliance).
    "NonStateActor",    # Insurgencies, PMCs, cartels, terrorist orgs
    "DomesticFaction",  # Internal power groups (military, oligarchs, opposition...)
    "Alliance",         # NATO, CSTO, AUKUS, SCO, BRICS, AU, ASEAN, EU (supranational), etc.

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

    # Temporal (sparse — snapshots only on Monthly/Epoch ticks)
    "Tick",             # Sparse time nodes (Monthly + Epoch only, NOT per-minute)
    "Event",            # Discrete occurrences (war, election, disaster, state changes)
    "ActionIntent",     # Queued agent decision awaiting execution
    "Conflict",         # Active armed conflicts

    # Game
    "Game",             # A game instance
    "Player",           # Human or AI player
    "AgentRole",        # Strategist, General, Economist, Diplomat, Propagandist, Spymaster

    # Provenance
    "DataSource",       # External data source registry
    "ImportBatch",      # Tracks each data import operation

    # Task Queue (agent coordination)
    "Task",             # Work items for agents, stored in Neo4j
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

    # Economic — trade routes through Commodity nodes (edges > properties!)
    # Full pattern: (Exporter)-[:PRODUCES {volume}]->(:Commodity)<-[:CONSUMES {volume}]-(Importer)
    # Simplified bilateral: (Nation)-[:TRADES {commodity, volume, value}]->(Nation)
    "PRODUCES":         "(Nation)-[:PRODUCES {volume, annual_capacity, pct_global}]->(Commodity)",
    "CONSUMES":         "(Nation)-[:CONSUMES {volume, dependency_score, import_pct}]->(Commodity)",
    "TRADES":           "(Nation)-[:TRADES {commodity_type, volume, value, route_via, friction}]->(Nation)",
    # NOTE: friction (float, 0.0-1.0) is REQUIRED for APOC shortest-path algorithms.
    # Pathfinding for sanction evasion MUST traverse TRADES/SUPPLY_ROUTE/ROUTE_THROUGH only.
    # NEVER traverse PRODUCES/CONSUMES edges — Commodity nodes are NOT transit hubs.
    "USES_CURRENCY":    "(Nation)-[:USES_CURRENCY]->(Currency)",
    "OWNS_BOND":        "(Nation)-[:OWNS_BOND {amount, yield_pct}]->(Nation)",

    # Military & Logistics
    "DEPLOYED_AT":      "(MilitaryUnit)-[:DEPLOYED_AT]->(Region|MilitaryBase)",
    "SUPPLY_ROUTE":     "(Nation)-[:SUPPLY_ROUTE {distance, friction, vulnerability}]->(Nation)",
    "CONTROLS":         "(Nation)-[:CONTROLS]->(Region)",
    "BLOCKADES":        "(Nation|NonStateActor)-[:BLOCKADES]->(Chokepoint)",
    "COMMANDS":         "(Nation)-[:COMMANDS]->(MilitaryUnit)",
    "ROUTE_THROUGH":    "(SupplyRoute)-[:ROUTE_THROUGH]->(Chokepoint|Port)",
    "ARMS_TRANSFER":    "(Nation)-[:ARMS_TRANSFER {tiv_value, year, equipment_types}]->(Nation)",

    # Internal politics
    "HAS_FACTION":      "(Nation)-[:HAS_FACTION]->(DomesticFaction)",
    "DEPENDS_ON_FACTION": "(Nation)-[:DEPENDS_ON_FACTION {approval}]->(DomesticFaction)",
    "LOBBIES":          "(DomesticFaction)-[:LOBBIES {influence, demands}]->(Nation)",
    "SUPPORTS":         "(Nation)-[:SUPPORTS {type, amount}]->(NonStateActor)",

    # Conflict & NSA
    "INVOLVED_IN":      "(Nation)-[:INVOLVED_IN {role}]->(Conflict)",
    "PARTY_TO":         "(NonStateActor)-[:PARTY_TO]->(Conflict)",
    "SPONSORED_BY":     "(NonStateActor)-[:SPONSORED_BY]->(Nation)",
    "OPERATES_IN":      "(NonStateActor)-[:OPERATES_IN]->(Nation)",

    # Intelligence & Belief
    "BELIEVES":         "(AgentRole)-[:BELIEVES {value, confidence}]->(target)",

    # Temporal (sparse snapshots — Monthly/Epoch only)
    "NEXT":             "(Tick)-[:NEXT]->(Tick)",
    "STATE_AT":         "(Entity)-[:STATE_AT {properties...}]->(Tick)",
    "OCCURRED_AT":      "(Event)-[:OCCURRED_AT]->(Tick)",
    "SCHEDULED_FOR":    "(ActionIntent)-[:SCHEDULED_FOR]->(Tick)",
    "ISSUED_BY":        "(ActionIntent|Event)-[:ISSUED_BY]->(Nation)",

    # Provenance
    "PROVENANCE":       "(Entity)-[:PROVENANCE {properties: [...]}]->(ImportBatch)",
    # properties on the EDGE enables O(1) lookup per property per entity
    "FROM_SOURCE":      "(ImportBatch)-[:FROM_SOURCE]->(DataSource)",

    # Task queue
    "DEPENDS_ON":       "(Task)-[:DEPENDS_ON]->(Task)",

    # Game
    "PLAYS":            "(Player)-[:PLAYS]->(Nation)",
    "ADVISES":          "(AgentRole)-[:ADVISES]->(Nation)",
    "PART_OF":          "(Nation)-[:PART_OF]->(Game)",
}

# ──────────────────────────────────────────────
# Constraints & Indexes (Cypher statements)
# ──────────────────────────────────────────────

SCHEMA_CONSTRAINTS = [
    # Uniqueness — Core
    "CREATE CONSTRAINT nation_iso3 IF NOT EXISTS FOR (n:Nation) REQUIRE n.iso3 IS UNIQUE",
    "CREATE CONSTRAINT nation_name IF NOT EXISTS FOR (n:Nation) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT alliance_name IF NOT EXISTS FOR (a:Alliance) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT commodity_name IF NOT EXISTS FOR (c:Commodity) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT commodity_type IF NOT EXISTS FOR (c:Commodity) REQUIRE c.type IS UNIQUE",
    "CREATE CONSTRAINT currency_code IF NOT EXISTS FOR (c:Currency) REQUIRE c.code IS UNIQUE",
    "CREATE CONSTRAINT chokepoint_name IF NOT EXISTS FOR (c:Chokepoint) REQUIRE c.name IS UNIQUE",

    # Uniqueness — Temporal & Game
    "CREATE CONSTRAINT tick_id IF NOT EXISTS FOR (t:Tick) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT game_id IF NOT EXISTS FOR (g:Game) REQUIRE g.id IS UNIQUE",
    "CREATE CONSTRAINT player_id IF NOT EXISTS FOR (p:Player) REQUIRE p.id IS UNIQUE",

    # Uniqueness — Provenance
    "CREATE CONSTRAINT datasource_id IF NOT EXISTS FOR (ds:DataSource) REQUIRE ds.id IS UNIQUE",
    "CREATE CONSTRAINT importbatch_id IF NOT EXISTS FOR (ib:ImportBatch) REQUIRE ib.id IS UNIQUE",

    # Uniqueness — Task Queue
    "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE",

    # Indexes for common queries
    "CREATE INDEX nation_cow_code IF NOT EXISTS FOR (n:Nation) ON (n.cow_code)",
    "CREATE INDEX nation_un_m49 IF NOT EXISTS FOR (n:Nation) ON (n.un_m49)",
    "CREATE INDEX tick_game_time IF NOT EXISTS FOR (t:Tick) ON (t.game_time)",
    "CREATE INDEX tick_type IF NOT EXISTS FOR (t:Tick) ON (t.tick_type)",
    "CREATE INDEX event_type IF NOT EXISTS FOR (e:Event) ON (e.type)",
    "CREATE INDEX event_game_tick IF NOT EXISTS FOR (e:Event) ON (e.game_tick)",
    "CREATE INDEX military_unit_nation IF NOT EXISTS FOR (u:MilitaryUnit) ON (u.nation_iso3)",

    # Composite index for agent task queue polling performance
    "CREATE INDEX task_queue IF NOT EXISTS FOR (t:Task) ON (t.status, t.assigned_to)",
]

# ──────────────────────────────────────────────
# Required plugins
# ──────────────────────────────────────────────

REQUIRED_PLUGINS = [
    "apoc",  # Awesome Procedures on Cypher — needed for shortest-path algorithms
             # (e.g., sanction evasion routing, supply chain analysis)
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
