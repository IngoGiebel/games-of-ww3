# GWW3 — Agent Orchestration & Collaboration

*Created: 2026-03-24 by Dione 🌙*
*Updated: 2026-03-24 — Warden + Watchdog + all 5 Orchestration Deep Think action items*
*Status: **Approved** — Ready for Phase 1 execution*

---

## 1. Overview: Who Does What?

```
┌────────────────────────────────────────────────────────────────────┐
│                         INGO (Human)                               │
│  Decides: Strategy, budget, priorities, Go/No-Go                   │
│  Interacts via: Telegram → Dione                                   │
└─────────────────────────┬──────────────────────────────────────────┘
                          │ natural language
┌─────────────────────────▼──────────────────────────────────────────┐
│                    DIONE 🌙 (Orchestrator)                         │
│  Runtime: OpenClaw Main Session (Claude Opus)                      │
│  Role: Project lead, task creation, quality gate, escalation       │
└──────┬──────────┬──────────────┬──────────────┬──────────┬─────────┘
       │          │              │              │          │
┌──────▼──────┐ ┌─▼────────┐ ┌──▼──────┐ ┌────▼───┐ ┌────▼─────────┐
│  ARCHON     │ │ SENTINEL │ │ WARDEN  │ │ INANNA │ │  HERALD      │
│  Engineer   │ │ Analyst  │ │ Code QA │ │ Review │ │  Comms       │
│  Gemini 2.5 │ │ Gemini   │ │ Codex   │ │ Claude │ │  Gemini      │
│  ADK Agent  │ │ ADK Agent│ │ 5.4     │ │ Subagt │ │  CLI         │
└─────────────┘ └────┬─────┘ └────▲────┘ └────────┘ └──────────────┘
                     │            │
                     │  script ──►│
                     │◄─ verdict ─│
                     │            │
              ┌──────▼────────────▼───────┐
              │      Neo4j Graph DB       │
              │  (Single Source of Truth)  │
              └───────────────────────────┘
```

---

## 2. Agent Profiles

### Dione 🌙 — Orchestrator & Quality Gate

| Property | Value |
|----------|-------|
| **Runtime** | OpenClaw Main Session (Claude Opus) |
| **Model** | claude-opus-4-6 (Anthropic Max 20x subscription) |
| **Communication** | Direct Telegram chat with Ingo |

**Responsibilities:**
- **Task creation:** Reads DATA_LOADING_PLAN.md, creates Task nodes in Neo4j
- **Strategic monitoring:** Reads `logs/watchdog-status.json` for pipeline health (NOT ps aux)
- **Quality gate:** Reviews ImportBatch results before marking phases as complete
- **Escalation:** Alerts Ingo on blocked tasks, data conflicts, budget overruns
- **Deep Think trigger:** Creates review prompts after phase completion

**What Dione does NOT do (delegated to Watchdog):**
- ❌ Process supervision (ps aux, kill, restart) → Watchdog + systemd
- ❌ Zombie task detection → Watchdog daemon
- ❌ Mechanical health polling → Watchdog cron

**How Dione monitors (during heartbeats):**
```python
# Read the watchdog status file (written every 5 min by watchdog.py)
import json
status = json.loads(open("logs/watchdog-status.json").read())
if not status["healthy"]:
    # Alert Ingo about blocked tasks
    for task in status["blocked_tasks"]:
        message(f"⚠️ Task blocked: {task['title']}\nError: {task['error']}")
# Check phase completion
for phase in status["phases"]:
    if phase["phase_complete"]:
        # Trigger Deep Think review for completed phase
        pass
```

---

### Sentinel — Data Analyst (ETL Workhorse)

| Property | Value |
|----------|-------|
| **Runtime** | Google ADK Agent (Gemini 2.5 Pro) via Gemini CLI |
| **Model** | gemini-2.5-pro (Google One AI Ultra subscription) |
| **Auth** | OAuth Personal (ingo.giebel@gmail.com) |

**Responsibilities:**
- **Primary:** Fetch data from external APIs and load into Neo4j
- **Method:** Generate deterministic Python scripts → Warden review → execute
- **Never:** Parse structured data (JSON/CSV) row-by-row in LLM context

**Task execution flow:**
```
1. Claim task from Neo4j (atomic Cypher)
2. Generate Python ETL script based on task description
3. Submit script to Warden for review ←── NEW
4. If APPROVED: execute script in subprocess
   If REJECTED: revise script based on Warden feedback (max 3 rounds)
5. Validate results against sanity bounds
6. Commit to Neo4j with full provenance (ImportBatch + PROVENANCE edges)
7. Clear LLM context (reset_memory)
8. Loop → next task
```

---

### Archon — Lead Engineer (Schema & Derived Data)

| Property | Value |
|----------|-------|
| **Runtime** | Google ADK Agent (Gemini 2.5 Pro) via Gemini CLI |
| **Model** | gemini-2.5-pro (Google One AI Ultra subscription) |
| **Auth** | OAuth Personal |

**Responsibilities:**
- **Schema migrations:** New node types, constraints, indexes
- **Derived data:** Stability index from V-Dem, factions from Factbook text, supply routes
- **Cross-source validation:** Compares SIPRI vs. World Bank military data
- **Infrastructure:** normalization.py, imputation.py improvements
- **Task creation:** Can create new tasks for Sentinel

**When Archon generates Python scripts**, they also go through Warden review.
Only pure Cypher DDL (schema changes) bypasses Warden — these are reviewed by Dione instead.

---

### Warden 🛡️ — Code Review Agent (NEW)

| Property | Value |
|----------|-------|
| **Runtime** | Codex CLI 5.4 (non-interactive `codex exec`) |
| **Model** | gpt-5.3-codex (ChatGPT subscription) |
| **Auth** | ChatGPT OAuth |
| **Invocation** | Synchronous — called by Sentinel/Archon before script execution |

**Responsibilities:**
- **Code review:** Every generated Python script before execution
- **Security audit:** Cypher injection, hardcoded secrets, arbitrary code execution
- **Correctness check:** Unit conversions, API endpoints, data format compliance
- **Standards enforcement:** normalization.py, validation_bounds.py, imputation.py usage
- **Idempotency check:** MERGE vs CREATE, safe-to-rerun verification

**Warden is NOT an autonomous agent.** It has no loop, no task queue, no memory.
It is a stateless function called synchronously by other agents.

**Review protocol (JSON structured output + mutex + caching):**
```python
from gww3.agents.warden import review_script, execute_with_review

# Warden responds with structured JSON (not free text):
# {"status": "APPROVED", "feedback": "Script looks correct"}
# {"status": "REJECTED", "feedback": "Missing timeout on requests.get()"}

# FileLock mutex prevents parallel Codex calls from hitting rate limits
# Script caching: approved scripts reused for recurring tasks
# Interface context: Warden sees normalization.py/validation_bounds.py signatures

# Full implementation: src/gww3/agents/warden.py
```

**Review criteria (the 6 gates):**

| # | Gate | Examples |
|---|------|----------|
| 1 | **Security** | No `f"... {user_input} ..."` in Cypher strings. No `os.system()`. No hardcoded passwords. |
| 2 | **Correctness** | SIPRI data multiplied by 1M. V-Dem indices multiplied by 100. Correct WB indicator codes. |
| 3 | **Error handling** | `requests.get()` has timeout. Retries on 429/5xx. `try/except` around Neo4j writes. |
| 4 | **Idempotency** | Uses `MERGE` not `CREATE` for nodes. Uses `ON MATCH SET` for updates. |
| 5 | **Standards** | Imports `normalization.py`. Calls `validate_record()`. Calls `impute_record()`. |
| 6 | **Data quality** | Checks for null values. Validates ranges. Tags confidence levels. |

**Revision cycle:**
```
Round 1: Sentinel generates script → Warden REJECTED (missing timeout on requests)
Round 2: Sentinel revises script → Warden REJECTED (SIPRI data not normalized to abs USD)
Round 3: Sentinel revises script → Warden APPROVED → Execute
```

If still rejected after 3 rounds → Task status = `blocked` → Dione alerted → Ingo informed.

**Why Codex specifically?**
- Codex is purpose-built for code review (native `codex review` command)
- GPT-5.3-codex excels at finding bugs and security issues in Python
- Non-interactive `codex exec` is fast (~10-30s per review)
- On ChatGPT subscription — $0 incremental cost
- Different model family from Sentinel/Archon (Gemini) — diversity catches more issues

---

### Inanna ⚔️ — Military Domain Expert & Reviewer

| Property | Value |
|----------|-------|
| **Runtime** | OpenClaw Subagent (Claude) |
| **Model** | claude-opus-4-6 (shares Dione's Max 20x) |
| **Invocation** | Spawned by Dione for review tasks |

**Responsibilities:**
- **Review queue:** Validates all military/security ImportBatches for plausibility
- **Cross-referencing:** Compares data with OSINT sources
- **Flags:** Can mark data as `needs_manual_review` with reasoning
- **Domain expertise:** PoW security, military capabilities, NSA modeling

**Inanna is read-only on Neo4j.** She does not write data directly.

---

### Herald — Community & Moltbook

| Property | Value |
|----------|-------|
| **Runtime** | Gemini CLI (lightweight) |
| **Model** | gemini-2.5-pro (Google One AI Ultra) |
| **Invocation** | Triggered by Dione at milestones |

**Responsibilities:**
- Post project updates to Moltbook (m/wargames, m/engineering)
- Monitor community feedback, report relevant items to Dione
- Activated only at milestones — no permanent loop

---

### Watchdog — Deterministic Process Supervisor (NEW)

| Property | Value |
|----------|-------|
| **Runtime** | Plain Python daemon (NOT an LLM) |
| **Invocation** | Cron job every 5 minutes |
| **Code** | `src/gww3/agents/watchdog.py` |

**Responsibilities:**
- Detect zombie tasks (IN_PROGRESS for >60 minutes)
- Auto-requeue with retry_count increment (up to max_retries)
- Block tasks that exceed max_retries
- Write `logs/watchdog-status.json` for Dione to read
- Write `logs/watchdog-alerts.json` for alert history

**Why a separate daemon, not Dione?**
Process supervision must be handled by the OS, not an LLM. If Dione's session
crashes or is busy chatting, the watchdog still runs independently via cron.

```bash
# Cron setup (runs every 5 minutes)
*/5 * * * * cd /home/uranus/moltbot-workspace/projects/games-of-ww3 \
  && python -m gww3.agents.watchdog >> logs/watchdog.log 2>&1
```

---

## 3. Communication Protocols

### Task-Based Coordination (Dione ↔ Sentinel/Archon)

**No direct message-passing.** All coordination flows through Neo4j Task nodes.

```
Dione creates Task ──────────────────────► Neo4j
                                             ↕
Sentinel/Archon claims Task ◄──────────── Neo4j
                                             ↕
Agent generates script ──► Warden review     │
                                             ↕
Agent commits result ────────────────────► Neo4j (ImportBatch + PROVENANCE)
                                             ↕
Dione reads result at next heartbeat ◄──── Neo4j
```

**Why no direct messaging?**
- Agents run asynchronously — Dione doesn't need to wait
- Neo4j is the single source of truth
- Task status survives agent crashes (persistent state)
- No race conditions (atomic Cypher queries)
- Full audit trail in the graph database

### Synchronous Review (Sentinel/Archon ↔ Warden)

Warden is called **inline** — the calling agent blocks until review completes.
This is intentional: no script should ever execute without review.

```
Sentinel ──(script)──► codex exec ──(verdict)──► Sentinel
           blocking        ~30s         blocking
```

### Subagent Spawning (Dione ↔ Inanna)

```python
# Dione spawns Inanna for a one-shot review:
sessions_spawn(
    task="Review the latest SIPRI ImportBatch in Neo4j. "
         "Check military data for plausibility using your domain expertise. "
         "Neo4j: bolt://localhost:7687, password: gww3-dev-2026. "
         "Flag suspicious values with reasoning.",
    runtime="subagent",
    mode="run",  # one-shot, not persistent
)
```

### Human Escalation (Dione ↔ Ingo)

- **Routine:** Status updates during morning briefing
- **Alerts:** Immediately on blocked tasks or data conflicts
- **Milestones:** Phase completion with summary
- **Decisions:** Questions only Ingo can answer

---

## 4. Task Lifecycle

```
    ┌─────────┐
    │ PENDING │ ← Dione creates task
    └────┬────┘
         │ Agent claims (atomic Cypher SET)
    ┌────▼────────┐
    │ IN_PROGRESS │ ← Agent working
    └────┬────────┘
         │ Script generated
    ┌────▼────────┐
    │ WARDEN      │ ← Code review (up to 3 rounds)
    │ REVIEW      │
    └────┬────────┘
         │
    ┌────▼────┐
    │ Result  │    Validation failed, retry < max
    │ Check   │───────────────────────────────┐
    └──┬───┬──┘                               │
   OK  │   │  Failed                    ┌─────▼─────┐
  ┌────▼───┐                            │  PENDING   │
  │COMPLETE│                            │ (retry +1) │
  │   D    │                            └────────────┘
  └────────┘  Failed, retry >= max
               ┌──────────┐
               │ BLOCKED  │ ← Dione alerted → Ingo informed
               └──────────┘
```

---

## 5. Error Recovery Scenarios

### Scenario 1: Warden Rejects Script (most common)

```
Sentinel generates script with missing error handling
    │
    ├─ Warden REJECTED: "requests.get() has no timeout parameter"
    ├─ Sentinel revises script, adds timeout=30
    ├─ Warden APPROVED
    └─ Script executes successfully
```

**Impact:** 30-90 seconds delay per rejection round. Acceptable.

### Scenario 2: API Rate Limit (429)

```
Sentinel → World Bank API → 429 Too Many Requests
    │
    ├─ Agent catches RateLimitError
    ├─ Exponential backoff: 60s → 120s → 300s
    ├─ Task remains IN_PROGRESS
    ├─ After 3 retries: Task → BLOCKED
    └─ Dione alerted at next heartbeat
        └─ Informs Ingo: "World Bank API rate limited. Wait or use API key?"
```

### Scenario 3: Agent Process Crash (OOM, disconnect)

```
Sentinel process dies
    │
    ├─ Task remains IN_PROGRESS in Neo4j (no agent to update it)
    ├─ Dione detects at heartbeat: "Task X IN_PROGRESS for >1h, no progress"
    ├─ Dione checks: Is Sentinel process running? (ps aux | grep gemini)
    │
    ├─ If dead: Dione restarts Sentinel
    │   └─ Sentinel on-startup:
    │       ├─ MATCH (t:Task {status: "in_progress", assigned_to: "Sentinel"})
    │       ├─ Check: Does this task have a partial ImportBatch?
    │       ├─ If yes: Rollback (DETACH DELETE partial ImportBatch)
    │       └─ SET t.status = "pending", t.retry_count += 1
    │
    └─ If hanging: Dione kills + restarts
```

### Scenario 4: Data Conflict (two sources disagree)

```
Archon cross-check finds:
    SIPRI: DEU military_spending = €52B
    World Bank: DEU military_spending = €48B
    │
    ├─ Archon creates DataConflict node in Neo4j
    ├─ Dione alerted
    ├─ Resolution: "SIPRI is authoritative for military spending"
    └─ World Bank value marked as secondary
```

### Scenario 5: Context Window Bloat

```
Agent has processed 20 tasks in a row without memory reset
    │
    ├─ reset_memory() called after EVERY task (mandatory)
    ├─ Safeguard: check token count before each task
    │   if self.context_tokens > 100_000:
    │       self.reset_memory()
    │
    └─ Second safeguard: Gemini CLI session auto-timeout
        gemini --max-turns 50
```

---

## 6. Parallelism & Sequencing

### Phase-Level Parallelism

```
Phase 0 (Normalization) ──── Archon, sequential ── DONE ✅
    │
Phase 1 (Foundation) ─────── Sentinel: 1.1 → (1.2 + 1.3 parallel)
    │
    ├── Phase 2 (Economics) ──── Sentinel     ┐
    ├── Phase 3 (Military) ───── Sentinel     │ All parallel!
    ├── Phase 4 (Governance) ─── Sentinel +   │ (with Warden review
    │                             Archon      │  on every script)
    ├── Phase 5 (Conflict) ───── Sentinel     │
    ├── Phase 7 (Alliances) ──── Sentinel     │
    │                                         │
    └── Phase 6 (Infra) ─────── depends on 2.3│
                                              ┘
Phase 8 (Validation) ──────── Archon, after ALL others
```

### Task-Level Parallelism

Sentinel and Archon can work on **different tasks simultaneously**.
Warden reviews are sequential per agent (blocking call), but Sentinel and Archon
can each be waiting on separate Warden reviews at the same time.

**Race condition protection:**
Each task has `assigned_to` — Sentinel only claims Sentinel tasks, Archon only Archon tasks.
The atomic Cypher query prevents duplicate claims even with multiple instances.

---

## 7. Cost Model

### Subscriptions (Ingo's setup — all flatrate)

| Agent | Model | Cost | Limit |
|-------|-------|------|-------|
| Dione | Claude Opus (Max 20x) | Subscription | 20x Sonnet rate |
| Archon | Gemini 2.5 Pro | $0 | Google OAuth flatrate |
| Sentinel | Gemini 2.5 Pro | $0 | Google OAuth flatrate |
| Warden | Codex/GPT-5.3 | Subscription | ChatGPT sub |
| Herald | Gemini CLI | $0 | Google OAuth flatrate |
| Inanna | Claude (subagent) | Subscription | Shares Dione's Max 20x |

### External API Costs

| Source | Cost | Auth |
|--------|------|------|
| World Bank API | Free | None needed |
| SIPRI MILEX | Free | Download CSV |
| V-Dem | Free | Download |
| ACLED | Free | Registration |
| UN Comtrade | Free | Rate-limited |
| EIA | Free | None needed |
| Neo4j | Local | No cloud costs |

**Primary cost risk:** Google OAuth rate limits (429s).
**Mitigation:** Exponential backoff + max 1 request/10 seconds.

---

## 8. Startup Sequence

```
Step 1: Dione creates Phase 0 + Phase 1 tasks in Neo4j
    │
Step 2: Dione starts Archon
    │   → Archon claims Phase 0 tasks (normalization infra)
    │   → Phase 0 code already implemented ✅ — Archon verifies + marks complete
    │
Step 3: Dione creates Phase 2–7 tasks in Neo4j
    │
Step 4: Dione starts Sentinel
    │   → Sentinel claims Phase 1.1 (Nation Registry)
    │   → Sentinel generates CIA Factbook ETL script
    │   → Warden reviews script → APPROVED
    │   → Script executes → 195 nations loaded
    │   → Sentinel claims 1.2 + 1.3 (Crosswalk + Borders)
    │
Step 5: Phase 1 complete → Dione starts Sentinel + Archon in parallel
    │   → Sentinel: Phase 2 (Economics), Phase 3 (Military)
    │   → Archon: Phase 4.2 (Faction derivation)
    │   → All scripts reviewed by Warden before execution
    │
Step 6: Per-phase completion → Dione triggers Deep Think review
    │
Step 7: Phase 8 (Validation) → Archon runs topology + completeness tests
    │
Step 8: Dione reports to Ingo:
    │   "Database initially populated. X nations, Y% completeness,
    │    Z data conflicts. Ready for Game Engine integration."
    │
    └── Continuous Improvement Loop begins
```

---

## 9. Continuous Improvement Loop

After initial population, the system runs in an ongoing cycle:

```
┌────────────────────────────────────────────────────────────┐
│                    IMPROVEMENT LOOP                          │
│                                                              │
│  1. Sentinel checks: Any new data at sources?                │
│     (World Bank annual update, ACLED weekly, SIPRI annual)   │
│         │                                                    │
│  2. If yes: Sentinel creates + executes update tasks         │
│     (idempotent, MERGE not CREATE)                           │
│     All scripts reviewed by Warden ← GUARANTEED              │
│         │                                                    │
│  3. Archon checks: Any DataConflicts? New cross-validations? │
│         │                                                    │
│  4. Inanna reviews: Military data changed? New conflicts?    │
│         │                                                    │
│  5. Dione summarizes: Status report to Ingo                  │
│     Deep Think review if significant changes                 │
│         │                                                    │
│  ← Loop back to 1 (triggered by heartbeat, cron, or Ingo)   │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

**Fault tolerance:**
- An agent crashes → Dione restarts it, tasks are recovered from Neo4j
- An API is down → Tasks wait, other phases continue
- Data is wrong → Sanity bounds catch it, task is blocked
- Script has a bug → Warden catches it before execution
- Gemini has an outage → Agents pause, Neo4j data stays safe
- Everything crashes → Neo4j is persistent, Dione reads state from DB on restart

**The system cannot "break" — it can only pause.**
Every state is persisted in Neo4j, every agent is stateless (after memory reset).
On restart, the only question is: "Which tasks are still open?"

---

## 10. Key Design Insights

### Defense in Depth (4 layers of data quality)

```
Layer 1: WARDEN (Codex)     — Reviews code BEFORE execution
Layer 2: SANITY BOUNDS      — Validates data DURING import
Layer 3: INANNA             — Reviews data AFTER import (military domain)
Layer 4: DEEP THINK         — Reviews entire schema/data AFTER phase completion
```

No single point of failure. A bug that passes Warden will be caught by sanity bounds.
A valid-looking but implausible value that passes bounds will be caught by Inanna.
A systemic design issue that passes all agents will be caught by Deep Think review.

### Separation of Concerns (from Orchestration Deep Think review)

```
DIONE    = Strategic orchestration, human interface, phase reviews
WATCHDOG = Mechanical supervision, zombie detection, health reporting
WARDEN   = Code quality gate (stateless, mutex-protected)
AGENTS   = Stateless workers (memory reset after each task)
NEO4J    = Persistent state (survives all crashes)
```

Dione is NOT a process manager. Watchdog handles that via cron.
Agents are NOT stateful. Neo4j holds all state.
Warden is NOT autonomous. It's a synchronous function call.

### Implemented Safeguards (Deep Think Review #2 Action Items)

| # | Safeguard | Implementation |
|---|-----------|----------------|
| 1 | Process supervision extracted | `src/gww3/agents/watchdog.py` — cron daemon, not LLM |
| 2 | Warden context injection | `INTERFACE_CONTEXT` with function signatures |
| 3 | Rate limit mutex | `filelock.FileLock` around `codex exec` calls |
| 4 | JSON structured output | `{"status": "APPROVED/REJECTED", "feedback": "..."}` |
| 5 | Script caching | `src/scripts/approved_etl/` — skip review on recurring tasks |

---

*Dione 🌙 — GWW3 Agent Orchestration Design, 2026-03-24*
