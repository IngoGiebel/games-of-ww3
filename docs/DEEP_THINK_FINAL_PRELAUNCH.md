# Gemini Deep Think — Final Pre-Launch Review

## Role

You are a senior systems architect performing the **final go/no-go review** before launching the GWW3 multi-agent data pipeline. This is the third Deep Think review — the previous two identified and resolved critical issues. Your job is to find anything remaining that would cause the pipeline to fail during Phase 1 execution.

**Be harsh. If something will break at runtime, say so. If it's fine, say GO.**

## What Has Been Built

A multi-agent system that populates a Neo4j graph database with real-world geopolitical data for ~195 nations. The system has been through two rounds of Deep Think review. All identified issues have been resolved.

### Completed & Tested
- ✅ Neo4j schema v2.1 (19 Nations, 5 Alliances, 13 DataSources, provenance model)
- ✅ 38 Python tests passing (normalization, validation bounds, imputation, pulse engine)
- ✅ Phase 0 infrastructure: `normalization.py`, `imputation.py`, `validation_bounds.py`
- ✅ Warden code review gate: `warden.py` (JSON output, mutex, context injection, caching)
- ✅ Watchdog daemon: `watchdog.py` (zombie detection, auto-requeue, status reporting)
- ✅ EU reclassified from Nation to Alliance (supranational) — prevents double-counting
- ✅ Atomic task claiming in Neo4j (no race conditions)
- ✅ Composite index on Task(status, assigned_to)

### Agent Team
| Agent | Model | Role | Status |
|-------|-------|------|--------|
| Dione | Claude Opus | Orchestrator | Running (OpenClaw main session) |
| Sentinel | Gemini 2.5 Pro | ETL data loading | Ready to start |
| Archon | Gemini 2.5 Pro | Engineering, derived data | Ready to start |
| Warden | Codex 5.4 / GPT-5.3 | Code review gate | Implemented, stateless |
| Watchdog | Plain Python | Process supervision | Implemented, cron-ready |
| Inanna | Claude Opus | Military domain review | On-demand via OpenClaw |
| Herald | Gemini 2.5 Pro | Community posts | On-demand |

## Documents to Review

Review these for any remaining issues that would cause runtime failures:

### 1. `docs/AGENT_ORCHESTRATION.md` — Master Plan
The complete orchestration design with all safeguards from reviews #1 and #2.

### 2. `docs/AGENT_ARCHITECTURE_V2.md` — Technical Implementation
Agent loop, Warden integration, ETL standard, memory management.

### 3. `docs/SCHEMA_V2.md` — Neo4j Schema v2.1
All node types, relationships, constraints, design decisions.

### 4. `docs/DATA_LOADING_PLAN.md` — Phase Execution Plan
8 phases, data sources, agent assignments, quality targets.

### 5. `src/gww3/agents/warden.py` — Warden Implementation
The actual code for the code review gate.

### 6. `src/gww3/agents/watchdog.py` — Watchdog Implementation
The actual code for the process supervisor daemon.

### 7. `src/gww3/data/normalization.py` — Normalization Registry
Property specifications, unit conversions, source mappings.

### 8. `src/gww3/data/validation_bounds.py` — Sanity Bounds
Hard invariants and cross-property checks.

### 9. `src/gww3/data/imputation.py` — Imputation Logic
Missing data handling hierarchy.

### 10. `src/gww3/db/schema.py` — Schema Code
The actual Cypher constraints and indexes.

---

## Specific Review Focus

### A. Runtime Failure Modes
For each component, answer: **What will go wrong when we actually run this?**

1. Sentinel starts, claims Phase 1.1 task, generates a CIA Factbook ETL script.
   - Will `codex exec` actually work with `--approval-mode full-auto` and stdin piping?
   - Will the JSON output parsing handle real-world Codex responses reliably?
   - What happens if Codex is down?

2. The generated script calls the World Bank API for 195 nations × 10 years × 11 indicators.
   - Will the API handle this volume? Rate limits?
   - Will the script correctly MERGE 195 Nation nodes without duplicating existing G20 data?

3. Watchdog runs every 5 minutes and finds a zombie task.
   - Will the rollback Cypher correctly clean up partial ImportBatches?
   - What if the zombie task actually IS still running (just slow)?

### B. Integration Gaps
4. The `agents/` directory has old agent stubs (`agents/archon/agent.py`, `agents/sentinel/agent.py`) from v1 AND new code in `src/gww3/agents/`. Is this confusing? Should old stubs be removed?

5. `normalization.py` has a `WORLDBANK_INDICATOR_MAP` but no corresponding `SIPRI_FIELD_MAP` or `VDEM_FIELD_MAP`. Will Sentinel scripts know how to map source fields to our properties?

6. `warden.py` uses `codex exec` with `-` for stdin. Does Codex CLI actually support reading prompts from stdin?

### C. Missing Pieces
7. There are no Task nodes in Neo4j yet. Who creates them and when?
8. There is no `AGENTS.md` in the project root that tells Sentinel/Archon how to behave (the current `AGENTS.md` is generic). Should there be agent-specific instruction files?
9. Pyproject.toml — does it include all required dependencies (neo4j, pandas, requests, filelock)?

### D. Scale & Performance
10. 195 nations × 10 years × ~30 properties = ~58,500 data points. Plus STATE_AT relationships for historical snapshots. How many Neo4j nodes/edges will this create? Will a local Neo4j on a ThinkPad X1 (32GB RAM) handle this?

---

## Output Format

### Verdict
One of:
- **GO** — No blocking issues found. Launch Phase 1.
- **CONDITIONAL GO** — Minor issues that can be fixed during execution.
- **NO-GO** — Blocking issues that must be fixed before launch.

### Blocking Issues (if any)
Numbered list with specific fix instructions.

### Warnings (non-blocking)
Things to watch for during execution.

### Missing Pieces
Things that need to exist before Phase 1 tasks are created.

### Recommendations
Improvements to make after Phase 1 completes.
