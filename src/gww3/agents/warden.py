"""Warden — Code Review Gate (Codex 5.4 / GPT-5.3-codex).

Stateless code review agent. Every generated script passes through Warden
before execution. No exceptions.

Design decisions (from Deep Think review):
1. JSON structured output — no string matching "APPROVED" (brittle)
2. Interface context injection — Warden sees function signatures, not full code
3. FileLock mutex — prevents parallel Codex calls from hitting rate limits
4. Script caching — approved scripts saved for recurring task reuse
5. Strict negative constraint — Warden does NOT reject for style/PEP8

Usage:
    from gww3.agents.warden import review_script, execute_with_review

    approved, verdict = review_script(script_content, task_info)
    result = execute_with_review(generate_fn, task, max_rounds=3)
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("warden")

# ── Configuration ──

PROJECT_DIR = Path("/home/uranus/moltbot-workspace/projects/games-of-ww3")
APPROVED_SCRIPTS_DIR = PROJECT_DIR / "src" / "scripts" / "approved_etl"
REVIEW_LOG_DIR = PROJECT_DIR / "logs" / "warden"
LOCK_FILE = PROJECT_DIR / "logs" / ".warden.lock"

CODEX_MODEL = "gpt-5.3-codex"
CODEX_TIMEOUT = 180  # seconds

# ── Interface Context (injected into Warden's prompt) ──

INTERFACE_CONTEXT = """
=== PROJECT API SIGNATURES (you must verify scripts use these correctly) ===

# normalization.py
def normalize_value(property_name: str, raw_value: Any) -> Any:
    \"\"\"Normalize a raw value to canonical form per PROPERTY_SPECS registry.\"\"\"

def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    \"\"\"Normalize all values in a record dict. Unknown keys passed through.\"\"\"

WORLDBANK_INDICATOR_MAP: dict[str, str]  # WB code → property name
# Key conversions: SIPRI millions → absolute USD (*1_000_000)
#                  V-Dem 0-1 → 0-100 integer (*100)
#                  All monetary values in absolute USD
#                  All rates as percentages (5.9 means 5.9%)

# validation_bounds.py
def validate_record(record: dict) -> ValidationResult:
    \"\"\"Check record against all bounds. Returns .passed, .errors, .warnings.\"\"\"

def validate_batch(records: list[dict]) -> dict[str, ValidationResult]:
    \"\"\"Validate batch. Returns {iso3: ValidationResult}.\"\"\"

# Key bounds: 10M < GDP < 50T, military_spending < GDP, population > 800,
#             0 <= stability_index <= 100, manpower_active <= population

# imputation.py
def build_imputation_context(nation_records: list[dict]) -> ImputationContext:
    \"\"\"Build averages from existing data for imputation.\"\"\"

def impute_record(record, context, historical=None) -> tuple[dict, list[ImputationResult]]:
    \"\"\"Fill all None values using 4-level hierarchy:
       temporal_backfill → regional_avg → income_group_avg → global_median.\"\"\"

# Neo4j patterns:
# MERGE (not CREATE) for idempotent node creation
# ON MATCH SET for updates
# Always create ImportBatch + PROVENANCE edges with properties list on edge
# ALL writes MUST be inside a single transaction (session.begin_transaction())
#   — partial writes corrupt the database; transactions roll back atomically

# Source field mappings (verify scripts use these, not guessed column names):
WORLDBANK_INDICATOR_MAP: dict[str, str]  # WB indicator code → property name
SIPRI_FIELD_MAP: dict[str, str]          # SIPRI CSV column → property name
VDEM_FIELD_MAP: dict[str, str]           # V-Dem column code → property name
ACLED_FIELD_MAP: dict[str, str]          # ACLED CSV column → property/node field
EIA_FIELD_MAP: dict[str, str]            # EIA series ID template → property name
FAO_FIELD_MAP: dict[str, str]            # FAO item → property name
=== END PROJECT API SIGNATURES ===
"""

# ── Structured Review Prompt ──

REVIEW_PROMPT_TEMPLATE = """You are Warden, a code review agent for the GWW3 geopolitical simulation project.

Review the Python script below for safety and correctness before it is executed against a Neo4j database.

Task context: {task_title}
Data source: {source_id}

{interface_context}

REVIEW CRITERIA (reject ONLY for these):
1. SECURITY: Cypher injection, hardcoded secrets, arbitrary code execution, unsafe eval/exec
2. CORRECTNESS: Wrong units (must use absolute USD not millions, rates as %, V-Dem *100), wrong API endpoints, wrong data parsing
3. ERROR HANDLING: Missing timeouts on requests, missing try/except on Neo4j writes, no retry on 429/5xx
4. IDEMPOTENCY: Uses CREATE instead of MERGE, would create duplicates on rerun
5. STANDARDS: Does not call validate_record() or normalize_record() when it should
6. DATA QUALITY: Leaves null values in non-nullable fields without imputation

CRITICAL: Do NOT reject for PEP8, missing type hints, variable naming, docstring style, or any cosmetic preferences. If the script works safely and correctly, approve it.

SCRIPT TO REVIEW:
```python
{script_content}
```

You MUST output ONLY a valid JSON object in this exact format, nothing else:
{{"status": "APPROVED", "feedback": "Brief approval note"}}
or
{{"status": "REJECTED", "feedback": "Specific list of issues that must be fixed"}}
"""


def _extract_verdict_json(raw: str) -> dict:
    """Robustly extract the verdict JSON from Codex output.
    
    Handles: bare JSON, markdown code fences, conversational padding,
    and multiple JSON-like blocks (takes the one with "status" key).
    """
    import re
    
    # Strategy 1: Try the whole string as JSON
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code fence
    fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if fence_match:
        try:
            candidate = json.loads(fence_match.group(1))
            if "status" in candidate:
                return candidate
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find ALL {...} blocks, return the one with "status"
    candidates = []
    depth = 0
    start = -1
    for i, ch in enumerate(raw):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(raw[start:i+1])
                start = -1
    
    for candidate_str in reversed(candidates):  # prefer last (most likely the verdict)
        try:
            candidate = json.loads(candidate_str)
            if "status" in candidate:
                return candidate
        except json.JSONDecodeError:
            continue
    
    raise ValueError(f"No valid JSON with 'status' key found in output ({len(raw)} chars)")


@dataclass
class ReviewVerdict:
    """Result of a Warden review."""
    approved: bool
    feedback: str
    raw_output: str
    model: str = CODEX_MODEL
    attempt: int = 1


def _acquire_lock() -> "FileLock":
    """Acquire file lock to prevent parallel Codex calls (rate limit protection)."""
    try:
        from filelock import FileLock
    except ImportError:
        # Fallback: no locking (still works, just risks 429s)
        log.warning("filelock not installed — no mutex on Codex calls. "
                     "Install with: pip install filelock")
        return None

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(LOCK_FILE), timeout=CODEX_TIMEOUT + 60)
    lock.acquire()
    return lock


def _release_lock(lock):
    """Release file lock."""
    if lock is not None:
        lock.release()


def _get_cache_key(task_source: str, task_step: str) -> str:
    """Generate cache key for approved script reuse."""
    return f"{task_source}_{task_step}"


def get_cached_script(task: dict) -> str | None:
    """Check if an approved script exists for this task type.
    
    Returns script content if cached, None otherwise.
    """
    cache_key = _get_cache_key(task.get("source_id", ""), task.get("step", ""))
    cache_path = APPROVED_SCRIPTS_DIR / f"{cache_key}.py"
    if cache_path.exists():
        log.info(f"Cache hit: {cache_path}")
        return cache_path.read_text()
    return None


def cache_approved_script(task: dict, script_content: str):
    """Save an approved script for future reuse."""
    APPROVED_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = _get_cache_key(task.get("source_id", ""), task.get("step", ""))
    cache_path = APPROVED_SCRIPTS_DIR / f"{cache_key}.py"
    cache_path.write_text(script_content)
    log.info(f"Cached approved script: {cache_path}")


def review_script(
    script_content: str,
    task: dict,
    attempt: int = 1,
) -> ReviewVerdict:
    """Submit a script to Warden (Codex) for review.

    Uses file lock to prevent parallel Codex API calls.
    Expects JSON structured output from Codex.

    Args:
        script_content: The Python script to review
        task: Task dict with 'title', 'source_id', etc.
        attempt: Which revision round (1-3)

    Returns:
        ReviewVerdict with approved/rejected status and feedback
    """
    prompt = REVIEW_PROMPT_TEMPLATE.format(
        task_title=task.get("title", "Unknown task"),
        source_id=task.get("source_id", "unknown"),
        interface_context=INTERFACE_CONTEXT,
        script_content=script_content,
    )

    lock = _acquire_lock()
    try:
        # Pass prompt as positional argument (codex exec <prompt>)
        # Stdin piping may not be supported by all codex versions.
        result = subprocess.run(
            ["codex", "exec",
             "--full-auto",
             "-c", f'model="{CODEX_MODEL}"',
             prompt],
            capture_output=True,
            text=True,
            timeout=CODEX_TIMEOUT,
            cwd=str(PROJECT_DIR),
        )
    except subprocess.TimeoutExpired:
        return ReviewVerdict(
            approved=False,
            feedback=f"Warden review timed out after {CODEX_TIMEOUT}s",
            raw_output="TIMEOUT",
            attempt=attempt,
        )
    finally:
        _release_lock(lock)

    # BLOCKING FIX #1: Check returncode and stderr BEFORE parsing stdout.
    # If Codex CLI fails (API down, auth expired, rate limited), it exits
    # non-zero and writes to stderr. Without this check, we'd burn 3 revision
    # rounds trying to "fix" perfectly valid code for a network outage.
    if result.returncode != 0:
        error_msg = result.stderr.strip() or f"Exit code {result.returncode}"
        log.error(f"Codex CLI failed: {error_msg}")
        raise RuntimeError(
            f"Codex CLI failed (exit {result.returncode}): {error_msg}"
        )

    raw_output = result.stdout.strip()

    # Log the review
    _log_review(task, script_content, raw_output, attempt)

    # Parse JSON response — robust extraction handles conversational padding,
    # markdown code fences, and multiple JSON blocks (take last valid one).
    try:
        verdict_data = _extract_verdict_json(raw_output)
        approved = verdict_data.get("status", "").upper() == "APPROVED"
        feedback = verdict_data.get("feedback", "No feedback provided")
    except (json.JSONDecodeError, ValueError) as e:
        log.warning(f"Warden output is not valid JSON, treating as rejection: {raw_output[:200]}")
        approved = False
        feedback = f"Warden output was not valid JSON ({e}). Raw: {raw_output[:500]}"

    return ReviewVerdict(
        approved=approved,
        feedback=feedback,
        raw_output=raw_output,
        attempt=attempt,
    )


def _log_review(task: dict, script: str, output: str, attempt: int):
    """Log review details to file (not Neo4j — keep graph clean)."""
    REVIEW_LOG_DIR.mkdir(parents=True, exist_ok=True)
    task_id = task.get("id", "unknown")
    log_path = REVIEW_LOG_DIR / f"{task_id}_attempt{attempt}.log"
    log_path.write_text(
        f"=== Warden Review: {task_id} (attempt {attempt}) ===\n"
        f"Task: {task.get('title', 'unknown')}\n"
        f"Timestamp: {__import__('datetime').datetime.now().isoformat()}\n"
        f"Model: {CODEX_MODEL}\n\n"
        f"--- Script ---\n{script}\n\n"
        f"--- Warden Output ---\n{output}\n"
    )


def execute_with_review(
    generate_fn,
    revise_fn,
    execute_fn,
    task: dict,
    max_rounds: int = 3,
) -> dict:
    """Full review-gated execution cycle.

    1. Check script cache → if hit, skip generation + review
    2. Generate script → Warden review → execute if approved
    3. If rejected, revise and retry (up to max_rounds)
    4. If still rejected after max_rounds → raise TaskBlockedError

    Args:
        generate_fn: Callable() -> str  (generates initial script)
        revise_fn: Callable(script, feedback) -> str  (revises script based on feedback)
        execute_fn: Callable(script_path) -> dict  (executes approved script)
        task: Task dict
        max_rounds: Maximum revision cycles

    Returns:
        Execution result dict

    Raises:
        TaskBlockedError: After max_rounds rejections
    """
    # Check cache first
    cached = get_cached_script(task)
    if cached is not None:
        log.info(f"Using cached approved script for task {task.get('id')}")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", prefix=f"gww3_etl_{task.get('id', 'x')}_",
            delete=False
        ) as f:
            f.write(cached)
            return execute_fn(f.name)

    # Generate + review loop
    script = None
    rejection_feedback = None

    for attempt in range(1, max_rounds + 1):
        if attempt == 1:
            script = generate_fn()
        else:
            script = revise_fn(script, rejection_feedback)

        verdict = review_script(script, task, attempt=attempt)

        if verdict.approved:
            log.info(f"Warden APPROVED task {task.get('id')} (attempt {attempt})")
            # Cache the approved script
            cache_approved_script(task, script)
            # Execute
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", prefix=f"gww3_etl_{task.get('id', 'x')}_",
                delete=False
            ) as f:
                f.write(script)
                return execute_fn(f.name)
        else:
            rejection_feedback = verdict.feedback
            log.warning(f"Warden REJECTED task {task.get('id')} "
                       f"(attempt {attempt}/{max_rounds}): {rejection_feedback}")

    # All rounds exhausted
    raise TaskBlockedError(
        f"Script failed Warden review after {max_rounds} revisions. "
        f"Last rejection: {rejection_feedback}"
    )


class TaskBlockedError(Exception):
    """Raised when a task cannot pass Warden review."""
    pass
