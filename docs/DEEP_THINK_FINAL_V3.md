# Gemini Deep Think — Fix Verification Review (Review #5)

## Role

You are verifying that 4 specific code fixes are correctly implemented. This is a **pure verification review** — not a design review. The architecture has been approved across 4 prior rounds.

**Be precise. For each fix, answer: Is it correct? Will it work at runtime? Any edge cases missed?**

## Fixes to Verify

Review #4 found 4 blocking issues. Here's what was changed:

### Fix 1: Neo4j tx.commit() Removed
**File:** `docs/AGENT_ARCHITECTURE_V2.md` (commit_result method)
**Bug:** Explicit `tx.commit()` inside a `with session.begin_transaction() as tx:` block caused `TransactionError` because the context manager auto-commits on clean exit.
**Fix:** Removed `tx.commit()`. Added comment explaining why.
**Verify:** Is the context manager pattern now correct? Will the transaction auto-commit on clean exit and auto-rollback on exception?

### Fix 2: Watchdog Rescue Logic (was: Provenance Destruction)
**File:** `src/gww3/agents/watchdog.py`
**Bug:** Watchdog deleted ImportBatch + PROVENANCE edges for zombie tasks. But since commits are now atomic (transaction-based), if an ImportBatch exists, the transaction SUCCEEDED — the agent just crashed before marking the task complete. Deleting it orphans data.
**Fix:** Three-way logic:
  - ImportBatch exists → mark task as "completed" (rescue successful work)
  - No ImportBatch + retries left → requeue as "pending"
  - No ImportBatch + max retries exceeded → mark as "blocked"
Also increased `ZOMBIE_THRESHOLD_MINUTES` from 60 to 240 (4 hours).
**Verify:** Is the three-way logic correct? Any edge cases where an ImportBatch could exist but the data is actually corrupt? Is 240 minutes the right threshold?

### Fix 3: ID Crosswalk Dependency
**File:** `src/scripts/seed_tasks.py`
**Bug:** Phase 2-7 data import tasks depended only on `task-P1-01-nation-registry`. External datasets (SIPRI, V-Dem, ACLED, etc.) use their own country IDs and cannot be mapped to our `iso3` primary keys without the crosswalk.
**Fix:** Added `task-P1-02-id-crosswalk` as a dependency to all 13 external data import tasks in Phases 2-7. Tasks that already have transitive coverage (P5-02 via P5-01, P7-02 via P7-01) were left as-is.
**Verify:** Is the dependency DAG now complete? Any tasks that should depend on the crosswalk but don't? Any circular dependencies introduced?

### Fix 4: Split-Brain Ownership Check
**File:** `docs/AGENT_ARCHITECTURE_V2.md` (commit_result method)
**Bug:** If Watchdog requeues a slow task, a second agent can claim it. Both agents finish and commit, causing double-writes.
**Fix:** At the start of the commit transaction, check that the task is still `in_progress` and assigned to this agent. If not, raise `RuntimeError` to abort.
**Verify:** Is the ownership check inside the transaction (so it's atomic with the writes)? Could there still be a TOCTOU race between the check and the writes within the same transaction? Is `RuntimeError` the right exception type for the agent loop to handle?

## Files to Review

| # | File | What to check |
|---|------|---------------|
| 1 | `docs/AGENT_ARCHITECTURE_V2.md` | Fix 1 (tx.commit removed) + Fix 4 (ownership check) |
| 2 | `src/gww3/agents/watchdog.py` | Fix 2 (three-way rescue logic, 240min threshold) |
| 3 | `src/scripts/seed_tasks.py` | Fix 3 (crosswalk deps on all 13 Phase 2-7 tasks) |

Only these 3 files changed. Review them against the fix descriptions above.

## Additional Context (unchanged, for reference only)
| # | File | Purpose |
|---|------|---------|
| 4 | `src/gww3/agents/warden.py` | Warden (verified ✅ in review #4) |
| 5 | `src/gww3/data/normalization.py` | Source maps (verified ✅ in review #4) |
| 6 | `src/gww3/db/schema.py` | Schema constraints |

## Output Format

### Verdict
**GO** or **NO-GO**

### Fix Verification
For each fix (1-4):
- ✅ **Correct** — will work at runtime
- ⚠️ **Correct with caveat** — works but has a non-blocking edge case
- ❌ **Incorrect** — will fail at runtime (explain why and how to fix)

### Edge Cases
Any non-blocking issues or things to monitor during Phase 1.
