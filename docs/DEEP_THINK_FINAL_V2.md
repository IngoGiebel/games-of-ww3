# Gemini Deep Think — Final Go/No-Go Review (v2)

## Role

You are a senior systems architect performing the **absolute final review** before launching the GWW3 multi-agent data pipeline. This is the **fourth** Deep Think review. The previous three identified and resolved 15+ critical issues. Your job is to confirm all fixes are correct and find any remaining runtime failures.

**This is a GO/NO-GO gate. Be ruthless. If something will break, say NO-GO with the specific fix. If everything is solid, say GO.**

## What Changed Since Last Review (NO-GO → fixes applied)

The previous review (#3) identified 3 blocking issues + 5 integration gaps. All have been resolved:

### Blocking Fixes Applied
1. **Warden silent error swallowing** → `warden.py` now checks `result.returncode` and `result.stderr` before parsing stdout. Codex CLI failures raise `RuntimeError` instead of burning revision rounds.
2. **Partial write corruption** → `commit_result()` now uses `session.begin_transaction()` for atomic all-or-nothing writes. Crash mid-batch = full Neo4j rollback.
3. **Watchdog rollback data destruction** → Cypher changed from `ENDS WITH t.step` to `ENDS WITH ('-' + t.step)`. No more cross-phase matching.

### Integration Fixes Applied
4. **Module shadowing** → Old `agents/` directory deleted. All code in `src/gww3/agents/`.
5. **Missing source field maps** → `SIPRI_FIELD_MAP`, `VDEM_FIELD_MAP`, `ACLED_FIELD_MAP`, `EIA_FIELD_MAP`, `FAO_FIELD_MAP` added to `normalization.py`. Warden `INTERFACE_CONTEXT` updated to reference them.
6. **Codex CLI stdin** → Changed from stdin pipe to positional argument.
7. **Deterministic task seeding** → `src/scripts/seed_tasks.py` with 30 tasks across 8 phases. MERGE-based, idempotent. No LLM hallucination risk.
9. **Dependency pinning** → `requests>=2.31` and `filelock>=3.13` added to `pyproject.toml`.

### Test Status
- 38/38 Python tests passing
- Git: trunk @ 71cc60e, clean working tree

## Documents to Review (focus on the FIXES)

Please verify each fix is correctly implemented:

### 1. `src/gww3/agents/warden.py` — Warden (FIXED)
- Verify: returncode check is in the right place (after subprocess.run, before stdout parsing)
- Verify: RuntimeError is raised (not swallowed) so the agent loop handles it as transient error
- Verify: JSON parsing fallback is robust
- Verify: FileLock mutex prevents parallel calls
- Verify: Codex exec invocation is correct (positional argument, not stdin)

### 2. `src/gww3/agents/watchdog.py` — Watchdog (FIXED)
- Verify: Rollback Cypher uses `ENDS WITH ('-' + t.step)` — no cross-phase matching
- Verify: Zombie detection threshold (60 min) is reasonable
- Verify: Status file output is useful for Dione

### 3. `src/gww3/data/normalization.py` — Source Maps (FIXED)
- Verify: SIPRI_FIELD_MAP column names match real SIPRI CSV exports
- Verify: VDEM_FIELD_MAP codes match real V-Dem dataset columns
- Verify: ACLED_FIELD_MAP fields match real ACLED API/CSV exports
- Verify: The V-Dem corruption index inversion note is correct (0=clean→0=corrupt)

### 4. `src/scripts/seed_tasks.py` — Task Seeder (NEW)
- Verify: All 30 tasks have correct dependency DAGs (no circular deps, no missing deps)
- Verify: Phase ordering is correct (Phase 1 before 2-7, Phase 8 after all)
- Verify: Task granularity is appropriate (not too coarse, not too fine)
- Verify: MERGE-based seeding is truly idempotent

### 5. `docs/AGENT_ARCHITECTURE_V2.md` — Architecture (UPDATED)
- Verify: `commit_result()` transaction pattern is correct Neo4j Python driver usage
- Verify: The Warden implementation reference is accurate

### 6. `src/gww3/data/validation_bounds.py` — Bounds
### 7. `src/gww3/data/imputation.py` — Imputation
### 8. `src/gww3/db/schema.py` — Schema Code
### 9. `docs/AGENT_ORCHESTRATION.md` — Orchestration
### 10. `docs/DATA_LOADING_PLAN.md` — Phase Plan

Review 6-10 briefly for consistency with the fixes applied above.

---

## Specific Verification Questions

1. **Transaction scope:** The `commit_result()` method creates the ImportBatch AND writes all nation properties in a single transaction. For 195 nations × 10 properties, is a single Neo4j transaction of ~2000 operations safe? Or should it be batched (e.g., 50 nations per transaction)?

2. **Warden prompt length:** The `REVIEW_PROMPT_TEMPLATE` includes `INTERFACE_CONTEXT` (~50 lines of function signatures) + the full script content. For a complex ETL script (~200 lines), the total prompt could be 400+ lines. Will Codex CLI handle this as a single positional argument? Shell argument length limits?

3. **seed_tasks.py dependency graph:** Is there any circular dependency or missing edge? Example: task-P4-01-vdem depends on task-P1-02-id-crosswalk. Is that correct? (V-Dem uses its own country IDs, so the crosswalk must exist first.)

4. **Watchdog vs. slow tasks:** The previous review warned about "split-brain" with tasks legitimately taking >60 minutes (e.g., UN Comtrade pagination). The current code has no mechanism to distinguish "slow but alive" from "zombie." Is 60 minutes the right threshold? Should tasks be able to send heartbeat signals?

5. **First execution path:** When Sentinel starts for the first time and claims task-P1-01-nation-registry, it needs to:
   - Generate a Python script to fetch CIA Factbook data
   - Get it reviewed by Warden
   - Execute it
   - MERGE 195 Nation nodes (some of which already exist from G20 mock data)
   Will the existing 19 G20 nations be correctly updated (not duplicated)?

---

## Output Format

### Verdict
**GO** or **NO-GO** (with specific blocking issues)

### Fix Verification
For each of the 8 fixes: ✅ Correct or ❌ Issue found (with fix)

### Answers to Questions 1-5

### Remaining Risks (non-blocking)
Things to monitor during Phase 1 execution.
