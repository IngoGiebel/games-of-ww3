# SPRINTS.md — GWW3 Development Sprints

*Updated: 2026-03-27 by Dione 🌙*

---

## Sprint 1: Initial Data + Validation ✅ COMPLETE

**Goal:** Populate Neo4j with real-world baseline data for all ~195 nations. Validate completeness and consistency.

**Duration:** 2026-03-24 → 2026-03-26

### Phase 0 — Infrastructure ✅
- [x] `normalization.py` — Property registry, unit conversions (38 tests)
- [x] `imputation.py` — 4-level missing data hierarchy
- [x] `validation_bounds.py` — 22 bounds + 4 cross-property invariants
- [x] `warden.py` + `review_and_run.sh` — Code review gate (Codex 5.4)
- [x] `watchdog.py` — Deterministic process supervisor
- [x] `seed_tasks.py` — 29 tasks across 8 phases

### Phase 1 — Foundation ✅
- [x] P1-01: Nation Registry — 195 sovereign nations (REST Countries API)
- [x] P1-02: ID Crosswalk — ISO-3 ↔ COW ↔ UN M49 ↔ V-Dem ↔ WB
- [x] P1-03: Borders — 624 BORDERS edges (312 border pairs)

### Phase 2 — Economics ✅
- [x] P2-01: World Bank GDP (190 nations)
- [x] P2-02: World Bank demographics (population 195, urbanization 193, internet)
- [x] P2-03: World Bank macro (inflation 181, unemployment, gini 144, debt, forex)
- [x] P2-04: UN Comtrade bilateral trade (28 TRADES_WITH + 20 Trade nodes)
- [x] P2-05: EIA oil/gas production and consumption (5 Commodity nodes)
- [x] P2-06: FAO wheat production/consumption
- [x] P2-07: USGS rare earth + mineral production
- [x] P2-08: GDP 10yr CAGR (derived)

### Phase 3 — Military ✅
- [x] P3-01: SIPRI military expenditure (47 MilitaryExpenditure nodes)
- [x] P3-02: Military capabilities (25 MilitaryCapability nodes)
- [x] P3-03: FAS nuclear warheads (195 nations, 9 nuclear states)
- [x] P3-04: SIPRI arms transfers (15 ArmsDeal nodes)

### Phase 4 — Governance ✅
- [x] P4-01: V-Dem democracy and governance indices
- [x] P4-02: Domestic factions (499 DomesticFaction nodes)

### Phase 5 — Conflict & Non-State Actors ✅
- [x] P5-01: ACLED conflict events (68 Conflict nodes)
- [x] P5-02: Non-state actors (392 NonStateActor nodes)

### Phase 6 — Infrastructure ✅
- [x] P6-01: Chokepoints (15 Chokepoint nodes with EIA transit data)
- [x] P6-02: Supply routes (26 SUPPLY_ROUTE relationships)

### Phase 7 — Alliances & Diplomacy ✅
- [x] P7-01: Alliances (21 Alliance nodes, 38 MEMBER_OF edges)
- [x] P7-02: Bilateral diplomatic relations (199 DIPLOMATIC_RELATION edges)

### Phase 8 — Validation ✅
- [x] P8-01: Historical Tick nodes (120 Ticks, T=-120 to T=-1)
- [x] P8-02: T=0 baseline STATE_AT snapshot
- [x] P8-03: Full graph validation (1,749 issues, mostly expected 2025 data gaps)

### Sprint 1 Final Stats (Neo4j)
| Metric | Count |
|--------|-------|
| Nation nodes | 195 |
| DomesticFaction nodes | 499 |
| NonStateActor nodes | 392 |
| Conflict nodes | 68 |
| MilitaryExpenditure nodes | 47 |
| MilitaryCapability nodes | 25 |
| Alliance nodes | 21 |
| Trade nodes | 20 |
| Chokepoint nodes | 15 |
| ArmsDeal nodes | 15 |
| Commodity nodes | 5 |
| BORDERS edges | 624 |
| STATE_AT edges | 2,105 |
| HAS_FACTION edges | 499 |
| DIPLOMATIC_RELATION edges | 199 |
| Tick nodes | 120 |

### Data Coverage (Nation properties)
| Property | Coverage |
|----------|----------|
| Population | 195/195 (100%) |
| Nuclear status | 195/195 (100%) |
| Urbanization | 193/195 (99%) |
| GDP nominal | 190/195 (97%) |
| Inflation | 181/195 (93%) |
| Gini | 144/195 (74%) |
| Military spending | 19/195 (10%) ⚠️ |

**Note:** Military spending is low on Nation nodes (19) but has 47 separate MilitaryExpenditure nodes — data exists, just stored differently.

---

## Sprint 2: Historical Data + Temporal Model ✅ COMPLETE

**Goal:** Load 10 years of historical data (2016-2025), create Tick nodes and STATE_AT snapshots.

**Duration:** 2026-03-25 → 2026-03-26

### Results
- 120 Tick nodes (monthly, Jan 2016 — Dec 2025)
- 2,105 STATE_AT edges (16 distinct properties: GDP, population, inflation, unemployment, gini, urbanization, internet, forex, debt, military, governance, corruption, freedom_house, press_freedom, stability, morale, war_weariness)
- GDP coverage: 179-190 nations per year
- Derived metrics: CAGR, trend slopes, volatility (stored as Nation properties + JSON)
- V-Dem historical: static snapshot (full time series JSON still missing)

---

## Sprint 3: Complete Data Model + Bias Infrastructure ⏳ NEXT

**Goal:** Finalize the complete data model (including bias/correction infrastructure), fill data gaps, and prepare the lean schema that the Rules Engine (Sprint 4) will consume.

**Duration:** ~2 weeks

**Key Design Decision (from Gemini Deep Think review 2026-03-28):**
Strict Hot-Path / Cold-Path separation. STATE_AT carries only values + confidence floats. All textual bias metadata lives on Correction/BiasReport nodes (Cold Path).

### 3.1 Schema Refactor — Hot/Cold Separation
- [ ] Strip all textual bias metadata from STATE_AT design
- [ ] Add `{prop}_c` (confidence float) fields to STATE_AT for all properties
- [ ] Define `:BiasReport`, `:Correction`, `:CounterSource` node types in schema.py
- [ ] Define new relationships: `HAS_BIAS`, `HAS_CORRECTION`, `GENERATED`, `BASED_ON`, `SUPPLEMENTS`, `SELF_REPORTS`
- [ ] Add constraints/indexes for new node types

### 3.2 Bias Infrastructure MVP
- [ ] Create `bias_overrides.json` — hardcoded Top 5 critical corrections:
  1. China population (demographic_manipulation → c=0.55)
  2. ACLED conflict events (classification_asymmetry → reclassification)
  3. V-Dem governance indices (expert_subjectivity → c=0.70 for contested cases)
  4. Freedom House scores (funding_dependency → c=0.65)
  5. World Bank GDP for low-capacity states (self_reporting → c=0.70)
- [ ] Wire ETL pipeline: Normalizers → **Bias Tagger** → **Correction Overlay** → **Re-Derive Computations** → Validators → Neo4j
- [ ] Import Airwars + TBIJ as CounterSource nodes

### 3.3 Data Gap Closure
- [ ] Consolidate SIPRI MILEX (47 nodes) into Nation STATE_AT properties
- [ ] Expand TRADES edges: target 200+ bilateral pairs (from current 28)
- [ ] Load V-Dem historical time series (currently static snapshot only)
- [ ] Load UNGA voting data → diplomatic alignment edges

### 3.4 Data Model Extension
- [ ] Economic dependencies: trade flow analysis, sanction impact modeling
- [ ] Military force projection: deployment ranges, logistics costs
- [ ] Diplomatic influence: UN voting patterns, alliance strength scores
- [ ] Domestic politics: faction dynamics, leader stability
- [ ] ~~Belief Subgraph foundation~~ → **Moved to Sprint 5** (no AI agents to consume it yet)

### 3.5 Documentation
- [ ] Update SCHEMA_V2.md → SCHEMA_V3.md (incorporating Hot/Cold + bias nodes)
- [ ] Update DATA_MODEL_COMPLETE.md with final schema
- [ ] Document ETL bias pipeline with examples

### Sprint 3 Acceptance Criteria
- Schema v3 deployed to Neo4j with bias node types + confidence fields
- bias_overrides.json applied to all 5 critical sources
- SIPRI MILEX merged into STATE_AT (195 nations)
- TRADES edges ≥200
- V-Dem historical loaded
- Deep Think review of final schema (SCHEMA_V3) passed
- DATA_MODEL_COMPLETE.md is the single source of truth

---

## Sprint 4: Rules Engine (GSL) ⏭️ PLANNED

**Goal:** Build the GSL parser, evaluator, and intent reducer. First deterministic game loop with real data.

**Depends on:** Sprint 3 (complete data model with confidence fields)

### 4.1 GSL Parser (Lark)
- [ ] EBNF grammar (.lark file)
- [ ] Parse 3 example rules to valid AST dataclasses
- [ ] Unicode operator support (∧, ∨, ¬, ⟹, ×=, ⤳)

### 4.2 Math Core
- [ ] Distribution classes (𝐿𝑁, 𝛽, 𝒩, 𝒰, ℬ, 𝒫, ℰ)
- [ ] Mean-preserving confidence adjustment formulas
- [ ] Deterministic per-effect RNG seeding
- [ ] **c_source integration:** Read `{prop}_c` from Neo4j Node properties, apply to variance widening
- [ ] ~~**Weakest-link propagation:** `c_derived = min(c_inputs)` for LET bindings~~ **REMOVED:** No auto engine-level propagation. Rule authors explicitly pull `{prop}_c` via LET statements.

### 4.3 Cypher Executor & Evaluator
- [ ] MATCH → Cypher query with pushdown WHERE
- [ ] Execution Matrix (list of bound variable dicts)
- [ ] SymbolTable with lexical scoping
- [ ] Nested IF/THEN/ELSE evaluation

### 4.4 Intent Reducer
- [ ] Additive Modifier Pool: additives → modifiers → direct → converge → type clamp
- [ ] Commutative reduction proof

### 4.5 Integration Test
- [ ] Determinism proof: 3 conflicting rules, 100 ticks, 10 runs → byte-identical state hash
- [ ] First game loop: 2 nations (USA + CHN), 100 ticks with real data
- [ ] Economic simulation produces plausible GDP trajectories

### Sprint 4 Acceptance Criteria
- GSL parser handles all 3 example rules from RULE_ENGINE_CONCEPT.md
- Confidence values from STATE_AT correctly widen distributions
- 100-tick determinism proof passes
- Economic outputs within plausible ranges

---

## Sprint 5+ (Future — to be planned after Sprint 4)

### Potential Topics
- AI Game Agents (ADK): Strategist, Economist, General, Diplomat
- Cabinet protocol: multi-agent debate → consensus → decision
- Belief Subgraph: full cognitive layer (agents query BELIEVES, not STATE_AT)
- Moltbook voting UI for bias corrections
- Web UI MVP (FastAPI + React + Deck.gl globe)
- Full AI-vs-AI simulation (USA vs China)
- Community features: spectator mode
- Public beta preparation

---

## Agent Roles Per Sprint

| Sprint | Dione | Sentinel | Archon | Warden | Inanna |
|--------|-------|----------|--------|--------|--------|
| 1 ✅ | Orchestrate, ETL | ETL (autonomous) | — | Review scripts | — |
| 2 ✅ | Orchestrate | Historical ETL | Temporal model | Review scripts | — |
| 3 ⏳ | Schema v3 + Bias docs | Data gaps + bias ETL | Schema refactor code | Review code | ACLED reclassification |
| 4 | GSL grammar + rules | Data validation | Parser + evaluator | Review all code | Combat rules review |
| 5+ | Orchestrate | Data updates | Engine + API + UI | Review all code | Combat system |

---

## Status Legend
- ✅ = Complete
- 🔄 = In Progress
- ⏳ = Blocked / Next
- ❌ = Failed (needs intervention)
