# GWW3 — Neo4j Graph Schema v2.0

*Created: 2026-03-24 by Dione 🌙*
*Status: Pending Deep Think Review*

## Design Philosophy

1. **Graph-native:** Relationships ARE the game mechanics (trade disruption = edge deletion)
2. **Temporal via STATE_AT:** Monthly snapshots on relationships, not node duplication
3. **Full provenance:** Every node traces back to a DataSource via ImportBatch
4. **195 nations + non-state actors** — no shortcuts

---

## Node Types

### Core Entities

#### Nation
Primary entity. Every sovereign state + EU as quasi-state.
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
  data_provenance: "import-2026-03-24-worldbank",
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
  name: "Crude Oil",             // PRIMARY KEY
  type: "oil",                   // machine-readable slug
  unit: "barrels_per_day",
  global_supply: 100000000,
  strategic_importance: "critical"  // critical | major | standard
})
```

Planned commodities (10):
Oil, Natural Gas, Wheat, Semiconductors, Rare Earth Elements, Steel, Uranium, Lithium, Copper, Coal

#### Alliance
International organizations and formal alliances.
```
(:Alliance {
  name: "NATO",                  // PRIMARY KEY
  type: "military",             // military | economic | political | forum
  founded: 1949,
  headquarters: "Brussels"
})
```

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
Discrete occurrences that change state.
```
(:Event {
  id: "evt-2026-01-15-sanctions-ru",
  type: "sanctions",
  description: "EU extends sanctions package on Russia",
  severity: "major",           // minor | moderate | major | critical
  timestamp: datetime("2026-01-15")
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
  properties_set: ["gdp_nominal", "gdp_growth", "gdp_per_capita"],
  notes: "World Bank WDI 2024 release",
  confidence: "high",
  requires_replacement: false
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
(Nation)-[:TRADES_WITH {volume, value, commodities[], year}]->(Nation)
(Nation)-[:PRODUCES {volume, capacity, pct_global}]->(Commodity)
(Nation)-[:CONSUMES {volume, dependency_score, import_pct}]->(Commodity)
(Nation)-[:SANCTIONS {type, since, severity}]->(Nation)
```

### Military & Security
```
(Nation)-[:BORDERS {length_km, disputed}]->(Nation)
(Nation)-[:MEMBER_OF {role, since, commitment_level}]->(Alliance)
(Nation)-[:ARMS_TRANSFER {tiv_value, year, equipment_types[]}]->(Nation)
(Nation)-[:SUPPLY_ROUTE {via, commodities[], vulnerability}]->(Nation)
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
(any entity)-[:PROVENANCE]->(ImportBatch)
(ImportBatch)-[:FROM_SOURCE]->(DataSource)
```

---

## Constraints Summary

| Constraint | Label | Property |
|-----------|-------|----------|
| nation_iso3 | Nation | iso3 |
| nation_name | Nation | name |
| commodity_name | Commodity | name |
| alliance_name | Alliance | name |
| chokepoint_name | Chokepoint | name |
| currency_code | Currency | code |
| game_id | Game | id |
| player_id | Player | id |
| tick_id | Tick | id |
| datasource_id | DataSource | id |
| importbatch_id | ImportBatch | id |

---

## Open Questions for Deep Think Review

1. **EU as Nation?** Currently EU is a `(:Nation {iso3: "EUR"})` — should it be a separate label like `(:Supranational)`?
2. **Property explosion:** Nations have 30+ properties. Should some be split into sub-nodes (e.g., `(:EconomicProfile)`, `(:MilitaryProfile)`)?
3. **Temporal granularity:** Monthly STATE_AT is coarse. Should some properties (e.g., GDP) be annual while others (morale, war_weariness) are weekly?
4. **Derived data:** When Archon derives `stability_index` from V-Dem sub-indices, should the derivation formula be stored in the ImportBatch?
5. **Historical depth:** Should we load 5-10 years of historical data for trend analysis, or just the latest?
6. **Currency representation:** Dedicated Currency nodes vs. just storing `currency: "USD"` on economic edges?
