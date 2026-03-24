# Gemini Deep Think Review — GWW3 Schema v2 + Architecture

## Role

You are a senior systems architect reviewing the data model, data loading plan, and agent architecture for **Games of World War 3 (GWW3)** — a hyper-realistic geopolitical simulation game with ~195 nations, >1000 parameters per entity, and AI agents as both developers and in-game players.

**Tech stack:** Neo4j (graph DB), Python 3.13, Google ADK (Agent Development Kit), Gemini 2.5 Pro.

## Context

The project started 2026-03-23. An initial prototype loaded 20 nations (G20) with mock data into Neo4j. We've now redesigned the schema to include full data provenance and planned an 8-phase data loading pipeline. We need your deep analysis before implementation.

## Current Neo4j State

```
Nodes: Nation(20), DomesticFaction(20), DataSource(13), NonStateActor(6), 
       Commodity(5), Tick(5), Chokepoint(5), Alliance(4), Event(2), ImportBatch(1)
Relationships: MEMBER_OF(35), TRADES_WITH(30), CONSUMES(28), PRODUCES(23), 
               HAS_FACTION(14), BORDERS(8), PROVENANCE(56), FROM_SOURCE(1)
```

All existing data is tagged `data_confidence: low` or `medium` (mock/estimated).

---

## Documents to Review

Please analyze these documents thoroughly:

### 1. `docs/SCHEMA_V2.md` — Neo4j Graph Schema
The complete data model with all node types, relationship types, constraints, and provenance model.

**Review for:**
- Schema correctness and normalization for a graph DB (not relational thinking)
- Are there missing node types or relationships critical for a geopolitical simulation?
- Property explosion risk on Nation nodes (30+ properties) — should some be sub-nodes?
- Is the Provenance model (DataSource → ImportBatch → entity) sound?
- Are the constraints sufficient? Missing indexes for query performance?
- The 6 open questions at the bottom need your recommendation

### 2. `docs/DATA_LOADING_PLAN.md` — 8-Phase Data Pipeline
How we plan to fill the database with real data from 13+ external sources.

**Review for:**
- Is the phasing order correct? Are there hidden dependencies?
- Are the data sources appropriate? Missing critical sources?
- Is the "one source per property domain" principle sound, or do we need multi-source reconciliation?
- Data quality targets (95%/85%/60% completeness by tier) — realistic?
- Missing data strategy: is flagging as `null` better than imputation for a game?
- Should we load historical time series (5-10 years) or just latest?

### 3. `docs/AGENT_ARCHITECTURE_V2.md` — Resilient ADK Agent Loop
How agents coordinate, handle errors, and continuously improve.

**Review for:**
- Is the Task Queue in Neo4j a good idea, or should we use a proper job queue?
- Is the error recovery strategy complete? Missing failure modes?
- Agent specialization (Sentinel=ETL, Archon=engineering, Inanna=review) — right split?
- The continuous improvement loop (Load→Validate→Cross-Check→Deep Review→Fix) — practical?
- ADK-specific concerns: is this architecture compatible with Google ADK patterns?
- Should agents use LLM reasoning for data import, or is deterministic ETL code better?

### 4. `docs/DESIGN_v0.2.md` — Game Design Document
The consolidated game design (mechanics, time model, economics, combat).

**Review for:**
- Does the schema support all game mechanics described here?
- Any game mechanics that would require schema changes?

### 5. `docs/DATA_SOURCES_CATALOG.md` — Available Data Sources
Catalog of 30+ data sources identified during research.

**Review for:**
- Are we using the best available sources per domain?
- Any sources we should add or replace?

### 6. `src/gww3/engine/pulse.py` — Pulse Engine (Time Architecture)
The multi-resolution tick system (1 tick = 1 minute, economic ticks monthly).

**Review for:**
- Does the temporal model in SCHEMA_V2 align with the Pulse Engine?
- Any conflicts between the STATE_AT relationship design and the engine's expectations?

### 7. `src/gww3/db/schema.py` — Current Schema Code
The existing Cypher schema from the prototype.

**Review for:**
- Gaps between this code and SCHEMA_V2.md

---

## Specific Questions Requiring Recommendations

1. **EU as Nation?** Currently `(:Nation {iso3: "EUR"})`. Should it be `(:Supranational)` with different semantics? It has GDP/population but no military of its own.

2. **Property sub-nodes:** Should `Nation` be decomposed into `(:EconomicProfile)`, `(:MilitaryProfile)`, `(:GovernanceProfile)` linked via relationships? Trade-off: cleaner schema vs. query complexity.

3. **Temporal granularity:** Monthly `STATE_AT` for all properties, or different frequencies? GDP/trade = annual or monthly? Morale/war_weariness = weekly or per-event?

4. **Derived data formulas:** When an agent computes `stability_index` from V-Dem sub-indices, should the derivation formula (e.g., `0.3*polyarchy + 0.3*corruption + 0.4*state_capacity`) be stored in the `ImportBatch`?

5. **Historical data depth:** 1 year (current only), 5 years (trend), or 10+ years (deep analysis)? Impact on DB size and import complexity.

6. **ADK vs. plain Python for ETL:** Should Sentinel use LLM reasoning to handle API quirks, or should each importer be deterministic Python code with LLM only as fallback?

7. **Task queue scaling:** Neo4j Task nodes work for ~100 tasks. If we hit 1000+ tasks (e.g., per-country granularity), should we switch to Redis/Celery?

8. **Game balance:** With real data, power asymmetry is extreme (USA GDP = 73× South Africa). How should the game handle this without making small nations unplayable?

9. **Missing data for small nations:** ~50 nations will have <50% data coverage. Better to: (a) impute from regional averages, (b) use LLM estimation with low confidence tag, (c) leave null and handle in game engine, or (d) exclude from initial release?

10. **Error cascade risk:** If Sentinel loads bad GDP data, it propagates into trade calculations, military spending ratios, etc. How do we prevent error cascades in the improvement loop?

---

## Output Format

Please structure your response as:

### Executive Summary
2-3 paragraph overview of strengths, weaknesses, and critical risks.

### Schema Review
- Issues found (critical / major / minor)
- Recommended changes
- Missing elements

### Data Loading Plan Review
- Phase order assessment
- Source quality assessment  
- Missing steps or sources

### Agent Architecture Review
- Architectural fitness
- Risk assessment
- Recommended changes

### Answers to Specific Questions
Numbered 1-10, with clear recommendation and reasoning.

### Priority Action Items
Ordered list of what to fix/change before starting implementation.
