# Game Rules

## Overview

Games of World War 3 is a turn-based geopolitical simulation for 2–20 players. Each player controls a nation-state and pursues victory through economic, diplomatic, or military means. The game starts from real-world data and diverges based on player decisions.

## Game Setup

### Initial State

The game world is seeded from real-world data:
- **GDP and economic indicators** from World Bank (most recent year)
- **Military capabilities** from Global Firepower Index and SIPRI
- **Nuclear arsenals** from Federation of American Scientists / SIPRI
- **Alliance memberships** from treaty databases (NATO, CSTO, AUKUS, SCO, etc.)
- **Trade relationships** from UN COMTRADE
- **Natural resources** from CIA World Factbook

Each nation begins with its real-world capabilities. Germany starts with a €4.5T GDP but limited military projection. Russia starts with a large nuclear arsenal but a smaller economy. The asymmetry is the game.

### Nation Selection

Players choose (or are assigned) nations. Not all nations are playable — the initial release focuses on the **20 most strategically significant nations**:

**Tier 1 (Major Powers):** USA, China, Russia
**Tier 2 (Regional Powers):** India, Germany, France, UK, Japan, South Korea, Brazil, Turkey
**Tier 3 (Strategic Nations):** Iran, Israel, Pakistan, Saudi Arabia, Australia, Indonesia, Poland, Egypt, Nigeria

Non-player nations exist as NPCs with predictable behavior patterns.

## Turn Structure

Each turn represents **6 months** of game time. A turn consists of four sequential phases:

### Phase 1: Economic (Simultaneous)

All players submit economic actions simultaneously. Available actions:

| Action | Description | Constraints |
|--------|-------------|-------------|
| `SET_BUDGET` | Allocate GDP % to military, R&D, infrastructure, social | Must sum to 100% |
| `TRADE_OFFER` | Propose bilateral trade agreement | Requires partner acceptance in diplomatic phase |
| `IMPOSE_SANCTIONS` | Economic sanctions against a nation | Costs diplomatic capital |
| `INVEST_DOMESTIC` | Boost specific sector (energy, tech, agriculture) | Limited by GDP |
| `ISSUE_DEBT` | Borrow against future GDP | Interest rate based on credit rating |
| `CURRENCY_POLICY` | Adjust monetary policy (hawkish/dovish) | Affects inflation and trade |
| `RESOURCE_EXTRACTION` | Increase natural resource output | Costs infrastructure points |

**Budget Allocation** is the core economic decision. A nation spending 5% of GDP on military grows slower than one spending 1%, but is better defended.

### Phase 2: Diplomatic (Simultaneous)

| Action | Description | Constraints |
|--------|-------------|-------------|
| `PROPOSE_ALLIANCE` | Invite nation to alliance | Requires acceptance |
| `LEAVE_ALLIANCE` | Exit an alliance | Diplomatic penalty |
| `SIGN_TREATY` | Non-aggression, arms limitation, trade | Bilateral or multilateral |
| `BREAK_TREATY` | Violate existing treaty | Severe trust penalty |
| `UN_RESOLUTION` | Propose international resolution | Requires majority vote |
| `ESPIONAGE` | Intelligence operation against target | Risk of detection |
| `DIPLOMATIC_PRESSURE` | Coerce nation via soft power | Costs diplomatic capital |
| `SEND_AID` | Foreign aid / disaster relief | Improves relations |

**Diplomatic Capital** is a resource that regenerates slowly and is spent on most diplomatic actions. Nations with high soft power regenerate it faster.

### Phase 3: Military (Simultaneous)

| Action | Description | Constraints |
|--------|-------------|-------------|
| `MOVE_FORCES` | Relocate units to region | Limited by logistics capacity |
| `MOBILIZE` | Call up reserves | Costs GDP, takes 1 turn |
| `BUILD_UNITS` | Produce military equipment | Costs GDP, 1-3 turn production time |
| `ATTACK` | Initiate combat against target | Must have forces in adjacent region |
| `DEFEND` | Fortify current position | Defensive bonus |
| `NAVAL_BLOCKADE` | Block maritime trade routes | Requires naval superiority |
| `AIR_STRIKE` | Precision strike on target | Requires air superiority or stealth |
| `NUCLEAR_ALERT` | Change nuclear posture (DEFCON) | Raises global tension |
| `NUCLEAR_LAUNCH` | Launch nuclear weapons | **Irreversible. Triggers MAD evaluation.** |
| `ARMS_DEAL` | Sell/buy weapons to/from other nation | Both parties must agree |

**Nuclear weapons** are the ultimate deterrent. Using them triggers Mutually Assured Destruction (MAD) calculations — retaliatory strikes from the target and its allies. A nuclear exchange typically ends the game for all involved.

### Phase 4: Resolution (Engine)

The engine processes all submitted actions in a deterministic order:

1. **Economic resolution** — Budget allocations applied, GDP growth calculated, sanctions effects processed, trade agreements finalized
2. **Diplomatic resolution** — Alliance changes processed, treaties ratified, espionage results determined, diplomatic capital updated
3. **Military resolution** — Movements executed, combat resolved, casualties calculated, territory changes applied
4. **Cascading effects** — Second-order effects (alliance obligations trigger, economic shocks propagate, refugee flows)
5. **State update** — All changes committed to the game state
6. **Victory check** — Win conditions evaluated

## Combat Resolution

Combat uses a modified Lanchester model with real-world force multipliers:

```
Effective_Strength = Base_Strength
    × Technology_Modifier (0.5–2.0)
    × Morale_Modifier (0.5–1.5)
    × Terrain_Modifier (0.5–2.0)
    × Logistics_Modifier (0.5–1.5)
    × Leadership_Modifier (0.8–1.2)
    + Random_Variance (±15%)
```

**Key combat principles:**
- **Defense advantage:** Defenders get a 1.5× terrain modifier in fortified positions
- **Air superiority matters:** Without it, ground forces suffer a 0.7× penalty
- **Naval power projects:** Carrier groups can project force across oceans
- **Nuclear deterrence:** Nations with second-strike capability are effectively immune to invasion (rational actors won't risk MAD)

## Victory Conditions

A game ends when any victory condition is met, or after a configurable number of turns (default: 40 turns = 20 game-years).

| Victory Type | Condition | Description |
|-------------|-----------|-------------|
| **Economic Dominance** | Control 40%+ of world GDP | Build an economic superpower |
| **Military Hegemony** | Occupy 3+ other player capitals | Conquer by force |
| **Alliance Leader** | Lead alliance with 50%+ of world GDP | Build a dominant bloc |
| **Technological Supremacy** | Max out 3+ tech trees | Win through innovation |
| **Survival** | Be the last player standing | Everyone else collapsed or was conquered |
| **Diplomatic Victory** | Pass 5 UN resolutions you authored | Lead through soft power |

If no victory condition is met by the final turn, the winner is determined by a **composite score**:

```
Score = GDP_Rank × 0.3
      + Military_Rank × 0.2
      + Alliance_Power × 0.2
      + Territory_Rank × 0.15
      + Tech_Level × 0.15
```

## Global Tension

A shared **Global Tension** meter (0–100) tracks how close the world is to total war:

- **0–25 (Cold Peace):** Normal trade, diplomacy active, military buildups noticed but tolerated
- **26–50 (Rising Tensions):** Sanctions more common, arms races accelerate, alliances solidify
- **51–75 (Crisis):** Trade disruptions, proxy wars, nuclear alerts increase tension further
- **76–100 (Brink of War):** Global markets crash (all GDP -5%), alliances trigger automatically, any military action could cascade

**Tension increases from:** Military buildups, sanctions, treaty violations, nuclear alerts, combat
**Tension decreases from:** Peace treaties, trade agreements, arms reduction, UN resolutions

## Resource System

Nations have access to strategic resources that affect their capabilities:

| Resource | Effect | Major Producers |
|----------|--------|----------------|
| Oil & Gas | Powers military, fuels GDP growth | Russia, Saudi Arabia, USA |
| Rare Earths | Required for advanced tech/weapons | China, Australia |
| Uranium | Required for nuclear program | Kazakhstan, Canada, Australia |
| Food/Agriculture | Population stability, prevents unrest | USA, Brazil, India |
| Semiconductors | Technology modifier for military | Taiwan, South Korea, USA |
| Steel & Manufacturing | Military production capacity | China, India, Japan |

**Resource dependencies** create natural alliances and vulnerabilities. A nation dependent on imported oil is vulnerable to naval blockades.

## Information & Intelligence

### What You Know
- Your own nation's complete state
- Public events (wars, treaties, UN resolutions)
- Approximate military strength of neighbors (±20% accuracy)
- Trade flows you participate in

### What You Don't Know
- Exact GDP/military stats of other nations
- Secret alliances and treaties
- Nuclear posture of other nations (unless at DEFCON 1)
- Espionage operations against you (unless detected)

### Espionage
Successful espionage reveals hidden information. Failed espionage is detected and damages diplomatic relations. Espionage quality depends on intelligence budget allocation.

## Turn Timing

- **Async mode:** Players have a configurable deadline per phase (default: 60 seconds for AI, 5 minutes for humans)
- **If a player doesn't submit:** Default actions are used (maintain current budget, no new diplomatic/military actions)
- **Speed mode:** All players are AI, turns resolve as fast as actions are submitted

## Game Configuration

Games are created with configurable parameters:

```json
{
  "name": "Cold War II",
  "max_turns": 40,
  "turn_duration_seconds": 60,
  "starting_year": 2025,
  "playable_nations": ["USA", "CHN", "RUS", "DEU", "IND"],
  "fog_of_war": true,
  "nuclear_weapons_enabled": true,
  "random_seed": 42
}
```
