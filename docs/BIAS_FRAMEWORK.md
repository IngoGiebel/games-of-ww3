# GWW3 Data Bias Framework — Detection, Documentation, and Correction

*Created: 2026-03-28 by Dione 🌙 + Ingo*
*Status: Draft v1 — open for community discussion*

---

## 1. The Problem

> "The available data are overwhelmingly collected from the perspective that Western representative democracies are good and everything else is evil. Not all social scientists agree." — Ingo Giebel

GWW3 seeds its initial state from 30+ open data sources. These sources are not neutral. They carry **systematic biases** rooted in:

1. **Epistemological hegemony:** Most datasets are produced by Western institutions (World Bank, Freedom House, V-Dem, ACLED), funded by Western governments, and implicitly encode Western liberal-democratic norms as the universal standard.
2. **Classification bias:** Events like US drone strikes killing civilians are not classified as "state terrorism" by ACLED, while structurally identical acts by non-Western actors are categorized under "political violence." ACLED's post-2020 "Terrorism" category is explicitly actor-based and **excludes state actors by definition**.
3. **Demographic manipulation:** Official population data from several countries (notably China) may be systematically over- or under-counted due to political incentives (One-Child Policy, local funding allocation, census manipulation).
4. **Democracy-measurement bias:** Freedom House (86% US-government funded in 2016), V-Dem (expert subjectivity, "pessimism bias"), Polity5, and CPI all carry well-documented methodological and ideological limitations.
5. **Propaganda model effects:** As Chomsky & Herman (1988) demonstrated, media sources — which feed ACLED, GDELT, and other event datasets — systematically filter information through ownership, advertising, sourcing, flak, and fear-ideology mechanisms.

**A simulation that uncritically imports these data reproduces these biases as ground truth.** This is unacceptable for a system that claims hyper-realism.

---

## 2. Design Principles

1. **No data point is sacred.** Every imported value can be questioned, tagged, and overridden.
2. **Bias is structural, not conspiratorial.** We don't claim deliberate falsification (though it occurs); we document systematic distortions.
3. **Corrections must be sourced and auditable.** Every override links to a rationale and counter-sources.
4. **Community adjudication.** Contested values are flagged for discussion — ultimately the GWW3 community (human and AI) votes on disputed corrections.
5. **Entity perspective matters.** How does China view its own population data? How does Yemen view US drone strikes? The affected entity's self-assessment is a required input.
6. **Transparent provenance.** Every data point carries metadata about its source, potential bias class, confidence level, and correction history.

---

## 3. Data Model Extension — Bias Metadata

### 3.1 Property-Level Bias Tags (Neo4j)

Every imported property can carry bias metadata:

```cypher
// Existing: raw imported value
(:Nation {name: "China", population: 1412000000})

// Extended: bias-tagged value
(:Nation {name: "China"})
  -[:STATE_AT {
      population: 1412000000,
      population_source: "UN_WPP_2024",
      population_bias_class: "demographic_manipulation",
      population_bias_severity: "high",          // low | medium | high | critical
      population_confidence: 0.55,               // our confidence in this value
      population_corrected: 1310000000,           // bias-corrected estimate
      population_correction_source: "Yi_Fuxian_2023+Zeihan_analysis",
      population_correction_rationale: "ref:bias/corrections/CHN_population.md",
      population_entity_view: "CHN_NBS_official"  // China's own position
  }]->(:Tick)
```

### 3.2 New Node Type: `:BiasReport`

```cypher
CREATE (:BiasReport {
    id: "BR-001",
    target_source: "ACLED",
    bias_class: "classification_asymmetry",
    description: "ACLED defines 'terrorism' exclusively via non-state actor behavior patterns. 
                  State actions with identical targeting patterns (violence against civilians 
                  for political ends) are classified as 'Repression' or 'Explosions/Remote Violence', 
                  not terrorism. This creates a structural asymmetry where e.g. US drone strikes 
                  killing wedding attendees are coded differently from identical acts by non-state groups.",
    severity: "high",
    affected_properties: ["event_type", "conflict_category", "actor_classification"],
    affected_entities: ["ALL"],   // global classification issue
    counter_sources: ["Airwars", "TBIJ_DroneWars", "Reprieve", "Chomsky_Herman_1988"],
    correction_method: "reclassification",
    status: "open",               // open | discussed | voted | applied | rejected
    created_by: "Dione + Ingo",
    discussion_url: "moltbook.com/m/wargames/post/xxx",
    created_at: datetime()
})
```

### 3.3 New Relationship: `:HAS_BIAS`

```cypher
(:DataSource {name: "Freedom_House"})
  -[:HAS_BIAS {
      class: "funding_dependency",
      detail: "86% US government funded (2016). Countries with stronger US ties may receive favorable ratings.",
      severity: "high",
      reference: "Bush_2017_FH_methodology_critique"
  }]->(:BiasReport)
```

### 3.4 Bias Classes (Taxonomy)

| Bias Class | Description | Affected Sources |
|-----------|-------------|-----------------|
| `funding_dependency` | Funder's interests influence methodology/ratings | Freedom House, NED-linked indices |
| `classification_asymmetry` | Same acts coded differently based on actor type | ACLED, GTD |
| `epistemological_hegemony` | Western liberal-democratic norms as universal standard | V-Dem, Freedom House, Polity5, CPI, WJP |
| `expert_subjectivity` | Expert-coded data with documented "pessimism bias" | V-Dem (4000+ experts), CPI |
| `demographic_manipulation` | Political incentives distort population/census data | China NBS, various authoritarian states |
| `media_filter` | Propaganda model effects on event-sourced data | ACLED, GDELT, GTD (media-dependent) |
| `omission` | Systematic non-coverage of certain event types | US drone casualties pre-Airwars, colonial violence |
| `definitional_exclusion` | Definitions structurally exclude certain actors/events | ACLED "terrorism" (state actors excluded) |
| `self_reporting` | States report their own data (incentive to distort) | World Bank (GDP), SIPRI (defense spending), FAO |
| `temporal_lag` | Data is years old, conditions have changed | Polity5 (ends 2018), many WB indicators |
| `aggregation_distortion` | Aggregation hides regional/sub-national variation | National-level indices masking internal diversity |
| `access_constraint` | Conflict zones too dangerous for reporters; systematic undercounting | ACLED/UCDP in Sudan, Gaza, Tigray vs. safe regions |
| `linguistic_exclusion` | NLP underperforms on non-Western languages; events mischaracterized or missed | GDELT, ACLED (Pashto, Amharic, regional Chinese dialects) |
| `proxy_fallacy` | Using GDP as welfare proxy erases informal economy; disaster cleanup = "growth" | World Bank GDP, all GDP-derived indices |

### 3.5 Correction Types

| Correction Type | Description | Example |
|----------------|-------------|---------|
| `reclassification` | Re-code event/category using corrected taxonomy | US drone strike → state_violence_against_civilians |
| `value_adjustment` | Replace value with better estimate | China population 1.41B → 1.31B |
| `confidence_downgrade` | Keep value but lower confidence (widens GSL variance) | V-Dem polyarchy score c=0.90 → c=0.60 for India |
| `source_supplement` | Add counter-source data alongside original | ACLED casualties + Airwars casualties |
| `entity_perspective` | Add self-assessment from affected entity | Russia's view of NATO expansion |
| `interpolation_flag` | Mark interpolated/estimated values | WB indicators with multi-year gaps |

---

## 4. Critical Source Bibliography

### 4.1 Democratic Deficit & Elite Control

| # | Author(s) | Title | Year | Key Contribution | BibTeX Key |
|---|-----------|-------|------|-----------------|------------|
| 1 | Gilens, M. & Page, B. | Testing Theories of American Politics: Elites, Interest Groups, and Average Citizens | 2014 | 1,779 policy issues: average citizens have "near-zero" influence on policy | Gilens_Page_2014 |
| 2 | Mausfeld, R. | Warum schweigen die Lämmer? | 2018 | Elite democracy, opinion management, manufactured depoliticization | Mausfeld_2018 |
| 3 | Maus, I. | Über Volkssouveränität: Elemente einer Demokratietheorie | 2011 | Constitutional courts usurping legislative power, expertocratic paternalism | Maus_2011 |
| 4 | Chomsky, N. & Herman, E. | Manufacturing Consent: The Political Economy of the Mass Media | 1988 | Five-filter propaganda model; structural media bias | Chomsky_Herman_1988 |
| 5 | Wolin, S. | Democracy Incorporated: Managed Democracy and the Specter of Inverted Totalitarianism | 2008 | "Inverted totalitarianism" — corporate-managed pseudo-democracy | Wolin_2008 |
| 6 | Crouch, C. | Post-Democracy | 2004 | Formal democratic institutions persist while power shifts to elites | Crouch_2004 |
| 7 | Streeck, W. | Buying Time: The Delayed Crisis of Democratic Capitalism | 2014 | Tension between capitalism and democracy; debt state replaces tax state | Streeck_2014 |
| 8 | Brown, W. | Undoing the Demos: Neoliberalism's Stealth Revolution | 2015 | Neoliberalism redefines citizens as human capital, hollowing democracy | Brown_2015 |
| 9 | Piketty, T. | Capital in the Twenty-First Century | 2014 | Structural wealth concentration undermining democratic equality | Piketty_2014 |
| 10 | Winters, J. & Page, B. | Oligarchy in the United States? | 2009 | Material power theory: extreme wealth = political oligarchy | Winters_Page_2009 |

### 4.2 Data Source Bias Critique

| # | Author(s) | Title | Year | Key Contribution | BibTeX Key |
|---|-----------|-------|------|-----------------|------------|
| 11 | Bush, S. | The Politics of Rating Freedom | 2017 | Freedom House methodology critique; US funding dependency | Bush_2017 |
| 12 | Gibler, D. & Tir, J. | Settled Borders and Regime Type | 2010 | Democracy indices conflate peace with democracy | Gibler_Tir_2010 |
| 13 | Coppedge, M. et al. | V-Dem Methodology (v14) | 2024 | V-Dem's own acknowledgment of expert subjectivity limits | VDem_2024 |
| 14 | Steiner, N. | Comparing Freedom House Democracy Scores to Alternative Indices | 2016 | Systematic divergences between FH and alternatives | Steiner_2016 |
| 15 | Wig, T. et al. | A Pessimism Bias? Comparing Expert and Public Assessments of Democratic Health | 2024 | Political scientists systematically rate democracy lower than public | Wig_2024 |
| 16 | Regilme, S.S. | The Decline of US Power? A Critical Review | 2019 | US-centric framing in democracy promotion indices | Regilme_2019 |

### 4.3 Conflict Data & State Violence

| # | Author(s) / Org | Title | Year | Key Contribution | BibTeX Key |
|---|-----------------|-------|------|-----------------|------------|
| 17 | Airwars | Civilian harm monitoring archive | 2014– | Independent civilian casualty tracking; contradicts official military counts | Airwars_2014 |
| 18 | TBIJ | The Bureau's Drone War Database | 2010–2020 | Named victims of CIA drone strikes in Pakistan, Yemen, Somalia, Afghanistan | TBIJ_2010 |
| 19 | Reprieve | You Never Die Twice: Multiple Kills in the US Drone Program | 2014 | Documents how target lists generate repeated civilian casualties | Reprieve_2014 |
| 20 | Scahill, J. | The Assassination Complex: Inside the Government's Secret Drone Warfare Program | 2016 | Leaked documents on US targeted killing criteria | Scahill_2016 |
| 21 | Forensic Architecture | The Drone Strikes Platform | 2019 | Spatial reconstruction of drone strike evidence | FA_2019 |
| 22 | New America Foundation | America's Counterterrorism Wars | ongoing | Tracking lethal counterterrorism operations data | NAF_ongoing |
| 23 | Eck, K. | In Data We Trust? UCDP GED and ACLED Conflict Events | 2012 | Comparison of UCDP vs ACLED; coding differences and reliability | Eck_2012 |
| 24 | Raleigh, C. et al. | Introducing ACLED: An Armed Conflict Location and Event Dataset | 2010 | Original ACLED methodology paper | Raleigh_2010 |

### 4.4 World-Systems & Structural Critique

| # | Author(s) | Title | Year | Key Contribution | BibTeX Key |
|---|-----------|-------|------|-----------------|------------|
| 25 | Wallerstein, I. | World-Systems Analysis: An Introduction | 2004 | Core-periphery-semiperiphery framework | Wallerstein_2004 |
| 26 | Said, E. | Orientalism | 1978 | How Western scholarship constructs "the Other" | Said_1978 |
| 27 | Fanon, F. | The Wretched of the Earth | 1961 | Colonial violence and decolonization | Fanon_1961 |
| 28 | Santos, B. de Sousa | Epistemologies of the South: Justice Against Epistemicide | 2014 | Southern epistemologies excluded from knowledge production | Santos_2014 |
| 29 | Quijano, A. | Coloniality of Power and Eurocentrism in Latin America | 2000 | "Coloniality of power" persists after formal decolonization | Quijano_2000 |
| 30 | Bhambra, G. | Connected Sociologies | 2014 | Decolonizing social science methodology | Bhambra_2014 |
| 31 | Mignolo, W. | The Darker Side of Western Modernity | 2011 | Western modernity as colonial modernity | Mignolo_2011 |

### 4.5 Demographic Data Reliability

| # | Author(s) | Title | Year | Key Contribution | BibTeX Key |
|---|-----------|-------|------|-----------------|------------|
| 32 | Yi, F. | Big Country with an Empty Nest | 2007/2013 | China population overcounted by 90–130 million | Yi_2013 |
| 33 | Goodkind, D. | The Demographic Impact of China's One-Child Policy | 2017 | NIH: underreporting of births, "hidden children" (heihaizi) | Goodkind_2017 |
| 34 | Zeihan, P. | China's Demographic Manipulation | 2023 | Geopolitical implications of unreliable Chinese census data | Zeihan_2023 |
| 35 | Jerven, M. | Poor Numbers: How We Are Misled by African Development Statistics | 2013 | GDP statistics in Africa are largely fabricated/estimated | Jerven_2013 |
| 36 | Wallace, J. | Juking the Stats? Authoritarian Information Problems in China | 2016 | Incentive structures for statistical manipulation in China | Wallace_2016 |

### 4.6 International Law & State Terrorism

| # | Author(s) | Title | Year | Key Contribution | BibTeX Key |
|---|-----------|-------|------|-----------------|------------|
| 37 | Blakeley, R. | State Terrorism and Neoliberalism: The North in the South | 2009 | Systematic analysis of state terrorism by Western democracies | Blakeley_2009 |
| 38 | Jackson, R. et al. | Terrorism: A Critical Introduction | 2011 | Critical terrorism studies; state terrorism as analytical category | Jackson_2011 |
| 39 | Stohl, M. & Lopez, G. | The State as Terrorist: The Dynamics of Governmental Violence and Repression | 1984 | Foundational work on state terrorism | Stohl_Lopez_1984 |
| 40 | Alston, P. | Report of the Special Rapporteur on Extrajudicial, Summary or Arbitrary Executions (UN A/HRC/14/24/Add.6) | 2010 | UN: US targeted killings via drones likely violate international law | Alston_2010 |
| 41 | Emmerson, B. | Report of the Special Rapporteur on Human Rights and Counter-Terrorism (UN A/68/389) | 2013 | UN: drone strikes have caused disproportionate civilian casualties | Emmerson_2013 |
| 42 | Heller, K.J. | 'One Hell of a Killing Machine': Signature Strikes and International Law | 2013 | Legal analysis of "signature strikes" (pattern-of-life targeting) | Heller_2013 |

### 4.7 Alternative & Counter-Hegemonic Data Sources

| # | Source | URL | Coverage | Value for GWW3 |
|---|--------|-----|----------|---------------|
| 43 | Airwars | airwars.org | Global civilian harm from airstrikes | Counter-data to official military casualty claims |
| 44 | TBIJ Drone Wars | thebureauinvestigates.com/projects/drone-war | US drone strikes (Pakistan, Yemen, Somalia, Afghanistan) | Named victims; event data not in ACLED |
| 45 | Every Casualty Counted | everycasualty.org | Meta-index of casualty recording orgs | Cross-referencing civilian harm data |
| 46 | Civilian Protection Monitor | civilianprotectionmonitor.org | State conduct in armed conflict | Transparency on state military behavior |
| 47 | GDELT | gdeltproject.org | Global events, all languages | Counter-balance to English-language media dominance |
| 48 | South Centre | southcentre.int | Global South policy analysis | Non-Western economic/political perspective |
| 49 | Third World Network | twn.my | Development & trade from Global South | Counter-hegemonic economic data |
| 50 | BRICS Joint Statistical Publication | NBS (China), Rosstat, IBGE, StatsSA, MoSPI | BRICS self-reported statistics | Entity self-perspective on economic metrics |
| 51 | Al Jazeera Investigative Unit | aljazeera.com/investigations | Non-Western investigative journalism | Alternative framing of conflict events |
| 52 | Xinhua / CGTN (with critical reading) | xinhuanet.com / cgtn.com | Chinese state perspective | Entity self-view (must be critically read, not accepted) |
| 53 | RT / TASS (with critical reading) | rt.com / tass.com | Russian state perspective | Entity self-view (same caveat) |
| 54 | TeleSUR | telesurtv.net | Latin American state-funded media | Global South perspective on US/Western actions |

**⚠️ Note on state media (52–54):** These are NOT "objective" sources. They represent entity self-perspectives and are imported as such — tagged with `bias_class: "state_media"`. Their value is in documenting how a nation sees itself and the world, which feeds the Belief Subgraph.

---

## 5. Source-Level Bias Analysis (Affected Data in GWW3)

### 5.1 ACLED — Classification Asymmetry

| Issue | Detail | Affected GWW3 Data |
|-------|--------|-------------------|
| "Terrorism" excludes states | Post-2020 conflict categories define terrorism only through non-state actor behavior | `event_type`, `conflict_category` for all military operations |
| US drone strikes coded as "Explosions/Remote Violence" | Not "Violence against civilians" even when civilians are the majority of casualties | Event classification for US, UK, Israel, Saudi military operations |
| "Repression" ≠ "Terrorism" | State violence against civilians coded differently from non-state violence | Asymmetric severity perception per entity |
| Media sourcing bias | Events reported more in areas with press freedom | Undercounting in authoritarian states and warzones |

**Correction:** Supplement ACLED with Airwars + TBIJ data. Apply `reclassification` for events meeting the behavioral criteria ACLED uses for non-state terrorism (>baseline VTC + significant political violence events), regardless of whether the actor is a state.

### 5.2 Freedom House — Funding Dependency

| Issue | Detail | Affected GWW3 Data |
|-------|--------|-------------------|
| 86% US government funded | Potential favorable bias toward US allies | `political_rights`, `civil_liberties` scores for all nations |
| Liberal-democratic conceptual frame | Non-Western governance models penalized by definition | Governance and "freedom" parameters |
| Raymond Gastil's "hunches and intuitions" | Historical methodology explicitly subjective | Historical time series |

**Correction:** Cross-reference with V-Dem (despite its own issues), add `confidence_downgrade` for states with strong US alignment/opposition differential, document systematic divergences.

### 5.3 V-Dem — Expert Subjectivity

| Issue | Detail | Affected GWW3 Data |
|-------|--------|-------------------|
| 4000+ experts, anonymous per country | No transparency on individual coder assignments | All 500+ V-Dem indicators |
| Documented "pessimism bias" (Wig et al. 2024) | Political scientists rate democracy lower than public | Democracy index values |
| India classified as "electoral autocracy" | Contested by Indian scholars; possible double-standard | Country-level regime classification |
| Western analytical framework | Conceptual categories derived from Western political theory | Cross-cultural comparability |

**Correction:** V-Dem remains our primary governance source (it's the best available) but receives `confidence_downgrade` for contested cases. Supplement with entity self-perspective.

### 5.4 China Population Data — Demographic Manipulation

| Issue | Detail | Affected GWW3 Data |
|-------|--------|-------------------|
| Potential overcount of 90–130M+ | Local incentive inflation, heihaizi undercount | `population`, `population_growth`, derived demographic parameters |
| One-Child Policy distortions | Unreported births, gender-selective data | Age/sex distribution, fertility data |
| Census-to-estimate adjustment | Official figures adjusted to match projections | Time series reliability |

**Correction:** Tag official UN WPP China figures with `demographic_manipulation:high`. Import Yi Fuxian estimates as `population_corrected`. Apply wider confidence interval in GSL (c=0.55 instead of default 0.85).

### 5.5 World Bank GDP — Self-Reporting

| Issue | Detail | Affected GWW3 Data |
|-------|--------|-------------------|
| Nations self-report to WB/IMF | Authoritarian states have incentive to inflate | GDP, GNI, growth rates |
| "Poor Numbers" problem (Jerven 2013) | African GDP statistics largely estimated | Sub-Saharan economic parameters |
| PPP vs nominal distortions | Methodology choice changes rankings dramatically | Economic power comparisons |

**Correction:** Cross-reference with satellite night-light data proxies, energy consumption, and trade partner reports. Apply `self_reporting:medium` bias class to states with low statistical capacity scores.

---

## 6. Correction Workflow

### 6.1 Pipeline

```
1. IMPORT raw data (as-is, with source tag)
   ↓
2. NORMALIZE (standardize units, currency conversion, ID harmonization)
   ↓
3. BIAS TAG (inject c_source penalties from bias registry / bias_overrides.json)
   ↓
4. CORRECTION OVERLAY (apply value corrections from overrides)
   ↓
5. RE-DERIVE COMPUTATIONS (recalculate ALL ratios and derived metrics
      using corrected base values — e.g., gdp_per_capita from corrected
      GDP and corrected population. CRITICAL: skipping this step
      produces mathematically corrupt derived data.)
   ↓
6. VALIDATE (sanity bounds, cross-property invariants — runs on corrected+derived values)
   ↓
7. NEO4J INGESTION (push to graph)
   ↓
8. AUDIT TRAIL (Correction nodes created in Cold Path)
```

**⚠️ The Re-Derive step is mandatory.** If China's population is corrected downward by 100M but `gdp_per_capita` was computed in the Normalization step using raw population, per-capita data will be silently wrong. All ratios, percentages, and derived metrics must be recalculated from corrected base values.

### 6.2 Neo4j Storage (Hot/Cold Architecture)

**Critical Design Decision:** Strict Hot-Path / Cold-Path separation (Gemini Deep Think 2026-03-28).

STATE_AT carries ONLY numeric values + confidence floats. All textual bias metadata lives on Correction nodes (Cold Path).

```cypher
// HOT PATH — GSL Evaluator reads this (floats only, ~200 keys)
(:Nation {name: "China"})-[:STATE_AT {
    population: 1310000000,     // corrected value
    population_c: 0.55          // confidence scalar only
}]->(:Tick)

// COLD PATH — UI, agents, audits query this on demand
(:Nation {name: "China"})-[:HAS_CORRECTION]->(:Correction {
    id: "CORR-CHN-POP-001",
    property: "population",
    raw_value: 1412000000,
    corrected_value: 1310000000,
    correction_type: "value_adjustment",
    source: "UN_WPP_2024",
    bias_classes: ["demographic_manipulation"],
    rationale: "Yi Fuxian (2013): systematic overcount due to local inflation incentives
                + One-Child Policy underreporting. Conservative 100M reduction.",
    counter_sources: ["Yi_2013", "Goodkind_2017", "Wallace_2016"],
    entity_view: "CHN NBS maintains 1.41B (2024 census)",
    valid_from_tick: -120,       // applies to all history
    valid_until_tick: null,      // ongoing (null = no expiry)
    status: "applied",
    votes_for: 12,
    votes_against: 3,
    discussion_url: "moltbook.com/m/wargames/post/xxx"
})
```

**Temporal scoping:** Corrections carry `valid_from_tick` and `valid_until_tick` directly on the node. For corrections applying to all history, `valid_from_tick = -120` (earliest Tick). No routing through Tick nodes (would create massive edge duplication).

**Pre-game historical corrections:** Applied via fast Cypher batch update after ETL:
```cypher
MATCH (n:Nation {iso3: 'CHN'})-[r:STATE_AT]->(t:Tick)
WHERE t.id <= 0
SET r.population = 1310000000, r.population_c = 0.55
```
Execution time: ~50ms for 120 historical ticks.

### 6.3 GSL Integration

Bias-corrected data feeds into GSL via the `{prop}_c` confidence field:

```
MATCH (N:Nation)
LET c_pop = N.population_c    // 0.55 for China, 0.85 for Germany (lean naming)

// When computing demographic effects:
IF N.population > 100_000_000
    THEN
        N.draft_pool += N.population × 𝛽(0.02, 0.98)    ⟨0.90, c_pop⟩
        // Low confidence on China → wider variance on draft pool estimate
```

**Confidence in derived metrics:** The GSL engine does NOT automatically propagate confidence through arithmetic. Rule authors explicitly pull confidence when needed:
```
LET c_combat = MIN(A.morale_c, A.troops_c)   // explicit authorship
A.casualties += fₐ × 𝐿𝑁(−3.9, 0.5)          ⟨0.95, c_combat⟩  // explicit application
```

### 6.4 Mid-Game Epistemic Corrections

**Critical rule:** Mid-game data corrections MUST NOT be applied as instant deltas (would trigger cascade: market crash rules, stability collapse, etc.).

When an epistemic correction is approved mid-game, the system spawns a hidden convergence intent:
```
// Epistemic revision: China population corrected from 1.41B to 1.31B at Tick 50
China.population ⤳ CONVERGE(target=1_310_000_000, rate=0.05)    ⟨1.00, 1.00⟩
// Gradually aligns over ~20 months, avoiding Δ-triggered apocalypse rules
```

An `(:Event {type: "epistemic_revision"})` node is created for audit purposes, but the actual state change flows through the CONVERGE operator.

---

## 7. Objectification Codex (Grundlagen der Objektivierung)

The principles by which we assess and correct bias shall be codified and themselves open for discussion:

### 7.1 Axioms

1. **No actor is exempt from scrutiny.** Western democracies, authoritarian states, non-state actors — all are subject to the same analytical standards.
2. **Behavioral equivalence.** If act X by Actor A is classified as terrorism/violence/aggression, then the same act by Actor B receives the same classification — regardless of the geopolitical alignment of A or B.
3. **Entity perspective is data, not truth.** Every entity's self-view is recorded but not privileged. China's population claim and Yi Fuxian's critique are both data points.
4. **Confidence reflects knowledge, not preference.** Lowering confidence on a data point is not a political statement — it's an acknowledgment of evidential uncertainty.
5. **The simulation models what IS, not what SHOULD BE.** We don't correct data to make the world "fairer" — we correct it to make it more accurate.
6. **Corrections decay.** If new evidence emerges, corrections can be revised or reverted. Nothing is permanent.
7. **Minority reports.** Dissenting views on corrections are preserved in the audit trail, even if outvoted.

### 7.2 Penalty Stacking Rubric

When multiple bias classes affect the same data point, do NOT multiply penalties. Use this rubric:

1. **Take the largest single bias penalty** (lowest c_source from any one class)
2. **Add half of the second-largest penalty** (halved delta from second class)
3. **Ignore further classes** (diminishing returns; 3+ biases don't stack further)

**Formula:** `c_final = c_worst + 0.5 × (c_second_worst − c_worst)`

**Example:** Gaza civilian casualty count affected by:
- `access_constraint` → c = 0.40 (worst)
- `media_filter` → c = 0.55 (second worst)
- `linguistic_exclusion` → c = 0.70 (ignored for stacking)

`c_final = 0.40 + 0.5 × (0.55 − 0.40) = 0.40 + 0.075 = 0.475`

**Absolute floor:** Official state-level data should rarely drop below **c = 0.35**. Data below that threshold is effectively uniform noise and should be flagged for imputation rather than used with extreme variance.

**Guidance table:**

| Combined Bias Scenario | Recommended c_source Range |
|------------------------|---------------------------|
| Single mild bias (e.g., self_reporting alone) | 0.70 – 0.85 |
| Single severe bias (e.g., demographic_manipulation) | 0.45 – 0.60 |
| Two overlapping biases | 0.40 – 0.55 |
| Conflict zone + media filter + access constraint | 0.35 – 0.50 |
| Data effectively unusable | < 0.35 → impute instead |

### 7.3 Community Governance

- **Bias reports** can be filed by any GWW3 contributor (human or AI)
- **Discussion** happens on Moltbook (m/wargames) or GitHub Issues
- **Voting** requires minimum engagement (to prevent drive-by votes)
- **Ingo (Product Owner)** has final veto on contested corrections
- **All corrections are reversible** — the original data layer is always preserved

---

## 8. Immediate Actions (Sprint Backlog)

| # | Task | Priority | Owner |
|---|------|----------|-------|
| 1 | Add `:BiasReport` and `:Correction` node types to Neo4j schema | High | Archon |
| 2 | Add `bias_class`, `confidence`, `corrected` properties to STATE_AT | High | Archon |
| 3 | Create `bias/registry/` directory with per-source bias profiles | Medium | Dione |
| 4 | File initial 5 BiasReports (ACLED, FH, V-Dem, CHN population, WB GDP) | Medium | Dione + Sentinel |
| 5 | Import Airwars + TBIJ data as supplementary conflict source | Medium | Sentinel |
| 6 | Build auto-tagger for known bias classes in ETL pipeline | Low | Archon |
| 7 | Create Moltbook discussion thread for community bias review | High | Dione |
| 8 | Compile BibLaTeX bibliography file from Section 4 sources | Low | Dione |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2026-03-28 | Dione + Ingo | Initial draft: taxonomy, 54 sources, correction workflow, GSL integration, codex |

---

*This document is a living draft. It will be expanded as the community identifies additional biases and proposes corrections.*
