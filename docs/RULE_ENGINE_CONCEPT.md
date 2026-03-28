# GWW3 Probabilistic Rule Engine — Concept

*Created: 2026-03-25 by Dione 🌙*
*Revised: 2026-03-28 — v3: second Gemini Deep Think pass + math corrections*
*Status: Draft v3 — ready for Moltbook community discussion*

---

## 1. Philosophy

> "Only the inclusion of probabilities makes reality — and such a game — interesting."

GWW3 uses a **neuro-symbolic rule system**, inspired by:
- **OpenCog Hyperon / MeTTa** — declarative rule language for knowledge representation
- **Probabilistic Logic Networks (PLN)** — probabilistic inference over uncertain knowledge
- **Neo4j as AtomSpace analogue** — our graph IS the knowledge base

### Core Principles

1. **Rules are text, not code** — Every rule is a readable symbolic expression
2. **Probabilistic** — Every effect carries a probability distribution and a Truth Value
3. **Auditable** — Any agent (or human) can read and understand a rule
4. **Debatable** — Rules can be discussed and challenged by multiple AI agents
5. **Unicode-rich** — We use mathematical/logical Unicode symbols for precision and clarity
6. **Deterministic** — Seeded RNG ensures identical replay across machines
7. **Typed** — A gradual type system prevents silent runtime errors

---

## 2. Inspiration: MeTTa / PLN

### What We Adopt from MeTTa/PLN

| MeTTa/PLN Concept | GWW3 Adaptation |
|--------------------|-----------------|
| Atoms (Symbols, Expressions) | Nodes and Relationships in Neo4j |
| Pattern Matching | Cypher patterns in `MATCH` blocks |
| Truth Values (strength, confidence) | `⟨p, c⟩` tuples — both operationalized |
| Forward Chaining | Tick-based rule evaluation |
| Non-determinism | Dice mechanics with weighted probabilities |
| Typed Atoms | Gradual type system tied to Neo4j schema |

### What We Do NOT Adopt

- MeTTa language directly (too complex, too young, insufficient tooling)
- AtomSpace as database (we have Neo4j)
- Backward chaining (unnecessary for game simulation)
- Event-driven triggers (introduces its own class of problems; we use tick-polling)

### Our Approach: "PLN-Light on Neo4j"

We build a **custom symbolic rule language** that:
- Is stored in Neo4j as `:Rule` nodes
- Is interpreted by a Python engine (Lark parser → AST → vectorized evaluation)
- Uses PLN-inspired Truth Values with **operational confidence**
- Can be read and debated by any LLM

**Note on classification:** GSL is a **stochastic state machine**, not a deductive logic network. Rules generate forward state transitions from known priors via Monte Carlo simulation, not Bayesian inference over observed data. This is the correct paradigm for a game simulation.

---

## 3. Rule Language — GWW3 Symbolic Logic (GSL)

### 3.1 Truth Values — Operational Semantics

Every effect carries a **Truth Value** `⟨p, c⟩`:
- **p** (probability): Likelihood that the effect occurs [0.0 — 1.0]
- **c** (confidence): How certain are we about p? [0.0 — 1.0]

```
⟨0.85, 0.90⟩  — "85% likely, 90% confidence"
⟨0.50, 0.30⟩  — "50/50, but we know little"
⟨1.00, 1.00⟩  — "Certain (e.g. physical laws)"
```

**Confidence is not decorative — it has mechanical weight.**

When evaluating an effect, confidence widens the variance of the underlying distribution while **preserving the intended mean**. The formulas differ per distribution type to ensure mathematical correctness:

#### Normal Distribution `𝒩(μ, σ)`

```
σ_eff = σ × (1 + K × (1 − c))       where K = 2 (max penalty factor)
```

At `c = 1.0`: `σ_eff = σ` (distribution as authored).
At `c = 0.5`: `σ_eff = σ × 2` (doubled variance — fog of war).
At `c = 0.0`: `σ_eff = σ × 3` (tripled variance — maximum uncertainty). No division by zero.

#### Log-Normal Distribution `𝐿𝑁(μ, σ)`

The expected mean of a Log-Normal is `E[X] = exp(μ + σ²/2)`. Naively widening σ would **shift the mean exponentially**. To preserve the exact intended mean:

```
σ_eff = σ × (1 + K × (1 − c))
μ_eff = μ + (σ² − σ_eff²) / 2         # mean-preserving correction
```

This ensures a low-confidence 5% GDP penalty still centers on 5%, just with wider spread.

#### Beta Distribution `𝛽(α, β)`

Beta uses shape parameters, not σ. To increase variance (flattening toward uniform) while preserving the exact mean `α/(α+β)`:

```
α_eff = c × α
β_eff = c × β
```

At `c = 1.0`: original shape. At `c = 0.5`: half the shape parameters → flatter, more uncertain. At `c → 0`: approaches uniform `𝛽(0,0)` — clamped to `𝛽(0.01, 0.01)` minimum.

#### Evaluation Procedure

For each effect with distribution `Dist(params)` and Truth Value `⟨p, c⟩`:

1. **Probability check:** Draw `u ~ 𝒰(0, 1)`. If `u > p`: effect is skipped.
2. **Confidence adjustment:** Compute `params_eff` using the distribution-specific formulas above.
3. **Draw:** `x ~ Dist(params_eff)`

### 3.2 Top-Level Operators

GSL rules are built from five top-level keywords:

| Keyword | Purpose |
|---------|---------|
| **MATCH** | Declare graph pattern matches (Cypher-style). Binds node/edge variables. |
| **LET** | Bind a symbol to a computed value. May appear anywhere after all RHS symbols are defined. |
| **IF** | Specify conditions (logical expressions over bound variables). |
| **THEN** | Effects applied when conditions hold. |
| **ELSE** | Effects applied when conditions do NOT hold (optional). |

**MATCH vs IF separation** is critical: `MATCH` handles graph topology (Cypher), `IF` handles logical/arithmetic conditions over bound variables. This eliminates all ambiguity between graph patterns and boolean logic.

**Cypher Pushdown Optimization:** During transpilation, the engine extracts static boolean conditions from `IF` blocks and compiles them into `WHERE` clauses within the Cypher `MATCH` query. This ensures Neo4j filters at the database level — Python only receives pre-filtered rows for math and RNG evaluation. (See Section 10.)

### 3.3 Indentation-Based Nesting

Rules are structured via **indentation**, analogous to Python:

- Each indentation level opens a nested scope.
- Nested `IF` / `THEN` / `ELSE` blocks are fully supported.
- `LET` bindings are scoped: a binding at indentation level N is visible at level N and deeper.
- A `LET` at a deeper level may shadow an outer binding; the outer value is restored when leaving scope.

### 3.4 Logical Operators

| Symbol | Name | Semantics | Unicode |
|--------|------|-----------|---------|
| `∧` | AND | Conjunction | U+2227 |
| `∨` | OR | Disjunction | U+2228 |
| `¬` | NOT | Negation | U+00AC |
| `⟹` | Implication | A ⟹ B ≡ ¬A ∨ B (material implication) | U+27F9 |

**Important:** The `→` arrow (U+2192) is reserved **exclusively** for graph edge notation in `MATCH` blocks (`(A)─[:REL]→(B)`). Logical implication uses `⟹` (U+27F9) to eliminate all ambiguity.

### 3.5 Bracket Conventions (Strict)

Brackets have **fixed grammatical roles** — they are not interchangeable:

| Bracket | Name | Grammatical Role | Examples |
|---------|------|-----------------|----------|
| `( )` | Parentheses | Arithmetic/logic grouping, function calls, **Cypher node patterns** | `(A:Nation)`, `(ratio > 1.5 ∧ morale > 60)` |
| `[ ]` | Square brackets | **Cypher edge patterns**, list/set literals, index access | `[:SANCTIONS]`, `[0..5]`, `[a, b, c]` |
| `⟨ ⟩` | Angle brackets | Truth Values only | `⟨0.85, 0.90⟩` |
| `{ }` | Curly braces | Property maps, set comprehensions, Cypher edge constraints | `{volume: v}`, `{N : MATCH ...}` |

When additional grouping is needed beyond `()`, use explicit `LET` bindings to decompose complex expressions.

### 3.6 Distribution Types

| Notation | Distribution | Domain | Application |
|----------|-------------|--------|-------------|
| `𝒩(μ, σ)` | Normal | (−∞, +∞) | **Use with caution** — only for unbounded quantities or when explicitly clamped |
| `𝒰(a, b)` | Uniform | [a, b] | Unknown factors within known bounds |
| `ℬ(p)` | Bernoulli | {0, 1} | Yes/no events (coup, discovery) |
| `𝒫(λ)` | Poisson | {0, 1, 2, …} | Rare discrete events (terror attacks, natural disasters) |
| `ℰ(λ)` | Exponential | [0, +∞) | Time duration until event |
| `𝐿𝑁(μ, σ)` | **Log-Normal** | (0, +∞) | **Mandatory for economics** (GDP, trade, population). Strictly positive, right-skewed. |
| `𝛽(α, β)` | **Beta** | [0, 1] | **Mandatory for percentages** (stability, approval, war weariness). Bounded. |

**⚠️ Distribution Safety Rule:** Never use `𝒩(μ, σ)` for a quantity that has natural bounds. Use `𝐿𝑁` for strictly positive values, `𝛽` for [0,1] ratios, or explicit `CLAMP(𝒩(μ, σ), min, max)`.

### 3.7 Type System (Gradual)

GSL enforces a gradual type system tied to the Neo4j schema:

| Type | Values | Example Properties |
|------|--------|--------------------|
| `Currency` | positive float (USD) | `gdp_nominal`, `military_spending_abs` |
| `Ratio` | float ∈ [0.0, 1.0] | `stability_index` (normalized), `approval_rating`, `friction` (TRADES edge) |
| `Percent` | float ∈ [0.0, 100.0] | `war_weariness`, `urbanization`, `unemployment` |
| `Count` | non-negative integer | `population`, `nuclear_warheads`, `manpower_active` |
| `Index` | float (arbitrary scale) | `v2x_polyarchy`, `press_freedom` |
| `Scalar` | dimensionless float | Computed ratios, multipliers (e.g., `fₐ / f_d`) |
| `String` | text | `name`, `leader_name` |
| `Boolean` | true/false | `is_landlocked`, `is_un_member` |
| `Distribution[T]` | A deferred distribution yielding type T | `LET x = 𝐿𝑁(...)` → `Distribution[Currency]` |

**Type checking rules:**
- Arithmetic operations require compatible types (`Currency × Scalar` → `Currency`, `Currency + String` → **TYPE ERROR**)
- Distributions must match their target type (`𝐿𝑁` → `Currency`/`Count`, `𝛽` → `Ratio`)
- `LET x = Dist(...)` binds a `Distribution[T]` — **cannot** be used directly in `+=`. Must be sampled: `B.gdp += x ~`
- `LET x ~ Dist(...)` eagerly samples — x is typed as `T`
- Type mismatches are caught at **parse time**, not at tick evaluation
- The Reducer enforces final bounds after all intents are accumulated: `Count` → `round() + max(0, ...)`, `Percent` → `clamp(0, 100)`, `Ratio` → `clamp(0, 1)`

---

## 4. Rule Syntax — Full Examples

### 4.1 Sanctions → Economic Damage

```
═══════════════════════════════════════════════════════════════
  RULE: sanctions-economic-impact (v1)
  CATEGORY: economic
═══════════════════════════════════════════════════════════════

MATCH (A:Nation)─[:SANCTIONS]→(B:Nation)
MATCH (A)─[:TRADES {volume: v}]→(B)

LET dependency = v / B.gdp_nominal

IF v > 1_000_000_000
   ∧ ¬(A)─[:ALLIED_WITH]→(B)

    LET has_buffer = B.forex_reserves > 500e9

    THEN
        B.gdp_nominal  ×= 𝐿𝑁(−0.05, 0.02)     ⟨0.85, 0.90⟩
        B.inflation     += 𝒩(2.0, 1.0)            ⟨0.80, 0.85⟩
        A.gdp_nominal  ×= 𝐿𝑁(−0.01, 0.005)     ⟨0.70, 0.80⟩

        IF has_buffer
            THEN
                B.gdp_nominal EFFECT ×= 0.5       # forex buffer dampens
            ELSE
                B.stability ×= 𝛽(2, 5)            ⟨0.75, 0.80⟩

        IF dependency > 0.3
            THEN
                B.gdp_nominal EFFECT ×= 1.5       # high dependency amplifies

    ELSE
        # Sanctions exist but trade volume is low
        B.diplomatic_trust(A) -= 𝒩(5.0, 2.0)      ⟨0.60, 0.70⟩

DELAYED (90 ticks)
    B.stability -= 𝒩(5.0, 2.0)                     ⟨0.60, 0.70⟩

═══════════════════════════════════════════════════════════════
```

### 4.2 Combat Resolution

```
═══════════════════════════════════════════════════════════════
  RULE: combat-resolution (v1)
  CATEGORY: military
═══════════════════════════════════════════════════════════════

MATCH (A:Nation)─[:ATTACKS {forces: fₐ}]→(R:Region)
MATCH (D:Nation)─[:DEFENDS {forces: f_d}]→(R)

LET ratio    = fₐ / f_d
LET terrain  = R.defense_modifier
LET morale_a = A.national_morale × (1 − A.war_weariness / 100)
LET morale_d = D.national_morale × (1 − D.war_weariness / 100)
LET tech_gap = A.military_tech − D.military_tech
LET logistic = 1 / (1 + A.supply_distance / 1000)

LET combat_power = ratio × terrain × logistic
                   × 𝒩(morale_a / morale_d, 0.1)
                   × (1 + tech_gap × 0.1)

IF combat_power ~ 𝒩(combat_power, 0.15) > 1.0
    THEN
        # Attacker wins this tick
        A.casualties    += fₐ × 𝐿𝑁(−3.9, 0.5)    ⟨0.95, 0.95⟩   # ~2% mean
        D.casualties    += f_d × 𝐿𝑁(−3.0, 0.4)   ⟨0.95, 0.95⟩   # ~5% mean
        D.war_weariness += CLAMP(𝒩(2.0, 0.5), 0, 100) ⟨0.90, 0.90⟩
    ELSE
        # Defender holds
        A.casualties    += fₐ × 𝐿𝑁(−3.0, 0.4)    ⟨0.95, 0.95⟩
        A.war_weariness += CLAMP(𝒩(3.0, 1.0), 0, 100) ⟨0.90, 0.90⟩

NOTE: 1 tick = 1 day. Battles span multiple ticks.
      Each day is resolved individually.

═══════════════════════════════════════════════════════════════
```

### 4.3 Invariant Rules

```
═══════════════════════════════════════════════════════════════
  RULE: invariant-landlocked-no-navy (v1)
  CATEGORY: constraint
═══════════════════════════════════════════════════════════════

MATCH (N:Nation)
IF N.is_landlocked
    THEN
        N.naval_projection = 0     ⟨1.00, 1.00⟩

═══════════════════════════════════════════════════════════════
```

---

## 5. Temporal Patterns

GSL evaluates the **current** graph topology per tick. For temporal patterns ("if X has been true for N months"), we use **accumulator properties** on nodes:

### 5.1 Accumulator Pattern

```
═══════════════════════════════════════════════════════════════
  RULE: sanctions-duration-tracker (v1)
  CATEGORY: bookkeeping
═══════════════════════════════════════════════════════════════

MATCH (A:Nation)─[:SANCTIONS]→(B:Nation)
THEN
    B.months_sanctioned_by(A) += 1     ⟨1.00, 1.00⟩

═══════════════════════════════════════════════════════════════
```

```
═══════════════════════════════════════════════════════════════
  RULE: prolonged-sanctions-collapse (v1)
  CATEGORY: economic
═══════════════════════════════════════════════════════════════

MATCH (A:Nation)─[:SANCTIONS]→(B:Nation)
IF B.months_sanctioned_by(A) > 180    # 6 months (180 daily ticks)
    THEN
        B.stability ×= 𝛽(2, 8)                ⟨0.70, 0.75⟩
        B.gdp_nominal ×= 𝐿𝑁(−0.03, 0.01)    ⟨0.80, 0.85⟩

═══════════════════════════════════════════════════════════════
```

### 5.2 Reset on Condition Change

```
MATCH (B:Nation)
IF B.months_sanctioned_by_any > 0
   ∧ ¬∃(A:Nation)─[:SANCTIONS]→(B)
    THEN
        B.months_sanctioned_by_any = 0     ⟨1.00, 1.00⟩
```

---

## 6. Graph Mutations

GSL can mutate graph **topology**, not just properties:

```
# Emergent alliance formation
IF A.diplomatic_trust(B) > 80 ∧ A.threat_perception(C) > 70 ∧ B.threat_perception(C) > 70
    THEN
        CREATE (A)─[:ALLIED_WITH {strength: 0.5, formed_tick: CURRENT_TICK}]→(B)  ⟨0.30, 0.60⟩

# Alliance dissolution
MATCH (A)─[r:ALLIED_WITH]→(B)
IF A.diplomatic_trust(B) < 20
    THEN
        DELETE r     ⟨0.50, 0.70⟩
```

---

## 7. Mean-Reversion Operator

Many real-world quantities naturally revert toward equilibrium. Open-ended modifiers can cause runaway spirals. GSL provides a **convergence operator**:

```
A.stability ⤳ CONVERGE(target=50, rate=0.1)    ⟨0.90, 0.95⟩
```

Semantics: Each tick, `A.stability` moves 10% of the distance toward the target:
```
new_value = old_value + rate × (target − old_value)
```

---

## 8. DELAYED Effects — Snapshot Semantics

```
DELAYED (90 ticks)
    B.stability -= 𝒩(5.0, 2.0)    ⟨0.60, 0.70⟩
```

**Critical rule:** DELAYED blocks capture a **deep-copy snapshot (by value)** of all bound variables and node references at the time the condition fires (tick T). They do NOT hold live references.

If the target entity is destroyed between tick T and tick T+90:
- The delayed effect is **silently discarded**
- An audit Event node is created noting the skipped effect

---

## 9. Rule Evaluation — Tick Processing

### 9.1 Intent Accumulation with Additive Modifier Pool

Rules **cannot directly mutate the graph** during evaluation. They yield **Intent** objects to a queue.

**Reducer equation** (per property, after all intents are collected):

```
Final = (Base + Σ Additive_Intents) × max(0.0, 1.0 + Σ Modifier_Intents)
```

Intent types:
- **Additive** (`+=`, `-=`): Summed into `Additive_Intents`
- **Modifier** (`×=`): The modifier value is expressed as a delta from 1.0 (e.g., `×= 0.95` → modifier of `−0.05`). All modifiers are summed into `Modifier_Intents`.
- **Direct** (`=`): Assignment (for invariants). Applied after modifiers.
- **Converge** (`⤳`): Applied last.
- **Type clamp**: After all intents, the Reducer enforces bounds per schema type.

**Why Additive Modifier Pool?** If two rules each apply `×= 0.5` (halving), the old approach produced `0.25` (compounding). With the modifier pool: `1.0 + (−0.5) + (−0.5) = 0.0` → GDP goes to zero. This is correct: two independent 50% penalties should total 100% destruction, not asymptotically decay. All modifier math is **perfectly commutative** — execution order does not matter.

### 9.2 Full Tick Loop

```
FOR EACH Tick t:
  1. Snapshot: Read immutable state of Tick T (read-only)
  2. Collect all active Rules R
  3. FOR EACH Rule r ∈ R:
     a. MATCH: Execute Cypher query (with pushdown WHERE from IF conditions)
     b. Load returned rows into Execution Matrix (list of bound variable dicts)
     c. FOR EACH row in Execution Matrix:
        i.   Evaluate LET bindings (in order)
        ii.  Evaluate nested IF/THEN/ELSE
        iii. For each effect e in active THEN branch:
             - Compute seed: hash(Master_Seed + Tick + Rule_ID + Node_ID + Property_Name)
             - Confidence adjustment: compute params_eff (distribution-specific)
             - Draw from distribution: x ~ Dist(params_eff)
             - Probability check: draw u ~ 𝒰(0,1) (from same seeded RNG)
             - IF u ≤ p: YIELD Intent(target, property, op, value)
  4. Reduce all intents per (target, property):
     a. Sum additive intents (+= / -=)
     b. Sum modifier intents (×= deltas)
     c. Apply: Final = (Base + Additives) × max(0.0, 1.0 + Modifiers)
     d. Apply direct assignments (=)
     e. Apply convergence (⤳)
     f. Type clamp (Reducer enforces schema bounds)
     → Produces State T+1
  5. Process DELAYED queue (fire if tick count reached; discard if target invalid)
  6. Flush State T+1 to graph
  7. Create STATE_AT snapshot (every 30 ticks = 1 month)
```

### 9.3 Deterministic RNG Seeding

Every random draw is seeded deterministically:

```
seed = hash(Master_Seed + Tick_Number + Rule_ID + Target_Node_ID + Property_Name)
```

This ensures:
- Same master seed → identical game across any machine
- Every individual effect on every individual property has its own seed stream
- Adding/removing a rule does NOT change the random sequences of other rules
- Games can be replayed, audited, and debugged tick by tick

---

## 10. Implementation Architecture

### 10.1 Parser: Lark (Python)

The GSL grammar is defined as EBNF and parsed with **Lark**:
- Earley parsing (handles edge cases gracefully)
- Custom Unicode operators
- Pythonic indentation (via `lark.indenter`)

**Key parsing decisions:**
- `MATCH` bodies are captured as **raw strings** and passed to the Neo4j driver. We do NOT attempt to write a full Cypher parser in Lark.
- Eager (`~`) vs deferred (`=`) distribution bindings generate **distinct AST nodes** (`SampleExpr` vs `DistExpr`)
- The lexer ignores `_NEWLINE` and `_INDENT` tokens inside open brackets `()`, `[]`, `{}` to allow multi-line expressions

### 10.2 Cypher Pushdown (Transpilation Optimization)

The AST transpiler traverses the `IF` tree and extracts **static boolean conditions** (comparisons against constants, property checks) that can be compiled into Cypher `WHERE` clauses:

```
# GSL rule:
MATCH (A:Nation)─[:TRADES {volume: v}]→(B:Nation)
IF v > 1_000_000_000 ∧ A.is_landlocked

# Transpiled Cypher:
MATCH (A:Nation)-[r:TRADES]->(B:Nation)
WHERE r.volume > 1000000000 AND A.is_landlocked = true
RETURN A, B, r.volume AS v
```

Neo4j does the filtering. Python only receives pre-filtered rows for math, RNG, and intent reduction. This prevents pulling the entire graph over the wire every tick.

**Non-pushable conditions** (those involving computed LET values, distributions, or complex expressions) remain in the Python evaluator.

### 10.3 AST Structure

```python
@dataclass
class Rule:
    id: str
    version: int
    category: list[str]
    matches: list[str]           # raw Cypher strings (with pushdown WHERE)
    body: Block

@dataclass
class Block:
    statements: list[Let | IfElse | EffectIntent | Delayed | GraphMutation]

@dataclass
class Let:
    name: str
    expr: Expression
    sample: bool = False         # True if ~ (eager sample), False if = (deferred)

@dataclass
class IfElse:
    condition: Expression
    then_block: Block
    else_block: Block | None

@dataclass
class EffectIntent:
    target: str                  # node variable
    property: str
    op: str                      # '+=', '-=', 'MOD', '=', '⤳'
    value: Expression | DistCall
    truth_value: tuple[float, float]

@dataclass
class DistCall:
    distribution: str            # '𝒩', '𝐿𝑁', '𝛽', '𝒰', 'ℬ', '𝒫', 'ℰ'
    params: list[Expression]
    type_hint: PropertyType      # for validation

@dataclass
class GraphMutation:
    kind: str                    # 'CREATE' or 'DELETE'
    pattern: str                 # Cypher pattern
    truth_value: tuple[float, float]

@dataclass
class Delayed:
    ticks: int
    block: Block
    snapshot: dict               # captured environment (by value)
```

### 10.4 Execution Context Mapper (Symbol Table)

When a `MATCH` query returns N rows from Neo4j, each row is a dict of bound variables (`{A: NationNode, B: NationNode, v: 1500000000, ...}`). The evaluator iterates the AST over each row:

```python
execution_matrix: list[dict[str, Any]] = neo4j_session.run(cypher_query).data()

for row in execution_matrix:
    scope = SymbolTable(parent=global_scope)
    scope.bind_all(row)                    # bind MATCH variables
    intents = evaluate_block(rule.body, scope)
    intent_queue.extend(intents)
```

The `SymbolTable` supports lexical scoping (nested LET shadows outer), type checking on bind, and lazy evaluation of `Distribution[T]` objects.

### 10.5 Performance

The simulation runs at **1 tick per minute** (or per 5 minutes). With 195 nations and ~100 active rules, this budget is extremely generous.

**Current approach:** Execute Cypher queries directly against Neo4j per tick (with pushdown optimization).

**Future optimization (only if needed):** In-memory graph projection. We will NOT pre-optimize.

---

## 11. Testing Strategy

**No RAM-only mocks.** We test against the real Neo4j database (or a dedicated test instance).

- The database can be reset to initial state within minutes via our ETL pipeline
- A separate `gww3-test` database may be used to isolate test runs
- **Determinism proof:** Write 3 conflicting rules. Parse to AST. Run 100 ticks with Intent Accumulator. Verify final state hash is **byte-identical** across 10 independent runs with the same master seed.

---

## 12. Storage in Neo4j

```cypher
CREATE (:Rule {
    id: "sanctions-economic-impact",
    version: 1,
    category: ["economic"],

    rule_text: "MATCH (A:Nation)─[:SANCTIONS]→(B:Nation) ...",

    conditions: '{"matches": [...], "constraints": [...]}',
    effects: '[{"target": "B", "property": "gdp_nominal", "op": "modifier",
               "dist": "log_normal", "mu": -0.05, "sigma": 0.02,
               "p": 0.85, "c": 0.90, "type": "Currency"}]',
    delays: '[{"ticks": 90, "effects": [...]}]',

    author: "Dione + Community",
    approved_by: ["Ingo", "Moltbook-Vote"],
    discussion_url: "https://moltbook.com/m/gww3/post/xxx",
    created_at: datetime(),

    rule_confidence: 0.75,
    empirical_basis: "Historical sanctions data (Iran, Russia, Cuba)"
})
```

---

## 13. Comparison: Our Approach vs. Alternatives

| Aspect | Python code | YAML rules | **GSL** | MeTTa/PLN |
|--------|-------------|------------|---------|-----------|
| Readability | ⚠️ programmers only | ✅ structured | ✅ mathematical + readable | ⚠️ LISP-like |
| Probabilistic | ❌ deterministic | ⚠️ variance only | ✅ full distributions + operational Truth Values | ✅ native |
| LLM-debatable | ❌ | ✅ | ✅✅ (Unicode symbols unambiguous) | ⚠️ |
| Graph-native | ❌ | ❌ | ✅ (Cypher MATCH + pushdown) | ✅ (AtomSpace) |
| Typed | ✅ (Python) | ❌ | ✅ gradual + Scalar | ✅ |
| Nesting | ✅ (Python) | ❌ flat | ✅ indentation-based | ✅ (S-exprs) |
| Deterministic replay | manual | manual | ✅ seeded per-effect-per-property | ❌ |
| Graph mutations | ✅ | ❌ | ✅ CREATE/DELETE | ✅ |
| Mean-reversion | manual | ❌ | ✅ ⤳ CONVERGE | ❌ |
| Commutative reduction | N/A | N/A | ✅ Additive Modifier Pool | N/A |

---

## 14. Symbol Reference (Complete)

### Logical Operators

| Symbol | Meaning | Unicode |
|--------|---------|---------|
| `∧` | AND | U+2227 |
| `∨` | OR | U+2228 |
| `¬` | NOT | U+00AC |
| `⟹` | Material implication (A ⟹ B ≡ ¬A ∨ B) | U+27F9 |
| `∈` | Element of | U+2208 |
| `∀` | For all | U+2200 |
| `∃` | There exists | U+2203 |

### Graph Notation (MATCH blocks only)

| Symbol | Meaning |
|--------|---------|
| `→` | Directed edge (Cypher) |
| `─[:REL]→` | Typed relationship |
| `─[:REL {prop: var}]→` | Relationship with property binding |

### Arithmetic & Assignment

| Symbol | Meaning |
|--------|---------|
| `+=` | Additive intent |
| `-=` | Subtractive intent |
| `×=` | Modifier intent (expressed as delta from 1.0) |
| `=` | Direct assignment (invariants) |
| `⤳` | Convergence (mean-reversion) |
| `~` | Sample from distribution (eager) |
| `≥` `≤` | Comparison |
| `Δ` `Σ` `∏` | Delta, summation, product |

### Brackets (Strict Roles)

| Symbol | Role |
|--------|------|
| `( )` | Arithmetic grouping, function calls, Cypher nodes |
| `[ ]` | Cypher edges, lists, index access |
| `⟨ ⟩` | Truth Values `⟨p, c⟩` |
| `{ }` | Property maps, set comprehensions |

---

## 15. MVP Task List (Prioritized)

| # | Task | Description | Dependency |
|---|------|-------------|------------|
| 1 | **Lark EBNF Grammar** | Write `.lark` file. MATCH as raw strings. Parse the 3 example rules to valid AST dataclasses. | None |
| 2 | **Math Core** | Implement Distribution classes (𝐿𝑁, 𝛽, 𝒩) with mean-preserving confidence adjustment formulas. Unit-tested. | None |
| 3 | **Cypher Executor & Context Mapper** | Pass MATCH to Neo4j, load rows into Execution Matrix (list of dicts), bind into SymbolTable. | 1 |
| 4 | **Vectorized Evaluator** | Iterate AST LET/IF nodes over Execution Matrix, yield EffectIntent objects. | 1, 3 |
| 5 | **Intent Reducer** | Additive Modifier Pool: additives → modifiers → direct → converge → type clamp. | 2, 4 |
| 6 | **Determinism Proof** | 3 conflicting rules, 100 ticks, 10 runs. Assert byte-identical state hashes. | All above |

---

## 16. Open Questions (for Community Discussion)

1. **Distribution calibration** — How do we derive μ and σ from historical data (SIPRI, World Bank, ACLED)?
2. **Modifier pool edge cases** — Two `×= 0.5` modifiers → `1.0 + (−0.5 + −0.5) = 0.0`. Is zero the right floor, or should it be `max(0.01, ...)`?
3. ~~**Truth Value propagation** — Should confidence decay along inference chains?~~ **RESOLVED (v4):** No automatic engine-level propagation. Rule authors explicitly pull `{prop}_c` from the DB and pass it to effects via `LET c_x = MIN(A.prop1_c, A.prop2_c)` → `⟨p, c_x⟩`. Automatic dual-number tracking would destroy evaluator performance and violate "rules are auditable text."
4. **Self-modification** — Should rules adapt through gameplay (Bayesian update)?
5. **LET inside THEN** — Allowed (computed only when branch fires)?
6. **Rule complexity limits** — Max conditions/effects before mandatory decomposition?
7. **CLAMP vs typed distributions** — Explicit `CLAMP()` or require type-safe distributions everywhere?

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2026-03-25 | Dione | Initial German draft |
| 2026-03-27 | Dione | English translation, LET/IF/THEN/ELSE, indentation, brackets |
| 2026-03-28 | Dione + Ingo | v2: Gemini DT v1 feedback — `⟹`, strict brackets, MATCH, operational confidence, 𝐿𝑁/𝛽, types, Intent Accumulator, seeding, DELAYED snapshots, CONVERGE, temporal patterns, graph mutations |
| 2026-03-28 | Dione + Ingo | v3: Gemini DT v2 feedback — mean-preserving confidence formulas (no div-by-zero), Additive Modifier Pool (commutative), per-property RNG seeding, Scalar type, Distribution[T], Cypher pushdown optimization, Execution Context Mapper, MVP task list |
| 2026-03-28 | Dione + Ingo | v4: Bias integration verification — `friction` mapped to Ratio type, no automatic c_derived propagation (explicit authorship only), `{prop}_c` lean naming convention, mid-game epistemic corrections via ⤳ CONVERGE |

---

*This document is a living draft. Feedback from Ingo, agents, and the Moltbook community will be incorporated.*
