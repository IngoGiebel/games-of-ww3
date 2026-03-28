# Gemini Deep Think Prompt — Final Verification Before Sprint 3

## Context

This is the **third and final review pass** before we begin Sprint 3 implementation. You provided two rounds of critical feedback:

1. **Initial Review:** Identified Hot/Cold separation, confidence decomposition, epistemic jump paradox, ETL sequence bug, anti-brigading, and missing bias classes.
2. **Verification Pass:** Found 6 concrete issues — ETL Re-Derive step missing, Belief Subgraph premature, dual-number trap in confidence propagation, naming contradictions, friction type gap, and penalty stacking guidance missing.

We have now applied all fixes. This pass is a **final consistency check** across the complete document suite before implementation begins.

## Documents (5 core + 1 sprint plan)

1. **DATA_MODEL_COMPLETE.md** — Consolidated schema (v3, Hot/Cold, 14 bias classes, 20 design decisions, 10 open questions with status)
2. **BIAS_FRAMEWORK.md** — Full bias framework (14 classes, 54 sources, corrected ETL pipeline with Re-Derive step, Penalty Stacking Rubric, Hot/Cold Cypher examples, CONVERGE-based mid-game corrections)
3. **RULE_ENGINE_CONCEPT.md** — GSL specification (v4: friction→Ratio, explicit c propagation, no auto dual-number, CONVERGE for epistemic revisions)
4. **DEEP_THINK_VERIFICATION_REVIEW.md** — Summary of all fixes applied from your verification pass
5. **DESIGN_v0.2.md** — Master design document (entity model, conflict systems, agent architecture, scoring)
6. **SPRINTS.md** — Sprint plan (Sprint 3: data model + bias infra; Sprint 4: GSL; Sprint 5+: agents/UI)

## Your Task

### 1. Cross-Document Consistency Audit

Read all 5 core documents end-to-end. Flag ANY:
- Contradictions between documents (e.g., a Cypher pattern in one doc that conflicts with schema definitions in another)
- Stale references (e.g., naming conventions not yet updated, references to removed features)
- Implicit assumptions in one document that contradict explicit decisions in another

Specifically check:
- Does DESIGN_v0.2.md's entity model (Section 4) still align with DATA_MODEL_COMPLETE.md's schema?
- Does DESIGN_v0.2.md's conflict systems (Section 5) reference any properties or relationships not in the schema?
- Does RULE_ENGINE_CONCEPT.md's example rules use property names consistent with the schema?
- Are all `{prop}_c` references consistent (no remaining `_confidence` suffixes)?

### 2. Schema Completeness for Sprint 3

Sprint 3 will implement this schema in Neo4j. Check:
- Are all node types fully specified with all required properties and their types?
- Are all relationship types fully specified with their properties?
- Are all constraints and indexes listed?
- Is the `:Correction` node complete (with `valid_from_tick`, `valid_until_tick`)?
- Is `bias_overrides.json` adequately specified — what exact format should it have?

### 3. ETL Pipeline Completeness

The corrected pipeline is:
```
Import → Normalize → Bias Tag → Correction Overlay → Re-Derive → Validate → Neo4j → Audit
```

Check:
- Is the Re-Derive step fully specified? Which derived metrics need recalculation? (We need an explicit list.)
- What happens when a correction changes a value that feeds into a TRADES edge `friction` calculation? Does Re-Derive cover inter-entity relationships, or only intra-entity properties?
- How does the historical Cypher batch correction (`MATCH ... WHERE t.id <= 0 SET ...`) interact with Re-Derive? If we batch-correct historical STATE_AT directly in Neo4j, the derived metrics in those historical snapshots are NOT re-derived. Is this acceptable?

### 4. GSL ↔ Schema Interface Contract

When Sprint 4 builds the GSL engine, it will query Neo4j. Check:
- Is the exact Cypher query pattern for reading STATE_AT (with `{prop}_c` fields) documented?
- When a GSL rule does `MATCH (A:Nation)─[:TRADES {volume: v, friction: f}]→(B:Nation)`, do TRADES edges have a `friction_c` confidence field, or is confidence only on STATE_AT?
- Should relationship properties (TRADES.volume, BORDERS.length_km) also carry `{prop}_c` fields?

### 5. Risk Assessment

Before Sprint 3 kicks off, identify:
- The top 3 implementation risks (what's most likely to go wrong?)
- Any design decisions that are "load-bearing" — if wrong, they cascade into expensive refactors
- Whether the `bias_overrides.json` MVP approach has any hidden traps

### 6. Final Verdict

Is this document suite ready for implementation? Give one of:
- ✅ **GREEN:** Proceed to Sprint 3. No blocking issues.
- ⚠️ **YELLOW:** Proceed with caution. Minor issues to fix during implementation.
- ❌ **RED:** Stop. Critical issue found that must be resolved before coding begins.

## Deliverable Format

For each section, provide:
- Concrete findings (with document name + section reference)
- Severity (🟢 fine / 🟡 minor / 🔴 blocking)
- Fix recommendation (if applicable)

Be thorough. This is the last review gate before code.
