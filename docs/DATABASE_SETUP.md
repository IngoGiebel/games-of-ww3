# GWW3 — Database Setup & Reproduction Guide

*How to build the GWW3 Neo4j database from scratch.*

## Prerequisites

- **Neo4j 5.x** with APOC plugin
- **Python 3.12+** with packages: `neo4j`, `requests`, `pandas`, `filelock`
- Internet access (for REST Countries API, World Bank API, etc.)

## Quick Start (3 commands)

```bash
# 1. Install Python dependencies
cd /path/to/games-of-ww3
pip install -e .

# 2. Initialize schema (constraints + indexes)
PYTHONPATH=src python -c "
import asyncio
from neo4j import AsyncGraphDatabase
from gww3.db.schema import initialize_schema
async def main():
    driver = AsyncGraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'YOUR_PASSWORD'))
    applied = await initialize_schema(driver)
    print(f'Applied {len(applied)} constraints/indexes')
    await driver.close()
asyncio.run(main())
"

# 3. Run the full data pipeline
./scripts/rebuild_database.sh
```

## Step-by-Step (Manual)

### Step 0: Neo4j Setup

```bash
# Ubuntu/Debian
sudo apt install neo4j
sudo systemctl start neo4j

# Set password (first time)
cypher-shell -u neo4j -p neo4j
# > ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'your-password';

# Verify APOC is installed
cypher-shell -u neo4j -p 'your-password' "RETURN apoc.version()"
```

### Step 1: Seed Task Queue + DataSources

```bash
# Create all Task nodes and DataSource nodes
NEO4J_PASSWORD='your-password' PYTHONPATH=src python -m scripts.seed_tasks
```

### Step 2: Phase 1 — Foundation (Nations + Geography)

```bash
# P1-01: Load 195 sovereign nations
NEO4J_PASSWORD='your-password' python src/scripts/etl_nation_registry.py

# P1-02: Build ID crosswalk (COW, V-Dem, UN M49)
NEO4J_PASSWORD='your-password' python src/scripts/etl_id_crosswalk.py

# P1-03: Create border relationships
NEO4J_PASSWORD='your-password' python src/scripts/etl_borders.py
```

### Step 3: Phase 2 — Economics (coming soon)

```bash
# P2-01: World Bank GDP data (10 years)
NEO4J_PASSWORD='your-password' python src/scripts/etl_worldbank_gdp.py

# ... more ETL scripts as they are developed
```

## Pipeline Architecture

```
seed_tasks.py          → Task nodes + DataSource nodes in Neo4j
etl_nation_registry.py → 195 Nation nodes (REST Countries API)
etl_id_crosswalk.py    → COW/V-Dem/UN M49 codes on Nation nodes
etl_borders.py         → BORDERS relationships (~624 edges)
etl_worldbank_*.py     → Economic data (World Bank API)
etl_sipri_*.py         → Military data (SIPRI downloads)
etl_vdem.py            → Governance data (V-Dem dataset)
etl_acled.py           → Conflict data (ACLED API)
```

Each script:
- Is **idempotent** (uses MERGE, safe to rerun)
- Creates an **ImportBatch** node with provenance metadata
- Links all affected entities via **PROVENANCE** edges
- Runs all writes in a **single atomic transaction**
- Can be run independently (respects dependency order)

## Verifying the Database

```cypher
-- Node counts
MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count ORDER BY count DESC

-- Schema visualization (in Neo4j Browser)
CALL db.schema.visualization()

-- Data quality check
MATCH (n:Nation) WHERE n.region IS NULL RETURN n.iso3, n.name_short

-- Border sanity check (Germany should have 9 neighbors)
MATCH (de:Nation {iso3: "DEU"})-[:BORDERS]->(n) RETURN n.name_short ORDER BY n.name_short

-- Provenance trail
MATCH (n:Nation {iso3: "DEU"})-[p:PROVENANCE]->(ib:ImportBatch)-[:FROM_SOURCE]->(ds:DataSource)
RETURN ds.name AS source, ib.agent AS agent, p.properties AS properties, ib.timestamp AS when
```

## Resetting the Database

```bash
# WARNING: Deletes everything!
cypher-shell -u neo4j -p 'your-password' "MATCH (n) DETACH DELETE n"

# Then rerun from Step 1
```

## Data Sources & Licensing

| Source | URL | License | Used For |
|--------|-----|---------|----------|
| REST Countries | restcountries.com | MPL 2.0 | Nation identity, borders |
| World Bank WDI | data.worldbank.org | CC-BY 4.0 | GDP, population, economics |
| SIPRI | sipri.org | Open | Military spending, arms |
| V-Dem | v-dem.net | CC-BY-SA 4.0 | Democracy, governance |
| ACLED | acleddata.com | Open (registration) | Conflicts, NSAs |
| EIA | eia.gov | Public domain | Energy, oil, gas |
| FAO | fao.org | CC-BY 3.0 IGO | Agriculture, food |
| USGS | usgs.gov | Public domain | Minerals, rare earths |
| FAS | fas.org | Open | Nuclear weapons |
| CIA Factbook | cia.gov | Public domain | Geography, government |
