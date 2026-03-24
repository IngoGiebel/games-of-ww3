# GWW3 — Neo4j Graph Schema v2.1

*Created: 2026-03-24 by Dione 🌙*
*Updated: 2026-03-24 — Deep Think Review incorporated*
*Status: **Approved** — Ready for implementation*

## Design Philosophy

1. **Graph-native:** Relationships ARE the game mechanics (trade disruption = edge deletion)
2. **Temporal via STATE_AT:** Monthly snapshots on relationships, not node duplication
3. **Full provenance:** Every node traces back to a DataSource via ImportBatch
4. **~195 sovereign nations + non-state actors** — no shortcuts
5. **Properties stay flat on nodes** — Neo4j handles 100+ properties natively; sub-nodes add query hops for zero benefit
6. **Strictly monthly STATE_AT** — no mixed frequencies; mid-month changes via lightweight Event nodes with deltas

---

## Node Types

### Core Entities

#### Nation
Primary entity. Every sovereign state (~195). **NOT supranational blocs** (EU, AU → Alliance).
```
(:Nation {
  // Identity (Phase 1 — high confidence)
  iso3: "DEU",                    // PRIMARY KEY
  iso2: "DE",
  name: "Federal Republic of Germany",
  name_short: "Germany",
  cow_code: 255,                  // Correlates of War
  un_m49: 276,                    // UN M49 numeric
  vdem_id: 77,                    // V-Dem country ID
  region: "Europe",
  sub_region: "Western Europe",
  
  // Demographics (Phase 2 — World Bank)
  population: 84000000,
  urbanization: 77.5,             // % urban
  internet_penetration: 93.0,     // %
  
  // Economics (Phase 2 — World Bank)
  gdp_nominal: 4700000000000,     // USD
  gdp_growth: 0.3,                // % annual
  gdp_per_capita: 55900,          // USD
  gdp_10yr_cagr: 1.2,            // % Compound Annual Growth Rate (10yr)
  inflation_rate: 5.9,            // %
  unemployment: 3.0,              // %
  gini: 31.7,
  debt_to_gdp: 64.3,             // %
  forex_reserves: 270000000000,   // USD
  
  // Military (Phase 3 — SIPRI, IISS)
  military_spending_abs: 98700000000,  // USD
  military_spending_pct_gdp: 2.1,
  manpower_active: 183000,
  manpower_reserve: 30000,
  nuclear_warheads: 0,
  nuclear_status: "nato_sharing",  // none | capable | threshold | declared | nato_sharing
  
  // Governance (Phase 4 — V-Dem)
  government_type: "Federal parliamentary republic",
  leader_name: "Olaf Scholz",
  leader_ideology: "Social democracy",
  stability_index: 78,            // 0-100
  freedom_house_score: 94,        // 0-100
  corruption_index: 79,           // 0-100 (Transparency International CPI)
  press_freedom: 84,              // 0-100
  
  // Game State (Phase 8 — derived)
  national_morale: 65,            // 0-100
  war_weariness: 10,              // 0-100
  
  // Provenance metadata
  data_quality: "verified",       // verified | mock_realistic | estimated
  data_confidence: "high",        // high | medium | low | mock
  data_needs_verification: false
})
```

**Constraints:**
- `nation_iso3` UNIQUE on `iso3`
- `nation_name` UNIQUE on `name`

#### Commodity
Trade goods that nations produce/consume.
```
(:Commodity {
  name: "Crude Oil",             // PRIMARY KEY (UNIQUE)
  type: "oil",                   // machine-readable slug (UNIQUE)
  unit: "barrels_per_day",
  global_supply: 100000000,
  strategic_importance: "critical"  // critical | major | standard
})
```

Planned commodities (10):
Crude Oil, Natural Gas, Wheat, Semiconductors, Rare Earth Elements, Steel, Uranium, Lithium, Copper, Coal

#### Alliance
International organizations, formal alliances, **and supranational blocs**.
```
(:Alliance {
  name: "NATO",                  // PRIMARY KEY
  type: "military",             // military | economic | political | forum | supranational
  founded: 1949,
  headquarters: "Brussels"
})
```

**Supranational blocs** (EU, AU, etc.) are Alliances with `type: "supranational"`.
They are **NOT** Nations — this prevents GDP/population double-counting.
Game rules (e.g., reduced trade friction between EU members) are applied via
`MEMBER_OF` traversal, not properties on the Alliance node.

#### NonStateActor
Armed groups, terrorist organizations, PMCs, cartels.
```
(:NonStateActor {
  name: "Houthi Movement",      // PRIMARY KEY
  type: "insurgency",           // insurgency | terrorist | pmc | cartel | separatist | de_facto_government
  ideology: "Zaydi Shia Islamism",
  estimated_strength: 30000,     // fighters
  state_sponsor: "IRN",          // iso3 or null
  operational_area: ["YEM", "Red Sea"],
  threat_level: "regional"       // local | regional | global
})
```

#### DomesticFaction
Internal political forces within a nation.
```
(:DomesticFaction {
  name: "BJP Core",
  ideology: "Hindu Nationalism",
  influence: 90,                // 0-100
  loyalty_to_leader: 85,        // 0-100
  popular_support: 45,          // % of electorate
  controls: ["military", "media"]  // institutional control
})
```

#### Chokepoint
Strategic maritime/land passages.
```
(:Chokepoint {
  name: "Strait of Hormuz",
  type: "maritime",             // maritime | land | canal
  oil_transit_mbpd: 21.0,      // million barrels per day
  total_trade_pct: 0.25,       // % of global trade
  controlling_nations: ["IRN", "OMN"],
  alternative_routes: ["Cape of Good Hope"],
  vulnerability: "critical"     // critical | high | moderate | low
})
```

#### Conflict
Active armed conflicts.
```
(:Conflict {
  name: "Russo-Ukrainian War",
  type: "interstate",          // interstate | civil | insurgency | hybrid
  start_date: date("2022-02-24"),
  intensity: "high",           // low | medium | high
  fatalities_est: 500000,
  region: "Eastern Europe"
})
```

### Temporal Entities

#### Tick
Game time markers. Only monthly economic ticks create STATE_AT snapshots.
All macro properties use **strictly monthly** frequency — no mixing.
High-frequency mid-month changes are handled by lightweight Event nodes with deltas.
```
(:Tick {
  id: 43200,                   // minutes since game start
  tick_type: "ECONOMIC",       // ECONOMIC (monthly) | TACTICAL (hourly) | STRATEGIC (weekly)
  game_month: 1,
  game_time: datetime("2026-01-01"),
  real_time: datetime("2026-03-23T15:05:44Z")
})
```

#### Event
Discrete occurrences that change state between monthly snapshots.
```
(:Event {
  id: "evt-2026-01-15-sanctions-ru",
  type: "sanctions",
  description: "EU extends sanctions package on Russia",
  severity: "major",           // minor | moderate | major | critical
  timestamp: datetime("2026-01-15"),
  delta: {stability_index: -5, national_morale: -3}  // property deltas applied mid-month
})
```

### Provenance Entities

#### DataSource
Registry of all external data sources.
```
(:DataSource {
  id: "worldbank-wdi",          // PRIMARY KEY
  name: "World Bank - World Development Indicators",
  url: "https://data.worldbank.org/",
  type: "official_statistics",  // official_statistics | research | estimate | model_output
  update_frequency: "annual",
  license: "CC-BY-4.0",
  provides: ["gdp_nominal", "population", ...]  // what properties this source can fill
})
```

#### ImportBatch
Tracks each data import operation.
```
(:ImportBatch {
  id: "import-2026-03-24-worldbank-gdp",  // PRIMARY KEY
  timestamp: datetime("2026-03-24T10:30:00Z"),
  agent: "Sentinel",
  method: "api_import",         // api_import | scrape | manual | derived | estimated | mock
  source_query: "indicator=NY.GDP.MKTP.CD&country=all",
  record_count: 195,
  notes: "World Bank WDI 2024 release",
  confidence: "high",
  requires_replacement: false,
  derivation_formula: null      // For derived data: "0.3*polyarchy + 0.3*corruption + 0.4*state_capacity"
                                // or git commit hash / function name of derivation script
})
```

**Note:** `properties_set` lives on the PROVENANCE **edge**, not the ImportBatch node.
This enables O(1) lookup: "which batch set gdp_nominal on DEU?" →
```cypher
MATCH (n:Nation {iso3: "DEU"})-[p:PROVENANCE]->(ib:ImportBatch)
WHERE "gdp_nominal" IN p.properties
RETURN ib
```

#### Task
Agent task queue (stored in Neo4j for simplicity — sufficient for ~500-1000 tasks).
```
(:Task {
  id: "task-001-worldbank-gdp",
  phase: 2,
  step: "2.1",
  title: "Import World Bank GDP data for all nations",
  assigned_to: "Sentinel",
  status: "pending",        // pending | in_progress | completed | failed | blocked
  priority: 1,              // 1 = highest
  created_at: datetime(),
  started_at: null,
  completed_at: null,
  retry_count: 0,
  max_retries: 3,
  error_log: null,
  result_summary: null
})
```

### Planned (Not Yet Implemented)

#### Currency
```
(:Currency {code: "USD", name: "US Dollar", issuer: "USA"})
```

#### MilitaryUnit
```
(:MilitaryUnit {id: "usa-army-1ad", name: "1st Armored Division", type: "armored", strength: 16000})
```

---

## Relationship Types

### Economic
```
(Nation)-[:TRADES {commodity_type, volume, value, route_via, friction}]->(Nation)
// NOTE: `friction` (float, 0.0-1.0) is REQUIRED for APOC shortest-path algorithms.
// Pathfinding for sanction evasion traverses TRADES/SUPPLY_ROUTE only.
(Nation)-[:PRODUCES {volume, capacity, pct_global}]->(Commodity)
(Nation)-[:CONSUMES {volume, dependency_score, import_pct}]->(Commodity)
(Nation)-[:SANCTIONS {type, since, severity}]->(Nation)
```

### Military & Security
```
(Nation)-[:BORDERS {length_km, disputed}]->(Nation)
(Nation)-[:MEMBER_OF {role, since, commitment_level}]->(Alliance)
(Nation)-[:ARMS_TRANSFER {tiv_value, year, equipment_types[]}]->(Nation)
(Nation)-[:SUPPLY_ROUTE {via, commodities[], vulnerability, friction}]->(Nation)
(NonStateActor)-[:SPONSORED_BY]->(Nation)
(NonStateActor)-[:OPERATES_IN]->(Nation)
(NonStateActor)-[:PARTY_TO]->(Conflict)
(Nation)-[:INVOLVED_IN {role}]->(Conflict)
```

### Domestic
```
(Nation)-[:HAS_FACTION]->(DomesticFaction)
(DomesticFaction)-[:DEPENDS_ON_FACTION]->(DomesticFaction)
```

### Infrastructure
```
(Nation)-[:CONTROLS]->(Chokepoint)
(Chokepoint)-[:BLOCKADES {by}]->(Nation)  // game event
```

### Temporal
```
(Nation)-[:STATE_AT {gdp_nominal, inflation_rate, stability_index, ...}]->(Tick)
(Tick)-[:NEXT]->(Tick)
(Event)-[:OCCURRED_AT]->(Tick)
(Event)-[:ISSUED_BY]->(Nation)
```

### Provenance
```
(any entity)-[:PROVENANCE {properties: ["gdp_nominal", "gdp_growth"]}]->(ImportBatch)
// properties on the EDGE enables O(1) lookup per property per entity
(ImportBatch)-[:FROM_SOURCE]->(DataSource)
```

### Task Dependencies
```
(Task)-[:DEPENDS_ON]->(Task)
```

---

## Constraints & Indexes

| Constraint | Label | Property |
|-----------|-------|----------|
| nation_iso3 | Nation | iso3 |
| nation_name | Nation | name |
| commodity_name | Commodity | name |
| commodity_type | Commodity | type |
| alliance_name | Alliance | name |
| chokepoint_name | Chokepoint | name |
| currency_code | Currency | code |
| game_id | Game | id |
| player_id | Player | id |
| tick_id | Tick | id |
| datasource_id | DataSource | id |
| importbatch_id | ImportBatch | id |
| task_id | Task | id |

**Composite Indexes:**
| Index | Label | Properties | Purpose |
|-------|-------|-----------|---------|
| task_queue | Task | (status, assigned_to) | Agent loop polling performance |
| tick_game_time | Tick | (game_time) | Temporal queries |
| event_type | Event | (type) | Event filtering |

---

## Design Decisions (from Deep Think Review)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **EU = Alliance, not Nation** | Prevents GDP/population double-counting. Game rules applied via MEMBER_OF traversal. |
| 2 | **Properties flat on Nation** | Neo4j handles 100+ props natively. Sub-nodes would double read latency per game tick. |
| 3 | **Strictly monthly STATE_AT** | No mixed frequencies. Mid-month changes via Event deltas. Prevents temporal linked-list breakage. |
| 4 | **Derivation formulas stored** | In ImportBatch.derivation_formula or as git commit ref. Enables reproducibility for game balancing. |
| 5 | **10 years historical data** | Required for trend analysis (CAGR) and future reuse for financial analysis. Stored as historical STATE_AT snapshots at T=-120 through T=-1. |
| 6 | **Properties on PROVENANCE edge** | O(1) lookup vs. scanning all ImportBatch nodes. |
| 7 | **TRADES (not TRADES_WITH)** | Matches schema.py. Includes friction float for APOC pathfinding. |
| 8 | **Impute missing data, never null** | Game engine uses deterministic math; null crashes TypeError. Impute from regional/income-group averages with confidence="estimated". |
| 9 | **Game balance via systemic friction** | No artificial buffs. Imperial overstretch + asymmetric cost-exchange + diplomacy balance power naturally. |
| 10 | **Sanity bounds on all imports** | Hard invariants: 10M < GDP < 50T, mil_spend < GDP, population > 1000. Fail → block task → escalate. |
