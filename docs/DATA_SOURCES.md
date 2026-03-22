# Data Sources

## Overview

GWW3 seeds its initial game state from real-world data. This document catalogs all data sources, what we extract from each, and how they map to game mechanics.

## Primary Sources

### 1. World Bank Open Data
- **URL:** https://data.worldbank.org/
- **API:** https://api.worldbank.org/v2/
- **Format:** JSON/XML REST API, CSV downloads
- **License:** Creative Commons Attribution 4.0 (CC BY 4.0)
- **Data extracted:**
  - GDP (current USD) — `NY.GDP.MKTP.CD`
  - GDP growth rate — `NY.GDP.MKTP.KD.ZG`
  - GDP per capita — `NY.GDP.PCAP.CD`
  - Government debt (% of GDP) — `GC.DOD.TOTL.GD.ZS`
  - Trade (% of GDP) — `NE.TRD.GNFS.ZS`
  - Population — `SP.POP.TOTL`
  - Inflation (consumer prices) — `FP.CPI.TOTL.ZG`
  - Unemployment rate — `SL.UEM.TOTL.ZS`
  - Foreign direct investment — `BX.KLT.DINV.CD.WD`
  - R&D expenditure (% of GDP) — `GB.XPD.RSDV.GD.ZS`
- **Game mapping:** Seeds `Economy` model — GDP, growth, debt, trade openness

### 2. SIPRI (Stockholm International Peace Research Institute)
- **URL:** https://www.sipri.org/databases
- **Format:** Excel downloads, some API access
- **License:** Free for non-commercial use with attribution
- **Databases:**
  - **Military Expenditure Database** — Annual spending by country (1949–present)
  - **Arms Transfers Database** — International arms trade flows
  - **SIPRI Yearbook** — Nuclear forces data
- **Data extracted:**
  - Military expenditure (USD, constant prices)
  - Military expenditure (% of GDP)
  - Arms imports/exports by country pair
  - Nuclear warhead counts (strategic, nonstrategic, deployed, stockpiled)
- **Game mapping:** Seeds `Military` model — spending, arms trade relationships, nuclear arsenal

### 3. Global Firepower Index
- **URL:** https://www.globalfirepower.com/
- **Format:** Web scraping (no official API)
- **License:** Fair use / public data
- **Data extracted:**
  - Overall military strength ranking
  - Active military personnel
  - Reserve military personnel
  - Total aircraft (fighters, attack, transport, helicopters)
  - Naval vessels (aircraft carriers, submarines, destroyers, frigates)
  - Armored vehicles (tanks, AFVs, artillery)
  - Defense budget
  - Logistics capability (airports, ports, road/rail network)
- **Game mapping:** Seeds `Military` model — unit counts, force composition, logistics capacity

### 4. CIA World Factbook
- **URL:** https://www.cia.gov/the-world-factbook/
- **Format:** JSON via GitHub mirror (factbook/factbook.json)
- **License:** Public domain (US Government work)
- **Data extracted:**
  - Natural resources by country
  - Land area and borders
  - Coastline length
  - Energy production/consumption
  - Import/export commodities
  - Ethnic groups and languages (for stability modeling)
  - Government type
- **Game mapping:** Seeds `Country` base model — geography, resources, demographics

### 5. UN COMTRADE (International Trade Statistics)
- **URL:** https://comtradeplus.un.org/
- **API:** https://comtrade.un.org/data/dev/portal
- **Format:** JSON/CSV REST API
- **License:** Free for non-commercial use
- **Data extracted:**
  - Bilateral trade flows (import/export by country pair)
  - Trade by commodity (HS codes)
  - Top trading partners per country
  - Trade balance
- **Game mapping:** Seeds Neo4j `TRADES_WITH` relationships, trade dependency graph

### 6. Federation of American Scientists (FAS) — Nuclear Weapons Data
- **URL:** https://fas.org/issues/nuclear-weapons/
- **Format:** Reports, infographics, structured data in publications
- **License:** Fair use
- **Data extracted:**
  - Nuclear warhead inventories by country
  - Delivery systems (ICBMs, SLBMs, strategic bombers)
  - Nuclear doctrine (first use, no first use, etc.)
  - Missile range and accuracy estimates
- **Game mapping:** Seeds `NuclearCapability` — warhead counts, delivery systems, doctrine

### 7. Alliance & Treaty Databases

#### NATO
- **URL:** https://www.nato.int/cps/en/natohq/topics_52044.htm
- Member states, Article 5 obligations, defense spending commitments

#### CSTO (Collective Security Treaty Organization)
- **URL:** https://en.odkb-csto.org/
- Member states, mutual defense obligations

#### Other Alliances
- **AUKUS** — Australia, UK, USA
- **Quad** — USA, Japan, India, Australia
- **SCO** (Shanghai Cooperation Organisation) — China, Russia, India, Pakistan, + observers
- **Five Eyes** — Intelligence sharing: USA, UK, Canada, Australia, New Zealand
- **EU Common Security and Defence Policy**
- **Arab League / GCC** — Gulf Cooperation Council

**Game mapping:** Seeds Neo4j `ALLIED_TO` relationships with alliance type and strength

## Secondary Sources

### 8. Natural Resource Databases

#### USGS Mineral Commodity Summaries
- **URL:** https://www.usgs.gov/centers/national-minerals-information-center
- Rare earth production, critical mineral reserves

#### BP Statistical Review of World Energy
- **URL:** https://www.bp.com/en/global/corporate/energy-economics/statistical-review-of-world-energy.html
- Oil/gas production, reserves, consumption, renewable capacity

#### OPEC Annual Statistical Bulletin
- **URL:** https://asb.opec.org/
- Oil production quotas, proven reserves

**Game mapping:** Seeds `Resource` nodes — type, quantity, strategic value

### 9. Transparency International — Corruption Perceptions Index
- **URL:** https://www.transparency.org/cpi
- **Game mapping:** Government effectiveness modifier (affects economic growth, military morale)

### 10. Institute for Economics and Peace — Global Peace Index
- **URL:** https://www.visionofhumanity.org/maps/
- **Game mapping:** Initial stability score, domestic unrest probability

### 11. Credit Rating Agencies
- S&P, Moody's, Fitch sovereign ratings
- **Game mapping:** Borrowing costs, debt sustainability

## Data Pipeline

```
Raw Sources → Downloaders → Normalizers → Validators → Game-Ready JSON
                  │              │             │              │
            httpx/pandas    pandas/numpy   pytest        data/countries/
```

### Pipeline Steps

1. **Download** — Fetch from APIs or scrape from web (cached locally)
2. **Normalize** — Convert to common units (USD for money, standardized country codes ISO 3166-1 alpha-3)
3. **Validate** — Cross-reference between sources, flag outliers
4. **Transform** — Map to game model attributes with appropriate scaling
5. **Export** — Write to `data/countries/{ISO3}.json`

### Country Code Standard

All country references use **ISO 3166-1 alpha-3** codes:
- USA → United States
- CHN → China
- RUS → Russia
- DEU → Germany
- IND → India
- GBR → United Kingdom
- FRA → France
- JPN → Japan
- etc.

## Data Freshness

- **Target:** Most recent complete year available (currently 2024/2025 data)
- **Update frequency:** Annually, when major sources publish new data
- **Fallback:** If a specific indicator is unavailable for the latest year, use the most recent available with a staleness flag

## Scaling & Game Balance

Raw real-world data creates extreme asymmetries (US GDP is ~60× Russia's). While this is *realistic*, some scaling is needed for gameplay:

- **GDP** — Used as-is (asymmetry is a feature, not a bug)
- **Military strength** — Normalized to a composite score (0–1000) for combat resolution
- **Nuclear weapons** — Binary threshold: having >100 deployed warheads = second-strike capability
- **Technology** — Derived from R&D spending, semiconductor access, patent data; normalized 0–100
- **Diplomatic capital** — Derived from soft power indices, UN voting record, alliance count

The goal: **realistic starting positions, playable mechanics.**
