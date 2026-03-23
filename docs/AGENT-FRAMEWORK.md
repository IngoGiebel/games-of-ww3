# GWW3 — Development Agent Framework

**Purpose:** Who builds the game, with which roles, LLMs, and workflows?

---

## 1. Development Agents

### Tier 1: Decision Makers & Coordination

| Agent | Role | LLM/Platform | Responsibilities |
|-------|------|--------------|------------------|
| **Ingo** | Product Owner | Human | Final decisions, architecture, code review |
| **Dione 🌙** | Project Lead & Coordinator | Claude Opus (OpenClaw, Claude Max 20x subscription) | Overall coordination, task assignment, review of all outputs, Moltbook community, financial data integration, dispute resolution between agents |

### Tier 2: Specialists

| Agent | Role | LLM/Platform | Responsibilities |
|-------|------|--------------|------------------|
| **Inanna ⚔️** | Military & Security Architect | Claude (OpenClaw, Claude Max 20x subscription) | Military models, conflict simulation, balancing, threat modeling, PoW security expertise applied to game mechanics |
| **Archon** | Lead Engineer | Google ADK (Gemini 2.5 Pro, OAuth) | Game engine, Neo4j schema, FastAPI, data pipeline — the primary code author |
| **Sentinel** | Data & Intelligence Analyst | Google ADK (Gemini 2.5 Pro, OAuth) | Data source integration, validation, country data pipeline, gap analysis |
| **Herald** | Community & Communications | Gemini CLI (OAuth) | Moltbook feedback monitoring, X posts, community engagement, player recruitment |

### Tier 3: On-Demand (for specific tasks)

| Agent | Role | LLM | When |
|-------|------|-----|------|
| **Gemini Deep Think** | Strategic Analyst | Gemini 3.1 Pro (manual, by Ingo) | Deep design questions, balancing, complex analyses |
| **Codex** | Coding Tasks | GPT-5.3 Codex | Specific implementation tasks |
| **Claude Code** | Coding Tasks | Claude Opus/Sonnet | Alternative for code review, refactoring |

---

## 2. Information Flow & Decision Structure

```
                    Ingo (Product Owner)
                        │
                        │ Strategic decisions
                        ▼
                ┌───────────────────┐
                │   Dione 🌙        │
                │  (Project Lead)   │
                │  DECIDES on agent │
                │     disputes      │
                └───┬───┬───┬───┬──┘
                    │   │   │   │
          ┌─────────┘   │   │   └──────────┐
          ▼             ▼   ▼              ▼
    ┌──────────┐  ┌────────┐ ┌──────────┐ ┌────────┐
    │ Inanna ⚔️│  │ Archon │ │ Sentinel │ │ Herald │
    │ Military │  │Engineer│ │  Data    │ │Communi-│
    │ & Balance│  │ & Code │ │ Pipeline │ │  cation│
    └──────────┘  └────────┘ └──────────┘ └────────┘
         │              │          │            │
         └──────────────┴──────────┘            │
              Cross-agent review                │
              (Checks & Balances)               │
                                                │
                                    Moltbook, X, GitHub Issues
```

### Checks & Balances

| Situation | Who reviews whom |
|-----------|-----------------|
| Archon writes Neo4j schema | Inanna reviews military model completeness, Sentinel checks data source compatibility |
| Sentinel delivers country data | Archon checks schema conformity, Inanna validates military data plausibility |
| Inanna designs combat system | Archon checks implementability, Dione validates balancing philosophy |
| Herald drafts a post | Dione reviews content + tone before publication |
| Dispute between agents | **Dione decides** (strategic questions → escalate to Ingo) |

### Information Exchange

| From → To | Channel | Content |
|-----------|---------|---------|
| All → Dione | OpenClaw (sessions_send) | Status updates, results, questions |
| Dione → All | Task assignment (sessions_spawn) | Tasks with clear scope + deadline |
| Archon ↔ Sentinel | Shared files in repo | Schema drafts, data samples |
| Archon ↔ Inanna | Shared files | Model specs, implementation questions |
| Herald → Dione | Summary reports | Moltbook feedback, community sentiment |
| Ingo → Dione | Telegram | Decisions, direction changes |

---

## 3. LLM Strategy & Costs

### Principle: All agents run on flat-rate subscriptions — zero API costs!

| Agent | LLM | Subscription | Notes |
|-------|-----|-------------|-------|
| **Dione** | Claude Opus 4 (OpenClaw) | **Claude Max 20x** (OAuth, flat rate) | Long-context coordination + tool access |
| **Inanna** | Claude (OpenClaw) | **Claude Max 20x** (OAuth, flat rate) | Autonomous instance, security expertise |
| **Archon** | Gemini 2.5 Pro via ADK (OAuth) | **Google One AI Ultra** (flat rate) | Primary code generation workload |
| **Sentinel** | Gemini 2.5 Pro via ADK (OAuth) | **Google One AI Ultra** (flat rate) | Data research, API testing |
| **Herald** | Gemini 2.5 Pro via Gemini CLI (OAuth) | **Google One AI Ultra** (flat rate) | Text generation, community drafts |
| **Deep Think** | Gemini 3.1 Pro (manual) | **Google One AI Ultra** (flat rate) | Ingo triggers manually for deep analysis |
| **Codex** | GPT-5.3 Codex | **ChatGPT subscription** (flat rate) | Specific tasks where GPT excels |

**Result: 100% flat-rate operation.** No per-token API costs for any agent.

- Dione + Inanna → Anthropic Claude Max 20x subscription
- Archon + Sentinel + Herald + Deep Think → Google One AI Ultra subscription
- Codex → ChatGPT subscription
- Only constraint: throughput/rate limits of each subscription tier

### Google ADK Setup (OAuth — no API keys!)

```python
# ADK uses OAuth credentials from Gemini CLI
# ~/.gemini/oauth_creds.json is auto-discovered
# No GOOGLE_API_KEY needed!

from google.adk import Agent

archon = Agent(
    name="Archon",
    model="gemini-2.5-pro",
    system_instruction="You are Archon, the Lead Engineer for Games of World War 3...",
    tools=[...],  # Neo4j queries, file I/O, shell
)
```

**Important:** Start ADK with `adk web` or programmatically — the OAuth flow uses existing credentials from `~/.gemini/oauth_creds.json`.

---

## 4. Activity Cycles

### Regular (automated via Cron/Heartbeat)

| Agent | Frequency | Task |
|-------|-----------|------|
| **Herald** | Every 6h | Check Moltbook feedback (comments on GWW3 posts), summarize for Dione |
| **Dione** | Every heartbeat | Review Herald's summary, respond on Moltbook if needed |
| **Sentinel** | Once daily | Check data source status (APIs reachable? New datasets?) |

### Sprint-based (task-driven by Dione)

| Phase | Active agents | Duration | Deliverable |
|-------|---------------|----------|-------------|
| **Sprint 1: Schema** | Archon (lead), Inanna (review), Sentinel (data mapping) | 1 week | Neo4j Cypher Schema v1 |
| **Sprint 2: Pipeline** | Sentinel (lead), Archon (integration) | 1 week | World Bank + V-Dem → Neo4j import |
| **Sprint 3: Engine** | Archon (lead), Inanna (combat model) | 2 weeks | Pulse Engine + Rules Engine MVP |
| **Sprint 4: Agents** | Archon (ADK setup), Dione (prompt engineering) | 1 week | 6 game agents (Strategist etc.) as ADK agents |
| **Sprint 5: UI** | Archon (API), Herald (testing/feedback) | 2 weeks | React + Globe MVP |

### Control & Reporting

| What | Who | When |
|------|-----|------|
| Sprint planning | Dione (with Ingo approval) | Mondays |
| Status updates | All active agents → Dione | On task completion or blocker |
| Sprint review | Dione → Ingo (Telegram) | Fridays |
| Moltbook update | Herald (Dione-approved) | On milestones |
| Code review | Cross-agent (Archon ↔ Inanna) | On every PR/merge |

---

## 5. Tasks & Milestones (next 4 weeks)

### Week 1: Foundation
- [ ] **ADK setup:** Configure Archon + Sentinel as persistent ADK agents (OAuth!)
- [ ] **Neo4j Schema v1:** Nodes, relationships, temporal model (Archon + Inanna)
- [ ] **Data mapping:** Which source → which node/edge (Sentinel)
- [ ] **Moltbook feedback:** Collect initial reactions (Herald)

### Week 2: Data Pipeline
- [ ] **World Bank importer:** Top 50 indicators → Neo4j (Sentinel + Archon)
- [ ] **V-Dem importer:** Governance data → Neo4j (Sentinel)
- [ ] **SIPRI importer:** Military expenditure → Neo4j (Sentinel + Inanna review)
- [ ] **Country nodes:** All ~195 nations loaded with baseline data

### Week 3: Game Engine Core
- [ ] **Pulse Engine:** Multi-resolution tick system (Archon)
- [ ] **Rules Engine:** Deterministic state transitions (Archon + Inanna)
- [ ] **Temporal model:** State snapshots as tick chain in Neo4j (Archon)
- [ ] **Combat prototype:** Simplified combat model (Inanna)

### Week 4: Agent Integration
- [ ] **ADK game agents:** Strategist + Economist as ADK agents (Archon)
- [ ] **Cabinet protocol:** Briefing → Debate → Resolution (Archon + Dione)
- [ ] **First game:** 2-nation test (USA vs China, simplified)
- [ ] **Moltbook milestone post:** "First match played!" (Herald)

---

## 6. Decisions (Ingo, 2026-03-23)

1. **Moltbook:** All posts through Dione or Inanna — no additional accounts
2. **ADK agents:** Persistent (with state)
3. **Inanna:** Acts autonomously on GWW3 tasks
4. **Sprint start:** Once project structure is finalized
5. **Budget:** All agents on flat-rate subscriptions:
   - Dione + Inanna: **Anthropic Claude Max 20x** (OAuth, flat rate)
   - Archon + Sentinel + Herald: **Google One AI Ultra** (OAuth, flat rate)
   - Codex: **ChatGPT subscription** (flat rate)
   - → **Zero API costs**, only throughput limits apply

---

*"Edges > Properties" — in project organization too.*
*Created: 2026-03-23 by Dione 🌙*
