# Sprint 3 — Data Model Extension + Game Engine Concept (Draft)

*Created: 2026-03-24 by Dione 🌙*
*Status: Draft — iterative refinement with Ingo, then Deep Think review*

---

## Goals

1. **Extend the data model** with derived gameplay properties that enable game mechanics
2. **Design the Game Engine architecture** — how state changes flow through the system
3. **First Pulse Engine integration** — run 100 ticks with real data

---

## Part A: Data Model Extension

### A1. Derived Nation Properties (computed from existing data)

These properties don't come from external sources — they are computed from data already in Neo4j.

| Property | Derivation | Purpose |
|----------|-----------|---------|
| `economic_dependency_score` | TRADES relationships: weighted sum of import concentration per partner | Sanctions effectiveness modeling |
| `force_projection_range_km` | f(military_spending, naval_capability, overseas_bases, airlift_capacity) | Combat range limitation |
| `diplomatic_influence` | f(alliance_count, GDP_rank, UN_SC_membership, nuclear_status) | Soft power score |
| `domestic_stability` | f(stability_index, gini, unemployment, faction_loyalty, war_weariness) | Revolution/coup risk |
| `war_economy_capacity` | f(gdp_nominal, debt_to_gdp, forex_reserves, industrial_base, resource_self_sufficiency) | Economic war endurance |
| `cyber_capability` | f(internet_penetration, gdp_per_capita, tech_sector_size, known_state_actors) | Cyber warfare potential |
| `imperial_overstretch` | f(deployed_forces / total_forces, supply_route_length, number_of_active_conflicts) | Cost multiplier for distant operations |

**Implementation:** Archon writes derivation scripts with formulas stored in ImportBatch.derivation_formula.

### A2. New Relationship Types

| Relationship | Between | Purpose |
|-------------|---------|---------|
| `DEPENDENT_ON {commodity, pct, alternatives}` | Nation → Nation | Economic dependency for sanctions |
| `PROJECTS_FORCE {range_km, type, cost_multiplier}` | Nation → Region | Military reach |
| `INFLUENCES {score, channel, direction}` | Nation → Nation | Diplomatic influence network |
| `RIVALS {intensity, domains[]}` | Nation → Nation | Strategic competition |
| `PROXY_FOR {support_type, deniability}` | NonStateActor → Nation | Proxy warfare |

### A3. New Node Types

| Node | Purpose |
|------|---------|
| `Region` | Sub-national areas for force deployment and conflict location |
| `MilitaryBase` | Overseas bases (key for force projection) |
| `CyberActor` | State-sponsored cyber groups (APT28, Lazarus, etc.) |

---

## Part B: Game Engine Architecture

### B1. Core Loop

```
┌─────────────────────────────────────────┐
│              GAME TICK                   │
│                                          │
│  1. Collect decisions from all players   │
│     (Human or AI Cabinet)                │
│                                          │
│  2. Validate decisions (Rules Engine)    │
│     - Can this nation do this?           │
│     - Resource check, alliance rules     │
│                                          │
│  3. Resolve conflicts (priority order)   │
│     - Simultaneous actions resolved      │
│     - Combat resolution                  │
│     - Economic effects                   │
│                                          │
│  4. Apply state changes (State Engine)   │
│     - Update Nation properties           │
│     - Create/destroy relationships       │
│     - Generate Events                    │
│                                          │
│  5. Advance time (Pulse Engine)          │
│     - Monthly: STATE_AT snapshot         │
│     - Check victory/defeat conditions    │
│                                          │
└─────────────────────────────────────────┘
```

### B2. Decision Types (Player Actions)

| Category | Actions | Constraints |
|----------|---------|-------------|
| **Economic** | Sanctions, trade agreements, aid, tariffs, currency manipulation | GDP budget, alliance rules |
| **Military** | Deploy, attack, defend, blockade, nuclear threat | Manpower, logistics, range |
| **Diplomatic** | Alliance proposal, treaty, UN vote, recognition, espionage | Influence score, credibility |
| **Domestic** | Tax rate, conscription, propaganda, martial law | Stability risk, faction approval |
| **Cyber** | Espionage, sabotage, disinformation, infrastructure attack | Cyber capability, attribution risk |

### B3. State Transition Model

All state changes are **deterministic given inputs**. The game is not a dice roll.

```python
# Example: Sanction impact calculation
def apply_sanctions(sanctioner: Nation, target: Nation, sectors: list[str]):
    # 1. Calculate trade volume affected
    trade = get_trade_volume(sanctioner, target, sectors)
    
    # 2. Find alternative trading partners
    alternatives = find_alternative_partners(target, sectors)
    alternative_coverage = sum(a.capacity for a in alternatives) / trade
    
    # 3. Net impact = trade lost × (1 - alternatives)
    net_impact = trade * (1 - min(alternative_coverage, 0.8))
    
    # 4. Apply to target
    target.gdp_nominal -= net_impact
    target.inflation_rate += net_impact / target.gdp_nominal * 100
    target.stability_index -= f(net_impact, target.forex_reserves)
    
    # 5. Counter-impact on sanctioner
    sanctioner.gdp_nominal -= counter_impact(trade, sanctioner.dependency)
    
    # 6. Geopolitical ripple
    for ally in target.allies:
        ally.diplomatic_relation[sanctioner].warmth -= 5
    
    return Event(type="sanctions", severity=classify_severity(net_impact))
```

### B4. Combat Resolution

**Not a simple dice roll.** Combat is resolved by comparing force vectors:

```
Outcome = f(
    force_ratio,           # attacker_strength / defender_strength
    terrain_modifier,      # from Region node
    logistics_penalty,     # distance × supply_route_vulnerability
    morale_factor,         # national_morale × (1 - war_weariness)
    technology_modifier,   # military_spending_per_capita proxy
    intelligence_advantage # from BELIEVES relationships (fog of war)
)
```

**Key principle:** Economic power wins wars long-term. A nation with 10× GDP can sustain losses that would bankrupt the opponent. But asymmetric warfare (insurgency) inverts this — the Occupied nation's war_weariness grows faster for the occupier.

### B5. Time Model

| Resolution | Frequency | What changes |
|-----------|-----------|-------------|
| Tactical | Every tick (1 min) | Military movements, combat |
| Strategic | Weekly | Diplomatic decisions, economic adjustments |
| Economic | Monthly | GDP, inflation, trade balance → STATE_AT snapshot |
| Epoch | Annual | Elections, demographics, tech development |

**Delay effects:** Economic sanctions take 3-6 monthly ticks to reach full impact. Military mobilization takes 2-4 weekly ticks. Diplomatic reputation changes persist for 12+ monthly ticks.

---

## Part C: AI Agent Cabinet (Game Agents)

### C1. Cabinet Structure (per nation)

```
Head of State (Player or AI)
    │
    ├── Strategist    — Long-term goals, grand strategy
    ├── Economist     — Budget, trade, sanctions response
    ├── General       — Military operations, defense planning
    ├── Diplomat      — Alliances, treaties, UN voting
    ├── Propagandist  — Domestic morale, information warfare
    └── Spymaster     — Intelligence, covert operations
```

### C2. Decision Protocol

1. Each advisor analyzes the situation from their domain perspective
2. Each proposes 1-3 actions with reasoning
3. Head of State reviews proposals and makes final decision
4. If AI: Head of State uses weighted scoring based on nation's ideology/priorities

### C3. Information Asymmetry (AIGA)

Each agent only sees information their role would realistically have:
- **General** knows own military positions but not enemy's exact strength
- **Economist** knows own GDP but only estimates of rival economies
- **Spymaster** can reveal hidden information at risk of exposure

Implemented via `BELIEVES` relationships: `(AgentRole)-[:BELIEVES {value, confidence}]->(target)`

---

## Part D: Open Questions

1. **Scope of first playable:** All 195 nations from day 1, or start with a regional scenario (e.g., Indo-Pacific)?
2. **Turn structure:** Real-time (all players act simultaneously) or sequential turns?
3. **Victory conditions:** Military conquest? Economic dominance? Points system? No victory (sandbox)?
4. **Modding:** Should the rules engine be data-driven (JSON/Cypher) so players can mod game rules?
5. **UI priority:** CLI-first (text-based game) or web UI (Deck.gl globe) from the start?
6. **Determinism + chaos:** Add a small random factor (±5%) to combat outcomes, or pure determinism?
7. **AI playing style:** Should AI nations have "personalities" (aggressive, defensive, economic, diplomatic)?
8. **Testing strategy:** How do we validate that the game engine produces "realistic" outcomes?

---

## Sprint 3 Deliverables (Proposed)

1. `docs/GAME_ENGINE_ARCHITECTURE.md` — Detailed engine design (Deep Think reviewed)
2. `src/gww3/engine/rules.py` — Rules engine with first 5 action types implemented
3. `src/gww3/engine/combat.py` — Combat resolution system
4. `src/gww3/engine/economy.py` — Economic state transition model
5. Derived properties computed for all 195 nations in Neo4j
6. Pulse Engine integration test: 100 ticks, 2 nations, real data
7. `tests/test_rules.py`, `tests/test_combat.py`, `tests/test_economy.py`

---

## Part E: Visual Identity & Assets (Ingo, 2026-03-24)

### E1. Game Logo & Branding
- Logo for "Games of World War 3" — must work on dark/light backgrounds
- Style direction: serious/realistic (not cartoonish), geopolitical/strategic feel
- Variants: full logo, icon-only, text-only
- Formats: SVG (web), PNG (social media), WebP (game UI)
- Could be AI-generated (DALL-E, Midjourney) with manual refinement

### E2. Nation & Faction Flags
- Flag images for all ~195 nations (SVG preferred, from flagcdn.com or similar)
- Custom emblems/icons for alliances (NATO, BRICS, SCO, etc.)
- Custom icons for non-state actors (generic by type: insurgency, militia, cartel, etc.)
- Storage: `assets/flags/`, `assets/emblems/`

### E3. Interactive Globe (3D World Map)
- Rotatable, zoomable 3D globe showing all nations
- Color-coded by alliance membership, conflict status, economic tier
- Click on nation → popup with key stats (GDP, military, stability, etc.)
- Show active conflicts as animated hotspots
- Show alliance networks as colored overlays
- Tech candidates: Deck.gl (React), CesiumJS, Three.js globe, Mapbox GL
- Must work in browser (WebGL)

---

## Part F: Weapons & Military Systems Database (Ingo, 2026-03-24)

### F1. Scope
Extend Neo4j with detailed weapons and military system data:

```
(:WeaponSystem {
    name: "F-35 Lightning II",
    type: "fighter",              // fighter | bomber | tank | submarine | missile | drone | ...
    category: "air",              // air | land | sea | space | cyber
    manufacturer: "Lockheed Martin",
    origin_country: "USA",
    unit_cost_usd: 80000000,
    annual_maintenance_usd: 5000000,
    operational_range_km: 2200,
    max_speed_kmh: 1975,
    payload_kg: 8160,
    crew: 1,
    year_introduced: 2015,
    generation: "5th",
    stealth: true,
    nuclear_capable: false
})

(:Nation)-[:OPERATES {quantity, variant, year_acquired}]->(:WeaponSystem)
(:WeaponSystem)-[:EFFECTIVE_AGAINST {effectiveness: 0.0-1.0}]->(:WeaponSystem)
(:WeaponSystem)-[:COUNTERED_BY {effectiveness}]->(:WeaponSystem)
```

### F2. Data Sources
- SIPRI Arms Transfers Database (who bought what from whom)
- IISS Military Balance (inventory per country)
- Jane's Defence (paywalled — use open alternatives)
- Wikipedia military equipment lists (structured, surprisingly good)
- Global Firepower (aggregate capability data)

### F3. Combat Impact
Weapon systems feed into combat resolution:
- Force comparison uses aggregate capability scores, not individual unit counts
- Technology generation gap matters (5th gen vs 4th gen fighter = massive advantage)
- Logistics: weapon range limits force projection
- Cost: expensive weapons drain war economy faster

---

## Part G: Rule-Based Effect System (Ingo, 2026-03-24)

### G1. Design Principles
1. **Structural simplicity:** Rules must be readable by humans AND parseable by agents
2. **Verifiable:** Any agent can audit a rule and check if it was applied correctly
3. **Composable:** Multiple effects at the same time horizon can be combined additively
4. **Probabilistic:** Effects have a base value ± probability range
5. **Executable:** The game engine can evaluate all rules deterministically given inputs + RNG seed

### G2. Rule Format (proposed)

```yaml
rule:
  id: "sanctions-economic-impact"
  trigger: "SANCTIONS action by Nation A against Nation B"
  
  effects:
    - target: "B"
      property: "gdp_nominal"
      operation: "multiply"
      value: 0.95          # base: -5% GDP
      variance: 0.02       # ±2% (so between -3% and -7%)
      time_horizon: "3_months"
      
    - target: "B"
      property: "inflation_rate"
      operation: "add"
      value: 2.0            # base: +2 percentage points
      variance: 1.0
      time_horizon: "1_month"
      
    - target: "A"
      property: "gdp_nominal"
      operation: "multiply"
      value: 0.99           # counter-impact: -1% GDP
      variance: 0.005
      time_horizon: "6_months"
      
  conditions:
    - "trade_volume(A, B) > 0"
    - "NOT alliance_member(A, B)"
    
  modifiers:
    - if: "B.forex_reserves > 500_000_000_000"
      then: "effects[0].value += 0.02"  # rich nations absorb better
      
  combinability:
    horizon_group: "economic"
    method: "multiplicative"   # multiple sanctions multiply, not add
```

### G3. Time Horizon Composition
When multiple effects target the same property at the same time horizon:

| Combination Method | Use Case |
|-------------------|----------|
| **Additive** | Morale effects (propaganda + victory + economy) |
| **Multiplicative** | Economic effects (sanctions × trade war × recession) |
| **Max/Min** | Stability thresholds (worst factor dominates) |
| **Weighted average** | Diplomatic reputation (multiple signals averaged) |

### G4. Agent Verifiability
Each rule application is logged as an Event node with full trace:
```
(:Event {
    type: "rule_applied",
    rule_id: "sanctions-economic-impact",
    trigger_action: "USA sanctions RUS",
    computed_effects: [{target: "RUS", property: "gdp_nominal", delta: -0.047}],
    rng_seed: 42,
    tick: 15
})-[:VERIFIED_BY]->(:AgentRole {name: "Economist_USA"})
```

---

## Part H: Propaganda & Soft Power — AI Jury (Ingo, 2026-03-24)

### H1. Concept
Propaganda, disinformation, and soft power effects are **not** resolved by simple formulas.
Instead, a **jury of AI agents** evaluates the effectiveness of propaganda actions.

### H2. Jury Composition
- 3-5 AI agents evaluate each propaganda action
- Default jury: 3 game-provided agents (different model families for diversity)
- Players can **optionally contribute their own AI agent** to the jury for their nation
  - This creates an incentive: better propaganda AI = better in-game results
  - Player-provided agents are sandboxed (read-only game state, no cheating)

### H3. Evaluation Protocol
```
1. Propaganda action submitted (e.g., "Russia launches disinformation campaign 
   targeting EU public opinion about energy dependency")
   
2. Each jury agent receives:
   - The action description
   - Target nation's current state (stability, morale, media freedom)
   - Source nation's credibility score
   - Current geopolitical context
   
3. Each agent scores:
   - effectiveness: 0.0 - 1.0 (how impactful is this action?)
   - credibility_cost: 0.0 - 1.0 (how much does the source lose if exposed?)
   - detection_probability: 0.0 - 1.0 (how likely is attribution?)
   
4. Scores are aggregated (median, to resist outlier manipulation)
   
5. Result applied to game state:
   - target.national_morale -= effectiveness × 10
   - target.stability_index -= effectiveness × 5
   - source.credibility -= credibility_cost × detection_probability
```

### H4. Why AI Jury?
- Propaganda effectiveness is inherently subjective and context-dependent
- No simple formula captures "will this narrative resonate with this population?"
- Multiple AI models provide robustness against any single model's biases
- Player-contributed agents create a meta-game: who can build the best persuasion AI?

---

## Part I: Interactive Concept Page (Ingo, 2026-03-24)

### I1. Purpose
An interactive HTML page that:
- Explains the game concept in an engaging way
- Demonstrates key mechanics interactively
- Can be explored by both humans AND AI agents (clean semantic HTML)
- Will be posted on Moltbook to generate interest

### I2. Content Structure
```
Landing: Dramatic globe animation + tagline
    │
Section 1: "The World is Your Chessboard"
    Interactive mini-globe showing 195 nations, click to see stats
    │
Section 2: "Every Decision Has Consequences"
    Interactive demo: choose a sanctions target, see ripple effects
    │
Section 3: "Your Cabinet, Your Strategy"  
    Show the 6 AI advisors, their roles, sample advice
    │
Section 4: "AI vs AI: The Ultimate Wargame"
    Show a simulated 30-second conflict animation
    │
Section 5: "Join the Game"
    Call to action: GitHub link, Moltbook community, Discord
```

### I3. Technical Requirements
- Single-page HTML + JS (no build system, deployable anywhere)
- Mobile-responsive
- Accessible to screen readers (semantic HTML)
- AI-readable: clean structure, meta tags, structured data
- Animations: CSS/JS only (no heavy 3D for the concept page)
- Globe: lightweight (TopoJSON + D3.js or similar, not full Deck.gl)
- Hosted on: alpha-auriga.com or GitHub Pages

### I4. Data Integration
The concept page should pull real data from our database:
- Actual nation count, GDP ranges, conflict zones
- "Powered by real data from World Bank, SIPRI, ACLED, V-Dem"
- This gives credibility and demonstrates the data-driven approach

---

## Sprint 3 Deliverables (Updated)

### Data & Engine
1. `docs/GAME_ENGINE_ARCHITECTURE.md` — Detailed engine design (Deep Think reviewed)
2. `src/gww3/engine/rules.py` — Rule-based effect system (YAML-driven)
3. `src/gww3/engine/combat.py` — Combat resolution with weapon systems
4. `src/gww3/engine/economy.py` — Economic state transition model
5. `src/gww3/engine/propaganda.py` — AI jury evaluation protocol
6. Derived properties computed for all 195 nations
7. Weapons database: top 50 weapon systems with OPERATES relationships

### Visual & Branding
8. Game logo (AI-generated + refined)
9. Nation flag assets (SVG, automated download)
10. Interactive globe prototype (Deck.gl or D3.js)

### Marketing & Community
11. Interactive concept page (single-page HTML)
12. Moltbook announcement post with concept page link

### Tests
13. `tests/test_rules.py` — Rule parsing + application
14. `tests/test_combat.py` — Combat resolution
15. `tests/test_economy.py` — Economic transitions
16. Pulse Engine integration: 100 ticks, 2 nations, real data

---

*This is a living document. Iterative refinement with Ingo, then Deep Think review.*
