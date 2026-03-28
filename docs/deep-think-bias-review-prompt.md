# Gemini Deep Think Prompt — Bias-Aware Data Model Review

## Context

You are reviewing the data model for **Games of World War 3 (GWW3)** — a hyper-realistic, real-time geopolitical simulation where AI agents control ~195 nations with >1000 parameters each, stored in a Neo4j graph database.

The project has two key technical documents:

1. **DATA_MODEL_COMPLETE.md** — The full Neo4j graph schema including all node types (Nation, Commodity, Alliance, NonStateActor, DomesticFaction, Chokepoint, Conflict), all relationship types, temporal model, provenance tracking, AND the newly added bias/correction infrastructure (BiasReport, Correction, CounterSource nodes and relationships).

2. **BIAS_FRAMEWORK.md** — The full Data Bias Framework: a taxonomy of 11 bias classes, 54 critical academic sources, source-level bias analyses (ACLED, Freedom House, V-Dem, China population, World Bank GDP), correction types, the correction workflow pipeline, the "Objectification Codex" (7 axioms for unbiased assessment), and the GSL (rule language) integration via confidence parameters.

The game uses **GSL (GWW3 Symbolic Logic)** — a custom probabilistic rule language where every effect carries a Truth Value `⟨probability, confidence⟩`. The confidence parameter directly connects to bias detection: low-confidence data produces noisier outcomes through mean-preserving variance widening. See RULE_ENGINE_CONCEPT.md for the full GSL specification.

## Your Task

Perform a deep, critical analysis of the data model + bias framework integration. Focus on:

### A. Schema Architecture & Bias Integration

1. **Suffix convention scalability:** The bias metadata uses `{property}_source`, `{property}_confidence`, `{property}_bias_class` suffixes on STATE_AT relationships. With 100+ properties per Nation and bias metadata per property, STATE_AT could have 300-500 keys. Analyze: Is this performant in Neo4j? At what key count does performance degrade? Should bias metadata move to separate `:BiasAnnotation` nodes linked per (entity, property, tick)? What are the query-pattern trade-offs?

2. **Dual-layer data architecture:** Raw imports are preserved alongside corrected values. Analyze the implications for: (a) storage growth over 10+ game-years, (b) query complexity (which value does a rule engine query return by default?), (c) rollback scenarios (if a correction is reverted, does the game state need recalculation?).

3. **Counter-source integration:** CounterSource nodes supplement DataSource nodes. How should conflicting data from counter-sources be reconciled in the game engine? Should the engine support multiple "world views" (e.g., a Western-data world vs. a counter-hegemonic-data world)?

### B. Confidence ↔ Bias ↔ GSL Linkage

4. **Confidence conflation problem:** The GSL confidence parameter `c` currently serves double duty: (a) data quality uncertainty (source reliability) and (b) epistemic uncertainty (structural unknowability). These are different. A value can be from a reliable source but about an inherently uncertain quantity (e.g., exact Chinese population), or from an unreliable source about a precisely measurable quantity (e.g., a country's GDP self-report). Should `c` be decomposed into `c_source` and `c_epistemic`? If so, how do they combine in the variance-widening formula?

5. **Bias propagation through derived metrics:** Many game parameters are derived from multiple source values (e.g., `military_power = f(spending, manpower, tech, morale)`). If one input has low confidence due to bias, how should that propagate to the derived metric's confidence? Is it the minimum, the weighted average, or something else?

6. **Entity Belief Subgraph interaction:** GWW3 has a Belief Subgraph where agents act on what they *think* is true, not ground truth. How should bias-corrected data interact with the Belief Subgraph? Should agent beliefs be initialized from raw (biased) data reflecting each entity's self-perspective, while the "ground truth" game engine uses corrected values?

### C. Bias Taxonomy Completeness

7. **Missing bias classes:** The current taxonomy has 11 classes. Identify any significant bias types not covered. Consider: survivorship bias in historical conflict data, selection bias in which events get coded, linguistic bias (most datasets English-centric), urban-rural reporting asymmetry, conflict-zone access bias, gender bias in political data, and economic model bias (GDP as welfare proxy).

8. **Bias interaction effects:** Some biases compound. ACLED's media sourcing bias (undercounting in zones with low press freedom) interacts with Freedom House's press_freedom score (which itself has funding_dependency bias). How should the framework handle bias chains / cascading biases?

### D. Correction Governance

9. **Voting mechanism design:** BiasReports and Corrections are voted on by the community. Analyze: Who should vote? (Only human players? AI agents too?) How to prevent capture by organized blocs? Should different bias classes require different approval thresholds? Is there a risk that corrections themselves become politically biased?

10. **Temporal stability of corrections:** If the community votes to correct China's population mid-game, all historical STATE_AT snapshots and derived metrics would need retroactive adjustment. How should corrections be applied temporally? Only forward from the correction tick? Retroactively?

### E. Practical Implementation

11. **ETL pipeline changes:** The current data pipeline is: Raw Sources → Downloaders → Normalizers → Validators → Game-Ready JSON. How should the bias-tagging and correction steps integrate? Before or after validation? Before or after normalization?

12. **Performance budget:** The game runs at 1 tick per minute with 195 nations and ~100 active rules. The bias metadata adds query overhead (loading confidence per property per rule evaluation). Estimate the performance impact and propose mitigation strategies.

13. **Minimum viable bias infrastructure:** Given that GWW3 is pre-Sprint 3 (rules engine not yet built), what is the minimum bias infrastructure needed NOW versus what can be deferred? Propose a phased implementation.

## Deliverable

Provide a structured analysis with:
- Concrete recommendations (not just "consider this")
- Specific Neo4j Cypher examples where relevant
- Mathematical formulations for confidence decomposition (if recommending it)
- A prioritized action list (what to build first)
- Identification of risks / failure modes

Be rigorous. Challenge our assumptions. We want sharp, critical feedback — not validation.
