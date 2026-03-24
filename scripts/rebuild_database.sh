#!/usr/bin/env bash
# GWW3 — Rebuild the entire Neo4j database from scratch.
# 
# Usage:
#   NEO4J_PASSWORD='your-password' ./scripts/rebuild_database.sh
#   NEO4J_PASSWORD='your-password' ./scripts/rebuild_database.sh --phase 1  # Only Phase 1
#
# All scripts are idempotent (MERGE-based). Safe to rerun.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

: "${NEO4J_PASSWORD:?NEO4J_PASSWORD must be set}"
export NEO4J_PASSWORD

phase="${1:-all}"

log() { echo "$(date +%H:%M:%S) [rebuild] $*"; }

run_etl() {
    local script="$1"
    local desc="$2"
    log "▶ $desc"
    python "$script" 2>&1 | tail -3
    log "✓ $desc done"
    echo ""
}

# ── Phase 0: Task Queue + DataSources ──
if [[ "$phase" == "all" || "$phase" == "0" ]]; then
    log "═══ Phase 0: Seeding tasks + schema ═══"
    PYTHONPATH=src python -m scripts.seed_tasks
fi

# ── Phase 1: Foundation ──
if [[ "$phase" == "all" || "$phase" == "1" ]]; then
    log "═══ Phase 1: Foundation (Nations + Geography) ═══"
    run_etl "src/scripts/etl_nation_registry.py"  "P1-01: Nation Registry (195 nations)"
    run_etl "src/scripts/etl_id_crosswalk.py"     "P1-02: ID Crosswalk (COW/V-Dem/UN)"
    run_etl "src/scripts/etl_borders.py"          "P1-03: Borders (~624 edges)"
fi

# ── Phase 2: Economics ──
if [[ "$phase" == "all" || "$phase" == "2" ]]; then
    log "═══ Phase 2: Economics ═══"
    [[ -f src/scripts/etl_worldbank_gdp.py ]] && run_etl "src/scripts/etl_worldbank_gdp.py" "P2-01: World Bank GDP" || log "⏭ P2-01: not yet implemented"
    [[ -f src/scripts/etl_worldbank_demographics.py ]] && run_etl "src/scripts/etl_worldbank_demographics.py" "P2-02: Demographics" || log "⏭ P2-02: not yet implemented"
    [[ -f src/scripts/etl_worldbank_macro.py ]] && run_etl "src/scripts/etl_worldbank_macro.py" "P2-03: Macro" || log "⏭ P2-03: not yet implemented"
fi

# ── Phase 3: Military ──
if [[ "$phase" == "all" || "$phase" == "3" ]]; then
    log "═══ Phase 3: Military ═══"
    [[ -f src/scripts/etl_sipri_milex.py ]] && run_etl "src/scripts/etl_sipri_milex.py" "P3-01: SIPRI MILEX" || log "⏭ P3-01: not yet implemented"
fi

# Add more phases as ETL scripts are developed...

log "═══ Pipeline complete ═══"

# Summary
python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', '$NEO4J_PASSWORD'))
with d.session() as s:
    for r in s.run('MATCH (n) RETURN labels(n)[0] AS type, count(n) AS cnt ORDER BY cnt DESC'):
        print(f\"  {r['type']:20s} {r['cnt']:>6d}\")
    edges = s.run('MATCH ()-[r]->() RETURN count(r) AS cnt').single()['cnt']
    print(f\"  {'TOTAL EDGES':20s} {edges:>6d}\")
d.close()
"
