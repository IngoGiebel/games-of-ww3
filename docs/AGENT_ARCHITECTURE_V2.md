# GWW3 — Agent Architecture v2.0 (Resilient ADK Loop)

*Created: 2026-03-24 by Dione 🌙*
*Status: Draft — pending review + Deep Think validation*

## Core Problem

v1 agents ran as one-shot Gemini CLI sessions. When one hit a 429 or crashed, everything stopped.
We need: **autonomous agents that run in a loop, recover from errors, and continuously improve.**

## Design Goals

1. **Crash-resilient:** Agent dies → restarts → picks up where it left off
2. **Self-improving:** Each cycle detects and fixes data quality issues
3. **Observable:** Every action logged, every decision traceable
4. **Coordinated:** Agents don't step on each other, tasks don't duplicate
5. **Budget-aware:** Respect API rate limits, track token/credit usage

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              Dione (Orchestrator)            │
│         OpenClaw Main Session                │
│   - Assigns tasks via task queue             │
│   - Monitors agent health                    │
│   - Reviews & approves data imports          │
│   - Triggers Deep Think reviews              │
└──────────┬──────────────┬───────────────────┘
           │              │
    ┌──────▼──────┐ ┌─────▼──────┐
    │   Archon    │ │  Sentinel  │
    │ (Engineer)  │ │ (Analyst)  │
    │ ADK Agent   │ │ ADK Agent  │
    │ Gemini 2.5  │ │ Gemini 2.5 │
    └──────┬──────┘ └─────┬──────┘
           │              │
    ┌──────▼──────────────▼──────┐
    │        Neo4j Graph DB      │
    │   + Task Queue (nodes)     │
    │   + Import Log (nodes)     │
    └────────────────────────────┘
```

---

## Task Queue (in Neo4j)

Instead of external task queues, use the graph itself:

```cypher
(:Task {
  id: "task-001-worldbank-gdp",
  phase: 2,
  step: "2.1",
  title: "Import World Bank GDP data for all nations",
  assigned_to: "Sentinel",
  status: "pending",        // pending | in_progress | completed | failed | blocked
  priority: 1,              // 1 = highest
  depends_on: ["task-000-nation-registry"],
  created_at: datetime(),
  started_at: null,
  completed_at: null,
  retry_count: 0,
  max_retries: 3,
  error_log: null,
  result_summary: null
})
```

**Agent loop picks tasks:**
```
MATCH (t:Task {status: "pending", assigned_to: $agent_name})
WHERE NOT EXISTS {
  MATCH (t)-[:DEPENDS_ON]->(dep:Task)
  WHERE dep.status <> "completed"
}
RETURN t ORDER BY t.priority ASC LIMIT 1
```

---

## Agent Loop Design (ADK)

Each agent runs as a **Google ADK agent** with this core loop:

```python
class GWW3Agent:
    """Base class for all GWW3 ADK agents."""
    
    def run_loop(self):
        """Main resilient loop — runs until no tasks remain."""
        while True:
            try:
                # 1. Pick next task
                task = self.pick_task()
                if not task:
                    self.log("No tasks available. Sleeping 60s...")
                    time.sleep(60)
                    continue
                
                # 2. Claim task (atomic)
                self.claim_task(task['id'])
                
                # 3. Execute with timeout
                result = self.execute_task(task, timeout=300)
                
                # 4. Validate result
                validation = self.validate_result(task, result)
                
                if validation.passed:
                    # 5a. Commit to Neo4j + create ImportBatch
                    self.commit_result(task, result)
                    self.complete_task(task['id'], result.summary)
                else:
                    # 5b. Log failure, retry or escalate
                    self.fail_task(task['id'], validation.errors)
                    
            except RateLimitError as e:
                self.log(f"Rate limited: {e}. Backing off {e.retry_after}s")
                time.sleep(e.retry_after or 60)
                
            except Exception as e:
                self.log(f"Unexpected error: {e}")
                if task:
                    self.fail_task(task['id'], str(e))
                time.sleep(10)  # Brief pause before next task
    
    def execute_task(self, task, timeout):
        """Override per agent. Returns structured result."""
        raise NotImplementedError
    
    def validate_result(self, task, result):
        """Built-in validation: schema compliance, range checks, completeness."""
        checks = []
        # Check all required fields present
        checks.append(self.check_required_fields(task, result))
        # Check value ranges (e.g., GDP > 0, population > 0)
        checks.append(self.check_value_ranges(result))
        # Check no regressions (don't overwrite high-confidence with low)
        checks.append(self.check_no_regression(result))
        return ValidationResult(checks)
    
    def commit_result(self, task, result):
        """Write to Neo4j with full provenance."""
        batch_id = f"import-{datetime.utcnow().isoformat()}-{task['step']}"
        
        # Create ImportBatch
        self.neo4j.run("""
            CREATE (ib:ImportBatch {
                id: $batch_id, timestamp: datetime(), agent: $agent,
                method: $method, record_count: $count,
                properties_set: $props, confidence: $confidence
            })
            WITH ib
            MATCH (ds:DataSource {id: $source_id})
            MERGE (ib)-[:FROM_SOURCE]->(ds)
        """, batch_id=batch_id, agent=self.name, ...)
        
        # Write data + link provenance
        for record in result.records:
            self.neo4j.run("""
                MATCH (n:Nation {iso3: $iso3})
                SET n += $properties
                WITH n
                MATCH (ib:ImportBatch {id: $batch_id})
                MERGE (n)-[:PROVENANCE]->(ib)
            """, iso3=record.iso3, properties=record.data, batch_id=batch_id)
```

---

## Error Recovery Strategy

### Transient Errors (retry automatically)
| Error | Strategy |
|-------|----------|
| 429 Rate Limit | Exponential backoff (60s → 120s → 300s) |
| Network timeout | Retry 3x with 30s delay |
| Neo4j connection lost | Reconnect + retry current task |

### Permanent Errors (escalate to Dione)
| Error | Strategy |
|-------|----------|
| API key invalid | Alert Dione, pause agent |
| Source data format changed | Log + skip task + alert |
| Validation failure after 3 retries | Mark task as `blocked`, alert |
| Data conflict (two sources disagree) | Create `(:DataConflict)` node, alert |

### State Recovery (after crash)
- On startup, check for `in_progress` tasks owned by this agent
- If found: check Neo4j for partial writes
- If partial: rollback (delete ImportBatch + unlink PROVENANCE)
- Reset task to `pending` with incremented `retry_count`

---

## Agent Specializations

### Sentinel (Data Analyst)
- **Primary role:** Fetch data from external APIs, load into Neo4j
- **Tools:** HTTP requests, CSV/JSON parsing, Cypher writes
- **Loop:** Task queue → fetch → validate → commit
- **Error budget:** 3 retries per task, then escalate

### Archon (Lead Engineer)
- **Primary role:** Schema migrations, derived data, integration code
- **Tools:** Cypher DDL, Python scripts, test runner
- **Loop:** Task queue → implement → test → commit
- **Special:** Can create new Tasks for Sentinel

### Inanna (Military Reviewer)
- **Primary role:** Validate military/security data accuracy
- **Tools:** Read-only Neo4j, web search for cross-referencing
- **Loop:** Review queue → verify → approve/reject
- **Special:** Can flag data as `needs_manual_review`

### Herald (Community)
- **Primary role:** Post updates to Moltbook, engage community
- **Tools:** Moltbook API
- **Loop:** On milestone completion → draft post → post

---

## Continuous Improvement Cycle

```
     ┌──────────────────────┐
     │   1. Load Data       │ ← Sentinel fetches from APIs
     │      (ImportBatch)   │
     └──────────┬───────────┘
                │
     ┌──────────▼───────────┐
     │   2. Validate        │ ← Automated: schema, ranges, completeness
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
- `src/gww3/agents/base.py` — GWW3Agent base class with loop + error handling
- `src/gww3/agents/neo4j_client.py` — Neo4j connection pool + retry logic
- `src/gww3/agents/task_queue.py` — Task CRUD operations via Cypher
- `src/gww3/agents/provenance.py` — ImportBatch creation + linking

### Step 2: Sentinel Agent
- `src/gww3/agents/sentinel/agent.py` — Sentinel main class
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
- `src/gww3/agents/archon/derivation.py` — Derived data logic
- `src/gww3/agents/archon/validator.py` — Cross-source validation

### Step 4: Integration
- `src/gww3/agents/orchestrator.py` — Dione's task creation + monitoring
- `src/gww3/agents/adk_config.py` — ADK agent definitions
- `tests/test_agent_loop.py` — Loop resilience tests
- `tests/test_provenance.py` — Provenance chain tests

---

## Open Questions

1. **ADK vs. plain Python?** Do agents need LLM reasoning for data import, or is it scripted ETL? Sentinel might be 90% deterministic code with LLM only for edge cases.
2. **Task granularity?** One task per source per indicator, or one task per source?
3. **Neo4j as task queue — scale?** Fine for our ~100 tasks, but would need Redis/etc. for >10k.
4. **How does Dione monitor?** Heartbeat check on agent processes? Neo4j task status queries?
5. **Token budget:** Should agents have a per-task token limit to prevent runaway costs?
