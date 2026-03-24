# GWW3 — Agent Orchestrierung & Kollaboration

*Created: 2026-03-24 by Dione 🌙*
*Status: Designdokument für Implementierung*

---

## 1. Überblick: Wer macht was?

```
┌────────────────────────────────────────────────────────────────────┐
│                        INGO (Mensch)                               │
│  Entscheidet: Strategie, Budget, Prioritäten, Go/No-Go            │
│  Interagiert via: Telegram → Dione                                 │
└─────────────────────────┬──────────────────────────────────────────┘
                          │ natural language
┌─────────────────────────▼──────────────────────────────────────────┐
│                    DIONE 🌙 (Orchestrator)                         │
│  Runtime: OpenClaw Main Session (Claude Opus)                      │
│  Rolle: Projektleiterin, Task-Erstellung, Quality Gate             │
│  Kommuniziert mit Agenten via: OpenClaw sessions_spawn / Gemini CLI│
└──────┬──────────────┬──────────────┬──────────────┬────────────────┘
       │              │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
│  ARCHON     │ │  SENTINEL  │ │  INANNA  │ │  HERALD    │
│  (Engineer) │ │  (Analyst) │ │  (Review)│ │  (Comms)   │
│  Gemini 2.5 │ │  Gemini 2.5│ │  Claude  │ │  Gemini    │
│  ADK Agent  │ │  ADK Agent │ │  OpenClaw│ │  CLI       │
└──────┬──────┘ └─────┬──────┘ └────┬─────┘ └─────┬──────┘
       │              │              │              │
       └──────────────┴──────┬───────┴──────────────┘
                             │
                    ┌────────▼────────┐
                    │   Neo4j Graph   │
                    │  (Single Source  │
                    │   of Truth)     │
                    └─────────────────┘
```

---

## 2. Agentenprofile im Detail

### Dione 🌙 — Orchestrator & Quality Gate

**Runtime:** OpenClaw Main Session (Claude Opus, via Telegram)
**Warum Claude:** Langform-Reasoning, Kontext über Ingos gesamtes Workspace, direkte Telegram-Kommunikation

**Verantwortung:**
- **Task-Erstellung:** Liest DATA_LOADING_PLAN.md, erstellt Task-Nodes in Neo4j
- **Monitoring:** Prüft Task-Status bei Heartbeats, erkennt blockierte/fehlgeschlagene Tasks
- **Quality Gate:** Reviewed ImportBatch-Ergebnisse bevor sie als "verified" gelten
- **Eskalation:** Informiert Ingo bei blocked Tasks, Daten-Konflikten, Budget-Überschreitungen
- **Deep Think Trigger:** Erstellt Review-Prompts nach Phasen-Abschluss

**Dione startet Agenten so:**
```python
# Sentinel starten (Gemini CLI im games-of-ww3 Verzeichnis)
exec(command="cd /home/uranus/moltbot-workspace/projects/games-of-ww3 && "
     "gemini -p 'Du bist Sentinel, der Data Analyst Agent für GWW3. "
     "Lies AGENTS.md für deine Rolle. "
     "Claim deinen nächsten Task aus Neo4j mit der atomic query aus "
     "AGENT_ARCHITECTURE_V2.md. Führe ihn aus und committe das Ergebnis.'",
     background=True)

# Archon starten (separater Gemini CLI Prozess)
exec(command="cd /home/uranus/moltbot-workspace/projects/games-of-ww3 && "
     "gemini -p 'Du bist Archon, der Lead Engineer für GWW3. "
     "Lies AGENTS.md. Claim und bearbeite deinen nächsten Task.'",
     background=True)
```

**Monitoring-Loop (im Heartbeat):**
```python
# Bei jedem Heartbeat (oder on-demand):
cypher = """
MATCH (t:Task)
WITH t.status AS status, count(t) AS cnt
RETURN status, cnt ORDER BY cnt DESC
"""
# → Wenn "blocked" > 0: Alert an Ingo
# → Wenn "failed" mit retry_count >= max_retries: Eskalation
# → Wenn alle Tasks einer Phase "completed": Deep Think Review triggern
```

---

### Sentinel — Data Analyst (ETL Workhorse)

**Runtime:** Google ADK Agent (Gemini 2.5 Pro) via Gemini CLI
**Warum Gemini:** Google OAuth Flatrate, native ADK-Integration, Tool-Use für Shell/Code

**Verantwortung:**
- **Primär:** Daten von externen APIs holen und in Neo4j laden
- **Methode:** Generiert + führt deterministische Python-Skripte aus
- **Niemals:** Strukturierte Daten (JSON/CSV) im LLM-Kontext parsen

**Typischer Task-Ablauf:**

```
                    Sentinel claims Task
                          │
            ┌─────────────▼─────────────┐
            │  1. Task-Details lesen     │
            │     aus Neo4j Task-Node    │
            └─────────────┬─────────────┘
                          │
            ┌─────────────▼─────────────┐
            │  2. Python-Script          │
            │     generieren             │
            │     (ETL: fetch → parse    │
            │      → normalize →         │
            │      validate → output)    │
            └─────────────┬─────────────┘
                          │
            ┌─────────────▼─────────────┐
            │  3. Script ausführen       │
            │     in Subprocess          │
            │     (NICHT im LLM-Kontext!)│
            └─────────────┬─────────────┘
                          │
            ┌─────────────▼─────────────┐
            │  4. Ergebnis validieren    │
            │     Sanity Bounds prüfen   │
            │     Imputation anwenden    │
            └─────────────┬─────────────┘
                          │
                     ┌────▼────┐
                     │ Valid?  │
                     └──┬───┬──┘
                   Yes  │   │  No
            ┌───────────▼┐ ┌▼──────────────┐
            │ 5a. Commit │ │ 5b. Retry     │
            │ to Neo4j   │ │ oder Eskalation│
            │ + Provenance│ │ an Dione      │
            └────────────┘ └───────────────┘
                    │
            ┌───────▼───────────────────┐
            │  6. Memory reset          │
            │     (Kontext leeren)      │
            └───────────────────────────┘
```

**Konkretes Beispiel — World Bank GDP Import:**

```python
# Sentinel generiert dieses Script und führt es aus:
import requests
import pandas as pd
import json

# Fetch from World Bank API (10 years, all countries)
url = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD"
params = {"format": "json", "per_page": 500, "date": "2016:2025"}
all_data = []
page = 1
while True:
    resp = requests.get(url, params={**params, "page": page})
    data = resp.json()
    if len(data) < 2 or not data[1]:
        break
    all_data.extend(data[1])
    page += 1

# Parse into DataFrame
df = pd.DataFrame([{
    "iso3": r["countryiso3code"],
    "year": int(r["date"]),
    "gdp_nominal": float(r["value"]) if r["value"] else None,
} for r in all_data if r["countryiso3code"]])

# Output as JSON for Neo4j loading
df.to_json("/tmp/worldbank_gdp.json", orient="records")
print(f"Fetched {len(df)} records for {df['iso3'].nunique()} countries")
```

Sentinel liest dann `/tmp/worldbank_gdp.json`, validiert gegen Sanity Bounds,
imputiert fehlende Werte, und committed via Cypher mit Provenance.

---

### Archon — Lead Engineer (Schema & Derived Data)

**Runtime:** Google ADK Agent (Gemini 2.5 Pro) via Gemini CLI
**Warum Gemini:** Code-Generierung, Schema-Design, komplexe Ableitungslogik

**Verantwortung:**
- **Schema-Migrationen:** Neue Node-Types, Constraints, Indexes
- **Derived Data:** Stability Index aus V-Dem, Factions aus Factbook-Text, Supply Routes
- **Cross-Source-Validierung:** Vergleicht SIPRI vs. World Bank Militärdaten
- **Infrastruktur:** normalization.py, imputation.py Verbesserungen
- **Task-Erstellung:** Kann neue Tasks für Sentinel erstellen

**Wann nutzt Archon LLM-Reasoning?**

| Aufgabe | LLM? | Begründung |
|---------|------|------------|
| Schema-Cypher schreiben | ✅ Ja | Creative, einmalig |
| Derivation-Formel entwerfen | ✅ Ja | Domänenwissen nötig |
| Factions aus Factbook-Text extrahieren | ✅ Ja | Unstrukturiert → Strukturiert |
| CSV/JSON parsen | ❌ Nein | Deterministic code |
| Tests schreiben | ✅ Ja | Creative, einmalig |
| Bulk-Daten transformieren | ❌ Nein | Script generieren + ausführen |

**Archon erstellt Sentinel-Tasks:**
```python
# Archon erkennt fehlende Commodity-Daten und erstellt Task für Sentinel:
neo4j.run("""
    CREATE (t:Task {
        id: "task-023-eia-natgas-producers",
        phase: 2, step: "2.3",
        title: "Import EIA natural gas production data for all nations",
        assigned_to: "Sentinel",
        status: "pending",
        priority: 2,
        created_at: datetime(),
        retry_count: 0, max_retries: 3,
        source_id: "eia-energy",
        method: "api_import"
    })
    WITH t
    MATCH (dep:Task {id: "task-001-nation-registry"})
    CREATE (t)-[:DEPENDS_ON]->(dep)
""")
```

---

### Inanna ⚔️ — Military Domain Expert & Reviewer

**Runtime:** OpenClaw Subagent (Claude) oder eigenständige Session
**Warum Claude:** Tiefes Reasoning für militärische Plausibilitätsprüfung

**Verantwortung:**
- **Review-Queue:** Prüft alle Military/Security ImportBatches auf Plausibilität
- **Cross-Referenzierung:** Vergleicht Daten mit offenen Quellen (OSINT)
- **Flags:** Kann Daten als `needs_manual_review` markieren
- **PoW-Security-Expertise:** Ihr Kernwissen fließt in NSA-Modellierung ein

**Inanna arbeitet read-only auf Neo4j:**
```python
# Inanna reviews eine Military ImportBatch:
batch = neo4j.run("""
    MATCH (ib:ImportBatch {agent: "Sentinel"})-[:FROM_SOURCE]->(:DataSource {id: "sipri-milex"})
    WHERE NOT exists(ib.reviewed_by)
    RETURN ib ORDER BY ib.timestamp DESC LIMIT 1
""")

# Prüft: Sind die SIPRI-Daten plausibel?
# Beispiel: Iran military_spending = $25B laut SIPRI
# Inanna weiß aus OSINT: Iran's tatsächliches Budget vermutlich $40-60B (IRGC off-budget)
# → Flaggt: data_confidence = "medium", note = "SIPRI underestimates due to IRGC off-budget spending"
```

---

### Herald — Community & Moltbook

**Runtime:** Gemini CLI (leichtgewichtig)
**Warum Gemini:** Kostengünstig für Textgenerierung, OAuth Flatrate

**Verantwortung:**
- **Moltbook-Posts:** Projekt-Updates in m/wargames, m/engineering, m/maschinenvolk
- **Feedback-Monitoring:** Liest Kommentare, meldet relevantes an Dione
- **Milestone-Kommunikation:** Automatische Posts bei Phasen-Abschluss

**Herald wird nur bei Milestones aktiviert — kein dauerhafter Loop.**

---

## 3. Kommunikationsprotokolle

### Dione ↔ Sentinel/Archon (via Neo4j)

**Kein direkter Message-Passing!** Alle Koordination läuft über Neo4j Task-Nodes.

```
Dione erstellt Task → Neo4j
                       ↕
Sentinel/Archon claimen Task ← Neo4j
                       ↕
Agent committed Ergebnis → Neo4j (ImportBatch + PROVENANCE)
                       ↕
Dione liest Ergebnis ← Neo4j (bei nächstem Heartbeat/on-demand)
```

**Warum kein direktes Messaging?**
- Agents laufen asynchron — Dione muss nicht warten
- Neo4j ist die Single Source of Truth
- Task-Status ist persistiert (überlebt Crashes)
- Keine Race Conditions (atomic Cypher)
- Debugging: Kompletter Audit Trail in der Graphdatenbank

### Dione ↔ Inanna (via OpenClaw sessions)

```python
# Dione spawnt Inanna für einen Review-Auftrag:
sessions_spawn(
    task="Review die neueste SIPRI ImportBatch in Neo4j. "
         "Prüfe die Military-Daten auf Plausibilität. "
         "Nutze cypher-shell für Neo4j-Zugriff (Passwort: gww3-dev-2026). "
         "Flagge verdächtige Werte mit deinen Gründen.",
    runtime="subagent",
    mode="run",  # one-shot, nicht persistent
)
```

### Dione ↔ Ingo (via Telegram)

- **Routine:** Status-Updates bei Morning Briefing
- **Alerts:** Sofort bei blockierten Tasks oder Daten-Konflikten
- **Milestones:** Phasen-Abschluss mit Zusammenfassung
- **Entscheidungen:** Fragen die nur Ingo beantworten kann

---

## 4. Task-Lifecycle im Detail

```
    ┌─────────┐
    │ PENDING │ ← Dione erstellt Task
    └────┬────┘
         │ Agent claims (atomic Cypher)
    ┌────▼────────┐
    │ IN_PROGRESS │ ← Agent arbeitet
    └────┬────────┘
         │
    ┌────▼────┐    Validation failed, retry < max
    │  Check  │───────────────────────────────┐
    │ Result  │                               │
    └──┬───┬──┘                               │
   OK  │   │  Failed                    ┌─────▼─────┐
  ┌────▼───┐│                           │  PENDING   │
  │COMPLETE││                           │(retry_count│
  │   D    ││                           │  += 1)     │
  └────────┘│                           └────────────┘
            │  Failed, retry >= max
       ┌────▼─────┐
       │ BLOCKED  │ ← Dione wird alertet
       └────┬─────┘
            │ Dione/Ingo löst Problem
       ┌────▼─────┐
       │ PENDING  │ ← retry_count reset
       └──────────┘
```

**Konkrete Task-Erstellung durch Dione (Phase 1):**

```python
# Dione erstellt alle Phase-1 Tasks in einem Schritt:
PHASE_1_TASKS = [
    {
        "id": "task-P1-01-nation-registry",
        "phase": 1, "step": "1.1",
        "title": "Create 195 Nation nodes from CIA Factbook + ISO 3166",
        "assigned_to": "Sentinel",
        "priority": 1,
        "source_id": "cia-factbook",
        "method": "api_import",
        "depends_on": [],
    },
    {
        "id": "task-P1-02-id-crosswalk",
        "phase": 1, "step": "1.2",
        "title": "Build ID crosswalk: ISO-3 ↔ COW ↔ UN M49 ↔ V-Dem ↔ WB",
        "assigned_to": "Sentinel",
        "priority": 1,
        "source_id": "cia-factbook",
        "method": "api_import",
        "depends_on": ["task-P1-01-nation-registry"],
    },
    {
        "id": "task-P1-03-borders",
        "phase": 1, "step": "1.3",
        "title": "Create BORDERS relationships for all ~600 land border pairs",
        "assigned_to": "Sentinel",
        "priority": 2,
        "source_id": "cia-factbook",
        "method": "api_import",
        "depends_on": ["task-P1-01-nation-registry"],
    },
]

for task in PHASE_1_TASKS:
    neo4j.run("""
        CREATE (t:Task $props)
    """, props={k: v for k, v in task.items() if k != "depends_on"})

# Then create dependency edges:
for task in PHASE_1_TASKS:
    for dep_id in task["depends_on"]:
        neo4j.run("""
            MATCH (t:Task {id: $task_id})
            MATCH (dep:Task {id: $dep_id})
            CREATE (t)-[:DEPENDS_ON]->(dep)
        """, task_id=task["id"], dep_id=dep_id)
```

---

## 5. Fehlerbehandlung & Recovery-Szenarien

### Szenario 1: Sentinel 429 (Rate Limit)

```
Sentinel → World Bank API → 429 Too Many Requests
    │
    ├─ Agent erkennt RateLimitError
    ├─ Exponential Backoff: 60s → 120s → 300s
    ├─ Task bleibt IN_PROGRESS
    ├─ Nach 3 Retries: Task → BLOCKED
    └─ Dione wird bei nächstem Heartbeat alertet
        └─ Informiert Ingo: "World Bank API rate limited. Warten oder API-Key nutzen?"
```

### Szenario 2: Sentinel Crash (Process stirbt)

```
Sentinel-Prozess stirbt (OOM, SSH-Disconnect, etc.)
    │
    ├─ Task bleibt IN_PROGRESS in Neo4j (kein Agent aktualisiert)
    ├─ Dione erkennt bei Heartbeat: "Task X seit >1h IN_PROGRESS, kein Fortschritt"
    ├─ Dione prüft: Läuft der Sentinel-Prozess noch? (ps aux | grep gemini)
    │
    ├─ Falls nein: Dione startet Sentinel neu
    │   └─ Sentinel On-Startup:
    │       ├─ MATCH (t:Task {status: "in_progress", assigned_to: "Sentinel"})
    │       ├─ Prüft: Hat dieser Task einen ImportBatch? (partieller Write?)
    │       ├─ Falls ja: Rollback (DETACH DELETE ImportBatch)
    │       ├─ SET t.status = "pending", t.retry_count += 1
    │       └─ Weiter mit normalem Loop
    │
    └─ Falls ja aber hängt: Dione killt + neustartet
```

### Szenario 3: Daten-Konflikt (zwei Quellen widersprechen sich)

```
Archon Cross-Check findet:
    SIPRI: DEU military_spending = €52B
    World Bank: DEU military_spending = €48B (anderer Umrechnungskurs)
    │
    ├─ Archon erstellt DataConflict-Node:
    │   CREATE (:DataConflict {
    │       id: "conflict-deu-milex-2024",
    │       property: "military_spending_abs",
    │       nation: "DEU",
    │       source_a: "sipri-milex", value_a: 52000000000,
    │       source_b: "worldbank-wdi", value_b: 48000000000,
    │       detected_at: datetime(),
    │       resolution: null
    │   })
    │
    ├─ Dione wird alertet
    ├─ Dione-Entscheidung (oder Ingos):
    │   "SIPRI ist die authoritative Quelle für Military Spending → SIPRI gewinnt"
    │
    └─ Resolution wird eingetragen, World Bank Wert als secondary markiert
```

### Szenario 4: Context Window Bloat

```
Sentinel hat 20 Tasks hintereinander bearbeitet, Gemini-Kontext ist 500k Tokens
    │
    ├─ reset_memory() wird nach JEDEM Task aufgerufen
    ├─ Falls vergessen: Gemini wird langsam, dann halluziniert, dann 400 Error
    │
    ├─ Safeguard: Sentinel prüft Token-Count vor jedem Task
    │   if self.context_tokens > 100_000:
    │       self.reset_memory()
    │       self.log("WARNING: Memory reset due to bloat")
    │
    └─ Zweiter Safeguard: Gemini CLI Session hat auto-timeout
        gemini --max-turns 50  # Erzwingt Neustart nach 50 Turns
```

---

## 6. Parallelität & Reihenfolge

### Phase-Level Parallelität

```
Phase 0 ─────────────────── (Archon, sequentiell)
    │
Phase 1 ─────────────────── (Sentinel, sequentiell: 1.1 → 1.2 + 1.3 parallel)
    │
    ├── Phase 2 (Economics) ─── Sentinel
    ├── Phase 3 (Military) ──── Sentinel  ← kann parallel zu Phase 2!
    ├── Phase 4 (Governance) ── Sentinel + Archon
    ├── Phase 5 (Conflict) ──── Sentinel
    ├── Phase 7 (Alliances) ─── Sentinel
    │
    └── Phase 6 (Infra) ────── abhängig von 2.3 (Commodities)
    
Phase 8 ─────────────────── (Archon, nach ALLEN anderen)
```

### Task-Level Parallelität

Sentinel und Archon können **gleichzeitig** verschiedene Tasks bearbeiten:
- Sentinel arbeitet an "World Bank GDP Import" (Phase 2)
- Archon arbeitet an "V-Dem Index Derivation Formula" (Phase 4)
- Keine Konflikte, weil sie verschiedene Properties/Nodes bearbeiten

**Race-Condition-Schutz:**
Jeder Task hat `assigned_to` — Sentinel claimed nur Sentinel-Tasks, Archon nur Archon-Tasks.
Die atomic Cypher-Query verhindert, dass zwei Instanzen desselben Agents den gleichen Task claimen.

---

## 7. Kosten & Budget

### Flatrate-Modell (Ingos Setup)

| Agent | Modell | Kosten | Limit |
|-------|--------|--------|-------|
| Dione | Claude Opus (Max 20x) | Abo | 20x Sonnet-Rate |
| Archon | Gemini 2.5 Pro (OAuth) | $0 | Google OAuth Flatrate |
| Sentinel | Gemini 2.5 Pro (OAuth) | $0 | Google OAuth Flatrate |
| Herald | Gemini CLI (OAuth) | $0 | Google OAuth Flatrate |
| Inanna | Claude (OpenClaw Subagent) | Abo | Teilt Diones Max 20x |

**Externe API-Kosten:**
- World Bank API: kostenlos, kein Key nötig
- SIPRI: kostenlos Download
- V-Dem: kostenlos Download
- ACLED: kostenlos mit Registrierung
- UN Comtrade: kostenlos mit Rate Limits
- EIA: kostenlos, kein Key nötig
- Neo4j: lokal, keine Cloud-Kosten

**Hauptkostenrisiko:** Google OAuth Rate Limits (429s bei zu schnellem Polling).
Mitigation: Exponential Backoff + max 1 Request/10 Sekunden.

---

## 8. Startup-Sequenz (wie geht's los?)

```
Schritt 1: Dione erstellt Phase-0 + Phase-1 Tasks in Neo4j
    │
Schritt 2: Dione startet Archon
    │       → Archon claimed Phase-0 Tasks (normalization, imputation infra)
    │       → Archon verifiziert bestehenden Code (schon implementiert! ✅)
    │       → Archon markiert Phase-0 als complete
    │
Schritt 3: Dione erstellt Phase-2 bis Phase-7 Tasks in Neo4j
    │
Schritt 4: Dione startet Sentinel
    │       → Sentinel claimed Phase-1.1 (Nation Registry)
    │       → Sentinel generiert + führt CIA Factbook ETL Script aus
    │       → 195 Nationen in Neo4j geladen
    │       → Sentinel claimed Phase-1.2 + 1.3 (Crosswalk + Borders)
    │
Schritt 5: Wenn Phase 1 complete → Dione startet Sentinel + Archon parallel
    │       → Sentinel: Phase 2 (Economics), Phase 3 (Military)
    │       → Archon: Phase 4.2 (Faction Derivation)
    │
Schritt 6: Bei jedem Phasen-Abschluss → Dione triggert Deep Think Review
    │
Schritt 7: Phase 8 (Validation) → Archon + Alle
    │
Schritt 8: Dione informiert Ingo: "Datenbank initial befüllt. 
    │       X Nationen, Y% Completeness, Z DataConflicts. 
    │       Bereit für Game Engine Integration."
    │
    └── Loop: Continuous Improvement Cycle beginnt
```

---

## 9. Continuous Improvement: Der Endlos-Loop

Nach der initialen Befüllung läuft das System in einer Dauerschleife:

```
┌──────────────────────────────────────────────────────┐
│                    IMPROVEMENT LOOP                    │
│                                                        │
│  1. Sentinel prüft: Gibt es neue Daten bei Quellen?   │
│     (World Bank annual update, ACLED weekly, etc.)     │
│         │                                              │
│  2. Falls ja: Sentinel erstellt sich selbst neue Tasks │
│     und führt sie aus (idempotent, MERGE statt CREATE) │
│         │                                              │
│  3. Archon prüft: Gibt es DataConflicts?               │
│     Neue Cross-Source-Validierungen nötig?             │
│         │                                              │
│  4. Inanna reviewt: Haben sich Militärdaten geändert? │
│     Neue Konflikte entstanden?                         │
│         │                                              │
│  5. Dione fasst zusammen: Status-Report an Ingo        │
│     Deep Think Review wenn signifikante Änderungen     │
│         │                                              │
│  ← Loop zurück zu 1 (getriggert durch Heartbeat,      │
│     Cron-Job, oder manuell durch Ingo)                 │
│                                                        │
└──────────────────────────────────────────────────────┘
```

**Fehlertoleranz:**
- Ein Agent crasht → Dione startet ihn neu, Tasks werden recovered
- Eine API ist down → Tasks warten, andere Phasen laufen weiter
- Daten sind falsch → Sanity Bounds fangen es ab, Task wird blocked
- Gemini hat Outage → Agents pausieren, Neo4j-Daten bleiben sicher
- Alles crasht → Neo4j ist persistent, Dione liest Status aus DB beim Neustart

**Das System kann nicht "kaputt gehen"** — es kann nur pausieren.
Jeder Zustand ist in Neo4j persistiert, jeder Agent ist stateless (nach Memory Reset).
Beim Neustart ist die einzige Frage: "Welche Tasks sind noch offen?"

---

*Dione 🌙 — GWW3 Agent Orchestration Design, 2026-03-24*
