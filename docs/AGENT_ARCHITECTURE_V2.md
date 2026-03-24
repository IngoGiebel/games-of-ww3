# GWW3 — Agent Architecture v2.1 (Resilient ADK Loop)

*Created: 2026-03-24 by Dione 🌙*
*Updated: 2026-03-24 — Deep Think Reviews #1 + #2 incorporated, Warden + Watchdog implemented*
*Status: **Approved** — All 5 action items from Orchestration review implemented*

## Core Problem

v1 agents ran as one-shot Gemini CLI sessions. When one hit a 429 or crashed, everything stopped.
We need: **autonomous agents that run in a loop, recover from errors, and continuously improve.**

## Design Goals

1. **Crash-resilient:** Agent dies → restarts → picks up where it left off
2. **Self-improving:** Each cycle detects and fixes data quality issues
3. **Observable:** Every action logged, every decision traceable
4. **Coordinated:** Agents don't step on each other, tasks don't duplicate
5. **Budget-aware:** Respect API rate limits, track token/credit usage
6. **Memory-bounded:** Clear LLM context between tasks to prevent context window bloat
7. **Code-reviewed:** No generated script executes without passing Warden (Codex) review

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                 Dione (Orchestrator)                  │
│            OpenClaw Main Session (Claude Opus)        │
│   - Assigns tasks via task queue                      │
│   - Monitors agent health                             │
│   - Reviews & approves data imports                   │
│   - Triggers Deep Think reviews                       │
└──────┬──────────────┬──────────────┬─────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────────┐
│   Archon    │ │  Sentinel  │ │  Warden 🛡️  │
│ (Engineer)  │ │ (Analyst)  │ │ (Code QA)   │
│ Gemini 2.5  │ │ Gemini 2.5 │ │ Codex 5.4   │
└──────┬──────┘ └─────┬──────┘ └──────┬──────┘
       │              │               │
       │              │◄──APPROVED────┤
       │              │──script──────►│
       │              │◄──REJECTED────┤
       │              │               │
┌──────▼──────────────▼───────────────▼──┐
│           Neo4j Graph DB                │
│   + Task Queue + Provenance Chain       │
└─────────────────────────────────────────┘
```

---

## Task Queue (in Neo4j)

Instead of external task queues, use the graph itself.
Sufficient for ~500-1000 tasks. No need for Redis/Celery at this scale.

```cypher
(:Task {
  id: "task-001-worldbank-gdp",
  phase: 2,
  step: "2.1",
  title: "Import World Bank GDP data for all nations",
  assigned_to: "Sentinel",
  status: "pending",        // pending | in_progress | completed | failed | blocked
  priority: 1,              // 1 = highest
  created_at: datetime(),
  started_at: null,
  completed_at: null,
  retry_count: 0,
  max_retries: 3,
  error_log: null,
  result_summary: null
})
```

**Required index (created):**
```cypher
CREATE INDEX task_queue IF NOT EXISTS FOR (t:Task) ON (t.status, t.assigned_to)
```

**Atomic task claim (prevents race conditions):**
```cypher
MATCH (t:Task {status: "pending", assigned_to: $agent_name})
WHERE NOT EXISTS {
  MATCH (t)-[:DEPENDS_ON]->(dep:Task)
  WHERE dep.status <> "completed"
}
WITH t ORDER BY t.priority ASC LIMIT 1
SET t.status = "in_progress", t.started_at = datetime()
RETURN t
```

This is a single atomic Cypher query — no TOCTOU race between pick and claim.

---

## Agent Loop Design (ADK)

Each agent runs as a **Google ADK agent** with this core loop:

```python
class TaskOwnershipLostError(Exception):
    """Raised when Watchdog has requeued a task while the agent was working.
    Must NOT trigger fail_task() — the task now belongs to another agent."""
    pass

class GWW3Agent:
    """Base class for all GWW3 ADK agents."""
    
    def run_loop(self):
        """Main resilient loop — runs until no tasks remain."""
        while True:
            try:
                # 1. Pick AND claim task atomically (single Cypher query)
                task = self.claim_next_task()
                if not task:
                    self.log("No tasks available. Sleeping 60s...")
                    time.sleep(60)
                    continue
                
                # 2. Execute with timeout
                result = self.execute_task(task, timeout=300)
                
                # 3. Validate result (sanity bounds + schema compliance)
                validation = self.validate_result(task, result)
                
                if validation.passed:
                    # 4a. Commit to Neo4j + create ImportBatch + PROVENANCE edges
                    self.commit_result(task, result)
                    self.complete_task(task['id'], result.summary)
                else:
                    # 4b. Log failure, retry or escalate
                    self.fail_task(task['id'], validation.errors)
                
                # 5. CRITICAL: Clear LLM context after each task
                #    Prevents context window bloat over long-running sessions
                self.reset_memory()
                    
            except TaskOwnershipLostError as e:
                # Watchdog requeued this task — another agent owns it now.
                # Do NOT call fail_task() — that would corrupt the other agent's state.
                self.log(f"Ownership lost (normal): {e}")
                self.reset_memory()
                continue
                
            except RateLimitError as e:
                self.log(f"Rate limited: {e}. Backing off {e.retry_after}s")
                time.sleep(e.retry_after or 60)
                
            except Exception as e:
                self.log(f"Unexpected error: {e}")
                if task:
                    self.fail_task(task['id'], str(e))
                self.reset_memory()  # Clear potentially corrupted context
                time.sleep(10)
    
    def claim_next_task(self):
        """Atomic pick+claim in a single Cypher query. No race conditions."""
        result = self.neo4j.run("""
            MATCH (t:Task {status: "pending", assigned_to: $agent})
            WHERE NOT EXISTS {
              MATCH (t)-[:DEPENDS_ON]->(dep:Task)
              WHERE dep.status <> "completed"
            }
            WITH t ORDER BY t.priority ASC LIMIT 1
            SET t.status = "in_progress", t.started_at = datetime()
            RETURN t
        """, agent=self.name)
        return result.single() if result else None
    
    def execute_task(self, task, timeout):
        """Override per agent. Returns structured result."""
        raise NotImplementedError
    
    def validate_result(self, task, result):
        """Built-in validation: sanity bounds, schema compliance, range checks."""
        checks = []
        checks.append(self.check_required_fields(task, result))
        checks.append(self.check_sanity_bounds(result))  # Hard invariants from validation_bounds.py
        checks.append(self.check_no_regression(result))   # Don't overwrite high-confidence with low
        return ValidationResult(checks)
    
    def commit_result(self, task, result):
        """Write to Neo4j with full provenance inside a SINGLE TRANSACTION.
        
        CRITICAL: All writes happen in one transaction. If the script crashes
        mid-batch, Neo4j rolls back everything automatically. No partial writes,
        no orphaned data, no need for watchdog rollback of properties.
        """
        batch_id = f"import-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}-{task['step']}"
        
        with self.neo4j.session() as session:
            with session.begin_transaction() as tx:
                # VERIFY OWNERSHIP before committing (split-brain protection).
                # If Watchdog requeued this task while we were working,
                # another agent may have claimed it. Abort to prevent double-write.
                check = tx.run("""
                    MATCH (t:Task {id: $task_id})
                    RETURN t.status AS status, t.assigned_to AS agent
                """, task_id=task['id']).single()
                
                if (not check 
                    or check["status"] != "in_progress" 
                    or check["agent"] != self.name):
                    raise TaskOwnershipLostError(
                        f"Task {task['id']} ownership lost "
                        f"(status={check['status'] if check else '?'}, "
                        f"agent={check['agent'] if check else '?'}). "
                        f"Aborting commit to prevent split-brain double-write."
                    )
                
                # Create ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: $agent,
                        method: $method, record_count: $count,
                        notes: $notes, confidence: $confidence,
                        derivation_formula: $formula,
                        warden_approved: $warden_ok,
                        warden_review_attempts: $warden_attempts,
                        warden_model: $warden_model
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: $source_id})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id, agent=self.name, 
                     method=task.get('method', 'api_import'),
                     count=len(result.records), notes=task.get('title'),
                     confidence=result.confidence,
                     formula=result.derivation_formula,
                     source_id=task['source_id'],
                     warden_ok=result.warden_approved,
                     warden_attempts=result.warden_attempts,
                     warden_model=result.warden_model)
                
                # Write data + link provenance — single UNWIND (no N+1 loop).
                # Passes entire batch as one parameter, one network roundtrip.
                records_param = [
                    {"iso3": r.iso3, "properties": r.data, 
                     "prop_names": list(r.data.keys())}
                    for r in result.records
                ]
                tx.run("""
                    UNWIND $records AS rec
                    MATCH (n:Nation {iso3: rec.iso3})
                    SET n += rec.properties
                    WITH n, rec
                    MATCH (ib:ImportBatch {id: $batch_id})
                    MERGE (n)-[p:PROVENANCE]->(ib)
                    SET p.properties = rec.prop_names
                """, records=records_param, batch_id=batch_id)
                
                # MUST explicitly commit. Neo4j's unmanaged transaction
                # (begin_transaction) auto-ROLLBACKS on exit, not auto-commits.
                # Without this line, all writes silently vanish.
                tx.commit()
    
    def reset_memory(self):
        """Clear LLM conversation history to prevent context window bloat.
        ADK agents maintain conversation history — without this, an agent
        running for days will OOM or hit token limits."""
        if hasattr(self, 'session'):
            self.session.clear()
        self.log("Memory cleared after task completion")
```

---

## ETL Standard: Deterministic Scripts, Not LLM Parsing

**⚠️ CRITICAL DESIGN RULE:**

Sentinel does NOT parse structured data payloads (JSON, CSV, XML) row-by-row via LLM context.

**Why:** Feeding megabytes of World Bank JSON into an LLM context window will:
1. Hallucinate data (swap values between countries)
2. Drop rows silently
3. Exhaust API rate limits instantly
4. Cost 100x more than a Python script

**Correct pattern (with Warden review gate):**
```python
class SentinelAgent(GWW3Agent):
    def execute_task(self, task, timeout):
        """Sentinel: generate → Warden review → execute deterministic Python ETL script."""
        
        if task['method'] == 'api_import':
            # Use the review-and-execute loop (up to 3 revision cycles)
            return self.execute_task_with_review(task, timeout)
        
        elif task['method'] == 'llm_extract':
            # Only for unstructured data: leader ideologies, faction names, etc.
            # These also go through Warden review.
            return self.llm_extract_with_review(task)
```

---

## Warden Review Gate (Codex 5.4)

Every generated script passes through Warden before execution. No exceptions.

### Review Flow

```
Sentinel/Archon generates script
        │
        ▼ write to /tmp/gww3_etl_{task_id}.py
┌───────────────────────────────┐
│  WARDEN (Codex 5.4)          │
│  codex exec (non-interactive) │
│                               │
│  Checks:                      │
│  1. Security (injections)     │
│  2. Correctness (units, APIs) │
│  3. Error handling            │
│  4. Idempotency (MERGE>CREATE)│
│  5. Standards compliance      │
└───────────┬───────────────────┘
            │
       ┌────▼────┐
       │Approved?│
       └──┬───┬──┘
     Yes  │   │  No (with feedback)
          │   │
          ▼   └──► Sentinel revises script (max 3 rounds)
     Execute        └──► Still rejected? → Task BLOCKED → Dione alert
```

### Implementation

See `src/gww3/agents/warden.py` for the full implementation. Key design decisions
(from Orchestration Deep Think review):

```python
from gww3.agents.warden import review_script, execute_with_review, get_cached_script

# 1. JSON structured output (no brittle string matching)
#    Warden prompt demands: {"status": "APPROVED"|"REJECTED", "feedback": "..."}
#    Parsed with json.loads(), with fallback extraction for surrounding text

# 2. Interface context injection (Warden sees function signatures)
#    INTERFACE_CONTEXT string contains signatures of normalization.py,
#    validation_bounds.py, imputation.py — so Warden knows WHAT to enforce

# 3. FileLock mutex (prevents parallel Codex rate limit hits)
#    filelock.FileLock around every codex exec call
#    Sentinel and Archon serialize their reviews automatically

# 4. Script caching (skip review on recurring tasks)
#    Approved scripts saved to src/scripts/approved_etl/{source}_{step}.py
#    On recurring tasks: cache hit → execute directly, skip LLM + Warden

# 5. Strict negative constraint (no style nits)
#    Prompt explicitly says: "Do NOT reject for PEP8, type hints, naming"

# Usage in agent loop:
result = execute_with_review(
    generate_fn=lambda: self.generate_script(task),
    revise_fn=lambda script, feedback: self.revise_script(task, script, feedback),
    execute_fn=lambda path: self.execute_script(path, timeout=300),
    task=task,
    max_rounds=3,
)
```

### Warden Review Record (Provenance)

Every review is logged in the ImportBatch for full traceability:
```python
# When committing results, include Warden review metadata:
ib_properties = {
    ...
    "warden_approved": True,
    "warden_review_attempts": attempt + 1,
    "warden_model": "gpt-5.3-codex",
}
```

**When LLM reasoning IS appropriate:**
- Unstructured text parsing (leader ideologies from CIA Factbook free text)
- Fuzzy entity matching (ACLED rebel group names → standard IDs)
- Derived/synthesized data (domestic factions from multiple source narratives)
- Script debugging (when a generated script fails, LLM diagnoses + fixes)

---

## Error Recovery Strategy

### Transient Errors (retry automatically)
| Error | Strategy |
|-------|----------|
| 429 Rate Limit | Exponential backoff (60s → 120s → 300s) |
| Network timeout | Retry 3x with 30s delay |
| Neo4j connection lost | Reconnect + retry current task |
| Script execution timeout | Retry with increased timeout |

### Permanent Errors (escalate to Dione)
| Error | Strategy |
|-------|----------|
| API key invalid | Alert Dione, pause agent |
| Source data format changed | Log + skip task + alert |
| Sanity bound violation after 3 retries | Mark task as `blocked`, alert |
| Data conflict (two sources disagree) | Create `(:DataConflict)` node, alert |

### State Recovery (after crash)
- On startup, check for `in_progress` tasks owned by this agent
- If found: check Neo4j for partial writes (ImportBatch exists but incomplete)
- If partial: rollback (delete ImportBatch + unlink PROVENANCE edges)
- Reset task to `pending` with incremented `retry_count`

### Context Window Management
- **MANDATORY:** Call `reset_memory()` after every task completion
- ADK agents accumulate conversation history; without clearing, they will exceed token limits
- Task-relevant context is loaded fresh from Neo4j Task node at start of each cycle
- Long-term state lives in Neo4j, NOT in LLM memory

---

## Agent Specializations

### Sentinel (Data Analyst)
- **Primary role:** Fetch data from external APIs, load into Neo4j
- **Method:** Generate + execute deterministic Python scripts (NOT LLM row-parsing)
- **Tools:** Shell execution (Python scripts), Neo4j writes
- **Loop:** Claim task → generate script → execute → validate → commit
- **Error budget:** 3 retries per task, then escalate

### Archon (Lead Engineer)
- **Primary role:** Schema migrations, derived data, integration code, normalization infrastructure
- **Method:** Direct code writing + execution
- **Tools:** Cypher DDL, Python scripts, test runner
- **Loop:** Claim task → implement → test → commit
- **Special:** Can create new Tasks for Sentinel

### Inanna (Military Reviewer)
- **Primary role:** Validate military/security data accuracy
- **Method:** LLM reasoning for cross-referencing open sources
- **Tools:** Read-only Neo4j, web search
- **Loop:** Review queue → verify → approve/reject
- **Special:** Can flag data as `needs_manual_review`

### Warden 🛡️ (Code Review)
- **Primary role:** Review all generated ETL scripts before execution
- **Runtime:** Codex CLI 5.4 (GPT-5.3-codex, ChatGPT subscription)
- **Method:** Non-interactive `codex exec` with structured review prompt
- **Checks:** Security (injection), correctness (units, endpoints), error handling, idempotency, standards compliance
- **Loop:** Invoked synchronously by Sentinel/Archon before each script execution
- **Output:** APPROVED or REJECTED with specific fixes needed
- **Revision cycle:** Up to 3 rounds; if still rejected → task blocked → escalate to Dione

### Herald (Community)
- **Primary role:** Post updates to Moltbook, engage community
- **Tools:** Moltbook API
- **Loop:** On milestone completion → draft post → post

---

## Continuous Improvement Cycle

```
     ┌──────────────────────┐
     │   1. Load Data       │ ← Sentinel executes Python ETL scripts
     │      (ImportBatch)   │
     └──────────┬───────────┘
                │
     ┌──────────▼───────────┐
     │   2. Validate        │ ← Automated: sanity bounds, schema, completeness
     │      (per-task)      │
     └──────────┬───────────┘
                │
     ┌──────────▼───────────┐
     │   3. Cross-Check     │ ← Archon: compare sources, detect conflicts
     │      (weekly)        │
     └──────────┬───────────┘
                │
     ┌──────────▼───────────┐
     │   4. Deep Review     │ ← Gemini Deep Think: structural analysis
     │      (per-phase)     │
     └──────────┬───────────┘
                │
     ┌──────────▼───────────┐
     │   5. Fix & Improve   │ ← Generate new Tasks from review findings
     │      (loop back)     │
     └──────────┘───────────┘
```

Each Phase completion triggers a Deep Think review.
Review findings become new Tasks → agents pick them up → loop continues.

---

## ADK Implementation Plan

### Step 1: Base Infrastructure
- `src/gww3/agents/base.py` — GWW3Agent base class with loop + error handling + memory management
- `src/gww3/agents/neo4j_client.py` — Neo4j connection pool + retry logic
- `src/gww3/agents/task_queue.py` — Atomic task claim + CRUD operations via Cypher
- `src/gww3/agents/provenance.py` — ImportBatch creation + PROVENANCE edge linking
- `src/gww3/data/normalization.py` — Unit & scale normalization registry
- `src/gww3/data/imputation.py` — Missing data imputation hierarchy
- `src/gww3/data/validation_bounds.py` — Hard sanity bounds for all properties

### Step 2: Sentinel Agent
- `src/gww3/agents/sentinel/agent.py` — Sentinel main class (script generator + executor)
- `src/gww3/agents/sentinel/importers/worldbank.py`
- `src/gww3/agents/sentinel/importers/sipri.py`
- `src/gww3/agents/sentinel/importers/vdem.py`
- `src/gww3/agents/sentinel/importers/acled.py`
- `src/gww3/agents/sentinel/importers/eia.py`
- `src/gww3/agents/sentinel/importers/fao.py`
- `src/gww3/agents/sentinel/importers/cia_factbook.py`

### Step 3: Archon Agent
- `src/gww3/agents/archon/agent.py` — Archon main class
- `src/gww3/agents/archon/schema_manager.py` — Schema migrations
- `src/gww3/agents/archon/derivation.py` — Derived data logic (with formula tracking)
- `src/gww3/agents/archon/validator.py` — Cross-source validation

### Step 4: Warden Integration
- `src/gww3/agents/warden.py` — Warden review API (wraps `codex exec`)
- `tests/test_warden.py` — Review gate tests (approve/reject/revision cycle)

### Step 5: Integration
- `src/gww3/agents/orchestrator.py` — Dione's task creation + monitoring
- `src/gww3/agents/adk_config.py` — ADK agent definitions
- `tests/test_agent_loop.py` — Loop resilience tests (crash recovery, race conditions)
- `tests/test_provenance.py` — Provenance chain tests
- `tests/test_sanity_bounds.py` — Validation bounds tests
- `tests/test_imputation.py` — Imputation hierarchy tests
