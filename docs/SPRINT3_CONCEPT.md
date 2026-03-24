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

*This is a living document. We'll refine iteratively before Deep Think review.*
