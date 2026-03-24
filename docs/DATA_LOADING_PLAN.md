# GWW3 — Data Loading Plan (v1.0)

*Created: 2026-03-24 by Dione 🌙*

## Principles

1. **Every datum has provenance** — No value enters the DB without a linked `ImportBatch` → `DataSource`
2. **Replace, don't patch** — Mock data gets replaced by real data, not merged on top
3. **One source per property domain** — Avoid conflicting values from multiple sources
4. **Idempotent imports** — Every import script can run repeatedly without creating duplicates
5. **Confidence tagging** — Every Nation carries `data_confidence` (high/medium/low/mock)

---

## Provenance Schema (implemented)

```
(:DataSource {id, name, url, type, update_frequency, license, provides[]})
(:ImportBatch {id, timestamp, agent, method, record_count, properties_set[], notes, confidence})

(entity)-[:PROVENANCE]->(ImportBatch)-[:FROM_SOURCE]->(DataSource)
```

**Property-level tags** (on critical Nation properties):
- `data_provenance` — batch ID reference
- `data_confidence` — high | medium | low | mock
- `data_needs_verification` — boolean

---

## Phase 1: Foundation Data (Nations + Geography)

All ~195 sovereign nations. Focus: identity, geography, basic demographics.

### Step 1.1: Nation Identity Registry
- **Source:** CIA World Factbook + ISO 3166
- **Agent:** Sentinel
- **Properties:** iso3, iso2, name, name_short, cow_code, un_m49, government_type, region, sub_region, leader_name, leader_ideology
- **Method:** API/scrape CIA Factbook + static ISO mapping
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

## Phase 2: Economic Data

### Step 2.1: Core Economics (World Bank WDI)
- **Source:** `worldbank-wdi` — API: `api.worldbank.org/v2/country/all/indicator/`
- **Agent:** Sentinel
- **Properties:** gdp_nominal, gdp_growth, gdp_per_capita, population, inflation_rate, unemployment, gini, debt_to_gdp, forex_reserves, urbanization, internet_penetration
- **Indicators:** NY.GDP.MKTP.CD, NY.GDP.MKTP.KD.ZG, NY.GDP.PCAP.CD, SP.POP.TOTL, FP.CPI.TOTL.ZG, SL.UEM.TOTL.ZS, SI.POV.GINI, GC.DOD.TOTL.GD.ZS, FI.RES.TOTL.CD, SP.URB.TOTL.IN.ZS, IT.NET.USER.ZS
- **Year:** Latest available (2023 or 2024)
- **Scope:** ~195 nations
- **Confidence:** high
- **Missing data strategy:** Flag as `null` with `data_confidence = "unavailable"`, do NOT estimate

### Step 2.2: Trade Relationships (UN Comtrade)
- **Source:** `un-comtrade`
- **Agent:** Sentinel
- **Relationships:** `(Nation)-[:TRADES_WITH {volume, value, commodities[]}]->(Nation)`
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
- **Agent:** Sentinel
- **Properties:** military_spending_abs, military_spending_pct_gdp
- **Scope:** ~170 nations (SIPRI coverage)
- **Confidence:** high

### Step 3.2: Military Capabilities (IISS + Open Sources)
- **Source:** `iiss-milbal` (paywalled — use open alternatives: Global Firepower, Wikipedia)
- **Agent:** Sentinel + manual verification
- **Properties:** manpower_active, manpower_reserve, equipment counts (tanks, aircraft, ships)
- **Scope:** Top 50 military powers in detail, rest estimated
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
- **Scope:** All transfers 2020-2025
- **Confidence:** high

---

## Phase 4: Governance & Society

### Step 4.1: Democracy & Governance (V-Dem)
- **Source:** `vdem`
- **Agent:** Sentinel
- **Properties:** v2x_polyarchy, v2x_liberal, v2x_partipdem, v2x_corr, press_freedom, stability_index
- **Note:** Map V-Dem's granular indices to our simplified scores
- **Scope:** ~180 nations
- **Confidence:** high

### Step 4.2: Domestic Factions
- **Source:** Derived from V-Dem party data + CIA Factbook + Freedom House
- **Agent:** Archon (synthesis)
- **Method:** derived — combine V-Dem party institutionalization scores with Factbook political parties
- **Nodes:** `(:DomesticFaction {name, ideology, influence, loyalty_to_leader})`
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
- **Agent:** Sentinel
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
- **Relationships:** `(Nation)-[:SUPPLY_ROUTE {via, commodities[], vulnerability}]->(Nation)`
- **Confidence:** medium

---

## Phase 7: Alliances & Diplomacy

### Step 7.1: Formal Alliances & Organizations
- **Source:** CIA Factbook + COW Formal Alliances dataset
- **Agent:** Sentinel
- **Nodes:** Expand from 4 to ~20 (NATO, EU, BRICS, SCO, ASEAN, AU, AUKUS, Quad, OPEC, OPEC+, CSTO, GCC, MERCOSUR, ECOWAS, CIS, Pacific Islands Forum, Arab League, Five Eyes, G7, G20)
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

### Step 8.1: Baseline Snapshots
- **Create `STATE_AT` relationships** for Month 0 (game start = Jan 2026) for ALL nations
- **Properties on STATE_AT:** gdp_nominal, inflation_rate, military_spending_abs, stability_index, national_morale, war_weariness
- **Source:** Aggregated from Phase 2-4 data
- **Confidence:** matches underlying data confidence

### Step 8.2: Full Graph Validation
- **Run topology tests:** Every nation has borders, trade partners, alliance memberships, at least 1 faction
- **Run data completeness:** % of non-null values per property per nation tier (G20/G50/rest)
- **Run consistency checks:** GDP vs military spending ratios, nuclear status vs declared, etc.
- **Output:** `data/validation_report.json`

---

## Execution Order & Dependencies

```
Phase 1 (Foundation) ─── no dependencies
    │
Phase 2 (Economics) ──── depends on 1.1 (nation nodes exist)
    │
Phase 3 (Military) ───── depends on 1.1
    │
Phase 4 (Governance) ─── depends on 1.1, partially on 1.2 (V-Dem crosswalk)
    │
Phase 5 (Conflict) ───── depends on 1.1, 1.3 (geography for conflict location)
    │
Phase 6 (Infrastructure) depends on 1.1, 2.3 (commodity nodes)
    │
Phase 7 (Alliances) ──── depends on 1.1
    │
Phase 8 (Temporal) ───── depends on ALL above
```

Phases 2-7 can run in **parallel** after Phase 1 completes (except noted dependencies).

---

## Agent Assignment

| Phase | Lead Agent | Review Agent | Method |
|-------|-----------|-------------|--------|
| 1. Foundation | Sentinel | Dione | API + static |
| 2. Economics | Sentinel | Dione | API |
| 3. Military | Sentinel | Inanna | API + manual |
| 4. Governance | Sentinel + Archon | Dione | API + derived |
| 5. Conflict | Sentinel | Inanna | API |
| 6. Infrastructure | Sentinel + Archon | Dione | API + derived |
| 7. Alliances | Sentinel | Dione | API + static |
| 8. Validation | Archon | ALL | automated tests |

---

## Data Quality Targets

| Nation Tier | Count | Target Completeness | Target Confidence |
|-------------|-------|--------------------|--------------------|
| G20 | 20 | >95% properties filled | >80% high confidence |
| G50 (top 50 by GDP) | 30 | >85% properties filled | >70% high confidence |
| Rest (~125) | 125 | >60% properties filled | >50% high confidence |

---

## After Data Loading: Next Steps

1. **Gemini Deep Think Review** — Feed complete schema + sample data for structural review
2. **Agent Architecture Redesign** — ADK-based, resilient loop with error recovery
3. **Game Engine Integration** — Connect Pulse Engine to real data
