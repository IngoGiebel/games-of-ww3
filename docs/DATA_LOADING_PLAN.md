# GWW3 — Data Loading Plan (v2.0)

*Created: 2026-03-24 by Dione 🌙*
*Updated: 2026-03-24 — Deep Think Review + Ingo feedback incorporated*

## Principles

1. **Every datum has provenance** — No value enters the DB without a linked `ImportBatch` → `DataSource`
2. **Replace, don't patch** — Mock data gets replaced by real data, not merged on top
3. **One source per property domain** — Avoid conflicting values from multiple sources
4. **Idempotent imports** — Every import script can run repeatedly without creating duplicates
5. **Confidence tagging** — Every Nation carries `data_confidence` (high/medium/low/estimated)
6. **Never null — always impute** — Missing values are imputed from regional/income-group averages and tagged `data_confidence: "estimated"`. The game engine uses deterministic math; null values cause TypeError crashes.
7. **Historical depth: 10 years** — Load 2016-2025 time series for trend analysis (CAGR, trajectories). Required for both game engine and future financial analysis reuse.

---

## Provenance Schema (implemented)

```
(:DataSource {id, name, url, type, update_frequency, license, provides[]})
(:ImportBatch {id, timestamp, agent, method, record_count, notes, confidence, derivation_formula})

(entity)-[:PROVENANCE {properties: [...]}]->(ImportBatch)-[:FROM_SOURCE]->(DataSource)
```

**Properties on the PROVENANCE edge** (not on ImportBatch) enable O(1) per-property lookup.

---

## Phase 0: Data Normalization Standard (NEW)

**Must complete before any Phase 1+ import.**

Sources use vastly different scales and formats. Define and implement a normalization layer:

### Step 0.1: Unit & Scale Registry
- **File:** `src/gww3/data/normalization.py`
- **Defines:** Canonical units for every property
  - GDP → USD (current prices, not PPP)
  - Military spending → USD
  - Population → integer
  - Rates (inflation, growth, unemployment) → % as float (e.g., 5.9, not 0.059)
  - V-Dem indices → 0-1 float, mapped to 0-100 integer for game use
  - Freedom House → 0-100
  - SIPRI MILEX → millions USD, converted to absolute USD
- **Agent:** Archon (one-time setup)
- **Confidence:** N/A (infrastructure)

### Step 0.2: Imputation Hierarchy
- **File:** `src/gww3/data/imputation.py`
- **Strategy (in priority order):**
  1. Use latest available year from same source (e.g., WB 2022 if 2024 missing)
  2. Regional average (same sub_region, same income group)
  3. Income-group average (World Bank income classifications)
  4. Global median
- **All imputed values tagged:** `data_confidence: "estimated"`, `imputation_method: "regional_avg"`
- **Agent:** Archon (one-time setup)

### Step 0.3: Sanity Bounds Registry
- **File:** `src/gww3/data/validation_bounds.py`
- **Hard invariants that block import if violated:**
  - `10_000_000 < gdp_nominal < 50_000_000_000_000`
  - `military_spending_abs < gdp_nominal`
  - `population > 1000`
  - `0 <= stability_index <= 100`
  - `0 <= inflation_rate <= 10000` (hyperinflation allowed)
  - `nuclear_warheads >= 0`
  - `manpower_active <= population`
- **Agent:** Archon
- **Action on violation:** Task → `blocked`, escalate to Dione

---

## Phase 1: Foundation Data (Nations + Geography)

All ~195 sovereign nations. Focus: identity, geography, basic demographics.
**EU is NOT a Nation** — it's an Alliance with `type: "supranational"`.

### Step 1.1: Nation Identity Registry
- **Source:** CIA World Factbook + ISO 3166
- **Agent:** Sentinel (deterministic script, not LLM parsing for structured fields)
- **Properties:** iso3, iso2, name, name_short, cow_code, un_m49, government_type, region, sub_region
- **LLM-assisted:** leader_name, leader_ideology (unstructured text parsing from Factbook)
- **Method:** Deterministic Python script generates Cypher; LLM only for free-text fields
- **Scope:** ~195 nations (replace G20-only)
- **Confidence:** high

### Step 1.2: ID Crosswalk
- **Source:** Correlates of War, UN, ISO, V-Dem codebook
- **Agent:** Sentinel
- **Output:** `data/id_crosswalk.json` — ISO-3 ↔ COW ↔ UN M49 ↔ V-Dem ↔ WB
- **Confidence:** high

### Step 1.3: Borders & Geography
- **Source:** CIA Factbook, Natural Earth
- **Agent:** Sentinel
- **Relationships:** `(Nation)-[:BORDERS]->(Nation)` for all land borders
- **Scope:** ~600 border pairs
- **Confidence:** high

---

## Phase 2: Economic Data (10-Year Time Series)

### Step 2.1: Core Economics (World Bank WDI)
- **Source:** `worldbank-wdi` — API: `api.worldbank.org/v2/country/all/indicator/`
- **Agent:** Sentinel (deterministic Python script using `requests` + `pandas`)
- **⚠️ ETL Standard:** Sentinel generates and executes a deterministic Python script. Sentinel does NOT parse structured API payloads row-by-row via LLM context.
- **Properties:** gdp_nominal, gdp_growth, gdp_per_capita, population, inflation_rate, unemployment, gini, debt_to_gdp, forex_reserves, urbanization, internet_penetration
- **Indicators:** NY.GDP.MKTP.CD, NY.GDP.MKTP.KD.ZG, NY.GDP.PCAP.CD, SP.POP.TOTL, FP.CPI.TOTL.ZG, SL.UEM.TOTL.ZS, SI.POV.GINI, GC.DOD.TOTL.GD.ZS, FI.RES.TOTL.CD, SP.URB.TOTL.IN.ZS, IT.NET.USER.ZS
- **Years:** 2016-2025 (10-year window)
- **Scope:** ~195 nations × 10 years
- **Confidence:** high
- **Missing data strategy:** Impute per Phase 0.2 hierarchy. Tag as `data_confidence: "estimated"`.
- **Derived properties:** `gdp_10yr_cagr` computed post-load from time series

### Step 2.2: Trade Relationships (UN Comtrade)
- **Source:** `un-comtrade`
- **Agent:** Sentinel
- **Relationships:** `(Nation)-[:TRADES {commodity_type, volume, value, friction}]->(Nation)`
- **Note:** `friction` float (0.0-1.0) required for APOC shortest-path algorithms
- **Scope:** Top 500 bilateral trade pairs by value
- **Confidence:** high

### Step 2.3: Commodity Production/Consumption
- **Sources:** `eia-energy` (oil, gas), `fao-stat` (wheat, food), `usgs-minerals` (rare earths, minerals)
- **Agent:** Sentinel
- **Relationships:** `(Nation)-[:PRODUCES {volume, capacity}]->(Commodity)`, `(Nation)-[:CONSUMES {volume, dependency_score}]->(Commodity)`
- **Commodities to add:** Steel, Uranium, Lithium, Copper, Coal (beyond current 5)
- **Scope:** All significant producers/consumers per commodity
- **Confidence:** high

---

## Phase 3: Military & Security Data

### Step 3.1: Military Expenditure (SIPRI)
- **Source:** `sipri-milex` — downloadable Excel/CSV
- **Agent:** Sentinel (deterministic: download CSV → pandas → normalize to USD → Cypher)
- **Properties:** military_spending_abs, military_spending_pct_gdp
- **Years:** 2016-2025 (for historical trends)
- **Scope:** ~170 nations (SIPRI coverage)
- **Confidence:** high
- **Normalization:** SIPRI reports in millions USD → convert to absolute USD

### Step 3.2: Military Capabilities (IISS + Open Sources)
- **Source:** `iiss-milbal` (paywalled — use open alternatives: Global Firepower, Wikipedia)
- **Agent:** Sentinel + manual verification
- **Properties:** manpower_active, manpower_reserve, equipment counts (tanks, aircraft, ships)
- **Scope:** Top 50 military powers in detail, rest imputed from regional averages
- **Confidence:** medium (open sources) to high (IISS where available)

### Step 3.3: Nuclear Status (FAS)
- **Source:** `fas-nuclear`
- **Agent:** Sentinel
- **Properties:** nuclear_warheads, nuclear_status (none/capable/threshold/declared)
- **Scope:** All nations (9 nuclear states + threshold states)
- **Confidence:** high

### Step 3.4: Arms Transfers (SIPRI)
- **Source:** `sipri-arms`
- **Agent:** Sentinel
- **Relationships:** `(Nation)-[:ARMS_TRANSFER {tiv_value, year, equipment_types[]}]->(Nation)`
- **Scope:** All transfers 2016-2025 (10-year window)
- **Confidence:** high

---

## Phase 4: Governance & Society

### Step 4.1: Democracy & Governance (V-Dem)
- **Source:** `vdem`
- **Agent:** Sentinel
- **Properties:** v2x_polyarchy, v2x_liberal, v2x_partipdem, v2x_corr, press_freedom
- **Derived:** stability_index = f(V-Dem sub-indices). Formula stored in ImportBatch.derivation_formula.
- **Normalization:** V-Dem 0-1 floats → multiply by 100 for 0-100 game scale
- **Years:** 2016-2025
- **Scope:** ~180 nations
- **Confidence:** high

### Step 4.2: Domestic Factions
- **Source:** Derived from V-Dem party data + CIA Factbook + Freedom House
- **Agent:** Archon (synthesis) — LLM reasoning appropriate here (unstructured text → structured factions)
- **Method:** derived — combine V-Dem party institutionalization scores with Factbook political parties
- **Nodes:** `(:DomesticFaction {name, ideology, influence, loyalty_to_leader})`
- **Derivation formula:** Stored in ImportBatch
- **Scope:** Top 50 nations (3-5 factions each), rest get 2 generic factions
- **Confidence:** medium (derived/synthesized)

---

## Phase 5: Conflict & Non-State Actors

### Step 5.1: Active Conflicts (ACLED)
- **Source:** `acled`
- **Agent:** Sentinel
- **Nodes:** `(:Conflict {name, type, start_date, intensity, region})`
- **Relationships:** `(Nation)-[:INVOLVED_IN]->(Conflict)`, `(NonStateActor)-[:PARTY_TO]->(Conflict)`
- **Scope:** All active conflicts 2024-2026
- **Confidence:** high

### Step 5.2: Non-State Actors (ACLED + GTD + Open Sources)
- **Source:** `acled` + Uppsala Conflict Data + manual
- **Agent:** Sentinel (structured fields) + Archon (LLM for fuzzy-matching rebel group names to standard IDs)
- **Properties:** name, type, region, estimated_strength, ideology, state_sponsor, operational_area
- **Scope:** ~50 significant NSAs (expand from current 6)
- **Confidence:** medium

---

## Phase 6: Infrastructure & Chokepoints

### Step 6.1: Maritime Chokepoints (EIA)
- **Source:** `eia-energy` + shipping data
- **Agent:** Sentinel
- **Properties:** name, oil_transit_mbpd, total_trade_value, controlling_nations, alternative_routes
- **Scope:** 8-10 critical chokepoints (expand from 5)
- **Confidence:** high

### Step 6.2: Supply Routes
- **Source:** Derived from trade + geography
- **Agent:** Archon
- **Relationships:** `(Nation)-[:SUPPLY_ROUTE {via, commodities[], vulnerability, friction}]->(Nation)`
- **Note:** friction required for APOC pathfinding
- **Confidence:** medium

---

## Phase 7: Alliances & Diplomacy

### Step 7.1: Formal Alliances & Organizations
- **Source:** CIA Factbook + COW Formal Alliances dataset
- **Agent:** Sentinel
- **Nodes:** Expand from 5 to ~20 (NATO, EU [supranational], BRICS, SCO, ASEAN, AU, AUKUS, Quad, OPEC, OPEC+, CSTO, GCC, MERCOSUR, ECOWAS, CIS, Pacific Islands Forum, Arab League, Five Eyes, G7, G20)
- **Note:** EU = `type: "supranational"`, NOT a Nation node
- **Relationships:** `(Nation)-[:MEMBER_OF {role, since}]->(Alliance)`
- **Confidence:** high

### Step 7.2: Bilateral Relations
- **Source:** Derived from voting patterns (UN GA), trade, alliances
- **Agent:** Archon
- **Relationships:** `(Nation)-[:DIPLOMATIC_RELATION {type, warmth_score}]->(Nation)`
- **Scope:** All bilateral pairs for G20, top partners for rest
- **Confidence:** medium

---

## Phase 8: Temporal Model & Validation

### Step 8.1: Historical Snapshots (10-Year)
- **Create Tick nodes** for T=-120 (Jan 2016) through T=-1 (Dec 2025)
- **Create `STATE_AT` relationships** from time series data loaded in Phases 2-4
- **Properties on STATE_AT:** gdp_nominal, inflation_rate, military_spending_abs, stability_index
- **Source:** Aggregated from Phase 2-4 historical data
- **Note:** T=0 (Jan 2026) is the game start baseline

### Step 8.2: Baseline Snapshot (T=0)
- **Create `STATE_AT` relationships** for Month 0 (game start = Jan 2026) for ALL nations
- **Properties on STATE_AT:** gdp_nominal, inflation_rate, military_spending_abs, stability_index, national_morale, war_weariness
- **Derived:** gdp_10yr_cagr, military_spending_trend computed from historical STATE_AT
- **Confidence:** matches underlying data confidence

### Step 8.3: Full Graph Validation
- **Topology tests:** Every nation has borders, trade partners, alliance memberships, at least 1 faction
- **Data completeness:** % of non-null values per property per nation tier (G20/G50/rest)
- **Consistency checks (sanity bounds from Phase 0.3):**
  - GDP vs military spending ratios
  - Nuclear status vs declared
  - Population vs manpower
  - No null values in critical game properties
- **Output:** `data/validation_report.json`

---

## Execution Order & Dependencies

```
Phase 0 (Normalization) ── no dependencies, MUST complete first
    │
Phase 1 (Foundation) ───── depends on Phase 0
    │
Phase 2 (Economics) ────── depends on 1.1 (nation nodes exist)
    │
Phase 3 (Military) ─────── depends on 1.1
    │
Phase 4 (Governance) ───── depends on 1.1, 1.2 (V-Dem crosswalk)
    │
Phase 5 (Conflict) ─────── depends on 1.1, 1.3 (geography)
    │
Phase 6 (Infrastructure) ─ depends on 1.1, 2.3 (commodity nodes)
    │
Phase 7 (Alliances) ────── depends on 1.1
    │
Phase 8 (Temporal) ─────── depends on ALL above
```

Phases 2-7 can run in **parallel** after Phase 1 completes (except noted dependencies).

---

## Agent Assignment & ETL Standard

**⚠️ CRITICAL RULE:** Sentinel generates and executes **deterministic Python scripts** (using `requests`, `pandas`, direct Cypher) for all structured API ingestion. Sentinel does **NOT** parse bulk JSON/CSV payloads row-by-row via LLM context window.

LLM reasoning is used **only** for:
- Unstructured text parsing (leader ideologies from CIA Factbook)
- Fuzzy entity matching (ACLED rebel names → standard IDs)
- Derived/synthesized data (domestic factions from multiple sources)

| Phase | Lead Agent | Review Agent | Method |
|-------|-----------|-------------|--------|
| 0. Normalization | Archon | Dione | Python infrastructure |
| 1. Foundation | Sentinel | Dione | Deterministic script + LLM for text |
| 2. Economics | Sentinel | Dione | Deterministic script |
| 3. Military | Sentinel | Inanna | Deterministic script |
| 4. Governance | Sentinel + Archon | Dione | Script + LLM for derived |
| 5. Conflict | Sentinel + Archon | Inanna | Script + LLM for matching |
| 6. Infrastructure | Sentinel + Archon | Dione | Script + derived |
| 7. Alliances | Sentinel | Dione | Deterministic script |
| 8. Validation | Archon | ALL | Automated tests |

---

## Data Quality Targets

| Nation Tier | Count | Target Completeness | Target Confidence |
|-------------|-------|--------------------|--------------------|
| G20 | 19 | >95% properties filled | >80% high confidence |
| G50 (top 50 by GDP) | 31 | >85% properties filled | >70% high confidence |
| Rest (~125) | ~125 | >60% properties filled | >50% high confidence |

Note: G20 = 19 nations (EU is Alliance, not Nation).
All properties have values (no nulls) — lower-tier nations may have more "estimated" values.
