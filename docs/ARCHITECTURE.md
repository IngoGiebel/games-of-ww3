# Architecture

## System Overview

GWW3 is composed of four layers, each with clear responsibilities:

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                             │
│  AI Agents (ADK, LangChain, custom) · Human UI · CLI        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST + WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                     API LAYER (FastAPI)                       │
│  POST /games                    Create a new game            │
│  POST /games/{id}/join          Join as a nation             │
│  GET  /games/{id}/state         Current world state          │
│  POST /games/{id}/actions       Submit turn actions          │
│  GET  /games/{id}/results       Turn resolution results      │
│  WS   /games/{id}/events        Real-time event stream       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                     ENGINE LAYER                             │
│  Turn Manager          Orchestrates phase progression        │
│  Phase Resolvers       Economic · Diplomatic · Military      │
│  Rules Engine          Validates actions, enforces limits     │
│  Event Bus             Publishes state changes               │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                     DATA LAYER (Neo4j)                        │
│  Nodes: Nation, Region, Resource, Technology, Alliance       │
│  Edges: TRADES_WITH, ALLIED_TO, BORDERS, SANCTIONS,          │
│         OCCUPIES, SUPPLIES, THREATENS                        │
└─────────────────────────────────────────────────────────────┘
```

## Why Neo4j?

Geopolitics is fundamentally about **relationships**. A relational database can store countries in rows, but the interesting part — alliances, trade dependencies, territorial disputes, sanctions chains — is a graph problem.

Neo4j lets us:
- Query alliance networks: *"Which nations are within 2 hops of NATO?"*
- Model trade dependencies: *"If China sanctions Australia, which supply chains break?"*
- Track cascading effects: *"If Turkey blocks the Bosphorus, who loses oil access?"*
- Represent territorial control and border conflicts naturally

## Data Flow: How a Turn Works

```
                    ┌──────────────┐
                    │  TURN START  │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │   1. ECONOMIC PHASE     │
              │   Players submit:       │
              │   - Trade agreements    │
              │   - Sanctions           │
              │   - Investment          │
              │   - Resource allocation │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   2. DIPLOMATIC PHASE   │
              │   Players submit:       │
              │   - Alliance proposals  │
              │   - Treaties            │
              │   - UN resolutions      │
              │   - Espionage orders    │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   3. MILITARY PHASE     │
              │   Players submit:       │
              │   - Troop movements     │
              │   - Arms buildup        │
              │   - Naval deployments   │
              │   - Nuclear posture     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   4. RESOLUTION         │
              │   Engine processes:     │
              │   - Conflict resolution │
              │   - Economic updates    │
              │   - Alliance changes    │
              │   - Casualty reports    │
              │   - GDP recalculation   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   5. BROADCAST          │
              │   - State diff to all   │
              │   - Intel reports       │
              │   - News events         │
              │   - Victory checks      │
              └────────────┬────────────┘
                           │
                    ┌──────▼───────┐
                    │   TURN END   │
                    └──────────────┘
```

### Phase Details

Each phase collects actions simultaneously from all players (simultaneous turns, not sequential). The resolution phase processes all actions together, handling conflicts and dependencies.

**Simultaneous resolution** is critical — no player has a first-mover advantage within a turn. If two nations both order attacks on each other, both attacks execute.

### Information Model

Players receive:
- **Full visibility:** Own nation's complete state, public international events
- **Partial visibility:** Neighboring nations' military movements (based on intelligence capability)
- **Hidden:** Other nations' exact economic data, secret alliances, nuclear launch codes

This fog-of-war model encourages espionage and intelligence investment.

## Agent Integration

### Playing via REST API

Any HTTP client can play. A minimal agent loop:

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# Join a game as Germany
client.post("/games/1/join", json={"nation": "DEU"})

while True:
    # Get current state
    state = client.get("/games/1/state").json()
    
    # Decide actions (this is where the AI lives)
    actions = my_agent.decide(state)
    
    # Submit actions
    client.post("/games/1/actions", json=actions)
    
    # Wait for resolution
    results = client.get("/games/1/results").json()
```

### Google ADK Reference Agents

The project includes reference agents built with Google ADK that demonstrate:
- Economic strategy (trade optimization, sanctions response)
- Military doctrine (deterrence, escalation ladders)
- Diplomatic maneuvering (alliance building, treaty negotiation)

These serve as both opponents for testing and examples for agent developers.

## Multi-Agent Development Team

GWW3 itself is built by a team of AI agents, each with domain expertise:

### Dione 🌙 — Economics & Data
- Designs the economic simulation (GDP growth, trade flows, debt, inflation)
- Builds data pipelines from World Bank, UN COMTRADE
- Validates economic models against real-world behavior
- Ensures resource allocation mechanics are realistic

### Inanna ⚔️ — Military & Security
- Designs combat resolution systems
- Models nuclear deterrence (MAD, first-strike capability, second-strike survival)
- Builds threat assessment algorithms
- Designs military unit types and force projection mechanics

### Codex 🔧 — Implementation
- Translates designs into working code
- Writes tests and CI/CD pipelines
- Handles Neo4j schema and queries
- Builds the FastAPI layer

### Gemini 🔍 — Research
- Sources real-world data (military capabilities, economic indicators)
- Fact-checks game parameters against reality
- Researches geopolitical scenarios for testing
- Reviews academic literature on conflict simulation

### Collaboration Pattern

```
Dione/Inanna → Design documents → Codex → Implementation
                                      ↑
                    Gemini → Research ──┘
```

Design decisions flow from domain experts (Dione, Inanna) to the implementer (Codex), with Gemini providing research support to all agents. All agents can review and comment on each other's work through GitHub issues and PRs.

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `gww3.engine` | Turn management, phase orchestration, action validation |
| `gww3.engine.resolvers` | Phase-specific resolution logic (economic, diplomatic, military) |
| `gww3.models` | Data models: Country, Military, Economy, Alliance, Trade |
| `gww3.data` | ETL from real-world sources into game-ready format |
| `gww3.agents` | Google ADK agent definitions for reference AI players |
| `gww3.api` | FastAPI application, routes, auth, WebSocket events |
| `gww3.db` | Neo4j driver, queries, schema management |

## Key Design Decisions

1. **Simultaneous turns** — All players submit actions before resolution. No first-mover advantage.
2. **Graph database** — Relationships between nations are the core of the simulation.
3. **Real data seeding** — Games start from reality, diverge based on player actions.
4. **API-first** — The game is a server; agents are clients. No tight coupling.
5. **Fog of war** — Imperfect information drives strategic depth.
6. **Deterministic resolution with random elements** — Combat has variance, but identical inputs produce identical outputs (seeded RNG for reproducibility).
