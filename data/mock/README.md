# Mock Data for Sprint 1

This directory contains static mock data for 2 nations (USA + CHN) used to
validate the Neo4j graph topology before live data ingestion in Sprint 2.

## Files
- `usa.json` — United States mock data (nation + factions + military)
- `chn.json` — China mock data (nation + factions + military)
- `commodities.json` — Shared commodity nodes (Oil, Semiconductors, Wheat, Rare Earths)
- `chokepoints.json` — Key chokepoints (Malacca, Hormuz, Panama, Suez)
- `alliances.json` — Alliance nodes (NATO, SCO, BRICS)
- `relationships.json` — All edges between mock nodes
- `seed.cypher` — Cypher script to load all mock data into Neo4j

## Purpose
- Validate schema constraints and indexes
- Test graph topology (nations connected to commodities, alliances, chokepoints)
- Test sparse temporal model (monthly STATE_AT snapshots)
- Verify pathfinding constraints (TRADES edges only, not PRODUCES/CONSUMES)
