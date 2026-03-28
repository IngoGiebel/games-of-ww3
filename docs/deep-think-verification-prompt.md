# Gemini Deep Think Prompt — Verification of Bias Integration Changes

## Context

You previously reviewed the GWW3 Data Model + Bias Framework and provided critical recommendations (see DEEP_THINK_BIAS_REVIEW.md). We have now integrated your recommendations into the codebase. This is a **verification pass** — confirm the changes are correctly implemented, identify any gaps or misinterpretations, and flag anything we missed.

## Documents to Review

1. **DATA_MODEL_COMPLETE.md** — The consolidated data model, now updated with:
   - Hot/Cold separation (Section 3.8)
   - 14 bias classes (Section 4, up from 11)
   - 20 design decisions (Section 9, up from 14)
   - 10 open questions with resolution status (Section 10)

2. **BIAS_FRAMEWORK.md** — Updated with 3 new bias classes (access_constraint, linguistic_exclusion, proxy_fallacy)

3. **DEEP_THINK_BIAS_REVIEW.md** — Our documentation of your recommendations and how we interpreted them

4. **SPRINTS.md** — Restructured sprint plan:
   - Sprint 3: Complete data model + bias infrastructure + data gaps
   - Sprint 4: Rules Engine (GSL)
   - Sprint 5+: AI agents, Belief Subgraph, Web UI

5. **RULE_ENGINE_CONCEPT.md** — GSL specification (unchanged, for reference)

## Your Task

### 1. Verify Hot/Cold Implementation

We split STATE_AT into:
- **Hot Path:** `{prop}: value, {prop}_c: float` (only numerics, ~200 keys)
- **Cold Path:** `:Correction` nodes with all textual metadata, linked via `[:HAS_CORRECTION]`

**Check:**
- Is `[:HAS_CORRECTION]` the right relationship name and direction? Should it go `(Nation)-[:HAS_CORRECTION]->(Correction)` or through the Tick for temporal scoping?
- How does the Cold Path handle corrections that apply to different time periods? A Correction for China's population applies to ALL historical ticks, not just one.
- When the GSL evaluator reads `population_c: 0.55`, it doesn't know *why* confidence is low. Is this information loss acceptable, or should there be a lightweight enum (e.g., `population_c_class: 2` mapping to bias class) on the Hot Path?

### 2. Verify Confidence Decomposition

We implemented:
```
σ_eff = σ_epistemic × (1 + K × (1 − c_source))
```
where `σ_epistemic` is rule-authored and `c_source` comes from `{prop}_c` in the DB.

**Check:**
- For Beta distributions: `α_eff = c × α, β_eff = c × β`. Is `c` here `c_source` only, or should it also incorporate the rule author's epistemic assessment?
- The weakest-link propagation `c_derived = min(c_inputs)` is conservative. In a rule like `combat_power = troops × morale × terrain × supply`, if `terrain_c = 0.95` (very reliable) and `morale_c = 0.4` (very unreliable), the entire combat_power gets `c = 0.4`. This might be too aggressive — terrain data shouldn't be penalized by morale uncertainty. Should we use a weighted approach or is min() correct?

### 3. Verify Sprint 3 Scope

Sprint 3 now includes:
- Schema refactor (Hot/Cold)
- `bias_overrides.json` (hardcoded top 5 corrections)
- ETL pipeline: Normalizers → Bias Tagger → Correction Overlay → Validators → Neo4j
- Data gap closure (SIPRI MILEX consolidation, TRADES expansion, V-Dem historical)
- Belief Subgraph foundation (SELF_REPORTS, BELIEVES relationships)

**Check:**
- Is Belief Subgraph foundation in Sprint 3 premature? You recommended keeping it for later. Should SELF_REPORTS/BELIEVES be Sprint 5 scope?
- The ETL pipeline change (inject bias AFTER normalization, BEFORE validation) — are there edge cases where a bias correction could produce values that pass validation but are semantically wrong? Example: correcting China's GDP downward by 20% might pass bounds but distort trade ratios that were computed from the raw GDP.
- Is `bias_overrides.json` sufficient as MVP, or do we need at minimum the `:BiasReport` nodes in Neo4j for Sprint 3 (even without voting)?

### 4. Verify Forward-Only Immutability

We decided: historical STATE_AT is never retroactively modified. Mid-game corrections generate `(:Event {type: "epistemic_revision"})` as delta at current tick.

**Check:**
- What about pre-game corrections? If before a game starts, the community corrects China's population, ALL 120 historical STATE_AT snapshots (2016-2025) need the corrected value. Our decision says "retroactive only valid in ETL before Tick 0." But re-running ETL for 120 months × 195 nations is expensive. Is there a smarter approach?
- The epistemic_revision Event: when it fires at Tick 50, does it create a sudden population "jump" of -100M in the game? That could trigger cascade effects (market crash rules, etc.). Should epistemic revisions be smoothed over multiple ticks?

### 5. Verify Bias Taxonomy (14 Classes)

We added your 3 recommendations:
- `access_constraint` — conflict zone undercounting
- `linguistic_exclusion` — NLP language bias
- `proxy_fallacy` — GDP as welfare proxy

**Check:**
- Are there interaction effects between the new classes and existing ones? E.g., `access_constraint` + `media_filter` in Gaza — double-penalizing the same data point?
- Your recommendation was "no dynamic cascade computation — flat c_source per correction." But when a human assigns c_source for a Gaza event, they need to mentally evaluate access_constraint + media_filter + linguistic_exclusion. Should the taxonomy provide guidance formulas (e.g., "if access_constraint AND media_filter both apply, recommended c_source range: 0.30-0.50")?

### 6. Anything We Missed?

Review the full set of changes against your original recommendations. Did we:
- Misinterpret any recommendation?
- Over-implement something you suggested deferring?
- Under-implement something critical?
- Introduce new contradictions between documents?

## Deliverable

Structured verification with:
- ✅ Correctly implemented
- ⚠️ Partially implemented / needs adjustment
- ❌ Misinterpreted or missing
- 💡 New insights from reviewing the integrated changes

Be specific. Cite document sections. If something is wrong, say exactly what to change.
