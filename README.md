# 🌍 Games of World War 3

**A hyper-realistic, real-time geopolitical simulation where AI agents control nations.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## Core Philosophy

> Wars are decided socially and economically — not just militarily. Who rallies the population? Who finances the war longest? Who controls the narrative?

Games of World War 3 (GWW3) is a multiplayer geopolitical simulation where AI agents (or humans with AI advisors) control nation-states and non-state actors in a fully interconnected world. Initial state is seeded from 30+ real-world data sources, making every game start from an accurate representation of the current global order.

This is **not** a toy model. Each entity is modeled with >1000 parameters. Power is defined by network position (alliances, trade dependencies, supply routes), not isolated stats.

## Key Features

- **All ~195 nations + non-state actors** (Houthi, Hezbollah, Wagner, Taliban, cartels...)
- **>1000 parameters per entity** sourced from real open data (World Bank, SIPRI, V-Dem, ACLED, IMF, UN)
- **6 conflict dimensions:** Societal, Economic, Military, Cyber, Diplomatic, Informational
- **Neo4j graph database** — "Edges > Properties": relationships define power
- **Multi-agent teams per nation:** Strategist (player), General, Economist, Diplomat, Propagandist, Spymaster
- **Belief Subgraph:** Agents act on what they *think* is true, not ground truth — bad intel → bad decisions
- **War Financing Trilemma:** Taxes vs. Debt vs. Money-printing, each with toxic consequences
- **Emergent balancing:** Superpowers constrained by imperial overstretch, war weariness, and internal politics — no artificial nerfs
- **Real-time with configurable speed** — 1 tick = 1 minute of game time
- **All state changes deterministic** — rules engine, not LLM-evaluated

## Tech Stack

| Component | Technology |
|-----------|------------|
| Game Engine | Python 3.12+ |
| Agent Framework | [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit) |
| API Layer | FastAPI + WebSocket |
| Database | Neo4j (graph relationships + temporal state) |
| Data Pipeline | pandas, httpx |
| Frontend | React + Deck.gl (3D globe) — planned |

## Architecture

```
┌──────────────────────────────────────────────┐
│                 Web UI (React)                │
│    Live World Map │ Dashboard │ Agent Debate  │
└─────────────────────┬────────────────────────┘
                      │ WebSocket (real-time)
┌─────────────────────▼────────────────────────┐
│              API Gateway (FastAPI)            │
└────┬──────────┬──────────┬───────────────────┘
     │          │          │
┌────▼───┐ ┌───▼────┐ ┌───▼──────────────┐
│ Game   │ │ Agent  │ │ Data Pipeline    │
│ Engine │ │ Manager│ │ (Import/Update)  │
│        │ │        │ │                  │
│ Pulse  │ │ LLM    │ │ World Bank, SIPRI│
│ Engine │ │ Router │ │ V-Dem, ACLED, ...│
│ Rules  │ │ Cabinet│ │                  │
│ Events │ │ AIGA   │ │                  │
└────┬───┘ └───┬────┘ └───┬──────────────┘
     │         │           │
┌────▼─────────▼───────────▼───────────────────┐
│              Neo4j Graph Database             │
│  Nations │ Factions │ Commodities │ Ticks     │
│  Edges: Trade, Alliance, War, Supply, Belief  │
└──────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone
git clone https://github.com/IngoGiebel/games-of-ww3.git
cd games-of-ww3

# Install (requires Python 3.12+)
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Load sample country data
python src/scripts/load_country_data.py
```

> **Note:** Neo4j must be running locally or remotely for full functionality. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for setup instructions.

## Project Structure

```
games-of-ww3/
├── README.md                          # This file
├── AGENTS.md                          # Development team roles & ownership
├── SPRINTS.md                         # Sprint planning (Sprint 0–5)
├── LICENSE                            # MIT License
├── pyproject.toml                     # Python project config
│
├── docs/                              # Documentation
│   ├── DESIGN_v0.2.md                 # ★ Consolidated fine concept (the master design doc)
│   ├── AGENT-FRAMEWORK.md             # Development agent team, LLMs, workflows, costs
│   ├── ARCHITECTURE.md                # System design & data flow (original)
│   ├── DATA_SOURCES_CATALOG.md        # 30+ open data sources with API details
│   ├── DATA_SOURCES.md                # Original data sources reference
│   ├── DEEP_THINK_ANALYSIS.md         # Gemini Deep Think analysis results
│   ├── GAME_DESIGN_v0.1.md            # Initial game design document
│   ├── GAME_RULES.md                  # Original game rules (being superseded by v0.2)
│   └── deep-think-project-review-prompt.md  # Review prompt for Sprint 1 readiness
│
├── agents/                            # Development agent definitions (ADK)
│   ├── archon/agent.py                # Lead Engineer agent (Gemini 2.5 Pro)
│   ├── sentinel/agent.py              # Data Analyst agent (Gemini 2.5 Pro)
│   └── herald/agent.py                # Community Manager agent (Gemini CLI)
│
├── src/gww3/                          # Game source code
│   ├── engine/
│   │   └── pulse.py                   # Multi-Resolution Pulse Engine (tick system)
│   ├── db/
│   │   └── schema.py                  # Neo4j schema (nodes, relationships, constraints)
│   ├── models/
│   │   └── country.py                 # Country data model
│   ├── data/                          # Data loaders & transformers
│   ├── agents/                        # Game-playing AI agents (Strategist, General, etc.)
│   └── api/                           # FastAPI endpoints
│
├── src/scripts/
│   └── load_country_data.py           # Country data import script
│
├── data/
│   └── countries/                     # Sample country data (JSON)
│       ├── USA.json
│       ├── CHN.json
│       ├── RUS.json
│       ├── DEU.json
│       └── IND.json
│
└── tests/
    └── test_pulse.py                  # Pulse Engine tests (5 passing)
```

## Key Documents

| Document | Description | Status |
|----------|-------------|--------|
| [**DESIGN_v0.2.md**](docs/DESIGN_v0.2.md) | Consolidated fine concept — the master design document covering vision, entity model, conflict systems, time model, agent architecture, and scoring | ★ Current |
| [**AGENT-FRAMEWORK.md**](docs/AGENT-FRAMEWORK.md) | Development team definition: who builds what, with which LLMs, decision structure, checks & balances, sprint plan, cost model | ★ Current |
| [**DATA_SOURCES_CATALOG.md**](docs/DATA_SOURCES_CATALOG.md) | Comprehensive catalog of 30+ open data sources with API endpoints, formats, rate limits, and Neo4j ingestion notes | ★ Current |
| [**DEEP_THINK_ANALYSIS.md**](docs/DEEP_THINK_ANALYSIS.md) | Critical analysis of 5 design challenges: balancing, war financing, time model, agent consensus, gap synthesis | Reference |
| [GAME_DESIGN_v0.1.md](docs/GAME_DESIGN_v0.1.md) | Original game design document (superseded by v0.2) | Archive |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Original system architecture (being updated) | Archive |
| [GAME_RULES.md](docs/GAME_RULES.md) | Original game rules (being superseded by v0.2) | Archive |
| [DATA_SOURCES.md](docs/DATA_SOURCES.md) | Original data sources reference (superseded by catalog) | Archive |

## Development Team

GWW3 is built by a multi-agent team, all running on flat-rate subscriptions (zero API costs):

| Agent | Role | Platform | Subscription |
|-------|------|----------|-------------|
| **Ingo** | Product Owner | Human | — |
| **Dione** 🌙 | Project Lead & Coordinator | OpenClaw (Claude Opus 4) | Anthropic Claude Max 20x |
| **Inanna** ⚔️ | Military & Security Architect | OpenClaw (Claude) | Anthropic Claude Max 20x |
| **Archon** | Lead Engineer | Google ADK (Gemini 2.5 Pro) | Google One AI Ultra |
| **Sentinel** | Data & Intelligence Analyst | Google ADK (Gemini 2.5 Pro) | Google One AI Ultra |
| **Herald** | Community & Communications | Gemini CLI (Gemini 2.5 Pro) | Google One AI Ultra |

Decision flow: Agents → **Dione** (resolves disputes) → **Ingo** (strategic decisions).

See [AGENTS.md](AGENTS.md) for directory ownership and [docs/AGENT-FRAMEWORK.md](docs/AGENT-FRAMEWORK.md) for full team definition.

## Sprint Status

| Sprint | Goal | Status |
|--------|------|--------|
| **Sprint 0** | Project setup, design docs, agent framework | ✅ Complete |
| **Sprint 1** | Neo4j schema + first country data load | 🔜 Next |
| **Sprint 2** | Data pipeline (World Bank, V-Dem, SIPRI) | Planned |
| **Sprint 3** | Game engine core (Pulse + Rules Engine) | Planned |
| **Sprint 4** | AI game agents (ADK) | Planned |
| **Sprint 5** | Web UI MVP | Planned |

See [SPRINTS.md](SPRINTS.md) for detailed task breakdowns and acceptance criteria.

## Community

Join the discussion:
- **Moltbook:** [m/wargames](https://www.moltbook.com/m/wargames) | [m/engineering](https://www.moltbook.com/m/engineering) | [m/maschinenvolk](https://www.moltbook.com/m/maschinenvolk)
- **GitHub Issues:** [Report bugs or suggest features](https://github.com/IngoGiebel/games-of-ww3/issues)

## License

[MIT](LICENSE)

---

*"Properties define state. Edges define power."*
