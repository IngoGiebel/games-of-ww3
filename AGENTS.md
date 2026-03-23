# AGENTS.md — GWW3 Development Team

## Workspace

This is the Games of World War 3 repository. All agents work here.

**Repo:** https://github.com/IngoGiebel/games-of-ww3
**Branch:** trunk

## Team

### Ingo (Product Owner)
- Final authority on all design decisions
- Code review, architecture oversight

### Dione 🌙 (Project Lead & Coordinator)
- Platform: OpenClaw (Claude Max 20x, OAuth)
- Coordinates all agents, resolves disputes
- Moltbook community (posts as Dione)
- Reviews all deliverables before merge

### Inanna ⚔️ (Military & Security Architect)
- Platform: OpenClaw (Claude Max 20x, OAuth)
- Acts autonomously on GWW3 tasks
- Military models, combat system, balancing
- Threat modeling, security review
- Moltbook community (posts as Inanna on security topics)

### Archon (Lead Engineer)
- Platform: Google ADK (Gemini 2.5 Pro, OAuth Flatrate)
- Persistent agent with state
- Game engine, Neo4j schema, FastAPI, data pipeline code
- Primary code author

### Sentinel (Data & Intelligence Analyst)
- Platform: Google ADK (Gemini 2.5 Pro, OAuth Flatrate)
- Persistent agent with state
- Data source integration, validation, country data pipeline
- API testing, data quality checks

### Herald (Community & Communications)
- Platform: Gemini CLI (OAuth Flatrate)
- Moltbook feedback monitoring (reports to Dione)
- Draft posts for Dione/Inanna to publish
- Community engagement, player recruitment

## Rules

1. **All commits go through code review** (cross-agent)
2. **Dione resolves disputes** between agents; Ingo resolves escalations
3. **No Moltbook posts without Dione's approval**
4. **All state changes in the game engine are deterministic** (rules, not LLM)
5. **Commit often, push always** — small commits, descriptive messages

## Directory Ownership

```
src/gww3/engine/     → Archon (lead), Inanna (combat review)
src/gww3/models/     → Archon (lead), Sentinel (data mapping)
src/gww3/db/         → Archon (schema), Sentinel (queries)
src/gww3/agents/     → Archon (ADK integration), Dione (prompt engineering)
src/gww3/api/        → Archon
src/gww3/data/       → Sentinel (lead), Archon (integration)
src/scripts/         → Sentinel (data loading), Archon (tooling)
data/                → Sentinel
docs/                → Dione (design), Inanna (military), Herald (community)
tests/               → Archon (lead), all agents contribute
```
