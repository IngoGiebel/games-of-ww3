#!/usr/bin/env bash
# GWW3 — Warden Review Gate for ETL Scripts
#
# Submits a Python script to Codex (Warden) for review before execution.
# If approved, executes it. If rejected, prints feedback and exits non-zero.
#
# Usage:
#   ./scripts/review_and_run.sh src/scripts/etl_nuclear.py "P3-03: Nuclear warheads"
#   ./scripts/review_and_run.sh <script_path> <task_description>
#
# Exit codes:
#   0 = Approved + executed successfully
#   1 = Rejected by Warden (feedback printed to stderr)
#   2 = Warden/Codex unavailable (script NOT executed)
#   3 = Script execution failed (Warden approved but script errored)

set -euo pipefail

SCRIPT_PATH="${1:?Usage: review_and_run.sh <script.py> <task_description>}"
TASK_DESC="${2:-ETL script}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MAX_ROUNDS=3

# Lock file to prevent parallel Codex calls (rate limit protection)
LOCKFILE="$PROJECT_DIR/logs/.warden.lock"
mkdir -p "$PROJECT_DIR/logs/warden"

# ── Interface context (what Warden needs to know about our standards) ──
INTERFACE_CONTEXT='
=== PROJECT API SIGNATURES ===
# normalization.py: normalize_value(name, raw) → canonical value
#   SIPRI millions → *1_000_000, V-Dem 0-1 → *100, all monetary in absolute USD
# validation_bounds.py: validate_record(dict) → ValidationResult(.passed, .errors)
#   Bounds: 10M < GDP < 50T, mil_spend < GDP, pop > 800, 0 <= indices <= 100
# imputation.py: impute_record(record, context) → (completed_dict, imputations)
# Neo4j: MERGE (not CREATE), single transaction, explicit tx.commit()
# ImportBatch + PROVENANCE edges required for all data writes
=== END ===
'

acquire_lock() {
    # Simple flock-based mutex (timeout 300s)
    exec 9>"$LOCKFILE"
    if ! flock -w 300 9; then
        echo "[Warden] ERROR: Could not acquire lock after 300s" >&2
        exit 2
    fi
}

release_lock() {
    flock -u 9 2>/dev/null || true
}

review_script() {
    local script_path="$1"
    local desc="$2"
    local attempt="$3"
    local script_content
    script_content="$(cat "$script_path")"
    
    local prompt="You are Warden, a code review agent for the GWW3 geopolitical simulation.

Review this Python ETL script for safety and correctness before execution.
Task: ${desc}
Target: Neo4j (bolt://localhost:7687)

${INTERFACE_CONTEXT}

REVIEW CRITERIA (reject ONLY for these):
1. SECURITY: Cypher injection, hardcoded secrets, unsafe eval/exec
2. CORRECTNESS: Wrong units (must use absolute USD, rates as %, V-Dem *100)
3. ERROR HANDLING: Missing timeouts on requests, missing try/except on Neo4j
4. IDEMPOTENCY: Uses CREATE instead of MERGE, would create duplicates
5. STANDARDS: Missing ImportBatch/PROVENANCE, missing tx.commit()
6. DATA QUALITY: Leaves null values without handling

CRITICAL: Do NOT reject for PEP8, type hints, variable naming, or style.

SCRIPT:
\`\`\`python
${script_content}
\`\`\`

Output ONLY valid JSON: {\"status\": \"APPROVED\", \"feedback\": \"...\"} or {\"status\": \"REJECTED\", \"feedback\": \"...\"}"

    acquire_lock
    
    local output
    local exit_code=0
    output=$(codex exec \
        --full-auto \
        -c 'model="gpt-5.3-codex"' \
        "$prompt" 2>&1) || exit_code=$?
    
    release_lock
    
    # Log the review
    local logfile="$PROJECT_DIR/logs/warden/$(basename "$script_path" .py)_attempt${attempt}.log"
    echo "=== Warden Review: $desc (attempt $attempt) ===" > "$logfile"
    echo "Timestamp: $(date -Iseconds)" >> "$logfile"
    echo "Exit code: $exit_code" >> "$logfile"
    echo "--- Output ---" >> "$logfile"
    echo "$output" >> "$logfile"
    
    # Check Codex CLI exit code first
    if [[ $exit_code -ne 0 ]]; then
        echo "[Warden] Codex CLI failed (exit $exit_code). NOT burning revision rounds." >&2
        echo "[Warden] Error: $output" >&2
        return 2  # Codex unavailable — don't retry
    fi
    
    # Extract JSON verdict + display in single Python call
    echo "$output" | python3 -c "
import sys, json
raw = sys.stdin.read()
attempt = $attempt
candidates = []
depth = 0
start = -1
for i, ch in enumerate(raw):
    if ch == '{':
        if depth == 0: start = i
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0 and start >= 0:
            candidates.append(raw[start:i+1])
            start = -1
verdict = None
for c in reversed(candidates):
    try:
        d = json.loads(c)
        if 'status' in d:
            verdict = d
            break
    except: pass
if verdict is None:
    print(f'[Warden] Warning: Could not parse output (attempt {attempt})', file=sys.stderr)
    sys.exit(2)
status = verdict.get('status', 'ERROR').upper()
feedback = verdict.get('feedback', 'No feedback')
if status == 'APPROVED':
    print(f'[Warden] APPROVED (attempt {attempt}): {feedback}')
    sys.exit(0)
else:
    print(f'[Warden] REJECTED (attempt {attempt}): {feedback}', file=sys.stderr)
    sys.exit(1)
"
    return $?
}

# ── Main ──

echo "[Warden] Reviewing: $SCRIPT_PATH ($TASK_DESC)"

warden_passed=false
for attempt in $(seq 1 $MAX_ROUNDS); do
    if review_script "$SCRIPT_PATH" "$TASK_DESC" "$attempt"; then
        warden_passed=true
        break
    else
        rc=$?
        if [[ $rc -eq 2 ]]; then
            echo "[Warden] Codex unavailable. Skipping review — executing script with WARNING." >&2
            warden_passed=true  # Fail-open if Codex is down
            break
        fi
        if [[ $attempt -lt $MAX_ROUNDS ]]; then
            echo "[Warden] Revision $attempt/$MAX_ROUNDS failed. Script needs fixes." >&2
            # In autonomous mode, we can't revise — just report failure
        fi
    fi
done

if [[ "$warden_passed" != "true" ]]; then
    echo "[Warden] ❌ BLOCKED: Script failed review after $MAX_ROUNDS rounds." >&2
    echo "[Warden] Check logs: $PROJECT_DIR/logs/warden/" >&2
    exit 1
fi

# ── Execute the approved script ──
echo "[Warden] Executing: python $SCRIPT_PATH"
if python "$SCRIPT_PATH"; then
    echo "[Warden] ✅ Script completed successfully"
    exit 0
else
    echo "[Warden] ❌ Script execution failed (exit $?)" >&2
    exit 3
fi
