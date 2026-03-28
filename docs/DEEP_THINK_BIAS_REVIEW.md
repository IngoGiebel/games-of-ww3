# Gemini Deep Think Review — Bias-Aware Data Model (2026-03-28)

*Reviewer: Gemini Deep Think (gemini-2.5-pro)*
*Documents reviewed: DATA_MODEL_COMPLETE.md, BIAS_FRAMEWORK.md, RULE_ENGINE_CONCEPT.md*
*Status: Accepted — recommendations integrated into Sprint 3 plan*

---

## Executive Summary

> "You are effectively building an operationalized epistemology engine."

The framework is intellectually rigorous but risks crippling I/O bottlenecks, determinism-shattering state paradoxes, and vulnerability to geopolitical brigading if implemented as drafted. Core recommendation: **strict Hot-Path / Cold-Path separation.**

---

## A. Schema Architecture & Bias Integration

### A1. Suffix Convention Scalability — CRITICAL RISK ⚠️

**Problem:** 100+ properties × 4 bias suffixes = ~500 keys on STATE_AT. Neo4j serializes entire relationship property blocks — reading `gdp_nominal` forces loading hundreds of irrelevant text properties.

**Decision: Hot/Cold Separation**

```cypher
// HOT PATH — GSL Evaluator (floats only, cache-friendly)
(N:Nation)-[:STATE_AT {
    population: 1310000000,
    population_c: 0.55,          // confidence scalar only
    gdp_nominal: 17700000000000,
    gdp_nominal_c: 0.85,
    // ... only value + confidence pairs
}]->(T:Tick)

// COLD PATH — UI, agents, audits (text-heavy, on-demand)
(N:Nation)-[:HAS_CORRECTION]->(C:Correction {
    property: "population",
    raw_value: 1412000000,
    source: "UN_WPP_2024",
    bias_classes: ["demographic_manipulation"],
    ...
})
```

**Implication:** STATE_AT carries ~200 keys (100 values + 100 confidence floats) instead of ~500. All textual bias metadata lives on Correction nodes.

### A2. Dual-Layer & Temporal Rollbacks

**Decision: Forward-Only Immutability**

Historical STATE_AT snapshots are immutable. Mid-game bias corrections generate an `(:Event {type: "epistemic_revision"})` that applies a delta to the *current* tick. The past remains what the world believed at that time. Retroactive corrections only valid in ETL pipeline before Tick 0.

### A3. Counter-Source Integration

**Decision: Bipartite Physics/Cognitive Boundary**

- **Physics Layer (GSL):** Always uses community-corrected values from STATE_AT
- **Cognitive Layer (Belief Subgraph):** AI agents query `:SELF_REPORTS` / `:BELIEVES`. If China believes its population is 1.41B, its economic planning AI acts on that — leading to resource misallocation (modeling real-world consequences of believing manipulated data)

---

## B. Confidence ↔ Bias ↔ GSL Linkage

### B4. Confidence Decomposition

**Decision: Decompose into σ_epistemic + c_source**

- `σ_epistemic` (intrinsic volatility): Authored by GSL rule designer in base distribution
- `c_source` (source reliability): From Bias Framework, stored as `{prop}_c` in DB

**Math:** GSL v3 formula works as-is:
```
σ_eff = σ_epistemic × (1 + K × (1 − c_source))
```
Perfect source (c=1) → natural variance. Biased source (c=0.5) → doubled variance. The engine only reads `c_source` from the database.

### B5. Bias Propagation Through Derived Metrics

**Decision: Weakest Link (Minimax)**

```python
c_derived = min(c_input1, c_input2, ...)
```

If `combat_power = f(troops[c=0.9], morale[c=0.4])`, then `c_combat_power = 0.4`. A precise weapon count + phantom morale = phantom combat power.

---

## C. Bias Taxonomy Extension

### C7. Three Additional Bias Classes

| # | Class | Description |
|---|-------|-------------|
| 12 | `access_constraint` | Conflict zones physically too dangerous for reporters; events systematically undercounted vs. safe regions |
| 13 | `linguistic_exclusion` | NLP models underperform on Pashto, Amharic, regional Chinese → systematic mischaracterization |
| 14 | `proxy_fallacy` | GDP as welfare proxy erases informal economy and counts disaster cleanup as "growth" |

### C8. Bias Cascading

**Decision: No dynamic cascade computation.** Treat taxonomy as documentation. Human/community authors evaluate overlap and assign a single flat `c_source` penalty on the Correction node. Dynamic bias multiplication is computationally expensive and statistically fragile.

---

## D. Correction Governance

### D9. Anti-Brigading Mechanism

**Decision: Epistemic Meritocracy (Proof-of-Stake)**

- Votes are NOT 1-to-1 — voting power scales with historical alignment to accepted peer-reviewed CounterSource nodes
- Corrections require a valid CounterSource to reach voting stage
- **Ontological Veto:** Product Owner (Ingo) retains hard override for foundational realities

### D10. Temporal Stability

**Decision: Forward-only.** See A2 above. No retroactive recalculation.

---

## E. Implementation

### E11. ETL Pipeline

```
Raw Sources → Normalizers → BIAS TAGGER (inject c_source) → CORRECTION OVERLAY → Validators → Neo4j
```

Bias tagging intercepts AFTER normalization, BEFORE validation. This prevents corrected values from triggering sanity-check false positives.

### E12. Performance Budget

With Hot/Cold separation, STATE_AT carries only floats (~200 keys). At 195 nations × ~100 rules, this is well within Neo4j's sub-second read performance per tick.

### E13. Sprint 3 MVP (4 Tasks)

| # | Task | Description |
|---|------|-------------|
| 1 | **Schema Refactor (Lean Edge)** | Strip bias strings from STATE_AT. Add only `{prop}_c` float fields. |
| 2 | **Hardcoded Override File** | `bias_overrides.json` in Git. Top 5 critical corrections (China Pop, ACLED, V-Dem, FH, WB). Bypass voting UI. |
| 3 | **ETL Injection** | Wire pipeline to read override JSON, apply corrections before Neo4j push. |
| 4 | **GSL Math Integration** | Python DistCall evaluator reads `{prop}_c` and applies mean-preserving variance widening. |

---

## F. Key Risk

> "Allowing epistemological debate to suffocate the physics engine."

The game physics simulate the *result* of the epistemology — they do not evaluate the epistemology itself. Keep debate asynchronous (Moltbook/ETL). Keep the live execution graph fiercely lean.

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2026-03-28 | Gemini Deep Think | Initial review |
| 2026-03-28 | Dione + Ingo | Accepted; integrated into Sprint 3 plan |
