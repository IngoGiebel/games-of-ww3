# Games of World War 3 – Open Data Source Catalog

Last updated: 2026-03-23

Purpose: pipeline-ready inventory of free/open (and key paid) geopolitical data sources for Neo4j ingestion, targeting >1000 parameters per entity (states + non-state actors).

## Quick Integration Architecture (Neo4j)

- Use `country-year` as the base grain for state indicators (economy, governance, demographics).
- Use `event` grain for conflict/terror/non-state activity (ACLED, UCDP GED, GTD).
- Use `dyad-year` grain for trade, alliances, votes, disputes (Comtrade, ATOP, UNGA voting, COW dyads).
- Normalize IDs early: ISO3 + COW code + UN M49 + source-native IDs.
- Keep source snapshots/version tags (`source_version`, `ingest_date`, `license`) to support replay and audits.

---

## 1) Economic Data Sources

### 1.1 World Bank Indicators API (WDI + 45+ DBs)
- URL: https://api.worldbank.org/v2/ ; docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
- Access method: Open API, no key required.
- Example endpoint:
  - Country-indicator time series: `https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json&per_page=20000`
  - Indicator metadata: `https://api.worldbank.org/v2/indicator?format=json&per_page=20000`
- Format: JSON (default XML also supported).
- Update frequency: Varies by indicator (annual/quarterly/monthly where available); WDI commonly annual refresh cycles.
- Coverage: ~16,000 indicators; ~200+ economies; multi-decade historical coverage.
- Rate limits: No strict published hard cap in the referenced doc; throttle politely.
- Approx data points: multi-million observations across all indicators (country x year x indicator).
- High-value indicators (codes) for simulation core:
  - GDP current US$: `NY.GDP.MKTP.CD`
  - GDP constant 2015 US$: `NY.GDP.MKTP.KD`
  - GDP growth %: `NY.GDP.MKTP.KD.ZG`
  - GDP per capita: `NY.GDP.PCAP.CD`
  - GNI current US$: `NY.GNP.MKTP.CD`
  - GNI per capita Atlas: `NY.GNP.PCAP.CD`
  - Inflation CPI %: `FP.CPI.TOTL.ZG`
  - Unemployment %: `SL.UEM.TOTL.ZS`
  - Population total: `SP.POP.TOTL`
  - Urban population %: `SP.URB.TOTL.IN.ZS`
  - Government final consumption % GDP: `NE.CON.GOVT.ZS`
  - Military expenditure % GDP: `MS.MIL.XPND.GD.ZS`
  - Exports goods/services % GDP: `NE.EXP.GNFS.ZS`
  - Imports goods/services % GDP: `NE.IMP.GNFS.ZS`
  - Trade % GDP: `NE.TRD.GNFS.ZS`
  - Current account balance % GDP: `BN.CAB.XOKA.GD.ZS`
  - FDI net inflows % GDP: `BX.KLT.DINV.WD.GD.ZS`
  - External debt stocks % GNI: `DT.DOD.DECT.GN.ZS`
  - Reserves (incl. gold), current US$: `FI.RES.TOTL.CD`
  - Poverty headcount $2.15/day: `SI.POV.DDAY`
  - Gini index: `SI.POV.GINI`

Pipeline note:
- Pull indicator catalog once, then maintain allowlist by theme (macro/fiscal/trade/social/infrastructure/security).

### 1.2 IMF World Economic Outlook (WEO)
- URL: https://data.imf.org/en/datasets/IMF.RES:WEO and https://www.imf.org/en/Publications/SPROLLS/world-economic-outlook-databases
- Access method: IMF Data portal (API + downloadable Excel). Free access to WEO dataset.
- Endpoint: exposed via IMF portal API resource for WEO (portal-native query interface).
- Format: API responses + Excel dataset files.
- Update frequency: Biannual (April and October editions).
- Coverage: Macro/fiscal/BOP/trade/unemployment/inflation/commodity aggregates; data from ~1980 onward + forward projections (~5 years).
- Countries: broad global + country groups/aggregates.
- Approx data points: hundreds of series x 190+ countries x 40+ years (millions including forecasts).

Pipeline note:
- Separate `actual` vs `forecast` values; keep vintage dimension (`WEO_YYYY_MM`).

### 1.3 OECD Data API (SDMX)
- URL: https://sdmx.oecd.org/public/rest/ ; explainer: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html
- Access method: Free SDMX REST API.
- Endpoint examples:
  - List dataflows: `https://sdmx.oecd.org/public/rest/dataflow/all`
  - Data query pattern: `/public/rest/data/{AGENCY},{DATASET},{VERSION}/{SELECTION}?startPeriod=...&format=jsondata`
- Format: JSON (`format=jsondata`), CSV (`csvfile`, `csvfilewithlabels`), XML (`genericdata`).
- Update frequency: Dataset-dependent (monthly/quarterly/annual releases).
- Coverage: OECD members + many partner economies; very broad topical coverage.
- Rate limits: Rate limiting is implemented (no universal public numeric cap disclosed in the explainer).
- Approx data points: tens of millions across all dataflows.

### 1.4 UN Comtrade
- URL: portal info https://comtradeplus.un.org ; developer portal https://comtradedeveloper.un.org ; product/pricing details https://shop.un.org/lec/node/55
- Access method: API via developer portal (key-based), plus web download tools; premium tiers for high-volume/bulk/async.
- Format: API JSON/CSV outputs depending endpoint; bulk files for premium workflows.
- Update frequency: continuous/periodic updates as reporters submit; annual series from 1962 onward; UNSD describes regular refreshes.
- Coverage: close to 200 reporters; goods trade by reporter/partner/commodity/flow; 3+ billion records cited by UNSD tools.
- Rate limits:
  - Free and premium limits vary by subscription/product level (paid tiers explicitly list query/day limits and unlimited institutional plans).
  - Treat free tier as constrained; implement pagination, backoff, and token rotation policy compliance.
- Approx data points: billions (global historical trade lines).

---

## 2) Military & Security Data Sources

### 2.1 SIPRI Military Expenditure Database
- URL: https://www.sipri.org/research/armaments/milex/milex_database ; methods: https://www.sipri.org/databases/milex/sources-and-methods
- Access method: Downloadable dataset (Excel) via SIPRI database pages; no public official REST API documented.
- Format: Excel + web query interface.
- Update frequency: Annual updates; historical revisions possible each cycle.
- Coverage: Country military expenditure, 1949-present (currently through 2024 in published description).
- Metrics: local currency, current/constant USD, % GDP, per capita, % government expenditure.
- Approx data points: country-year panel (~170+ countries x 75 years x multiple measures).

### 2.2 SIPRI Arms Transfers Database
- URL: https://www.sipri.org/databases/armstransfers ; direct DB: https://armstransfers.sipri.org
- Access method: Public web database query + exports; no open public API documented.
- Format: tabular exports from query interface.
- Update frequency: Annual (latest update noted 2026-03-09 for data through 2025).
- Coverage: major conventional arms transfers, 1950-present year.
- Includes: supplier/recipient, weapon class, deliveries, TIV.
- Approx data points: very large transfer-register-level records over 75+ years.

### 2.3 Global Firepower (GFP)
- URL: https://www.globalfirepower.com/
- Access method: Web pages only (no official public API); scraping likely required.
- Format: HTML tables/content; ranking + country pages.
- Update frequency: Annual index release (e.g., 2026 edition).
- Coverage: 145 countries; 60+ factors reported.
- Licensing/use: site content reuse restrictions apply; verify ToS before automated extraction.

### 2.4 IISS Military Balance
- URL: https://www.iiss.org/ (Military Balance products)
- Access method: Paid/subscription publication (not open).
- Format: reports + online tools for subscribers.
- Update frequency: Annual major releases + periodic updates by product.
- Coverage: global order of battle/defence capabilities.
- Open alternatives: SIPRI, IISS-adjacent open OSINT datasets, COW National Material Capabilities, ACLED/UCDP event-level.

### 2.5 ACLED
- URL: API docs https://acleddata.com/acled-api-documentation ; endpoint format docs https://acleddata.com/api-documentation/elements-acleds-api
- Access method: API (OAuth/keyed access), plus download tools.
- Endpoint example: `https://acleddata.com/api/acled/read?_format=json&...`
- Format: JSON (default), CSV, XML (documented response formats).
- Update frequency: near-real-time/continuous publishing (region dependent); API returns update metadata.
- Coverage: global political violence/protest events, state and non-state actors.
- Approx data points: millions of event rows.

### 2.6 NTI Nuclear Security Index
- URL: https://www.ntiindex.org/
- Access method: open downloadable data files from index site.
- Format: report + spreadsheet/model downloads.
- Update frequency: edition-based (not daily).
- Coverage: 175 countries + Taiwan; multiple index pillars and indicator-level scores.
- Approx data points: country x indicators x editions.

### 2.7 FAS Nuclear Notebook (Federation of American Scientists)
- URL: https://fas.org/publication-term/nuclear-notebook/
- Access method: published analyses and country estimates (open articles; some hosted via Bulletin publications).
- Format: article/PDF tables.
- Update frequency: rolling country notebooks, typically annual cadence by nuclear-armed state.
- Coverage: 9 nuclear-armed states; stockpile/deployed estimates and force structure analysis.
- Note: estimates, not official disclosed inventories for most states.

### 2.8 Global Terrorism Database (START)
- URL: https://www.start.umd.edu/gtd-download and https://www.start.umd.edu/data-tools/GTD
- Access method: downloadable dataset under EULA (registration required).
- Format: XLSX (full dataset and updates), codebook PDF.
- Update frequency: periodic releases (historical core through 2020 + update files).
- Coverage: global terrorism incidents since 1970; 200,000+ events cited by project pages.

---

## 3) Political & Governance Data Sources

### 3.1 Freedom House (Freedom in the World / FoN / Nations in Transit)
- URL: https://freedomhouse.org/country/scores and report page https://freedomhouse.org/report/freedom-world
- Access method: downloadable Excel historical/comparative files.
- Format: XLSX.
- Update frequency: annual report cycle.
- Coverage: FIW ratings since 1973 (country-level rights/civil liberties), plus thematic datasets.
- API: no official public API documented.

### 3.2 Transparency International Corruption Perceptions Index (CPI)
- URL: latest publication e.g. https://www.transparency.org/en/publications/corruption-perceptions-index-2025
- Access method: downloadable dataset from CPI publication pages.
- Format: XLSX/CSV-style downloadable tables (varies by year package).
- Update frequency: annual.
- Coverage: ~180+ countries/territories (182 in 2025 edition).
- API: no official public CPI API.

### 3.3 Fragile States Index (Fund for Peace)
- URL: global data page https://fragilestatesindex.org/global-data/ ; methodology https://fragilestatesindex.org/methodology/
- Access method: web global data table + Excel download.
- Format: Excel + web table.
- Update frequency: annual.
- Coverage: 178 countries; 12 main indicators + substructure; historical annual series (site currently exposes 2007+ full panel on global data page).
- API: no official public API documented.

### 3.4 V-Dem
- URL: https://www.v-dem.net/vdemds.html
- Access method: open downloadable packages (registration form on site).
- Format: CSV, STATA, R, SPSS + codebook.
- Update frequency: annual major version releases.
- Coverage: Country-year and country-date datasets; 500+ indicators and 200+ indices in recent versions.
- Approx data points: very high-dimensional panel (enough alone for hundreds of polity variables).

### 3.5 Polity (Polity5)
- URL: https://www.systemicpeace.org/inscrdata.html
- Access method: free download (Excel/SPSS + codebook).
- Format: XLS/SPSS.
- Update frequency: Polity5 currently documented through 2018 in public release.
- Coverage: 1800-2018; annual and polity-case formats.

### 3.6 World Justice Project Rule of Law Index
- URL: report pages with data downloads, e.g. https://worldjusticeproject.org/our-work/publications/rule-law-index-reports/wjp-rule-law-index-2020
- Access method: downloadable report + Excel data from report pages.
- Format: PDF + Excel.
- Update frequency: annual editions.
- Coverage: 100+ countries (expanded over time; 140+ in recent years per WJP communications).
- API: no stable public API documented.

---

## 4) Demographic & Social Data Sources

### 4.1 UN Population Division – World Population Prospects (WPP)
- URL: https://www.un.org/development/desa/pd/world-population-prospects-2024 and dataset page https://www.un.org/development/desa/pd/content/world-population-prospects-2024-dataset
- Access method: open dataset downloads + online portal.
- Format: CSV/XLSX bundles via UN DESA portal.
- Update frequency: major revision cycle (latest 2024 revision), with periodic UNdata refreshes.
- Coverage: 237 countries/areas; estimates 1950-2023, projections 2024-2100.
- Granularity: age/sex/fertility/mortality/migration and derived indicators.

### 4.2 World Bank Health/Education indicators
- URL: same WB API base (`api.worldbank.org/v2`).
- Access method: API.
- Format: JSON/XML.
- Update frequency: indicator-dependent.
- Coverage: global country panel across education, health, poverty, labor.
- Sample indicators:
  - Life expectancy: `SP.DYN.LE00.IN`
  - Infant mortality: `SP.DYN.IMRT.IN`
  - Physicians per 1,000: `SH.MED.PHYS.ZS`
  - Hospital beds per 1,000: `SH.MED.BEDS.ZS`
  - Current health expenditure % GDP: `SH.XPD.CHEX.GD.ZS`
  - School enrollment primary gross: `SE.PRM.ENRR`
  - School enrollment secondary gross: `SE.SEC.ENRR`
  - Government expenditure on education % GDP: `SE.XPD.TOTL.GD.ZS`

### 4.3 Pew Research (religion and social datasets)
- URL: https://www.pewresearch.org/religion-datasets/ and dataset portal https://www.pewresearch.org/datasets/
- Access method: free account login required for downloads.
- Format: typically SPSS/Excel + codebooks.
- Update frequency: release-based by study.
- Coverage examples:
  - Global restrictions on religion dataset: 198 countries/territories, 2007-2022.
  - Global religious composition estimates: 201 countries, 2010 and 2020 baseline comparison.
- API: no public API.

### 4.4 CIA World Factbook
- URL: https://www.cia.gov/the-world-factbook
- Access method: web content (country pages, comparisons, references); no official public API.
- Format: HTML (scrape/parse), structured sections by topic.
- Update frequency: continuous rolling updates (Factbook weekly/periodic field updates shown).
- Coverage: 258 world entities.
- Data types available: population, economy, energy, military/security, communications, transport, geography, environment, governance summary.

---

## 5) Geographic & Infrastructure Data Sources

### 5.1 Natural Earth
- URL: https://www.naturalearthdata.com/downloads/
- Access method: direct download.
- Format: SHP, GeoPackage, SQLite (raster + vector themes).
- Update frequency: versioned releases (currently 5.1.1 on major layers).
- Coverage: global; 1:10m, 1:50m, 1:110m scales.
- Key layers: admin boundaries, disputed areas, populated places, ports, airports, roads, urban areas, physical terrain features.
- License: free for any type of project (per Natural Earth terms).

### 5.2 OpenStreetMap ecosystem
- Core APIs and dumps:
  - OSM API v0.6 docs: https://wiki.openstreetmap.org/wiki/API_v0.6
  - Planet dumps: https://planet.openstreetmap.org/ and background https://wiki.openstreetmap.org/wiki/Planet.osm
  - Overpass query service docs: https://dev.overpass-api.de/command_line.html
  - Regional extracts (practical ingestion): https://www.geofabrik.de/geofabrik/openstreetmap.html
- Access method: API + full/partial dumps.
- Format: PBF, OSM XML, JSON/XML (API responses), derived geospatial formats.
- Update frequency: minutely/hourly diffs, weekly planet dumps.
- Coverage: global volunteered geodata down to street/building/POI where mapped.
- Rate/policy notes:
  - Public services are capacity-limited; self-hosting strongly recommended for heavy production use.
  - Nominatim public instance explicitly limits heavy use (max ~1 req/sec) per OSMF policy.

### 5.3 USGS (resources/minerals/geohazards)
- URL: mineral data hub https://www.usgs.gov/programs/mineral-resources-program/data ; earthquake feeds https://earthquake.usgs.gov/earthquakes/feed/
- Access method: open datasets and web services.
- Format: CSV/GeoJSON/KML/QuakeML and dataset-specific formats.
- Update frequency: near-real-time (earthquakes), periodic for mineral/resource datasets.
- Coverage: global geohazard feeds; mineral/resource datasets vary by commodity/project.
- Note: MRDS legacy references exist; prefer current USGS data program repositories for modern ingest.

### 5.4 EIA (U.S. Energy Information Administration)
- URL: docs https://www.eia.gov/opendata/documentation.php ; browser https://www.eia.gov/opendata/browser/
- Access method: API v2 with key.
- Endpoint pattern: `https://api.eia.gov/v2/{route}/data?api_key=...`
- Format: JSON.
- Update frequency: route-dependent (daily/monthly/annual series).
- Coverage: extensive US + international energy series (oil/gas/electricity/prices/trade/emissions subsets).
- Limits: API returns max rows per request (documented 5,000), supports pagination/offset.

### 5.5 IEA (International Energy Agency)
- URL: data portal https://www.iea.org/data-and-statistics ; API docs https://www.iea.org/documentation
- Access method:
  - Some free datasets/tools (e.g., selected monthly electricity/gas).
  - Enterprise/paid API access for release automation (documented bearer API for customers).
- Format: CSV/Excel/TXT depending product.
- Update frequency: product-dependent (monthly/annual).
- Coverage: 170+ countries in data browser; broad energy balances/statistics.

### 5.6 FAO / FAOSTAT
- URL: FAOSTAT portal https://www.fao.org/faostat/en/#data ; FAO data dissemination https://www.fao.org/statistics/databases/en/ ; release calendar https://www.fao.org/statistics/data-releases/en
- Access method: open bulk downloads + APIs used by FAOSTAT backend.
- Bulk format: zipped CSVs (normalized long format common).
- Common bulk base: `https://fenixservices.fao.org/faostat/static/bulkdownloads/`
- Update frequency: frequent scheduled releases (monthly/periodic by domain).
- Coverage: 23 major FAO databases; global food/agriculture/fisheries/forestry/nutrition.

---

## 6) Non-State Actor Data Sources

### 6.1 ACLED (primary)
- See section 2.5.
- Non-state utility: armed group names, event interactions, actor dyads, geolocated violence/protest events.

### 6.2 Stanford Mapping Militant Organizations (MMO)
- URL: https://web.stanford.edu/group/mappingmilitants/cgi-bin/pages/home
- Access method: web profiles/maps; no public official API documented.
- Format: HTML content + relationship maps (requires scraping/export engineering).
- Update frequency: project-maintained, theatre dependent.
- Coverage: selected conflict theatres; group profiles, ties, leadership, attacks context.

### 6.3 UCDP (Uppsala Conflict Data Program)
- URL: download center https://ucdp.uu.se/downloads/
- Access method: dataset downloads + API documentation linked from download center.
- Format: CSV/other statistical formats depending dataset version.
- Update frequency: annual versioned releases.
- Coverage:
  - GED (event-level, geo-coded, 1989-2024 in latest release stream)
  - Non-state conflict, one-sided violence, dyadic and battle deaths datasets.
- Licensing: free for academic/non-commercial uses; check current terms for redistribution/commercial use.

### 6.4 Janes (paid alternative benchmark)
- URL/API landing: https://api.janes.com/
- Access method: paid API subscriptions.
- Format: JSON/API payloads.
- Update frequency: continuous intelligence updates.
- Coverage: military equipment, force structures, defense intelligence.
- Open alternatives when budget-limited: SIPRI + ACLED + UCDP + GTD + OSMINT.

---

## 7) Alliances & Diplomacy Data Sources

### 7.1 ATOP (Alliance Treaty Obligations and Provisions)
- URL: https://www.atopdata.org/
- Access method: free download (CSV/STATA) from project data pages.
- Format: CSV/STATA + codebook + coding sheets.
- Update frequency: versioned releases (ATOP 5.1 through 2018 treaty coverage noted).
- Coverage: military alliance treaty content globally from 1815-2018.
- Use: alliance edges, obligation types, treaty commitment strength.

### 7.2 UN General Assembly Voting Data (UN Dag Hammarskjöld Library)
- URL: https://digitallibrary.un.org/record/4060887
- Access method: downloadable CSV dataset + metadata from UN Digital Library.
- Format: CSV + metadata markdown.
- Update frequency: versioned updates.
- Coverage: recorded votes on adopted GA resolutions from 1946 to latest published session cut-off (currently through Dec 2025 in version 5 listing).
- Scale: ~947,434 vote entries in latest listing.

### 7.3 Correlates of War (COW)
- URL: https://correlatesofwar.org/data-sets/
- Access method: free downloads subject to COW terms.
- Format: dataset-specific tabular files + documentation.
- Update frequency: per dataset/version (e.g., state membership updates in 2025).
- Coverage: interstate war, MIDs, alliances, national material capabilities, diplomatic exchange, trade-related historical IR datasets.

### 7.4 Formal bilateral/multilateral agreements
- UN Treaty Collection (primary legal source): https://treaties.un.org
- Access method: searchable/downloadable treaty texts and statuses; API access is limited/non-uniform publicly.
- Format: web documents, treaty metadata, status tables.
- Use: treaty graph edges (`SIGNED`, `RATIFIED`, `IN_FORCE`), legal obligations metadata.

---

## 8) Data Gap Analysis (What Open Data Cannot Fully Cover)

## 8.1 Parameters hard to source from open data
- Real-time classified military readiness:
  - exact force readiness rates, munitions stockpile levels, maintenance downtime, operational plans.
- Intelligence-grade order of battle details:
  - unit-level deployments, C2 structures, covert capabilities, EW/cyber posture.
- Secret/non-reported economic channels:
  - sanctions evasion networks, illicit finance volumes, black-market commodity flows.
- Leadership intent and crisis doctrine:
  - reliable quantitative indicators for decision-maker risk tolerance/escalation thresholds.
- Non-state actor latent capacities:
  - internal financing, recruitment pipelines, command cohesion.

## 8.2 Requires manual curation / estimation layers
- Actor/entity resolution and alias management (state names, militias, splinters, historical codes).
- Cross-source harmonization rules (ISO/COW/M49 + disputed territories handling).
- Missing-year interpolation nowcasting.
- “Power projection” synthetic indices combining logistics, basing, force quality, doctrine.
- Scenario priors and game-balance variables (morale, political will, clandestine support).

## 8.3 Sources requiring paid access (or strongly constrained free tiers)
- IISS Military Balance (subscription).
- Janes intelligence feeds/API (subscription).
- IEA enterprise API/release automation (customer license), while some datasets remain free.
- UN Comtrade high-throughput premium plans for unlimited batch/bulk at institutional scale.

---

## 9) Recommended Parameter Stack to Exceed 1000 Variables/Entity

Minimum practical mix for >1000 parameters per state entity:
- V-Dem full+others: 500+ indicators + 200+ indices.
- World Bank curated macro/social/infrastructure set: 150-300 indicators.
- WEO + OECD + EIA/IEA/FAO selected panels: 150-300 indicators.
- Governance overlays (Freedom House, CPI, WJP, FSI, Polity): 50-150 indicators.
- Geospatial/topology/infrastructure aggregates from OSM/Natural Earth/USGS: 100-300 engineered features.

Non-state actor feature stack:
- ACLED/UCDP/GTD event-engineered features (tempo, lethality, geography, targeting, alliances/rivalries): 300-1000+ engineered variables per group/time window.

---

## 10) Ingestion Prioritization (Actionable Build Order)

1. Build core country-year fact table: World Bank + WPP + V-Dem.
2. Add macro forecasts: IMF WEO vintages.
3. Add trade dyads: UN Comtrade (start with annual HS2/HS4 aggregates).
4. Add security panel: SIPRI milex + SIPRI transfers.
5. Add event graph: ACLED + UCDP + GTD (actor harmonization pipeline).
6. Add diplomacy graph: ATOP + UNGA voting + COW edges.
7. Add infrastructure geofeatures: Natural Earth + OSM extracts + USGS layers.
8. Add optional paid enrichments: Janes/IISS/IEA enterprise where budget allows.

---

## Source URLs (primary references used)

- World Bank API docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
- IMF WEO databases: https://www.imf.org/en/Publications/SPROLLS/world-economic-outlook-databases
- IMF data portal WEO dataset: https://data.imf.org/en/datasets/IMF.RES:WEO
- OECD API explainer: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html
- UN Comtrade background/pricing/developer:
  - https://comtrade.un.org/labs/data-explorer/About.html
  - https://comtradedeveloper.un.org/
  - https://shop.un.org/lec/node/55
- SIPRI databases:
  - https://www.sipri.org/research/armaments/milex/milex_database
  - https://www.sipri.org/databases/armstransfers
- ACLED API docs:
  - https://acleddata.com/acled-api-documentation
  - https://acleddata.com/api-documentation/elements-acleds-api
- Global Firepower: https://www.globalfirepower.com/
- NTI Index: https://www.ntiindex.org/
- FAS Nuclear Notebook: https://fas.org/publication-term/nuclear-notebook/
- GTD: https://www.start.umd.edu/gtd-download
- Freedom House: https://freedomhouse.org/report/freedom-world
- Transparency CPI: https://www.transparency.org/en/publications/corruption-perceptions-index-2025
- Fragile States Index:
  - https://fragilestatesindex.org/global-data/
  - https://fragilestatesindex.org/methodology/
- V-Dem: https://www.v-dem.net/vdemds.html
- Polity5: https://www.systemicpeace.org/inscrdata.html
- WJP Rule of Law Index reports/data pages:
  - https://worldjusticeproject.org/our-work/publications/rule-law-index-reports/wjp-rule-law-index-2020
  - https://worldjusticeproject.org/news/open-data-day-2026
- UN WPP 2024:
  - https://www.un.org/development/desa/pd/world-population-prospects-2024
  - https://www.un.org/development/desa/pd/content/world-population-prospects-2024-dataset
- Pew datasets:
  - https://www.pewresearch.org/religion-datasets/
  - https://www.pewresearch.org/dataset/dataset-of-global-religious-composition-estimates-for-2010-and-2020/
- CIA Factbook: https://www.cia.gov/the-world-factbook
- Natural Earth: https://www.naturalearthdata.com/downloads/
- OSM ecosystem:
  - https://wiki.openstreetmap.org/wiki/API_v0.6
  - https://planet.openstreetmap.org/
  - https://dev.overpass-api.de/command_line.html
  - https://www.geofabrik.de/geofabrik/openstreetmap.html
  - https://operations.osmfoundation.org/policies/nominatim/
- USGS:
  - https://www.usgs.gov/programs/mineral-resources-program/data
  - https://earthquake.usgs.gov/earthquakes/feed/
- EIA Open Data API: https://www.eia.gov/opendata/documentation.php
- IEA data/docs:
  - https://www.iea.org/data-and-statistics
  - https://www.iea.org/documentation
- FAO/FAOSTAT:
  - https://www.fao.org/faostat/en/#data
  - https://www.fao.org/statistics/databases/en/
  - https://www.fao.org/statistics/data-releases/en
- UCDP: https://ucdp.uu.se/downloads/
- Stanford MMO: https://web.stanford.edu/group/mappingmilitants/cgi-bin/pages/home
- ATOP: https://www.atopdata.org/
- UNGA voting dataset: https://digitallibrary.un.org/record/4060887
- COW datasets: https://correlatesofwar.org/data-sets/

