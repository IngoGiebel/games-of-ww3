#!/usr/bin/env python3
"""Deterministic Task Seeder for GWW3 Pipeline.

Idempotently creates all Task nodes and DEPENDS_ON edges in Neo4j
from a static task definition. Run this INSTEAD of having Dione
manually type CREATE (:Task) queries (hallucination vector).

Usage:
    python -m scripts.seed_tasks                # Seed all phases
    python -m scripts.seed_tasks --phase 1      # Seed only Phase 1
    python -m scripts.seed_tasks --dry-run      # Show what would be created

Design rationale (from Deep Think review #3):
    Asking an LLM to manually type 50+ CREATE (:Task) Cypher queries
    with perfect JSON formatting and dependency DAGs is a hallucination vector.
    One typo and the pipeline deadlocks. Use this deterministic script instead.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [seed] %(message)s")
log = logging.getLogger("seed_tasks")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

# ──────────────────────────────────────────────
# Task Definitions (Static, Deterministic)
# ──────────────────────────────────────────────

TASKS = [
    # ── Phase 0: Infrastructure (already done, mark as completed) ──
    {"id": "task-P0-01-normalization", "phase": 0, "step": "0.1",
     "title": "Implement normalization registry (normalization.py)",
     "assigned_to": "Archon", "priority": 1, "source_id": "internal",
     "method": "code", "status": "completed", "depends_on": []},
    {"id": "task-P0-02-imputation", "phase": 0, "step": "0.2",
     "title": "Implement imputation hierarchy (imputation.py)",
     "assigned_to": "Archon", "priority": 1, "source_id": "internal",
     "method": "code", "status": "completed", "depends_on": []},
    {"id": "task-P0-03-validation", "phase": 0, "step": "0.3",
     "title": "Implement sanity bounds (validation_bounds.py)",
     "assigned_to": "Archon", "priority": 1, "source_id": "internal",
     "method": "code", "status": "completed", "depends_on": []},

    # ── Phase 1: Foundation ──
    {"id": "task-P1-01-nation-registry", "phase": 1, "step": "1.1",
     "title": "Create ~195 Nation nodes from CIA Factbook + ISO 3166",
     "assigned_to": "Sentinel", "priority": 1, "source_id": "cia-factbook",
     "method": "api_import", "depends_on": []},
    {"id": "task-P1-02-id-crosswalk", "phase": 1, "step": "1.2",
     "title": "Build ID crosswalk: ISO-3 ↔ COW ↔ UN M49 ↔ V-Dem ↔ WB",
     "assigned_to": "Sentinel", "priority": 1, "source_id": "cia-factbook",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry"]},
    {"id": "task-P1-03-borders", "phase": 1, "step": "1.3",
     "title": "Create BORDERS relationships for all ~600 land border pairs",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "cia-factbook",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry"]},

    # ── Phase 2: Economics (10-year time series) ──
    {"id": "task-P2-01-wb-gdp", "phase": 2, "step": "2.1a",
     "title": "Import World Bank GDP data (NY.GDP.MKTP.CD) for 195 nations × 10 years",
     "assigned_to": "Sentinel", "priority": 1, "source_id": "worldbank-wdi",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P2-02-wb-demographics", "phase": 2, "step": "2.1b",
     "title": "Import World Bank demographics (population, urbanization, internet) × 10 years",
     "assigned_to": "Sentinel", "priority": 1, "source_id": "worldbank-wdi",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P2-03-wb-macro", "phase": 2, "step": "2.1c",
     "title": "Import World Bank macro (inflation, unemployment, gini, debt, forex) × 10 years",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "worldbank-wdi",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P2-04-comtrade", "phase": 2, "step": "2.2",
     "title": "Import UN Comtrade bilateral trade data (top 500 pairs)",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "un-comtrade",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P2-05-commodities-oil", "phase": 2, "step": "2.3a",
     "title": "Import EIA oil/gas production and consumption data",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "eia-energy",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P2-06-commodities-food", "phase": 2, "step": "2.3b",
     "title": "Import FAO wheat production/consumption data",
     "assigned_to": "Sentinel", "priority": 3, "source_id": "fao-stat",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P2-07-commodities-minerals", "phase": 2, "step": "2.3c",
     "title": "Import USGS rare earth + mineral production data",
     "assigned_to": "Sentinel", "priority": 3, "source_id": "usgs-minerals",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P2-08-cagr", "phase": 2, "step": "2.4",
     "title": "Compute gdp_10yr_cagr from historical GDP time series",
     "assigned_to": "Archon", "priority": 3, "source_id": "worldbank-wdi",
     "method": "derived", "depends_on": ["task-P2-01-wb-gdp"]},

    # ── Phase 3: Military ──
    {"id": "task-P3-01-sipri-milex", "phase": 3, "step": "3.1",
     "title": "Import SIPRI military expenditure data × 10 years",
     "assigned_to": "Sentinel", "priority": 1, "source_id": "sipri-milex",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P3-02-capabilities", "phase": 3, "step": "3.2",
     "title": "Import military capabilities (manpower, equipment) from open sources",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "iiss-milbal",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P3-03-nuclear", "phase": 3, "step": "3.3",
     "title": "Import FAS nuclear warhead counts and status",
     "assigned_to": "Sentinel", "priority": 1, "source_id": "fas-nuclear",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P3-04-arms-transfers", "phase": 3, "step": "3.4",
     "title": "Import SIPRI arms transfers data (2016-2025)",
     "assigned_to": "Sentinel", "priority": 3, "source_id": "sipri-arms",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},

    # ── Phase 4: Governance ──
    {"id": "task-P4-01-vdem", "phase": 4, "step": "4.1",
     "title": "Import V-Dem democracy and governance indices × 10 years",
     "assigned_to": "Sentinel", "priority": 1, "source_id": "vdem",
     "method": "api_import", "depends_on": ["task-P1-02-id-crosswalk"]},
    {"id": "task-P4-02-factions", "phase": 4, "step": "4.2",
     "title": "Derive DomesticFaction nodes from V-Dem + CIA Factbook",
     "assigned_to": "Archon", "priority": 2, "source_id": "vdem",
     "method": "derived", "depends_on": ["task-P4-01-vdem"]},

    # ── Phase 5: Conflict ──
    {"id": "task-P5-01-acled-conflicts", "phase": 5, "step": "5.1",
     "title": "Import ACLED conflict events and create Conflict nodes",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "acled",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk", "task-P1-03-borders"]},
    {"id": "task-P5-02-nsa", "phase": 5, "step": "5.2",
     "title": "Create NonStateActor nodes from ACLED + open sources",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "acled",
     "method": "api_import", "depends_on": ["task-P5-01-acled-conflicts"]},

    # ── Phase 6: Infrastructure ──
    {"id": "task-P6-01-chokepoints", "phase": 6, "step": "6.1",
     "title": "Expand Chokepoint nodes with EIA transit data",
     "assigned_to": "Sentinel", "priority": 3, "source_id": "eia-energy",
     "method": "api_import", "depends_on": ["task-P2-05-commodities-oil"]},
    {"id": "task-P6-02-supply-routes", "phase": 6, "step": "6.2",
     "title": "Derive SUPPLY_ROUTE relationships from trade + geography",
     "assigned_to": "Archon", "priority": 3, "source_id": "un-comtrade",
     "method": "derived", "depends_on": ["task-P2-04-comtrade", "task-P6-01-chokepoints"]},

    # ── Phase 7: Alliances ──
    {"id": "task-P7-01-alliances", "phase": 7, "step": "7.1",
     "title": "Expand Alliance nodes to ~20 organizations with MEMBER_OF edges",
     "assigned_to": "Sentinel", "priority": 2, "source_id": "cia-factbook",
     "method": "api_import", "depends_on": ["task-P1-01-nation-registry", "task-P1-02-id-crosswalk"]},
    {"id": "task-P7-02-bilateral", "phase": 7, "step": "7.2",
     "title": "Derive bilateral DIPLOMATIC_RELATION edges",
     "assigned_to": "Archon", "priority": 3, "source_id": "un-comtrade",
     "method": "derived", "depends_on": ["task-P7-01-alliances", "task-P2-04-comtrade"]},

    # ── Phase 8: Temporal & Validation ──
    {"id": "task-P8-01-historical-ticks", "phase": 8, "step": "8.1",
     "title": "Create historical Tick nodes (T=-120 to T=-1) and STATE_AT edges",
     "assigned_to": "Archon", "priority": 1, "source_id": "internal",
     "method": "derived",
     "depends_on": ["task-P2-01-wb-gdp", "task-P3-01-sipri-milex", "task-P4-01-vdem"]},
    {"id": "task-P8-02-baseline", "phase": 8, "step": "8.2",
     "title": "Create T=0 baseline STATE_AT snapshot for all nations",
     "assigned_to": "Archon", "priority": 1, "source_id": "internal",
     "method": "derived", "depends_on": ["task-P8-01-historical-ticks"]},
    {"id": "task-P8-03-validation", "phase": 8, "step": "8.3",
     "title": "Run full graph validation: topology, completeness, consistency",
     "assigned_to": "Archon", "priority": 1, "source_id": "internal",
     "method": "code", "depends_on": ["task-P8-02-baseline"]},
]


def seed_tasks(driver, phase_filter: int | None = None, dry_run: bool = False):
    """Idempotently create all Task nodes and DEPENDS_ON edges."""
    tasks = TASKS
    if phase_filter is not None:
        tasks = [t for t in tasks if t["phase"] == phase_filter]

    with driver.session() as session:
        for task in tasks:
            deps = task.pop("depends_on", [])
            status = task.pop("status", "pending")

            if dry_run:
                log.info(f"[DRY-RUN] Would create: {task['id']} ({task['title'][:60]}...)")
                continue

            # MERGE = idempotent
            session.run("""
                MERGE (t:Task {id: $id})
                ON CREATE SET t += $props, t.status = $status,
                              t.created_at = datetime(), t.retry_count = 0, t.max_retries = 3
            """, id=task["id"], props=task, status=status)

            # Create dependency edges
            for dep_id in deps:
                session.run("""
                    MATCH (t:Task {id: $task_id})
                    MATCH (dep:Task {id: $dep_id})
                    MERGE (t)-[:DEPENDS_ON]->(dep)
                """, task_id=task["id"], dep_id=dep_id)

            log.info(f"{'CREATED' if status == 'pending' else 'COMPLETED'}: "
                     f"{task['id']} → {len(deps)} deps")

    log.info(f"Seeded {len(tasks)} tasks (dry_run={dry_run})")


def main():
    parser = argparse.ArgumentParser(description="GWW3 Task Seeder")
    parser.add_argument("--phase", type=int, help="Seed only this phase")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    args = parser.parse_args()

    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    seed_tasks(driver, phase_filter=args.phase, dry_run=args.dry_run)
    driver.close()


if __name__ == "__main__":
    main()
