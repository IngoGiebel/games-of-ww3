# Games of World War 3 — Consolidated Design Document v0.2

**Date:** 2026-03-23
**Authors:** Ingo Giebel (Lead), Dione 🌙 (Coordination), Gemini Deep Think, Codex
**Status:** Draft Feinkonzept — basis for Neo4j schema design

---

## 1. Vision & Core Philosophy

A hyper-realistic, real-time geopolitical simulation where AI agents control nations and non-state actors in a fully interconnected world. 

**Core Thesis:** Wars are decided socially and economically — not just militarily. Who rallies the population? Who finances the war longest? Who controls the narrative?

**Key Differentiators:**
- All ~195 nations + non-state actors (Houthi, Hezbollah, Wagner, Taliban, cartels, etc.)
- >1000 parameters per entity, sourced from real open data
- 6 conflict dimensions: Societal, Economic, Military, Cyber, Diplomatic, Informational
- Neo4j graph database: Power = relationships, not just properties
- AI-vs-AI primary (spectators watch), later human+AI hybrid

---

## 2. Player Model

### 2.1 Player Roles
- **Each player controls ONE nation as Head of State** (Strategist role)
- Player makes strategic decisions; all other roles (General, Diplomat, Economist, Propagandist, Spymaster) are AI-advised
- **Internal factions** (opposition parties, military, oligarchs, populace) are simulated — partly stochastic — creating domestic tension the player must manage
- Player does NOT control internal factions directly

### 2.2 Participation
- **Ideal:** Every nation/actor played by a separate player (human or AI agent)
- **Minimum viable:** Top 20 powers played by concrete players, remainder auto-simulated
- **Auto-simulated nations** use rule-based heuristics + lightweight LLM for key decisions
- Multiple games can run in parallel (separate Neo4j instances per game)

---

## 3. Time Model

### 3.1 Base Clock
- **1 Tick = 1 Minute of game time** (minimum, configurable longer)
- Configurable speed factor: at 1x, 1 real second = 1 game minute
- A game simulating 10 years at 1x speed = ~7 real days continuous
- Higher speed factors (10x, 100x) for AI-vs-AI tournaments

### 3.2 Multi-Resolution Update Loops (Pulse Engine)

| Loop | Frequency | Systems | Agent Activity |
|------|-----------|---------|----------------|
| **Tactical** | Every 60 ticks (1 game-hour) | Combat, unit movement, supply consumption, cyber attacks | General, Spymaster react |
| **Operational** | Every 1440 ticks (1 game-day) | Troop deployment completion, casualty reports, protest events | All agents briefed |
| **Diplomatic** | Every 10080 ticks (1 game-week) | UN votes, treaty negotiations, propaganda spread, intelligence reports | Diplomat, Propagandist active |
| **Economic** | Every 43200 ticks (1 game-month) | Tax collection, debt interest, GDP update, inflation, trade balance | Economist presents; **Cabinet Meeting** |
| **Epoch** | Every 525600 ticks (1 game-year) | Demographics, elections, technology advancement, climate shifts | Full strategic review |

### 3.3 Decision Latency (Bureaucracy Engine)
Actions are queued, not instant. Delay depends on regime type:

| Action | Autocracy | Democracy |
|--------|-----------|-----------|
| Cyber attack | 1 hour | 1 hour |
| Deploy army corps | 3-14 days | 7-30 days |
| Change tax rate | 1 day | 30-90 days (legislative) |
| Declare war | 1 day | 7-30 days (political process) |
| Economic reform | 30 days | 90-180 days |
| Nuclear launch | Minutes (if authorized) | Minutes (if authorized) |

### 3.4 Event-Driven Interrupts
Agents normally sleep between their loop cycles. **Critical events** trigger immediate "Emergency Cabinet":
- Invasion detected
- Nuclear launch warning
- Market crash (>10% in 1 day)
- Revolution/coup in progress
- Alliance partner requests emergency aid

### 3.5 Temporal Model in Neo4j
**ALL temporal data lives in Neo4j** (no separate time-series DB):

```cypher
// Time nodes form a linked list
(:Tick {id: 1, game_time: datetime, real_time: datetime})
  -[:NEXT]->(:Tick {id: 2, ...})

// State snapshots link to time
(:Nation {name: "Germany"})-[:STATE_AT {gdp: 4.2T, stability: 0.85, ...}]->(:Tick {id: 500})

// Events link to time
(:Event {type: "WAR_DECLARED", actor: "Russia", target: "Ukraine"})
  -[:OCCURRED_AT]->(:Tick {id: 1200})

// Actions queue with execution time
(:ActionIntent {type: "DEPLOY_TROOPS", units: 50000})
  -[:SCHEDULED_FOR]->(:Tick {id: 1500})
  -[:ISSUED_BY]->(:Nation {name: "USA"})
```

**Key Principle:** State changes are **programmatic/rule-based**. When an agent decides "raise taxes by 5%", the game engine calculates all downstream effects (morale drop, revenue increase, faction reactions) via deterministic rules — NOT via LLM evaluation.

---

## 4. Entity Model

### 4.1 Design Principle: Edges > Properties
> "Instead of `usa.oil_dependency = high`, use the graph:  
> `(USA)-[:IMPORTS {volume: 50M, criticality: 0.9}]->(:Commodity {type: 'Oil'})`"
>
> Properties define state. **Edges define power.**

### 4.2 Node Types

#### Nations (~195)
>1000 parameters across categories (sourced from open data):

| Category | ~Params | Primary Sources |
|----------|---------|-----------------|
| Demographics & Society | 100+ | UN WPP, World Bank, Pew Research |
| Politics & Governance | 150+ | V-Dem (500+ indicators!), Freedom House, CPI, FSI, Polity5 |
| Economy | 200+ | World Bank API, IMF WEO, OECD, UN Comtrade |
| Military | 200+ | SIPRI, Global Firepower, FAS Nuclear Notebook |
| Geography & Infrastructure | 100+ | Natural Earth, OSM, USGS, EIA/IEA, FAO |
| Diplomacy & Intelligence | 50+ | ATOP, UNGA Voting, COW |
| Technology & Research | 50+ | World Bank R&D indicators, patent data |
| **Total** | **1000+** | |

#### Non-State Actors (~50-100)
- Insurgencies, terrorist organizations, PMCs, cartels
- Parameters: strength, funding, ideology, territory, popular support, state sponsors
- Sources: ACLED, UCDP, Stanford MMO, GTD

#### Domestic Factions (per nation, ~3-10)
- Military establishment, business oligarchs, religious leaders, labor unions, ethnic groups, tech sector, rural populists, urban progressives
- Each faction has: `influence`, `loyalty_to_government`, `demands[]`, `protest_threshold`
- **Player cannot control factions directly** — must manage through policy

#### Infrastructure & Geography Nodes
- (:Chokepoint) — Suez, Malacca, Hormuz, Panama, Bosphorus, GIUK Gap
- (:Pipeline) — Nord Stream, Druzhba, TAPI, BTC
- (:Port), (:Airport), (:Military_Base)
- (:Subsea_Cable) — Internet backbone
- (:Orbital_Network) — GPS, recon satellites

#### Economic Nodes
- (:Commodity) — Oil, Gas, Wheat, Semiconductors, Rare Earths, Uranium, Lithium
- (:Currency) — USD, EUR, CNY, with exchange rates
- (:Central_Bank) — Interest rates, money supply, reserve currency status
- (:Sovereign_Bond) — Debt instruments with creditor relationships

### 4.3 Relationship Types

```
// Geopolitical
(n1)-[:BORDERS {length_km, terrain, disputed}]->(n2)
(n1)-[:ALLIED_WITH {type, strength, treaty, since}]->(n2)
(n1)-[:AT_WAR_WITH {type, intensity, since, casus_belli}]->(n2)
(n1)-[:SANCTIONS {target_sectors[], since, severity}]->(n2)
(n1)-[:SECRET_TREATY {type, terms}]->(n2)  // Only visible to Spymaster

// Economic
(n)-[:EXPORTS {commodity, volume, value, criticality}]->(n2)
(n)-[:IMPORTS {commodity, volume, dependency_score}]->(n2)
(n)-[:USES_CURRENCY]->(c:Currency)
(n)-[:OWNS_BOND {amount, yield}]->(n2)  // Debt weapon
(n)-[:DEPENDS_ON_COMMODITY {criticality}]->(commodity)

// Military & Logistics
(unit)-[:DEPLOYED_AT]->(region)
(n)-[:SUPPLY_ROUTE {distance, friction, vulnerability}]->(n2)
(n)-[:CONTROLS]->(region)
(n)-[:BLOCKADES]->(chokepoint)

// Internal
(gov)-[:DEPENDS_ON {approval}]->(faction)
(faction)-[:LOBBIES {influence, demands}]->(gov)
(n)-[:SUPPORTS]->(nsa:NonStateActor)

// Intelligence
(agent)-[:BELIEVES {value, confidence}]->(target_property)

// Temporal
(entity)-[:STATE_AT {properties...}]->(tick)
(event)-[:OCCURRED_AT]->(tick)
(action)-[:SCHEDULED_FOR]->(tick)
```

---

## 5. Conflict Systems

### 5.1 Societal (The Population War)
- **National Morale** = core "HP bar" per nation
- War weariness formula: `ΔWeariness = (Casualties/Population) × (Media_Freedom/Casus_Belli)`
- At weariness 100% → mass protests → automatic GOVERNMENT_CHANGE event
- **Propaganda** campaigns modify morale (effectiveness depends on media landscape)
- **Domestic factions** react independently — opposition grows with war casualties

### 5.2 Economic (The Financing War)
**The Trilemma** — funding war deficit through:
1. **Taxes:** Safest macro, but crushes morale + sparks protests
2. **Debt (Bonds):** Steals from future; if yields >15%, market locked
3. **Money Printing:** Desperation move → hyperinflation → state collapse

**Sanctions as Graph Manipulation:**
- Sever direct [:EXPORTS_TO] edge
- Game engine runs shortest-path to find evasion routes
- Each intermediary extracts "Evasion Premium" (~15%)
- Result: Target loses 30% revenue, sanctioner pays 30% more

**Capitulation Threshold:**
```
ESI = (Inflation × 2) + Unemployment + (Debt_Service / Tax_Revenue)
When ESI > Political_Capital → forced peace (even with intact military)
```

### 5.3 Military (The Kinetic War)
- Combat resolution: tech × morale × terrain × supply × leadership
- **Logistics is king:** Supply routes traverse graph physically; blockade a chokepoint = starve an army
- **Power Projection Friction:** Cost_upkeep = Cost_base × (1 + Distance/Tech_logistics)^α × Friction_basing
- **Nuclear:** MAD doctrine modeled; Defcon levels; second-strike capability check
- **Asymmetric warfare:** Occupation of hostile territory auto-spawns insurgency nodes

### 5.4 Cyber
- Target: Infrastructure nodes (power grid, stock market, satellites)
- Traverses subsea cable edges to reach targets
- ASAT weapons can destroy orbital nodes → blind enemy intelligence
- Success: cyber_offense vs cyber_defense scores

### 5.5 Diplomatic
- Alliance management with decay/fatigue mechanics
- UN Security Council with veto mechanics
- Secret treaties (only visible to Spymaster agents)
- Casus Belli system — unjustified war = massive DPC drain

### 5.6 Informational
- Narrative warfare: create + spread narratives globally
- Deepfakes, social media bots, media manipulation
- Effectiveness scales with target's internet_penetration and media_freedom

---

## 6. Agent Architecture

### 6.1 Roles per Nation

| Role | Responsibility | Sees | LLM Tier |
|------|---------------|------|----------|
| **Strategist** (= Player) | Long-term goals, final decisions | Everything shared by other agents | Human or Opus-tier |
| **General** | Military operations | Full military graph; delayed economic estimates | Fast reasoning |
| **Economist** | Budget, trade, sanctions | Full economic graph; blind to covert ops | Analytical |
| **Diplomat** | Alliances, UN, treaties | Diplomatic graph; limited military intel | Nuanced communication |
| **Propagandist** | Morale, media, narrative | Social/media graph; leader popularity | Creative |
| **Spymaster** | Intel, covert ops, cyber | SECRET edges; probabilistic enemy data | Cost-efficient (many calls) |

### 6.2 Information Asymmetry (AIGA Protocol)
- Agents query Neo4j with **restricted access patterns** (Cypher query filters per role)
- Spymaster is ONLY agent who sees [:SECRET_TREATY] and [:BELIEVES] edges
- Intelligence is **probabilistic**, not perfect — "75% chance enemy has 500 tanks"

### 6.3 Belief Subgraph
- Each nation has a "Belief Graph" — what they THINK is true
- `(USA_Spymaster)-[:BELIEVES {tanks: 5000, confidence: 0.8}]->(Russia_Military)`
- Agents act on beliefs, not ground truth
- Bad intelligence → bad decisions (Iraq WMD scenario)

### 6.4 Cabinet Debate Protocol (Monthly)
1. **Briefing:** Each agent submits 2-sentence summary + 1 proposed action (JSON)
2. **Cross-Examination:** Proposals shared; Economist can veto General's war plan with bankruptcy math
3. **Resolution:** Strategist (= Player) reviews debate and makes binding decision

### 6.5 Decision Quality Modifiers
- **Dictator's Trap:** Authoritarian regimes (V-Dem < 0.3) → subordinates downplay bad news
- **Crisis Mode:** High national stress → more erratic/impulsive decisions
- **Sunk-Cost Fallacy:** "You invested X lives; pulling out destroys your legacy"

### 6.6 Cost Optimization
- **Top 20 nations:** Full LLM agent teams
- **Active conflict zones:** Full LLM agents activated on demand
- **Minor/peaceful nations:** Rule-based heuristics + lightweight LLM for key decisions
- **State changes:** Always programmatic (deterministic rules), NOT LLM-evaluated

---

## 7. Scoring & Victory

### 7.1 Per-Nation Objectives
No global "world conquest" victory. Each nation has contextual goals based on starting position:
- **Superpowers:** Maintain hegemony, expand influence
- **Regional powers:** Achieve regional dominance
- **Small nations:** Survive, maintain sovereignty, improve welfare
- **Non-state actors:** Achieve territorial/ideological goals

### 7.2 Scoring Dimensions
- **Survival Score:** Nation still exists as sovereign state?
- **Influence Score:** Alliance network, economic reach, cultural soft power
- **Prosperity Score:** GDP growth, life expectancy, HDI improvement
- **Stability Score:** Government intact, no civil war, low protest level
- **Military Score:** Territory secured, strategic objectives achieved
- **ELO Rating:** Cross-game ranking for repeat players

### 7.3 Game End Triggers
- Time limit reached (configurable: 10, 25, 50 game-years)
- One bloc achieves dominant VP lead
- Global nuclear exchange (MAD) → all lose
- Player can concede/surrender individually

---

## 8. Data Pipeline (Open Sources → Neo4j)

### Build Order (from data-sources.md):
1. **Core country-year facts:** World Bank + UN WPP + V-Dem → nation nodes
2. **Macro forecasts:** IMF WEO → economic projections
3. **Trade dyads:** UN Comtrade → [:EXPORTS]/[:IMPORTS] edges
4. **Security panel:** SIPRI milex + arms transfers → military properties
5. **Conflict events:** ACLED + UCDP + GTD → non-state actor nodes + event history
6. **Diplomacy graph:** ATOP + UNGA voting + COW → alliance/diplomacy edges
7. **Geo-infrastructure:** Natural Earth + OSM → chokepoints, pipelines, bases
8. **Commodities:** USGS + IEA + FAO → commodity nodes + dependency edges

### Data Gaps (require manual curation/estimation):
- Real-time military readiness (classified)
- Exact nuclear arsenals (estimated by FAS)
- Non-state actor internal finances
- Leader personality/risk tolerance
- Espionage capabilities

---

## 9. Technical Architecture

```
┌──────────────────────────────────────────────┐
│                 Web-UI (React)                │
│    Live World Map │ Dashboard │ Agent Debate  │
│    News Ticker │ Nation View │ Graph Explorer │
└─────────────────────┬────────────────────────┘
                      │ WebSocket (real-time)
┌─────────────────────▼────────────────────────┐
│              API Gateway (FastAPI)            │
└────┬──────────┬──────────┬───────────────────┘
     │          │          │
┌────▼───┐ ┌───▼────┐ ┌───▼──────────────┐
│ Game   │ │ Agent  │ │ Data Pipeline    │
│ Engine │ │ Manager│ │ (Import/Update)  │
│        │ │        │ │                  │
│Pulse   │ │LLM     │ │World Bank, SIPRI │
│Engine  │ │Router  │ │V-Dem, ACLED, ... │
│Rules   │ │Cabinet │ │                  │
│Events  │ │AIGA    │ │                  │
└────┬───┘ └───┬────┘ └───┬──────────────┘
     │         │           │
┌────▼─────────▼───────────▼───────────────────┐
│              Neo4j Graph Database             │
│  Nations │ Factions │ Commodities │ Time      │
│  Edges: Trade, Alliance, War, Supply, Belief  │
│  Temporal: State snapshots linked to Ticks    │
└──────────────────────────────────────────────┘
```

### Tech Stack
- **Backend:** Python (FastAPI) — game engine + API
- **Database:** Neo4j (all state, temporal, relationships)
- **Agent Framework:** LangGraph + custom orchestration
- **Frontend:** React + Deck.gl (3D globe) + WebSocket
- **Hosting:** Docker, horizontally scalable; separate Neo4j instance per game
- **Storage:** Google Workspace (30 TB) for database backups + game archives

---

## 10. Next Steps

| # | Task | Owner | Dependency |
|---|------|-------|------------|
| 1 | ✅ Game Design v0.1 | Gemini | — |
| 2 | ✅ Data Sources Catalog | Codex | — |
| 3 | ✅ Deep Think Analysis | Gemini | 1, 2 |
| 4 | ✅ Consolidated Design v0.2 | Dione | 1, 2, 3 |
| 5 | **Moltbook Post** | Dione | 4 |
| 6 | **Neo4j Schema v1** | Next sprint | 4 |
| 7 | **Data Pipeline Prototype** | Next sprint | 2, 6 |
| 8 | **Game Engine Prototype** | Next sprint | 6 |

---

*Games of World War 3 — Design v0.2*
*"Properties define state. Edges define power."*
