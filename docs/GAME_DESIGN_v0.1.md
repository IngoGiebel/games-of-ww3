# Game Design Document: Games of World War 3 (Draft v0.1)

**Author:** Senior Game Designer
**Date:** 2026-03-23
**Version:** 0.1

---

## 1. Game Overview

### 1.1. Vision
'Games of World War 3' (GWW3) is a hyper-realistic, real-time geopolitical grand strategy simulation. It models the entirety of our modern world, from the ~195 Done. The comprehensive Game Design Document (v0.1) for 'Games of World War 3' has been created and saved to `game-design-v0.1.md`.
g the map and more about navigating the complex, interwoven fabric of 21st-century power.

Our core philosophy is that modern conflicts are won or lost not just on the battlefield, but in the hearts, minds, and wallets of the populace. The ultimate victory lies in achieving national objectives while maintaining internal social cohesion and economic stability. Who can best finance a prolonged conflict? Whose population will endure the cost? Whose narrative will prevail?

### 1.2. Unique Selling Points (USPs)
*   **Hyper-Realism:** Over 1,000 parameters model each entity, from economic indicators and military readiness to cultural values and national morale.
*   **AI-Driven Narrative:** The world is a dynamic stage for AI agents representing national leaderships. Each nation's strategy is emergent, creating unique, unscripted alternate histories in every playthrough.
*   **Holistic Conflict Model:** War is more than just military force. GWW3 simulates six interconnected dimensions of conflict: Societal, Economic, Military, Cyber, Diplomatic, and Informational.
*   **Spectator Sport:** Primarily designed as an AI-vs-AI simulation, GWW3 offers a compelling spectator experience, allowing viewers to watch global events unfold, analyze AI strategies, and learn about the intricacies of geopolitics.
*   **Graph-Based World Model:** The use of a Neo4j graph database allows for a deeply interconnected and fluid representation of global relationships, from trade dependencies to secret alliances.

### 1.3. Target Audience
*   **Grand Strategy Veterans:** Players of Paradox Interactive titles (Hearts of Iron, Victoria), and other deep strategy games.
*   **Geopolitics & IR Enthusiasts:** Individuals with a keen interest in international relations, economics, and modern history.
*   **AI & Simulation Aficionados:** Researchers and hobbyists interested in emergent behavior, multi-agent systems, and large-scale simulations.
*   **Educational Institutions & Think Tanks:** A potential tool for modeling and visualizing geopolitical scenarios.

---

## 2. Core Gameplay Loop

GWW3 operates on a timed real-time model, where each "tick" represents a configurable unit of in-game time (e.g., 12 or 24 hours). The core loop for each national entity is a continuous cycle of perception, deliberation, and action.

**The OODA Loop for AI Agents:**

1.  **Observe (Perception):**
    *   Each of a nation's six AI agents (Strategist, Diplomat, General, Economist, Propagandist, Spymaster) queries the Neo4j graph database to get the current world state relevant to its domain.
    *   This perception is filtered by intelligence levels. Information may be incomplete, delayed, or inaccurate (misinformation).

2.  **Orient (Deliberation):**
    *   The **Strategist Agent** reviews the nation's long-term goals (e.g., "Achieve regional hegemony," "Become the world's leading tech economy").
    *   Each of the other five agents analyzes the situation from its perspective and formulates a set of proposed actions aligned with the Strategist's goals.
        *   *Example: Facing an economic downturn, the Economist may propose stimulus packages, the Diplomat may propose new trade deals, and the Propagandist may propose a media campaign to improve consumer confidence.*

3.  **Decide (Consensus):**
    *   The agents present their proposed actions in a "cabinet meeting."
    *   They "debate" the merits and risks of each action, considering resource costs, potential consequences, and cross-domain impact.
    *   A consensus mechanism (e.g., weighted voting, with the Strategist having tie-breaking authority) determines which set of actions will be executed for the current tick.

4.  **Act (Execution):**
    *   The approved actions are executed.
    *   These actions translate into database transactions that modify the nodes and relationships in the Neo4j world graph.
        *   *Example: A "Declare War" action creates a `WAR` relationship between two nation nodes. A "Build Factory" action increases a nation's `industrial_capacity` property and consumes `treasury` resources.*
    *   The results of these actions will be perceived by all agents in the subsequent "Observe" phase, thus completing the loop.

---

## 3. Entity Model (>1000 Parameters)

Each entity (nations and non-state actors) is a node in the graph, defined by a vast set of properties. Below are the primary categories and representative examples.

#### 3.1. Nation-State Parameters

**A. Geographic & Environmental ( ~50 params)**
*   `area_sq_km`, `coastline_km`, `arable_land_pct`
*   `climate_zone`, `avg_temperature`, `natural_disaster_risk` (earthquake, flood, etc.)
*   `natural_resources` (oil_reserves, gas_reserves, coal, uranium, rare_earths, etc.)
*   `strategic_chokepoints` (e.g., Strait of Hormuz, Panama Canal)

**B. Demographics (~100 params)**
*   `population_total`, `population_growth_rate`
*   `age_distribution` (0-14, 15-64, 65+ cohorts)
*   `urbanization_rate`, `population_density`
*   `ethnic_groups` & `ethnic_cohesion_index`
*   `religious_groups` & `religious_cohesion_index`
*   `linguistic_groups`
*   `life_expectancy`, `infant_mortality_rate`
*   `literacy_rate`, `education_index` (primary, secondary, tertiary enrollment)
*   `emigration_rate`, `immigration_rate`, `refugee_burden`

**C. Government & Politics (~150 params)**
*   `government_type` (e.g., Democracy, Authoritarian, Theocracy)
*   `political_stability_index`, `corruption_perception_index`
*   `leader_ideology`, `leader_popularity`, `years_in_power`
*   `ruling_party_ideology`, `opposition_strength`
*   `legislative_effectiveness`, `judicial_independence`
*   `freedom_of_press_index`, `civil_liberties_index`
*   `political_movements` (separatist, revolutionary, etc.) with `support_pct`
*   `bureaucracy_quality_index`
*   `election_cycle_status`, `next_election_date`

**D. Economy (~200 params)**
*   `gdp_nominal`, `gdp_ppp`, `gdp_growth_rate`, `gdp_per_capita`
*   `gdp_composition` (% agriculture, industry, services)
*   `inflation_rate`, `unemployment_rate`, `gini_coefficient`
*   `national_budget`, `tax_revenue`, `government_spending`
*   `national_debt_to_gdp_ratio`, `credit_rating`
*   `currency_name`, `currency_strength_index`, `forex_reserves`
*   `central_bank_interest_rate`
*   `major_imports` & `major_exports` (goods, partners)
*   `trade_balance`, `major_trade_routes`
*   `stock_market_index`, `fdi_inflows`, `fdi_outflows`
*   `war_chest_reserves`, `war_bond_issuance_capacity`
*   `key_industries` (automotive, pharma, aerospace, etc.) with `health_index`

**E. Societal & Cultural (~150 params)**
*   `national_morale` (core stat), `war_weariness`
*   `population_approval_of_leader`, `population_trust_in_government`
*   `dominant_cultural_values` (e.g., individualism vs. collectivism)
*   `social_cohesion_index`, `protest_risk_level`
*   `media_landscape` (state-controlled, free, mixed)
*   `internet_penetration_pct`, `social_media_usage_pct`
*   `national_identity_strength`, `regionalism_strength`
*   `soft_power_index` (cultural exports, tourism appeal, brand)
*   `public_health_index`, `healthcare_capacity`

**F. Military (~200 params)**
*   `military_spending_pct_gdp`
*   `manpower_active`, `manpower_reserves`, `manpower_fit_for_service`
*   `military_tech_level` (overall)
*   **Branches (Army, Navy, Air Force, Strategic Forces):**
    *   For each branch: `personnel_count`, `morale`, `readiness`, `equipment_tech_level`
    *   `army_units` (divisions, brigades by type: infantry, armor, artillery)
    *   `navy_units` (carriers, submarines, destroyers, etc.)
    *   `air_force_units` (squadrons by type: fighter, bomber, transport)
*   `logistics_capacity_index` (supply lines, transport)
*   `special_forces_capability`
*   **Nuclear Weapons:**
    *   `nuclear_status` (non-nuclear, capable, armed)
    *   `warhead_count_strategic`, `warhead_count_tactical`
    *   `delivery_systems` (ICBMs, SLBMs, Bombers - the "Triad")
    *   `launch_detection_capability`, `second_strike_capability`

**G. Infrastructure (~100 params)**
*   `transport_quality` (roads, rail, ports, airports)
*   `energy_grid_resilience`, `power_generation_capacity` (by type)
*   `telecom_infrastructure_quality`, `satellite_coverage`
*   `water_supply_security`
*   `cyber_defense_level` of critical infrastructure

**H. Technology & Research (~50 params)**
*   `r&d_spending_pct_gdp`
*   `patent_applications_per_year`
*   `tech_sectors_leadership` (AI, biotech, quantum, etc.)
*   `espionage_tech_defense`

**I. Diplomatic & Intelligence (~50 params)**
*   `alliances` (formal relationships)
*   `un_voting_record` (alignment with major blocs)
*   `diplomatic_influence_score`
*   `intelligence_agency_effectiveness` (offensive/defensive)
*   `foreign_aid_given`, `foreign_aid_received`

#### 3.2. Non-State Actor (NSA) Parameters
NSAs have a simplified but distinct model.

*   `nsa_type` (e.g., Insurgency, Terrorist Org, PMC, Cartel)
*   `ideology`, `primary_goals`
*   `personnel_strength`, `recruitment_rate`
*   `funding_sources` (donations, crime, state-sponsorship)
*   `area_of_operation`, `level_of_control`
*   `equipment_level` (small arms, technicals, IEDs, drones)
*   `morale`, `leadership_effectiveness`
*   `popular_support_in_ao`
*   `state_sponsors` & `state_enemies` (relationships)

---

## 4. Conflict Systems

### 4.1. Societal Conflict
*   **Morale & Stability:** `national_morale` is the central HP bar. It's affected by economic conditions, casualties, propaganda, and political freedom. Low morale increases `protest_risk_level`.
*   **Propaganda:** The Propagandist agent can launch campaigns (`media_control`, `social_media_ops`) to boost morale, justify wars, or demonize enemies. Effectiveness depends on `media_landscape` and opponent's `informational_defense`.
*   **Protests & Revolutions:** If `protest_risk_level` crosses a threshold, `Protest` events occur, reducing economic output and stability. If stability drops to zero, a `Civil War` or `Revolution` event can be triggered, potentially changing the government or splintering the nation.

### 4.2. Economic Conflict
*   **Trade & Sanctions:** Nations have `TRADE` relationships. Sanctions allow nations to target specific industries of another (`sanctions_effectiveness` depends on global market share). A full embargo is a severe escalation.
*   **War Financing:** Wars have a massive daily cost. Nations finance this through their `treasury`, by issuing `war_bonds` (increasing `national_debt`), or by printing money (increasing `inflation_rate`). Economic collapse is a primary losing condition.
*   **Currency & Debt Warfare:** Powerful economies can manipulate currency markets to devalue a rival's currency. A nation with high debt is vulnerable to its creditors.

### 4.3. Military Conflict
*   **Combat Resolution:** When armies meet, combat is resolved in a tick-based loop considering factors like equipment tech, morale, terrain, leadership, and importantly, `supply_status`. An army without supply suffers immense penalties.
*   **Logistics:** Supply lines are physical relationships on the graph, vulnerable to interdiction by naval blockades, air power, or special forces.
*   **Nuclear Deterrence:** Nuclear-armed states have a "Defcon" level. Escalating a conventional war against a nuclear power raises the Defcon level. At Defcon 1, nuclear launch is authorized. MAD (Mutually Assured Destruction) is modeled: a first strike will trigger a massive, game-ending retaliation if the target has `second_strike_capability`.

### 4.4. Cyber Conflict
*   **Infrastructure Attacks:** The Spymaster agent can launch cyberattacks against another nation's `Infrastructure` nodes (e.g., "Shutdown Power Grid," "Disrupt Stock Market"). Success depends on relative `cyber_offense` vs. `cyber_defense` levels.
*   **Espionage:** Cyber assets can be used to steal `technology`, reveal secret `diplomatic_treaties`, or gain insight into an opponent's `military_readiness`.

### 4.5. Diplomatic Conflict
*   **Alliances & Blocs:** `ALLIED_WITH` relationships provide defensive pacts. Nations can form blocs to vote together in the UN or coordinate economic policy.
*   **United Nations:** The UN allows for resolutions (e.g., "Condemn Invasion," "Enforce Sanctions"). A Security Council veto is a powerful diplomatic weapon.
*   **Treaties:** Agents can negotiate treaties for trade, research-sharing, or non-aggression. Secret treaties can exist, which if revealed by espionage, can cause major diplomatic incidents.

### 4.6. Informational Conflict
*   **Narrative Warfare:** The Propagandist agent can create and spread narratives (e.g., "Our war is a just liberation," "Their leader is a warmonger"). The success of a narrative is tracked globally.
*   **Disinformation:** Launch deepfake scandals to discredit leaders, use social media bots to amplify divisive issues, and sow confusion. The goal is to reduce an opponent's `social_cohesion_index` and `national_morale`.

---

## 5. Victory & Defeat Conditions

There is no single "World Conquest" victory. Each nation's Strategist AI pursues a set of dynamic goals based on its ideology and starting position.

*   **Victory Points (VPs):** VPs are awarded for achieving strategic goals, such as:
    *   **Hegemony:** Becoming the undisputed dominant power in a geographic region.
    *   **Economic Dominance:** Achieving the highest GDP and controlling key global trade routes.
    *   **Technological Supremacy:** Leading the world in key tech sectors.
    *   **Ideological Expansion:** Having a majority of nations adopt a similar government type or join your alliance bloc.
    *   **Survival:** For small nations, simply surviving and maintaining sovereignty is a victory.
*   **Game End Triggers:** The game session can end when:
    *   A pre-set time limit is reached (e.g., 50 years).
    *   A major bloc has achieved a dominant VP lead.
    *   A global nuclear exchange (MAD) occurs.
*   **Defeat Conditions (per-nation):**
    *   **Government Collapse:** Social and political stability fall to zero, leading to revolution or civil war.
    *   **Annexation:** The nation is conquered and absorbed by another.
    *   **Economic Ruin:** Hyperinflation and debt lead to a complete breakdown of the state.

---

## 6. Player Rating System

For the future human-player phase, a multi-dimensional ELO-like system will be used.

*   **Overall GELO (Geopolitical ELO):** The primary rating.
*   **Dimensional Ratings:**
    *   **Military Rating (M-ELO):** Measures success in conventional and unconventional warfare.
    *   **Economic Rating (E-ELO):** Measures ability to grow the economy and wield economic power.
    *   **Diplomatic Rating (D-ELO):** Measures skill in forming alliances and influencing global opinion.
    *   **Social Stability Rating (S-ELO):** Measures ability to maintain high morale and internal cohesion.

This system allows for different playstyles to be recognized. A player might be a "Diplomatic Master" with a high D-ELO but an average M-ELO.

---

## 7. Real-Time Model

*   **Time Progression:** The game runs in real-time with a configurable speed factor (from 1x to 1000x). A "tick" represents a discrete time step (e.g., 24 hours) where agent decisions are processed.
*   **Decision Latency:** Actions are not instantaneous. An agent's decision to "build a factory" might take several ticks to debate and approve, and the construction itself will take many more ticks. This simulates bureaucratic delay and long-term planning.
*   **Event System:** An event bus will manage discrete occurrences (e.g., battles, treaty signings, random events) that are pushed to the game state and agent perception systems.

---

## 8. Agent Architecture

Each nation is controlled by a team of six specialized Large Language Model (LLM) agents.

*   **The Strategist (Head of State):** The master agent. Sets long-term national goals and priorities. Has the final say in resolving inter-agent disputes.
*   **The General (Minister of Defense):** Manages all military operations, unit composition, and strategic deployment. Proposes military actions.
*   **The Economist (Minister of Finance/Treasury):** Manages the national economy, budget, trade, and industrial policy.
*   **The Diplomat (Minister of Foreign Affairs):** Manages all diplomatic relations, treaties, alliances, and UN interactions.
*   **The Spymaster (Director of National Intelligence):** Manages all covert operations, including espionage (offensive) and counter-intelligence (defensive), and cyber warfare.
*   **The Propagandist (Minister of Information/Culture):** Manages public morale, media control, and informational warfare.

**Human Override:** In player-controlled mode, the human player takes on the role of the Strategist, able to review agent suggestions, issue direct orders, and set national policy. The AI agents then become advisors, executing the player's grand strategy.

---

## 9. Random Events

To ensure dynamism and unpredictability, the simulation will include a wide range of random events.

*   **Natural Disasters:** Earthquakes, tsunamis, pandemics. These damage infrastructure, reduce population, and negatively impact the economy of the affected region.
*   **Political Events:** Assassinations of leaders, major corruption scandals, discovery of secret treaties.
*   **Economic Events:** Stock market crashes, unexpected resource discoveries (e.g., a massive new oil field).
*   **Technological Breakthroughs:** A nation might randomly achieve a breakthrough in AI, fusion power, or materials science, giving it a significant temporary advantage.

---

## 10. Balancing

Balancing a game with this level of asymmetry is paramount.

*   **Asymmetric Advantages:** Smaller nations can't compete with the US or China conventionally. They must rely on asymmetric strategies:
    *   **Guerrilla Warfare:** Non-state actors and smaller nations can inflict high `war_weariness` on larger occupying powers.
    *   **Cyber & Info Warfare:** A small, tech-savvy nation can cause significant disruption to a larger, more complex rival.
    *   **Diplomatic Bloc-Building:** Small nations can form powerful coalitions to counter the influence of superpowers.
*   **Internal Collapse:** The primary balancing mechanism. A superpower engaged in multiple foreign wars will see its `national_morale` and `economic_stability` plummet. The biggest threat to a superpower is often itself.
*   **Soft Power:** Cultural influence and a positive global image (`soft_power_index`) can be more effective than military might in building alliances and winning support.

---

## 11. Spectator Experience

The UI will be designed to make the complex simulation legible and engaging for viewers.

*   **Main View:** An interactive 3D globe with multiple data overlays (e.g., diplomatic relations, trade flows, conflict zones, sphere of influence).
*   **News Feed Ticker:** A real-time log of major global events, from battle results to UN votes to economic reports.
*   **Nation View:** Ability to "follow" a specific nation, showing its key stats, current goals, and a high-level summary of its AI agents' internal deliberations.
*   **"Why" Explanations:** When a major AI decision is made (e.g., declaring war), the UI will provide a tooltip with the AI's stated rationale, derived from the agent debate.
*   **Graph Explorer:** An advanced tool for viewers to directly explore the Neo4j graph, visualizing the intricate web of global relationships.

---

## 12. Technical Requirements

*   **Backend:** Python-based, using a multi-agent framework (e.g., LangGraph) to manage LLM interactions. A central server will manage the game loop and database transactions.
*   **Database:** Neo4j Graph Database.
    *   **Schema Concept:**
        *   **Nodes:** `Entity` (with subtypes `Nation` and `NonStateActor`), `City`, `MilitaryUnit`, `InfrastructurePoint`.
        *   **Relationships:** `ALLIED_WITH`, `TRADES_WITH`, `AT_WAR_WITH`, `HAS_BORDER_WITH`, `CONTROLS`, `SPONSORS`.
        *   **Properties:** The >1000 parameters will be stored as properties on the nodes (e.g., `USA.gdp = 25_trillion`).
*   **Frontend:** Web-based UI, likely using React or Vue.js with a library like Deck.gl for 3D globe visualization.
*   **LLMs:** Requires access to powerful foundation models for the agent system. The specific model for each agent role could be fine-tuned for its task.
