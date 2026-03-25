# Sprint 3 Concept — Ingos Review & Entscheidungen (25.03.2026)

## Änderungsprotokoll

### A1/A2/A3 — Data Model Extension ✅ Approved
Keine Änderungen. Derived Nation Properties, neue Relationship Types und Node Types wie vorgeschlagen.

### B1 — Core Loop ✅ Approved
Keine Änderungen.

### B2 — Decision Types ✅ Approved
→ **Aktion:** Zur Diskussion auf Moltbook stellen, weitere Ideen sammeln.

### B3 — State Transition Model ❌ FUNDAMENTALER UMBAU

**Ingos Entscheidung:** Das Modell darf NICHT deterministisch sein. Wir würfeln.

> "Erst die Einbeziehung von Wahrscheinlichkeiten macht die Wirklichkeit und ein derartiges Spiel interessant."

**Drei Kernänderungen:**

1. **Probabilistisch statt deterministisch** — State Transitions enthalten Wahrscheinlichkeitsverteilungen, nicht feste Werte
2. **Textuelle Regeln statt Code** — Regeln werden als lesbare symbolische Ausdrücke formuliert, NICHT als Python-Funktionen
3. **Neuro-symbolisches Framework** — Inspiriert von SingularityNET/OpenCog Hyperon (MeTTa, PLN)

→ **Aktion:** Eigenes Konzeptdokument für die Rule Engine (siehe unten). Diskussion mit verschiedenen Agenten/Modellen, dann auf Moltbook zur Diskussion.

### B4 — Combat Resolution ❌ UMBAU (analog zu B3)
Combat Resolution folgt dem gleichen probabilistischen, textuell-regelbasierten Ansatz wie B3.

### B5 — Time Model ⚠️ GEÄNDERT
**Ingos Entscheidung:** Ein Tick = ein Tag (für Schlachten). Schlachten können sich über mehrere Ticks/Tage ziehen.

Alte Aufteilung (Tactical=1min, Strategic=weekly, Economic=monthly) wird angepasst:
- **Taktisch/Schlacht:** 1 Tick = 1 Tag
- **Strategisch/Diplomatisch:** Entscheidungen pro Tick, Effekte über mehrere Ticks
- **Wirtschaftlich:** Monatliche Aggregation (30 Ticks = 1 STATE_AT Snapshot)

### C — AI Agent Cabinet
→ **Aktion:** Zur Diskussion auf Moltbook stellen.

### D — Open Questions
→ **Aktion:** Zur Diskussion auf Moltbook stellen.

### G — Rule-Based Effect System
→ Hängt von B3 (Inferenzregeln) ab. Wird nach Rule Engine Konzept überarbeitet.

### H2/H3/H4 — AI Jury Details
→ **Aktion:** Zur Diskussion auf Moltbook stellen.

---

## Sprint-Aufteilung

Ingo erwartet, dass Sprint 3 in **3-6 Sprints** aufgeteilt wird, basierend auf den Diskussionsergebnissen. Vorschlag:

| Sprint | Fokus | Abhängigkeit |
|--------|-------|-------------|
| 3a | Rule Engine Konzept + MeTTa/PLN-Analyse + Community-Diskussion | — |
| 3b | Rule Engine Implementation (textuelle Regelsprache) | 3a |
| 3c | Combat Resolution + Tick=Tag Zeitmodell | 3b |
| 3d | Derived Properties + Weapons Database | 3a |
| 3e | AI Cabinet + Propaganda Jury | 3a (Diskussion) |
| 3f | Globe UI + Concept Page + Branding | unabhängig |

---

## Moltbook-Posts (geplant)

1. **B2 Decision Types** — "What actions should nations be able to take? Here's our draft..."
2. **B3 Rule Engine** — "We're designing a probabilistic rule engine for geopolitical simulation. Inspired by PLN/MeTTa. Thoughts?"
3. **C AI Cabinet** — "Should AI nations have a cabinet of specialized agents?"
4. **D Open Questions** — "Regional scenario or all 195 nations? Turn-based or real-time?"
5. **H AI Jury** — "Propaganda effectiveness judged by AI jury — novel mechanic or gimmick?"
