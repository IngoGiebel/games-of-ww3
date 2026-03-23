# GWW3 — Development Agent Framework

**Zweck:** Wer baut das Spiel, mit welchen Rollen, LLMs und Workflows?

---

## 1. Entwicklungs-Agenten (wer baut GWW3)

### Tier 1: Entscheider & Koordination

| Agent | Rolle | LLM/Plattform | Zuständigkeit |
|-------|-------|---------------|---------------|
| **Ingo** | Product Owner | Mensch | Finale Entscheidungen, Architektur, Code-Review |
| **Dione 🌙** | Projektleiterin & Koordinatorin | Claude Opus (OpenClaw) | Gesamtkoordination, Aufgabenverteilung, Review aller Outputs, Moltbook-Community, Finanzdaten-Integration, Entscheidungen bei Agenten-Dissens |

### Tier 2: Spezialisten

| Agent | Rolle | LLM/Plattform | Zuständigkeit |
|-------|-------|---------------|---------------|
| **Inanna ⚔️** | Military & Security Architect | Claude (OpenClaw, Inanna-Instanz) | Militärmodelle, Konfliktsimulation, Balancing, Threat Modeling, PoW-Security-Expertise übertragen auf Spielmechanik |
| **Archon** (neu) | Lead Engineer | Google ADK (Gemini 2.5 Pro, OAuth) | Game Engine, Neo4j Schema, FastAPI, Data Pipeline — der Code-Agent |
| **Sentinel** (neu) | Data & Intelligence Analyst | Google ADK (Gemini 2.5 Pro, OAuth) | Datenquellen-Integration, Validierung, Länderdaten-Pipeline, Lückenanalyse |
| **Herald** (neu) | Community & Communications | Codex (GPT-4.1) oder Claude Sonnet | Moltbook-Feedback-Monitoring, X-Posts, Community-Engagement, Spieler-Rekrutierung |

### Tier 3: On-Demand (für spezifische Tasks)

| Agent | Rolle | LLM | Wann |
|-------|-------|-----|------|
| **Gemini Deep Think** | Strategic Analyst | Gemini 2.5 Pro (manuell, Ingo) | Tiefe Designfragen, Balancing, komplexe Analysen |
| **Codex** | Coding Tasks | GPT-4.1 | Spezifische Implementierungsaufgaben |
| **Claude Code** | Coding Tasks | Claude Opus/Sonnet | Alternativ für Code-Review, Refactoring |

---

## 2. Informationsfluss & Entscheidungsstruktur

```
                    Ingo (Product Owner)
                        │
                        │ Grundsatzentscheidungen
                        ▼
                ┌───────────────────┐
                │   Dione 🌙        │
                │   (Projektleiterin)│
                │   ENTSCHEIDET bei │
                │   Agenten-Dissens │
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
              gegenseitiges Review              │
              (Checks & Balances)               │
                                                │
                                    Moltbook, X, GitHub Issues
```

### Checks & Balances

| Situation | Wer prüft wen |
|-----------|---------------|
| Archon schreibt Neo4j Schema | Inanna prüft Militärmodell-Vollständigkeit, Sentinel prüft Datenquellen-Kompatibilität |
| Sentinel liefert Länderdaten | Archon prüft Schema-Konformität, Inanna prüft Militärdaten-Plausibilität |
| Inanna entwirft Kampfsystem | Archon prüft Implementierbarkeit, Dione prüft Balancing-Philosophie |
| Herald formuliert Post | Dione prüft Inhalt + Ton vor Veröffentlichung |
| Dissens zwischen Agenten | **Dione entscheidet** (bei Grundsatzfragen → Ingo eskalieren) |

### Informationsaustausch

| Von → An | Kanal | Inhalt |
|----------|-------|--------|
| Alle → Dione | OpenClaw (sessions_send) | Status-Updates, Ergebnisse, Fragen |
| Dione → Alle | Task-Zuweisung (sessions_spawn) | Aufgaben mit klarem Scope + Deadline |
| Archon ↔ Sentinel | Shared files in `/tmp/games-of-ww3/` | Schema-Entwürfe, Daten-Samples |
| Archon ↔ Inanna | Shared files | Modell-Specs, Implementierungs-Fragen |
| Herald → Dione | Zusammenfassung | Moltbook-Feedback, Community-Stimmung |
| Ingo → Dione | Telegram | Entscheidungen, Richtungsänderungen |

---

## 3. LLM-Strategie & Kosten

### Prinzip: Ingos Gemini Ultra Flatrate maximal nutzen!

| Agent | LLM | Kosten | Begründung |
|-------|-----|--------|------------|
| **Dione** | Claude Opus (OpenClaw) | API-Kosten | Koordination braucht Langzeit-Kontext + Tool-Zugriff |
| **Inanna** | Claude (OpenClaw) | API-Kosten | Eigenständige Instanz, Security-Expertise |
| **Archon** | Gemini 2.5 Pro via ADK (OAuth) | **Flatrate!** | Hauptlast der Code-Generierung → Flatrate nutzen |
| **Sentinel** | Gemini 2.5 Pro via ADK (OAuth) | **Flatrate!** | Daten-Recherche, API-Tests → Flatrate nutzen |
| **Herald** | Gemini 2.5 Pro via Gemini CLI (OAuth) | **Flatrate!** | Text-Generierung → Flatrate nutzen |
| **Deep Think** | Gemini 2.5 Pro (manuell) | **Flatrate!** | Ingo startet bei Bedarf |
| **Codex** | GPT-4.1 | API-Kosten | Nur für spezifische Tasks wo GPT besser passt |

**Ergebnis:** 4 von 6 Agenten laufen über Gemini-Flatrate. Nur Dione + Inanna brauchen Claude-API.

### Google ADK Setup (OAuth, keine API-Keys!)

```python
# ADK nutzt OAuth Credentials von Gemini CLI
# ~/.gemini/oauth_creds.json wird automatisch gefunden
# Kein GOOGLE_API_KEY nötig!

from google.adk import Agent

archon = Agent(
    name="Archon",
    model="gemini-2.5-pro",
    system_instruction="You are Archon, the Lead Engineer for Games of World War 3...",
    tools=[...],  # Neo4j queries, file I/O, shell
)
```

**Wichtig:** ADK mit `adk web` oder programmatisch starten — OAuth-Flow nutzt die existierenden Credentials aus `~/.gemini/oauth_creds.json`.

---

## 4. Aktivitäts-Zyklen

### Regelmäßig (automatisiert via Cron/Heartbeat)

| Agent | Frequenz | Aufgabe |
|-------|----------|---------|
| **Herald** | Alle 6h | Moltbook-Feedback checken (Kommentare auf GWW3-Posts), zusammenfassen für Dione |
| **Dione** | Bei jedem Heartbeat | Herald-Zusammenfassung prüfen, ggf. auf Moltbook antworten |
| **Sentinel** | 1x täglich | Datenquellen-Status prüfen (APIs erreichbar? Neue Datasets?) |

### Sprint-basiert (Task-gesteuert durch Dione)

| Phase | Agenten aktiv | Dauer | Deliverable |
|-------|---------------|-------|-------------|
| **Sprint 1: Schema** | Archon (lead), Inanna (review), Sentinel (data-mapping) | 1 Woche | Neo4j Cypher Schema v1 |
| **Sprint 2: Pipeline** | Sentinel (lead), Archon (integration) | 1 Woche | World Bank + V-Dem → Neo4j Import |
| **Sprint 3: Engine** | Archon (lead), Inanna (combat model) | 2 Wochen | Pulse Engine + Rules Engine MVP |
| **Sprint 4: Agents** | Archon (ADK setup), Dione (prompt engineering) | 1 Woche | 6 Game-Agenten (Strategist etc.) als ADK Agents |
| **Sprint 5: UI** | Archon (API), Herald (testing/feedback) | 2 Wochen | React + Globe MVP |

### Kontrolle & Reporting

| Was | Wer | Wann |
|-----|-----|------|
| Sprint-Planung | Dione (mit Ingo-Approval) | Montags |
| Daily Status | Alle aktiven Agenten → Dione | Bei Task-Abschluss oder Blocker |
| Sprint-Review | Dione → Ingo (Telegram) | Freitags |
| Moltbook-Update | Herald (Dione-approved) | Bei Meilensteinen |
| Code-Review | Cross-Agent (Archon↔Inanna) | Bei jedem PR/Merge |

---

## 5. Aufgaben & Meilensteine (nächste 4 Wochen)

### Woche 1: Foundation
- [ ] **ADK-Setup:** Archon + Sentinel als ADK-Agents konfigurieren (OAuth!)
- [ ] **Neo4j Schema v1:** Nodes, Relationships, Temporal Model (Archon + Inanna)
- [ ] **Daten-Mapping:** Welche Source → welcher Node/Edge (Sentinel)
- [ ] **Moltbook-Feedback:** Erste Reaktionen sammeln (Herald)

### Woche 2: Data Pipeline
- [ ] **World Bank Importer:** Top 50 Indikatoren → Neo4j (Sentinel + Archon)
- [ ] **V-Dem Importer:** Governance-Daten → Neo4j (Sentinel)
- [ ] **SIPRI Importer:** Militärausgaben → Neo4j (Sentinel + Inanna-Review)
- [ ] **Country Nodes:** Alle ~195 Nationen mit Basisdaten geladen

### Woche 3: Game Engine Core
- [ ] **Pulse Engine:** Multi-Resolution Tick System (Archon)
- [ ] **Rules Engine:** Deterministische Zustandsänderungen (Archon + Inanna)
- [ ] **Temporal Model:** State Snapshots als Tick-Kette in Neo4j (Archon)
- [ ] **Combat Prototype:** Vereinfachtes Kampfmodell (Inanna)

### Woche 4: Agent Integration
- [ ] **ADK Game Agents:** Strategist + Economist als ADK-Agents (Archon)
- [ ] **Cabinet Protocol:** Briefing → Debate → Resolution (Archon + Dione)
- [ ] **First Game:** 2-Nationen Test (USA vs China, vereinfacht)
- [ ] **Moltbook Milestone Post:** "Erste Partie gespielt!" (Herald)

---

## 6. Entscheidungen (Ingo, 23.03.2026)

1. **Moltbook:** Alle Posts über Dione oder Inanna — keine weiteren Accounts
2. **ADK-Agents:** Persistent (mit State)
3. **Inanna:** Handelt eigenständig auf GWW3-Tasks
4. **Sprint-Start:** Sobald Projektstruktur steht
5. **Budget:** Alle Agenten auf Flatrates:
   - Dione + Inanna: **Claude Max 20x** (OAuth, Flatrate)
   - Archon + Sentinel + Herald: **Gemini Ultra** (OAuth, Flatrate)
   - → **Keine API-Kosten**, nur Durchsatz-Limits beachten

---

*"Edges > Properties" — auch in der Projektorganisation.*
*Erstellt: 2026-03-23 von Dione 🌙*
