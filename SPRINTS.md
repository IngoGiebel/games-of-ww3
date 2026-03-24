# SPRINTS.md — GWW3 Development Sprints

*Updated: 2026-03-24 by Dione 🌙*

---

## Sprint 1: Initial Data + Validation (CURRENT)

**Goal:** Populate Neo4j with real-world baseline data for all ~195 nations. Validate completeness and consistency. No historical time series yet.

**Duration:** ~1 week (started 2026-03-24)

### Phase 0 — Infrastructure ✅ COMPLETE
- [x] `normalization.py` — Property registry, unit conversions (38 tests)
- [x] `imputation.py` — 4-level missing data hierarchy
- [x] `validation_bounds.py` — 22 bounds + 4 cross-property invariants
- [x] `warden.py` + `review_and_run.sh` — Code review gate (Codex 5.4)
- [x] `watchdog.py` — Deterministic process supervisor
- [x] `seed_tasks.py` — 29 tasks across 8 phases

### Phase 1 — Foundation ✅ COMPLETE
- [x] P1-01: Nation Registry — 195 sovereign nations (REST Countries API)
- [x] P1-02: ID Crosswalk — ISO-3 ↔ COW ↔ UN M49 ↔ V-Dem ↔ WB
- [x] P1-03: Borders — 624 BORDERS edges (312 border pairs)

### Phase 2 — Economics (IN PROGRESS)
- [x] P2-01: World Bank GDP (190 nations, 2024, 10yr CAGR)
- [ ] P2-02: World Bank demographics (population, urbanization, internet)
- [ ] P2-03: World Bank macro (inflation, unemployment, gini, debt, forex)
- [ ] P2-04: UN Comtrade bilateral trade (top 500 pairs)
- [ ] P2-05: EIA oil/gas production and consumption
- [ ] P2-06: FAO wheat production/consumption
- [ ] P2-07: USGS rare earth + mineral production
- [ ] P2-08: Compute GDP 10yr CAGR (derived from P2-01)

### Phase 3 — Military
- [x] P3-03: FAS nuclear warheads (9 nuclear states) ← Sentinel autonomous!
- [ ] P3-01: SIPRI military expenditure (10 years)
- [ ] P3-02: Military capabilities (manpower, equipment)
- [ ] P3-04: SIPRI arms transfers (2016-2025)

### Phase 4 — Governance
- [ ] P4-01: V-Dem democracy and governance indices (10 years)
- [ ] P4-02: Domestic factions (derived from V-Dem + CIA Factbook)

### Phase 5 — Conflict & Non-State Actors
- [ ] P5-01: ACLED conflict events → Conflict nodes (requires API key)
- [ ] P5-02: Non-state actors from ACLED + open sources

### Phase 6 — Infrastructure
- [ ] P6-01: Chokepoint data (EIA transit volumes)
- [ ] P6-02: Supply routes (derived from trade + geography)

### Phase 7 — Alliances & Diplomacy
- [ ] P7-01: Expand alliances to ~20 organizations + MEMBER_OF edges
- [ ] P7-02: Bilateral diplomatic relations (derived)

### Phase 8 — Validation (Sprint 1 scope: current data only)
- [ ] P8-03: Full graph validation — topology, completeness, consistency checks

### Sprint 1 Acceptance Criteria
- All ~195 nations have: GDP, population, military spending, governance scores
- All nations have: region, borders, at least 1 alliance membership
- Sanity bounds pass for all G20 nations (0 errors)
- Data completeness: G20 >95%, G50 >85%, rest >60%
- All ETL scripts committed, documented, reproducible
- Warden review gate operational and enforced

---

## Sprint 2: Historical Data + Temporal Model

**Goal:** Load 10 years of historical data (2016-2025), create Tick nodes and STATE_AT snapshots, validate temporal consistency.

**Duration:** ~1 week

### Tasks
- [ ] Load historical time series for all World Bank indicators (2016-2025)
- [ ] Load historical SIPRI military expenditure (2016-2025)
- [ ] Load historical V-Dem governance indices (2016-2025)
- [ ] P8-01: Create historical Tick nodes (T=-120 to T=-1, monthly)
- [ ] P8-02: Create T=0 baseline STATE_AT snapshot for all nations
- [ ] P8-03: Full temporal validation — consistency across years, trend plausibility
- [ ] Compute derived historical metrics (CAGR, trend slopes, volatility)

### Sprint 2 Acceptance Criteria
- 23,400 Tick nodes (195 nations × 120 months)
- STATE_AT snapshots for GDP, military spending, governance at minimum
- No null values in critical game properties at T=0
- Historical trends are monotonically plausible (no impossible jumps)
- Time series stored in data/timeseries/ as reproducible JSON files

---

## Sprint 3: Data Model Extension + Game Engine Concept

**Goal:** Extend the data model with derived game mechanics properties. Create initial Game Engine concept and architecture. First prototype of Pulse Engine with real data.

**Duration:** ~2 weeks

### Data Model Extension
- [ ] Economic dependencies: trade flow analysis, sanction impact modeling
- [ ] Military force projection: deployment ranges, logistics costs
- [ ] Diplomatic influence: UN voting patterns, alliance strength scores
- [ ] Domestic politics: faction dynamics, leader stability
- [ ] Asymmetric warfare: insurgency effectiveness vs. conventional forces

### Game Engine Concept
- [ ] Rules Engine design: deterministic state transitions from real data
- [ ] Economic model: GDP calculation, trade, inflation, debt spiral mechanics
- [ ] Combat resolution: force comparison, terrain, logistics, morale
- [ ] Diplomacy model: alliance formation, sanctions, treaties
- [ ] Event system: random events, historical triggers, player actions

### Pulse Engine Integration
- [ ] Connect Pulse Engine to real Neo4j data (currently uses mock ticks)
- [ ] First game loop: 2 nations (USA + CHN), 100 ticks with real data
- [ ] Validate: do economic outputs match expected ranges?

### Sprint 3 Acceptance Criteria
- Extended data model documented and reviewed (Deep Think)
- Game Engine architecture document approved
- Pulse Engine runs 100 ticks with real data without crashing
- Economic simulation produces plausible GDP trajectories

---

## Sprint 4+ (Future — to be planned after Sprint 3)

### Potential Topics
- AI Game Agents (ADK): Strategist, Economist, General, Diplomat
- Cabinet protocol: multi-agent debate → consensus → decision
- Web UI MVP (FastAPI + React + Deck.gl globe)
- Full AI-vs-AI simulation (USA vs China)
- Community features: Moltbook integration, spectator mode
- Public beta preparation

---

## Agent Roles Per Sprint

| Sprint | Dione | Sentinel | Archon | Warden | Inanna |
|--------|-------|----------|--------|--------|--------|
| 1 | Orchestrate, ETL | ETL (autonomous) | — | Review scripts | — |
| 2 | Orchestrate | Historical ETL | Temporal model | Review scripts | — |
| 3 | Design docs | Data extension | Engine code | Review code | Military model review |
| 4+ | Orchestrate | Data updates | Engine + API | Review all code | Combat system |

---

## Status Legend
- ✅ = Complete
- 🔄 = In Progress
- ⏳ = Blocked (waiting for dependency)
- ❌ = Failed (needs intervention)
