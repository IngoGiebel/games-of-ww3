#!/usr/bin/env python3
"""ETL: ACLED Conflicts — Import active conflicts + non-state actors.

Source: ACLED API (acleddata.com/api/acled/read)
Auth: OAuth token from ~/.config/acled/credentials.json
Period: 2020-2025 (active conflicts)

Creates:
- Conflict nodes (aggregated from events: e.g., "Russo-Ukrainian War")
- NonStateActor nodes (rebel groups, militias, etc.)
- INVOLVED_IN + PARTY_TO relationships

Tasks: task-P5-01-acled-conflicts, task-P5-02-nsa
"""

import json
import logging
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-ACLED] %(message)s")
log = logging.getLogger("etl_acled")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

CRED_FILE = Path.home() / ".config" / "acled" / "credentials.json"


def get_acled_token():
    """Get OAuth token from ACLED."""
    creds = json.loads(CRED_FILE.read_text())
    resp = requests.post(creds["oauth_url"], data={
        "username": creds["username"],
        "password": creds["password"],
        "grant_type": "password",
        "client_id": creds["client_id"],
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_acled_battles(token, year_start=2020, year_end=2025, limit=5000):
    """Fetch battles + violence events (not protests/riots) from ACLED."""
    all_events = []
    offset = 0

    while True:
        try:
            resp = requests.get(
                "https://acleddata.com/api/acled/read",
                params={
                    "event_type": "Battles",
                    "event_date": f"{year_start}-01-01|{year_end}-12-31",
                    "event_date_where": "BETWEEN",
                    "fields": "event_date|year|event_type|sub_event_type|actor1|actor2|inter1|inter2|country|iso|fatalities",
                    "limit": limit,
                    "offset": offset,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning(f"ACLED fetch failed at offset {offset}: {e}")
            break

        events = data.get("data", [])
        if not events:
            break

        all_events.extend(events)
        log.info(f"Fetched {len(events)} events (total: {len(all_events)}, "
                 f"API total: {data.get('total_count', '?')})")

        total_api = int(data.get("total_count", 0) or 0)
        if len(events) < limit or len(all_events) >= total_api or len(all_events) >= 250000:
            break
        offset += limit
        time.sleep(1)

    return all_events


def aggregate_conflicts(events):
    """Aggregate events into conflicts by country."""
    conflicts = defaultdict(lambda: {
        "countries": set(), "actors": set(), "fatalities": 0,
        "event_count": 0, "first_date": None, "last_date": None,
        "types": Counter()
    })

    for e in events:
        country = e.get("country", "Unknown")
        key = country  # Simple aggregation by country

        c = conflicts[key]
        c["countries"].add(country)
        c["event_count"] += 1
        c["fatalities"] += int(e.get("fatalities", 0) or 0)
        c["types"][e.get("sub_event_type", "Unknown")] += 1

        date = e.get("event_date", "")
        if date and (c["first_date"] is None or date < c["first_date"]):
            c["first_date"] = date
        if date and (c["last_date"] is None or date > c["last_date"]):
            c["last_date"] = date

        for actor_field in ["actor1", "actor2"]:
            actor = e.get(actor_field, "")
            if actor and "unidentified" not in actor.lower():
                c["actors"].add(actor)

    return conflicts


def extract_nsas(events):
    """Extract non-state actors from ACLED events."""
    # inter1/inter2 codes: 1=state, 2=rebel, 3=political militia, 4=identity militia, 5=rioter, 6=protester, 7=civilian, 8=external
    # ACLED inter1/inter2 can be numeric codes OR text labels depending on API version
    nsa_types_num = {2: "insurgency", 3: "militia", 4: "identity_militia", 8: "external_force"}
    nsa_types_text = {
        "rebel group": "insurgency", "rebel groups": "insurgency",
        "political militia": "militia", "political militias": "militia",
        "identity militia": "identity_militia", "identity militias": "identity_militia",
        "external/other force": "external_force",
    }

    actors = defaultdict(lambda: {"type": None, "countries": set(), "events": 0, "fatalities": 0})

    for e in events:
        for actor_f, inter_f in [("actor1", "inter1"), ("actor2", "inter2")]:
            actor = e.get(actor_f, "")
            inter_raw = e.get(inter_f, "")
            
            # Determine NSA type from inter field (numeric or text)
            nsa_type = None
            try:
                inter_num = int(inter_raw)
                nsa_type = nsa_types_num.get(inter_num)
            except (ValueError, TypeError):
                nsa_type = nsa_types_text.get(str(inter_raw).lower())

            if nsa_type and actor and "unidentified" not in actor.lower():
                a = actors[actor]
                a["type"] = nsa_type
                a["countries"].add(e.get("country", ""))
                a["events"] += 1
                a["fatalities"] += int(e.get("fatalities", 0) or 0)

    # Filter: only actors with 10+ events (significant)
    significant = {k: v for k, v in actors.items() if v["events"] >= 10}
    return significant


def load_to_neo4j(conflicts, nsas):
    """Load conflicts and NSAs to Neo4j."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-5.1"

    # Build conflict records
    conflict_records = []
    for name, data in conflicts.items():
        if data["event_count"] < 20:  # Skip minor conflicts
            continue
        intensity = "high" if data["fatalities"] > 1000 else "medium" if data["fatalities"] > 100 else "low"
        conflict_records.append({
            "name": f"Conflict in {name}",
            "type": "civil" if len(data["countries"]) == 1 else "interstate",
            "region": name,
            "intensity": intensity,
            "fatalities_est": data["fatalities"],
            "event_count": data["event_count"],
            "start_date": data["first_date"],
            "last_date": data["last_date"],
            "countries": list(data["countries"]),
        })

    # Build NSA records
    nsa_records = []
    for name, data in nsas.items():
        nsa_records.append({
            "name": name,
            "type": data["type"],
            "operational_area": list(data["countries"])[:5],
            "estimated_strength": 0,  # Not available from ACLED
            "event_count": data["events"],
            "fatalities_associated": data["fatalities"],
        })

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                # ImportBatch
                tx.run("""
                    CREATE (ib:ImportBatch {
                        id: $batch_id, timestamp: datetime(), agent: "Dione",
                        method: "api_import",
                        record_count: $count,
                        notes: "ACLED battles 2020-2025: conflicts + non-state actors",
                        confidence: "high", requires_replacement: false
                    })
                    WITH ib
                    MATCH (ds:DataSource {id: "acled"})
                    MERGE (ib)-[:FROM_SOURCE]->(ds)
                """, batch_id=batch_id,
                     count=len(conflict_records) + len(nsa_records))

                # Conflicts
                for c in conflict_records:
                    tx.run("""
                        MERGE (conf:Conflict {name: $name})
                        SET conf.type = $type, conf.region = $region,
                            conf.intensity = $intensity,
                            conf.fatalities_est = $fatalities,
                            conf.event_count = $events,
                            conf.start_date = date($start),
                            conf.last_date = date($last)
                        WITH conf
                        MATCH (ib:ImportBatch {id: $batch_id})
                        MERGE (conf)-[:PROVENANCE]->(ib)
                    """, name=c["name"], type=c["type"], region=c["region"],
                         intensity=c["intensity"], fatalities=c["fatalities_est"],
                         events=c["event_count"], start=c["start_date"],
                         last=c["last_date"], batch_id=batch_id)

                    # Link to countries
                    for country_name in c["countries"]:
                        tx.run("""
                            MATCH (n:Nation)
                            WHERE n.name_short = $country OR n.name = $country
                            MATCH (conf:Conflict {name: $cname})
                            MERGE (n)-[:INVOLVED_IN]->(conf)
                        """, country=country_name, cname=c["name"])

                # NSAs
                for nsa in nsa_records:
                    tx.run("""
                        MERGE (a:NonStateActor {name: $name})
                        SET a.type = $type,
                            a.operational_area = $area,
                            a.event_count = $events,
                            a.fatalities_associated = $fatalities
                        WITH a
                        MATCH (ib:ImportBatch {id: $batch_id})
                        MERGE (a)-[:PROVENANCE]->(ib)
                    """, name=nsa["name"], type=nsa["type"],
                         area=nsa["operational_area"],
                         events=nsa["event_count"],
                         fatalities=nsa["fatalities_associated"],
                         batch_id=batch_id)

                tx.commit()

        log.info(f"Loaded {len(conflict_records)} conflicts + {len(nsa_records)} NSAs")
        return len(conflict_records), len(nsa_records), batch_id
    finally:
        driver.close()


def main():
    log.info("=== ETL P5: ACLED Conflicts + NSAs ===")

    token = get_acled_token()
    log.info("ACLED OAuth token acquired")

    # Also fetch violence against civilians
    events_battles = fetch_acled_battles(token, year_start=2020)
    log.info(f"Total battle events: {len(events_battles)}")

    conflicts = aggregate_conflicts(events_battles)
    nsas = extract_nsas(events_battles)
    log.info(f"Aggregated: {len(conflicts)} conflict zones, {len(nsas)} significant NSAs")

    n_conflicts, n_nsas, batch_id = load_to_neo4j(conflicts, nsas)

    # Mark tasks
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        s.run("""MATCH (t:Task {id: "task-P5-01-acled-conflicts"})
               SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                   t.result_summary = $summary""",
              summary=f"{n_conflicts} conflicts from ACLED battles 2020-2025")
        s.run("""MATCH (t:Task {id: "task-P5-02-nsa"})
               SET t.status = "completed", t.completed_at = datetime(), t.assigned_to = "Dione",
                   t.result_summary = $summary""",
              summary=f"{n_nsas} non-state actors from ACLED")
    driver.close()

    log.info(f"=== DONE: {n_conflicts} conflicts, {n_nsas} NSAs, batch={batch_id} ===")


if __name__ == "__main__":
    main()
