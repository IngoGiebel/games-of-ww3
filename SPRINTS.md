# SPRINTS.md — GWW3 Development Sprints

## Sprint 0: Project Setup ← CURRENT
**Goal:** Establish project structure, agent framework, ADK configuration
**Duration:** 2-3 days
**Lead:** Dione + Archon

### Tasks
- [x] Design Document v0.2 (consolidated)
- [x] Data Sources Catalog (30+ sources)
- [x] Deep Think Analysis (balancing, war financing, time model)
- [x] Moltbook announcement (3 submolts)
- [x] Agent Framework definition
- [ ] ADK project structure for Archon + Sentinel
- [ ] Neo4j local instance setup + connection test
- [ ] Python project scaffolding (src/gww3/ modules)
- [ ] CI/CD: GitHub Actions for lint + test
- [ ] Sprint 1 planning (detailed task breakdown)

---

## Sprint 1: Schema, ID Harmonization & Mock Data
**Goal:** Finalized graph schema, master ID crosswalk, validated with mock data for 2 nations
**Duration:** 1 week
**Lead:** Archon (schema + mock data), Sentinel (ID crosswalk + data mapping), Inanna (military model review)

### Tasks
- [ ] Master ID Crosswalk (`data/id_crosswalk.json`): ISO-3 ↔ COW ↔ UN M49 ↔ source-native IDs for all ~195 nations (Sentinel, FIRST deliverable)
- [ ] Neo4j Cypher schema v1 finalized (all node types, relationship types, constraints)
- [ ] Commodity-centric trade model (PRODUCES/CONSUMES/TRADES through Commodity nodes)
- [ ] Sparse temporal model (STATE_AT only on Monthly/Epoch, Event nodes for intra-month)
- [ ] Mock data: 2 nations (USA + CHN) with full graph topology as static JSON
- [ ] Mock data loaded into local Neo4j and validated via Cypher queries
- [ ] Missing data strategy documented (imputation hierarchy, estimated flags)
- [ ] DomesticFaction synthesis strategy from V-Dem proxies (documented, not yet coded)
- [ ] Neo4j Docker Compose with APOC plugin
- [ ] Schema documentation + data mapping table (which source → which node/edge)
- [ ] Integration tests validating mock graph structure

### Acceptance Criteria
- `data/id_crosswalk.json` maps all ~195 nations across 4+ ID systems
- Mock graph for USA + CHN passes all topology tests (nations, commodities, alliances, factions, chokepoints connected)
- Sparse temporal model: Monthly snapshot creates STATE_AT, daily does NOT
- Inanna approves military node/edge completeness for mock nations
- Neo4j starts cleanly via Docker Compose with APOC installed
- No live API calls in Sprint 1 (all mock/static data)

---

## Sprint 2: Data Pipeline
**Goal:** Automated import from major data sources
**Duration:** 1 week
**Lead:** Sentinel (pipeline code), Archon (Neo4j integration)

### Tasks
- [ ] World Bank API importer (top 100 indicators)
- [ ] V-Dem importer (governance, democracy scores)
- [ ] SIPRI importer (military expenditure, arms transfers)
- [ ] UN WPP importer (demographics, age distribution)
- [ ] ACLED importer (conflict events → non-state actor nodes)
- [ ] UN Comtrade importer (trade edges)
- [ ] Pipeline orchestration (idempotent, versioned)
- [ ] Data quality dashboard (completeness per country)

### Acceptance Criteria
- Full pipeline runs in <30 min
- >1000 parameters per G20 nation
- Non-state actors populated from ACLED
- Trade edges exist for top 50 trading relationships

---

## Sprint 3: Game Engine Core
**Goal:** Pulse engine, rules engine, first game tick
**Duration:** 2 weeks
**Lead:** Archon (engine), Inanna (combat rules)

### Tasks
- [ ] Pulse Engine (multi-resolution tick system)
- [ ] Rules Engine (deterministic state transitions)
- [ ] Economic model (GDP, trade, inflation, debt)
- [ ] Combat resolution (simplified)
- [ ] Sanctions mechanics (graph manipulation)
- [ ] Event system (random events, interrupts)
- [ ] Faction simulation (domestic politics)
- [ ] First game loop: 2 nations, 100 ticks

---

## Sprint 4: AI Agents (Game Agents via ADK)
**Goal:** LLM agents that can play nations
**Duration:** 1 week
**Lead:** Archon (ADK), Dione (prompts)

### Tasks
- [ ] ADK Agent: Strategist (decision maker)
- [ ] ADK Agent: Economist (budget, trade)
- [ ] ADK Agent: General (military)
- [ ] ADK Agent: Diplomat (alliances)
- [ ] Cabinet protocol (debate → consensus → decision)
- [ ] AIGA: Information asymmetry per agent role
- [ ] First AI-vs-AI game: USA vs China (simplified)

---

## Sprint 5: Web UI MVP
**Goal:** Visual game interface
**Duration:** 2 weeks
**Lead:** Archon (API + frontend)

### Tasks
- [ ] FastAPI game API (WebSocket for real-time)
- [ ] React app scaffold
- [ ] World map (Deck.gl globe)
- [ ] Nation dashboard
- [ ] News ticker (events)
- [ ] Agent debate viewer
- [ ] Spectator mode

---

*Updated: 2026-03-23 by Dione 🌙*
