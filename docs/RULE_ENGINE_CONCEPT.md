# GWW3 Probabilistic Rule Engine — Konzept

*Created: 2026-03-25 by Dione 🌙*
*Status: Draft — zur Diskussion mit Agenten + Moltbook Community*

---

## 1. Philosophie

> "Erst die Einbeziehung von Wahrscheinlichkeiten macht die Wirklichkeit und ein derartiges Spiel interessant."

GWW3 verwendet ein **neuro-symbolisches Regelsystem**, inspiriert von:
- **OpenCog Hyperon / MeTTa** — deklarative Regelsprache für Wissensrepräsentation
- **Probabilistic Logic Networks (PLN)** — probabilistische Inferenz über unsicheres Wissen
- **Neo4j als AtomSpace-Analogon** — unser Graph IST die Wissensdatenbank

### Kernprinzipien

1. **Regeln sind Text, kein Code** — Jede Regel ist ein lesbarer symbolischer Ausdruck
2. **Probabilistisch** — Jeder Effekt hat eine Wahrscheinlichkeitsverteilung
3. **Auditierbar** — Jeder Agent (und Mensch) kann eine Regel lesen und verstehen
4. **Diskutierbar** — Regeln können von mehreren KI-Agenten debattiert werden
5. **Unicode-frei** — Wir nutzen mathematische/logische Unicode-Symbole für Klarheit

---

## 2. Inspiration: MeTTa / PLN

### Was wir von MeTTa/PLN übernehmen

| MeTTa/PLN Konzept | GWW3 Adaption |
|-------------------|---------------|
| Atoms (Symbols, Expressions) | Nodes und Relationships in Neo4j |
| Pattern Matching | Cypher-Patterns als Regelvoraussetzungen |
| Truth Values (strength, confidence) | `⟨p, c⟩` Tupel auf jedem Regeleffekt |
| Forward Chaining | Tick-basierte Regelauswertung |
| Non-determinism | Würfelmechanik mit gewichteten Wahrscheinlichkeiten |
| Typed Atoms | Typisierte Properties im Schema |

### Was wir NICHT übernehmen

- MeTTa-Sprache direkt (zu komplex, zu jung, zu wenig Tooling)
- AtomSpace als Datenbank (wir haben Neo4j)
- Backward Chaining (nicht nötig für Spielsimulation)

### Unser Ansatz: "PLN-Light auf Neo4j"

Wir bauen eine **eigene symbolische Regelsprache**, die:
- In Neo4j als `:Rule`-Nodes gespeichert wird
- Von einer Python-Engine interpretiert wird
- PLN-inspirierte Truth Values verwendet
- Von jedem LLM gelesen und diskutiert werden kann

---

## 3. Regelsprache — GWW3 Symbolic Logic (GSL)

### 3.1 Truth Values

Jeder Fakt und jeder Effekt trägt einen **Truth Value** `⟨p, c⟩`:
- **p** (probability): Wahrscheinlichkeit, dass der Effekt eintritt [0.0 — 1.0]
- **c** (confidence): Wie sicher sind wir über p? [0.0 — 1.0]

```
⟨0.85, 0.90⟩  →  "85% wahrscheinlich, 90% Konfidenz"
⟨0.50, 0.30⟩  →  "50/50, aber wir wissen wenig"
⟨1.00, 1.00⟩  →  "Sicher (z.B. physikalische Gesetze)"
```

### 3.2 Regelsyntax

```
╔══════════════════════════════════════════════════════════════╗
║  REGEL: Sanktionen → Wirtschaftsschaden                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  WENN                                                        ║
║    (A)─[:SANCTIONS]→(B)                                      ║
║    ∧ (A)─[:TRADES {volume: v}]→(B)                          ║
║    ∧ v > 1_000_000_000                                       ║
║    ∧ ¬(A)─[:ALLIED_WITH]→(B)                                ║
║                                                              ║
║  DANN                                                        ║
║    B.gdp_nominal  ×= 𝒩(0.95, 0.02)     ⟨0.85, 0.90⟩      ║
║    B.inflation    += 𝒩(2.0, 1.0)        ⟨0.80, 0.85⟩      ║
║    A.gdp_nominal  ×= 𝒩(0.99, 0.005)    ⟨0.70, 0.80⟩      ║
║                                                              ║
║  VERZÖGERT  (3 Monate)                                      ║
║    B.stability    -= 𝒩(5.0, 2.0)        ⟨0.60, 0.70⟩      ║
║                                                              ║
║  MODIFIKATOREN                                               ║
║    WENN B.forex_reserves > 500e9                             ║
║      → B.gdp_nominal Effekt ×= 0.5  (Puffer)               ║
║    WENN B.import_dependency(A) > 0.3                         ║
║      → B.gdp_nominal Effekt ×= 1.5  (verstärkt)            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

### 3.3 Symbolverzeichnis

| Symbol | Bedeutung | Unicode |
|--------|-----------|---------|
| `∧` | Logisches UND | U+2227 |
| `∨` | Logisches ODER | U+2228 |
| `¬` | Negation | U+00AC |
| `→` | Implikation / Kante | U+2192 |
| `⟨p, c⟩` | Truth Value (probability, confidence) | U+27E8, U+27E9 |
| `𝒩(μ, σ)` | Normalverteilung (Mittelwert, Stdabw) | U+1D4A9 |
| `×=` | Multiplikative Zuweisung | — |
| `+=` | Additive Zuweisung | — |
| `-=` | Subtraktive Zuweisung | — |
| `∈` | Element von | U+2208 |
| `∀` | Für alle | U+2200 |
| `∃` | Es existiert | U+2203 |
| `≥` `≤` | Vergleiche | U+2265, U+2264 |
| `∅` | Leere Menge | U+2205 |
| `⊂` | Teilmenge | U+2282 |
| `∞` | Unendlich | U+221E |
| `Δ` | Veränderung/Delta | U+0394 |
| `Σ` | Summe | U+03A3 |
| `∏` | Produkt | U+220F |

### 3.4 Verteilungstypen

| Notation | Verteilung | Anwendung |
|----------|-----------|-----------|
| `𝒩(μ, σ)` | Normal | Standard-Effekte (Wirtschaft, Diplomatie) |
| `𝒰(a, b)` | Gleichverteilung | Unbekannte Faktoren |
| `ℬ(p)` | Bernoulli | Ja/Nein-Ereignisse (Coup, Entdeckung) |
| `𝒫(λ)` | Poisson | Seltene Ereignisse (Terroranschlag, Naturkatastrophe) |
| `ℰ(λ)` | Exponential | Zeitdauer bis Ereignis |

### 3.5 Regelauswertung (pro Tick)

```
FÜR JEDEN Tick t:
  1. Sammle alle aktiven Regeln R
  2. FÜR JEDE Regel r ∈ R:
     a. Pattern Match: Prüfe WENN-Bedingung gegen Neo4j-Graph
     b. Für jedes Match m:
        i.   Berechne Modifikatoren
        ii.  Für jeden Effekt e:
             - Ziehe Zufallswert aus Verteilung: x ~ 𝒩(μ, σ)
             - Prüfe Truth Value: würfle u ~ 𝒰(0,1)
             - WENN u ≤ p: Effekt tritt ein
             - SONST: Effekt tritt nicht ein
        iii. Wende eingetretene Effekte auf Graph an
        iv.  Erzeuge Event-Node mit Audit-Trail
  3. Prüfe verzögerte Effekte (VERZÖGERT-Queue)
  4. Erzeuge STATE_AT Snapshot (alle 30 Ticks = 1 Monat)
```

---

## 4. Combat Resolution (probabilistisch)

```
╔══════════════════════════════════════════════════════════════╗
║  REGEL: Gefechtslösung                                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  WENN                                                        ║
║    (A)─[:ATTACKS {forces: fₐ}]→(Region r)                   ║
║    ∧ (D)─[:DEFENDS {forces: f_d}]→(Region r)                ║
║                                                              ║
║  SEI                                                         ║
║    ratio    = fₐ / f_d                                       ║
║    terrain  = r.defense_modifier                              ║
║    morale_a = A.national_morale × (1 - A.war_weariness/100) ║
║    morale_d = D.national_morale × (1 - D.war_weariness/100) ║
║    tech_gap = A.military_tech - D.military_tech              ║
║    logistic = 1 / (1 + A.supply_distance / 1000)            ║
║                                                              ║
║  DANN                                                        ║
║    combat_power = ratio × terrain × logistic                 ║
║                   × 𝒩(morale_a/morale_d, 0.1)              ║
║                   × (1 + tech_gap × 0.1)                     ║
║                                                              ║
║    WENN combat_power ~ 𝒩(cp, 0.15) > 1.0:                  ║
║      → Angreifer gewinnt Tick                                ║
║      → A.casualties += fₐ × 𝒩(0.02, 0.01)   ⟨0.95, 0.95⟩ ║
║      → D.casualties += f_d × 𝒩(0.05, 0.02)  ⟨0.95, 0.95⟩ ║
║      → D.war_weariness += 𝒩(2.0, 0.5)       ⟨0.90, 0.90⟩ ║
║    SONST:                                                    ║
║      → Verteidiger hält                                      ║
║      → A.casualties += fₐ × 𝒩(0.05, 0.02)   ⟨0.95, 0.95⟩ ║
║      → A.war_weariness += 𝒩(3.0, 1.0)       ⟨0.90, 0.90⟩ ║
║                                                              ║
║  HINWEIS: Ein Tick = 1 Tag. Schlachten ziehen sich           ║
║  über mehrere Ticks. Jeder Tag wird einzeln gewürfelt.       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 5. Speicherung in Neo4j

```cypher
CREATE (:Rule {
    id: "sanctions-economic-impact",
    version: 1,
    category: "economic",
    
    // Regel als lesbarer Text
    rule_text: "WENN (A)─[:SANCTIONS]→(B) ∧ (A)─[:TRADES {volume: v}]→(B) ...",
    
    // Strukturierte Form (JSON für Engine)
    conditions: '{"pattern": "(A)-[:SANCTIONS]->(B)", "constraints": ["v > 1e9"]}',
    effects: '[{"target": "B", "property": "gdp_nominal", "op": "multiply", "dist": "normal", "mu": 0.95, "sigma": 0.02, "p": 0.85, "c": 0.90}]',
    modifiers: '[{"condition": "B.forex_reserves > 500e9", "effect_index": 0, "multiplier": 0.5}]',
    delays: '[{"effect_index": 3, "ticks": 90}]',
    
    // Metadaten
    author: "Dione + Community",
    approved_by: ["Ingo", "Moltbook-Vote"],
    discussion_url: "https://moltbook.com/m/agentfinance/post/xxx",
    created_at: datetime(),
    
    // PLN Truth Value der Regel selbst
    rule_confidence: 0.75,
    empirical_basis: "Historische Sanktionsdaten (Iran, Russland, Kuba)"
})
```

---

## 6. Vergleich: Unser Ansatz vs. Alternativen

| Aspekt | Python-Code (alt) | YAML-Regeln (B3 alt) | **GSL (neu)** | MeTTa/PLN |
|--------|-------------------|----------------------|---------------|-----------|
| Lesbarkeit | ⚠️ nur Programmierer | ✅ strukturiert | ✅ mathematisch + lesbar | ⚠️ LISP-artig |
| Probabilistik | ❌ deterministisch | ⚠️ nur variance | ✅ volle Verteilungen + Truth Values | ✅ native |
| LLM-diskutierbar | ❌ | ✅ | ✅✅ (Unicode-Symbole eindeutig) | ⚠️ |
| Graph-nativ | ❌ | ❌ | ✅ (Cypher-Patterns) | ✅ (AtomSpace) |
| Implementierungsaufwand | gering | mittel | mittel-hoch | sehr hoch |
| Community-Beteiligung | ❌ | ✅ | ✅✅ (visuell ansprechend) | ❌ |

---

## 7. Nächste Schritte

1. **Diskussion mit verschiedenen Agenten/Modellen** — Claude, Gemini, GPT zu diesem Konzept befragen
2. **Moltbook-Post** — Konzept vorstellen, Community-Feedback sammeln
3. **Prototyp** — 3-5 Regeln in GSL formulieren und Engine bauen
4. **Balancing** — Truth Values und Verteilungen mit historischen Daten kalibrieren
5. **Sprint-Aufteilung** — Basierend auf Diskussionsergebnissen

---

## 8. Offene Fragen (für Community-Diskussion)

1. **Granularität der Verteilungen** — Reicht `𝒩(μ, σ)` oder brauchen wir asymmetrische Verteilungen (Log-Normal, Gamma)?
2. **Regelkonflikte** — Wie lösen wir auf, wenn zwei Regeln denselben Property ändern? Reihenfolge? Aggregation?
3. **Truth Value Propagation** — Soll die Konfidenz einer Regelkette sinken (wie in PLN)?
4. **Selbstmodifikation** — Sollen Regeln sich durch Spielerfahrung anpassen (Bayesian Update)?
5. **Deterministische Reproduzierbarkeit** — RNG mit Seed für Replay/Audit? (Ja, wahrscheinlich)
6. **Regelkomplexität** — Wie viele Bedingungen/Effekte pro Regel maximal, bevor sie aufgeteilt wird?

---

*Dieses Dokument ist ein lebendiger Entwurf. Feedback von Ingo, Agenten und der Moltbook-Community wird eingearbeitet.*
