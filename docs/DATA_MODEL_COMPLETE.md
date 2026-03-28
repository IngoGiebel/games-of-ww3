# GWW3 — Complete Data Model Reference

*Created: 2026-03-28 by Dione 🌙*
*Status: Draft — consolidation of SCHEMA_V2.md + BIAS_FRAMEWORK.md extensions*
*Purpose: Single reference document for Deep Think review of the complete data model including bias infrastructure*

---

## 1. Design Philosophy

1. **Graph-native:** Relationships ARE the game mechanics (trade disruption = edge deletion)
2. **Temporal via STATE_AT:** Monthly snapshots on relationships, not node duplication
3. **Full provenance:** Every node traces back to a DataSource via ImportBatch
4. **Bias-aware:** Every imported value carries bias metadata; corrections are a separate auditable layer
5. **~195 sovereign nations + non-state actors** — no shortcuts
6. **Properties stay flat on nodes** — Neo4j handles 100+ properties natively
7. **Strictly monthly STATE_AT** — no mixed frequencies; mid-month changes via lightweight Event nodes with deltas
8. **No data point is sacred** — every value can be tagged, questioned, and corrected

---

## 2. Node Types

### 2.1 Core Entities

#### Nation (~195)
Primary entity. Every sovereign state. NOT supranational blocs (EU, AU → Alliance).

```cypher
(:Nation {
  // Identity (Phase 1)
  iso3: "DEU",                    // PRIMARY KEY
  iso2: "DE",
  name: "Federal Republic of Germany",
  name_short: "Germany",
  cow_code: 255,
  un_m49: 276,
  vdem_id: 77,
  region: "Europe",
  sub_region: "Western Europe",

  // Demographics (Phase 2 — World Bank + UN WPP)
  population: 84000000,
  urbanization: 77.5,             // %
  internet_penetration: 93.0,     // %

  // Economics (Phase 2 — World Bank)
  gdp_nominal: 4700000000000,     // USD
  gdp_growth: 0.3,                // % annual
  gdp_per_capita: 55900,          // USD
  gdp_10yr_cagr: 1.2,            // % CAGR 10yr
  inflation_rate: 5.9,            // %
  unemployment: 3.0,              // %
  gini: 31.7,
  debt_to_gdp: 64.3,             // %
  forex_reserves: 270000000000,   // USD

  // Military (Phase 3 — SIPRI, IISS)
  military_spending_abs: 98700000000,
  military_spending_pct_gdp: 2.1,
  manpower_active: 183000,
  manpower_reserve: 30000,
  nuclear_warheads: 0,
  nuclear_status: "nato_sharing",

  // Governance (Phase 4 — V-Dem, Freedom House, CPI)
  government_type: "Federal parliamentary republic",
  leader_name: "Olaf Scholz",
  leader_ideology: "Social democracy",
  stability_index: 78,            // 0-100
  freedom_house_score: 94,        // 0-100
  corruption_index: 79,           // 0-100
  press_freedom: 84,              // 0-100

  // Game State (Phase 8 — derived)
  national_morale: 65,            // 0-100
  war_weariness: 10,              // 0-100

  // Provenance (on every node)
  data_quality: "verified",
  data_confidence: "high",
  data_needs_verification: false
})
```

**Constraints:** `nation_iso3` UNIQUE on `iso3`, `nation_name` UNIQUE on `name`

#### Commodity (10 planned)
```cypher
(:Commodity {
  name: "Crude Oil",
  type: "oil",
  unit: "barrels_per_day",
  global_supply: 100000000,
  strategic_importance: "critical"   // critical | major | standard
})
```

Planned: Crude Oil, Natural Gas, Wheat, Semiconductors, Rare Earth Elements, Steel, Uranium, Lithium, Copper, Coal

#### Alliance
International organizations, formal alliances, supranational blocs.
```cypher
(:Alliance {
  name: "NATO",
  type: "military",              // military | economic | political | forum | supranational
  founded: 1949,
  headquarters: "Brussels"
})
```

EU, AU etc. are Alliances with `type: "supranational"` — NOT Nations (prevents GDP double-counting).

#### NonStateActor
```cypher
(:NonStateActor {
  name: "Houthi Movement",
  type: "insurgency",            // insurgency | terrorist | pmc | cartel | separatist | de_facto_government
  ideology: "Zaydi Shia Islamism",
  estimated_strength: 30000,
  state_sponsor: "IRN",
  operational_area: ["YEM", "Red Sea"],
  threat_level: "regional"       // local | regional | global
})
```

#### DomesticFaction
```cypher
(:DomesticFaction {
  name: "BJP Core",
  ideology: "Hindu Nationalism",
  influence: 90,                 // 0-100
  loyalty_to_leader: 85,
  popular_support: 45,           // %
  controls: ["military", "media"]
})
```

#### Chokepoint
```cypher
(:Chokepoint {
  name: "Strait of Hormuz",
  type: "maritime",
  oil_transit_mbpd: 21.0,
  total_trade_pct: 0.25,
  controlling_nations: ["IRN", "OMN"],
  alternative_routes: ["Cape of Good Hope"],
  vulnerability: "critical"
})
```

#### Conflict
```cypher
(:Conflict {
  name: "Russo-Ukrainian War",
  type: "interstate",
  start_date: date("2022-02-24"),
  intensity: "high",
  fatalities_est: 500000,
  region: "Eastern Europe"
})
```

### 2.2 Temporal Entities

#### Tick
Only monthly/epoch ticks create STATE_AT snapshots.
```cypher
(:Tick {
  id: 43200,
  tick_type: "ECONOMIC",         // ECONOMIC | TACTICAL | STRATEGIC
  game_month: 1,
  game_time: datetime("2026-01-01"),
  real_time: datetime("2026-03-23T15:05:44Z")
})
```

#### Event
Discrete mid-month changes.
```cypher
(:Event {
  id: "evt-2026-01-15-sanctions-ru",
  type: "sanctions",
  description: "EU extends sanctions package on Russia",
  severity: "major",
  timestamp: datetime("2026-01-15"),
  delta: {stability_index: -5, national_morale: -3}
})
```

### 2.3 Provenance Entities

#### DataSource
```cypher
(:DataSource {
  id: "worldbank-wdi",
  name: "World Bank - World Development Indicators",
  url: "https://data.worldbank.org/",
  type: "official_statistics",   // official_statistics | research | estimate | model_output | counter_hegemonic | state_media
  update_frequency: "annual",
  license: "CC-BY-4.0",
  provides: ["gdp_nominal", "population", ...]
})
```

#### ImportBatch
```cypher
(:ImportBatch {
  id: "import-2026-03-24-worldbank-gdp",
  timestamp: datetime("2026-03-24T10:30:00Z"),
  agent: "Sentinel",
  method: "api_import",          // api_import | scrape | manual | derived | estimated | mock
  source_query: "indicator=NY.GDP.MKTP.CD&country=all",
  record_count: 195,
  notes: "World Bank WDI 2024 release",
  confidence: "high",
  requires_replacement: false,
  derivation_formula: null
})
```

### 2.4 Bias & Correction Entities (NEW — from BIAS_FRAMEWORK.md)

#### BiasReport
Documents a systematic bias in a data source or dataset.
```cypher
(:BiasReport {
  id: "BR-001",
  target_source: "ACLED",                          // DataSource id or name
  bias_class: "classification_asymmetry",          // see taxonomy below
  severity: "high",                                // low | medium | high | critical
  description: "ACLED defines terrorism exclusively via non-state actor behavior.
                State actions with identical targeting patterns are classified as
                Repression or Explosions/Remote Violence, not terrorism.",
  affected_properties: ["event_type", "conflict_category", "actor_classification"],
  affected_entities: ["ALL"],
  counter_sources: ["Airwars", "TBIJ_DroneWars", "Reprieve", "Chomsky_Herman_1988"],
  correction_method: "reclassification",           // see correction types below
  status: "open",                                  // open | discussed | voted | applied | rejected
  created_by: "Dione + Ingo",
  discussion_url: "moltbook.com/m/wargames/post/xxx",
  created_at: datetime()
})
```

#### Correction
Records a specific data correction applied to an entity/property.
```cypher
(:Correction {
  id: "CORR-CHN-POP-001",
  target_entity: "CHN",                            // iso3 or entity identifier
  target_property: "population",
  original_value: 1412000000,
  corrected_value: 1310000000,
  correction_type: "value_adjustment",             // see types below
  rationale: "Yi Fuxian (2013): systematic overcount due to local inflation incentives
              + One-Child Policy underreporting. Estimate: 90-130M overcount.
              Conservative 100M reduction applied.",
  sources: ["Yi_2013", "Goodkind_2017", "Wallace_2016"],
  entity_view: "CHN NBS maintains 1.41B (2024 census)",
  bias_report_id: "BR-005",                        // links to originating BiasReport
  status: "applied",                                // proposed | discussed | voted | applied | rejected | reverted
  votes_for: 12,
  votes_against: 3,
  discussion_url: "moltbook.com/m/wargames/post/xxx",
  applied_at: datetime(),
  applied_by: "Dione"
})
```

#### CounterSource
Represents an alternative/critical data source used to challenge or supplement primary sources.
```cypher
(:CounterSource {
  id: "CS-airwars",
  name: "Airwars",
  url: "https://airwars.org",
  type: "counter_hegemonic",     // counter_hegemonic | independent_monitor | entity_self_report | academic_critique
  coverage: "Global civilian harm from airstrikes",
  perspective: "Independent civilian casualty tracking; contradicts official military counts",
  bias_class_own: "none_documented",   // counter-sources may have their own biases
  reliability: "high"                   // high | medium | low | contested
})
```

---

## 3. Relationship Types

### 3.1 Economic
```cypher
(Nation)-[:TRADES {commodity_type, volume, value, route_via, friction}]->(Nation)
(Nation)-[:PRODUCES {volume, capacity, pct_global}]->(Commodity)
(Nation)-[:CONSUMES {volume, dependency_score, import_pct}]->(Commodity)
(Nation)-[:SANCTIONS {type, since, severity}]->(Nation)
```

`friction` (float, 0.0-1.0) is REQUIRED for APOC shortest-path (sanction evasion routing).

### 3.2 Military & Security
```cypher
(Nation)-[:BORDERS {length_km, disputed}]->(Nation)
(Nation)-[:MEMBER_OF {role, since, commitment_level}]->(Alliance)
(Nation)-[:ARMS_TRANSFER {tiv_value, year, equipment_types[]}]->(Nation)
(Nation)-[:SUPPLY_ROUTE {via, commodities[], vulnerability, friction}]->(Nation)
(NonStateActor)-[:SPONSORED_BY]->(Nation)
(NonStateActor)-[:OPERATES_IN]->(Nation)
(NonStateActor)-[:PARTY_TO]->(Conflict)
(Nation)-[:INVOLVED_IN {role}]->(Conflict)
```

### 3.3 Domestic
```cypher
(Nation)-[:HAS_FACTION]->(DomesticFaction)
(DomesticFaction)-[:DEPENDS_ON_FACTION]->(DomesticFaction)
```

### 3.4 Infrastructure
```cypher
(Nation)-[:CONTROLS]->(Chokepoint)
(Chokepoint)-[:BLOCKADES {by}]->(Nation)
```

### 3.5 Temporal
```cypher
(Nation)-[:STATE_AT {gdp_nominal, inflation_rate, stability_index, ...}]->(Tick)
(Tick)-[:NEXT]->(Tick)
(Event)-[:OCCURRED_AT]->(Tick)
(Event)-[:ISSUED_BY]->(Nation)
```

### 3.6 Provenance
```cypher
(any entity)-[:PROVENANCE {properties: ["gdp_nominal", "gdp_growth"]}]->(ImportBatch)
(ImportBatch)-[:FROM_SOURCE]->(DataSource)
```

### 3.7 Bias & Correction Relationships (NEW)

```cypher
// DataSource has documented biases
(DataSource)-[:HAS_BIAS {
    class: "funding_dependency",
    detail: "86% US government funded (2016)",
    severity: "high",
    reference: "Bush_2017"
}]->(BiasReport)

// BiasReport links to corrections it generated
(BiasReport)-[:GENERATED]->(Correction)

// Corrections reference counter-sources
(Correction)-[:BASED_ON]->(CounterSource)

// Counter-sources can supplement primary sources
(CounterSource)-[:SUPPLEMENTS]->(DataSource)

// Entity perspective on its own data
(Nation)-[:SELF_REPORTS {
    property: "population",
    claimed_value: 1412000000,
    source: "National Bureau of Statistics census 2024",
    plausibility: "contested"   // accepted | contested | rejected
}]->(BiasReport)
```

### 3.8 Bias-Extended STATE_AT Properties

The STATE_AT relationship gains optional bias metadata per property:

```cypher
(Nation)-[:STATE_AT {
    // Standard properties
    population: 1310000000,                      // corrected value used by game engine
    gdp_nominal: 17700000000000,
    stability_index: 65,

    // Bias metadata (per property, optional — only where bias is documented)
    population_raw: 1412000000,                  // original imported value
    population_source: "UN_WPP_2024",
    population_bias_class: "demographic_manipulation",
    population_bias_severity: "high",
    population_confidence: 0.55,                 // feeds into GSL Truth Value confidence
    population_correction_id: "CORR-CHN-POP-001",

    stability_index_raw: 72,
    stability_index_source: "V-Dem_v14",
    stability_index_bias_class: "expert_subjectivity",
    stability_index_confidence: 0.70,

    // Properties without documented bias carry default confidence
    gdp_nominal_confidence: 0.85                 // default for WB self-reported data
}]->(Tick)
```

**Design Decision:** Bias metadata uses a `{property}_*` suffix convention rather than nested objects, because Neo4j properties are flat key-value pairs. This keeps everything on the same relationship without sub-nodes.

---

## 4. Bias Taxonomy (11 Classes)

| Bias Class | Description | Affected Sources |
|-----------|-------------|-----------------|
| `funding_dependency` | Funder's interests influence methodology/ratings | Freedom House, NED-linked indices |
| `classification_asymmetry` | Same acts coded differently based on actor type | ACLED, GTD |
| `epistemological_hegemony` | Western liberal-democratic norms as universal standard | V-Dem, Freedom House, Polity5, CPI, WJP |
| `expert_subjectivity` | Expert-coded data with documented "pessimism bias" | V-Dem (4000+ experts), CPI |
| `demographic_manipulation` | Political incentives distort population/census data | China NBS, various authoritarian states |
| `media_filter` | Propaganda model effects on event-sourced data | ACLED, GDELT, GTD (media-dependent) |
| `omission` | Systematic non-coverage of certain event types | US drone casualties pre-Airwars |
| `definitional_exclusion` | Definitions structurally exclude certain actors/events | ACLED "terrorism" (state actors excluded) |
| `self_reporting` | States report their own data (incentive to distort) | World Bank (GDP), SIPRI (defense spending), FAO |
| `temporal_lag` | Data is years old, conditions have changed | Polity5 (ends 2018), many WB indicators |
| `aggregation_distortion` | Aggregation hides regional/sub-national variation | National-level indices masking internal diversity |

---

## 5. Correction Types

| Type | Description | Example |
|------|-------------|---------|
| `reclassification` | Re-code event/category using corrected taxonomy | US drone strike → state_violence_against_civilians |
| `value_adjustment` | Replace value with better estimate | China pop 1.41B → 1.31B |
| `confidence_downgrade` | Keep value but lower confidence (widens GSL variance) | V-Dem polyarchy c=0.90 → c=0.60 |
| `source_supplement` | Add counter-source data alongside original | ACLED + Airwars casualties |
| `entity_perspective` | Add self-assessment from affected entity | Russia's view of NATO expansion |
| `interpolation_flag` | Mark interpolated/estimated values | WB indicators with multi-year gaps |

---

## 6. GSL Integration — Confidence ↔ Bias Linkage

Bias-corrected data feeds into GSL via the `confidence` parameter on Truth Values:

```
MATCH (N:Nation)
LET c_pop = N.population_confidence    // 0.55 for China, 0.90 for Germany

IF N.population > 100_000_000
    THEN
        N.draft_pool += N.population × 𝛽(0.02, 0.98)    ⟨0.90, c_pop⟩
        // Low confidence on China → wider variance on draft pool estimate
```

**Mean-preserving confidence formulas:**
- Normal/Log-Normal: `σ_eff = σ × (1 + K × (1 − c))` where K=2
- Beta: `α_eff = c × α, β_eff = c × β`

Low-confidence data → noisier outcomes → simulation doesn't pretend to know what it doesn't know.

---

## 7. Correction Workflow Pipeline

```
1. IMPORT raw data (as-is, with source tag)
   ↓
2. AUTO-TAG known bias classes per source (from bias registry)
   ↓
3. APPLY confidence adjustments (lower c for high-bias data)
   ↓
4. GENERATE correction candidates (counter-source data + entity perspectives)
   ↓
5. COMMUNITY REVIEW (Moltbook discussion + voting)
   ↓
6. APPLY corrections (stored as correction layer, original preserved)
   ↓
7. AUDIT TRAIL (every correction links to rationale, vote, and sources)
```

**Critical invariant:** The original raw import is NEVER modified. Corrections are a separate layer. Both raw and corrected values are queryable.

---

## 8. Constraints & Indexes

| Constraint | Label | Property |
|-----------|-------|----------|
| nation_iso3 | Nation | iso3 |
| nation_name | Nation | name |
| commodity_name | Commodity | name |
| commodity_type | Commodity | type |
| alliance_name | Alliance | name |
| chokepoint_name | Chokepoint | name |
| tick_id | Tick | id |
| datasource_id | DataSource | id |
| importbatch_id | ImportBatch | id |
| task_id | Task | id |
| biasreport_id | BiasReport | id |
| correction_id | Correction | id |
| countersource_id | CounterSource | id |

**Composite Indexes:**
| Index | Label | Properties | Purpose |
|-------|-------|-----------|---------|
| task_queue | Task | (status, assigned_to) | Agent polling |
| tick_game_time | Tick | (game_time) | Temporal queries |
| event_type | Event | (type) | Event filtering |
| bias_by_source | BiasReport | (target_source, status) | Bias lookup per source |
| correction_by_entity | Correction | (target_entity, status) | Corrections per nation |
| correction_by_property | Correction | (target_property, status) | Corrections per property |

---

## 9. Design Decisions Summary

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | EU = Alliance, not Nation | Prevents GDP/population double-counting |
| 2 | Properties flat on Nation | Neo4j handles 100+ props; sub-nodes double read latency |
| 3 | Strictly monthly STATE_AT | No mixed frequencies; Event deltas for mid-month |
| 4 | 10 years historical data | Trend analysis (CAGR), stored as STATE_AT at T=-120..T=-1 |
| 5 | Properties on PROVENANCE edge | O(1) lookup per property |
| 6 | TRADES includes friction | APOC pathfinding for sanction evasion |
| 7 | Impute missing data, never null | Game engine math crashes on None |
| 8 | Sanity bounds on all imports | 10M < GDP < 50T, mil_spend < GDP, pop > 1000 |
| 9 | **Bias metadata via suffix convention** | `{prop}_source`, `{prop}_confidence`, `{prop}_bias_class` on STATE_AT |
| 10 | **Raw + corrected dual layer** | Original import preserved; corrections as separate Correction nodes |
| 11 | **Confidence feeds GSL variance** | Bias-tagged properties get lower c → wider distribution in game rules |
| 12 | **Entity perspectives are data** | SELF_REPORTS relationship stores how nations view their own numbers |
| 13 | **Counter-sources supplement, not replace** | Airwars supplements ACLED; both are queryable |
| 14 | **Community governance of corrections** | BiasReport → discussion → voting → apply/reject |

---

## 10. Open Questions for Review

1. **Suffix convention scalability:** With 100+ properties and bias metadata per property, STATE_AT relationships could have 300-500 keys. Is this performant in Neo4j, or should bias metadata move to separate `:BiasAnnotation` nodes linked per (entity, property, tick)?

2. **Confidence vs. epistemic uncertainty:** The confidence parameter in GSL currently conflates two things: (a) data quality uncertainty (source reliability) and (b) epistemic uncertainty (we don't know what we don't know). Should these be separated into two distinct parameters?

3. **Correction versioning:** When a correction is revised (new evidence), should the old correction be soft-deleted or maintained as a version chain? Currently `status: "reverted"` but no link to the superseding correction.

4. **Entity perspective conflicts:** When China claims 1.41B population and Yi Fuxian estimates 1.31B, which value does the game engine use? Currently: corrected value (1.31B) for game mechanics, both values queryable. Is this the right default?

5. **Bias auto-tagging granularity:** Should auto-tagging apply per-source (all Freedom House data gets `funding_dependency`) or per-property (only FH political_rights, not FH internet_freedom)?

6. **Counter-source reliability:** Who validates counter-sources? Airwars is widely respected, but TeleSUR is Venezuelan state media. Should there be a reliability tier system for counter-sources?

7. **GSL rule auditing:** When a GSL rule uses a bias-corrected value, should the rule evaluation log include the correction chain for full transparency?

---

*This document consolidates SCHEMA_V2.md and the bias infrastructure from BIAS_FRAMEWORK.md into a single reference. The full critical source bibliography (54 sources) is in BIAS_FRAMEWORK.md.*
