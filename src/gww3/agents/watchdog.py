#!/usr/bin/env python3
"""GWW3 Task Watchdog — Deterministic Process Supervisor.

NOT an LLM agent. A plain Python daemon that:
1. Requeues zombie tasks (IN_PROGRESS for >60 minutes with no progress)
2. Alerts via a status file that Dione reads during heartbeats
3. Runs on a cron job or as a systemd timer (every 5 minutes)

Design rationale (from Deep Think review):
  Process supervision must be handled by the Operating System, not an LLM.
  Dione should focus on strategic phase reviews and human escalation,
  not mechanical monitoring and ps aux | grep.

Usage:
  python -m gww3.agents.watchdog              # One-shot check
  python -m gww3.agents.watchdog --daemon      # Run every 5 minutes
  python -m gww3.agents.watchdog --dry-run     # Show what would change

Cron setup:
  */5 * * * * cd /home/uranus/moltbot-workspace/projects/games-of-ww3 && python -m gww3.agents.watchdog >> logs/watchdog.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [watchdog] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("watchdog")

# ── Configuration ──

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

ZOMBIE_THRESHOLD_MINUTES = 60       # Task stuck IN_PROGRESS for this long = zombie
MAX_AUTO_REQUEUE = 3                # Auto-requeue up to this many retries, then block
STATUS_FILE = Path("logs/watchdog-status.json")
ALERT_FILE = Path("logs/watchdog-alerts.json")


def get_driver():
    """Create Neo4j driver."""
    from neo4j import GraphDatabase
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def check_zombie_tasks(driver, dry_run: bool = False) -> list[dict]:
    """Find and requeue tasks that have been IN_PROGRESS too long.

    Returns list of actions taken.
    """
    threshold = datetime.now(timezone.utc) - timedelta(minutes=ZOMBIE_THRESHOLD_MINUTES)
    actions = []

    with driver.session() as session:
        # Find zombie tasks
        result = session.run("""
            MATCH (t:Task {status: "in_progress"})
            WHERE t.started_at < $threshold
            RETURN t.id AS id, t.title AS title, t.assigned_to AS agent,
                   t.started_at AS started, t.retry_count AS retries,
                   t.max_retries AS max_retries
        """, threshold=threshold)

        for record in result:
            task_id = record["id"]
            retries = record["retries"] or 0
            max_retries = record["max_retries"] or 3

            if retries >= max_retries:
                action = "blocked"
                if not dry_run:
                    session.run("""
                        MATCH (t:Task {id: $id})
                        SET t.status = "blocked",
                            t.error_log = "Watchdog: zombie task exceeded max retries after " +
                                          toString($retries) + " attempts"
                    """, id=task_id, retries=retries)
            else:
                action = "requeued"
                if not dry_run:
                    # Check for partial ImportBatch and rollback
                    session.run("""
                        MATCH (t:Task {id: $id})
                        OPTIONAL MATCH (ib:ImportBatch)
                        WHERE ib.id STARTS WITH 'import-' AND ib.id ENDS WITH t.step
                              AND ib.timestamp > t.started_at
                        // Rollback partial writes
                        OPTIONAL MATCH (entity)-[p:PROVENANCE]->(ib)
                        DELETE p
                        WITH t, ib
                        DETACH DELETE ib
                        SET t.status = "pending",
                            t.retry_count = t.retry_count + 1,
                            t.started_at = null,
                            t.error_log = coalesce(t.error_log, '') +
                                          '\\nWatchdog requeue at ' + toString(datetime())
                    """, id=task_id)

            entry = {
                "task_id": task_id,
                "title": record["title"],
                "agent": record["agent"],
                "started": str(record["started"]),
                "retries": retries,
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            actions.append(entry)
            log.info(f"{action.upper()}: {task_id} ({record['title']}) "
                     f"assigned to {record['agent']}, stuck since {record['started']}")

    return actions


def get_pipeline_status(driver) -> dict:
    """Get overall pipeline status for Dione to read."""
    with driver.session() as session:
        result = session.run("""
            MATCH (t:Task)
            WITH t.status AS status, count(t) AS cnt
            RETURN status, cnt ORDER BY cnt DESC
        """)
        status_counts = {r["status"]: r["cnt"] for r in result}

        # Check for blocked tasks
        blocked = session.run("""
            MATCH (t:Task {status: "blocked"})
            RETURN t.id AS id, t.title AS title, t.error_log AS error
        """)
        blocked_tasks = [dict(r) for r in blocked]

        # Phase completion
        phases = session.run("""
            MATCH (t:Task)
            WITH t.phase AS phase,
                 count(t) AS total,
                 sum(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) AS completed
            RETURN phase, total, completed,
                   CASE WHEN total = completed THEN true ELSE false END AS phase_complete
            ORDER BY phase
        """)
        phase_status = [dict(r) for r in phases]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_counts": status_counts,
        "blocked_tasks": blocked_tasks,
        "phases": phase_status,
        "healthy": len(blocked_tasks) == 0,
    }


def write_status(status: dict, alerts: list[dict]):
    """Write status files for Dione to consume."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    STATUS_FILE.write_text(json.dumps(status, indent=2, default=str))

    if alerts:
        existing = []
        if ALERT_FILE.exists():
            try:
                existing = json.loads(ALERT_FILE.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                existing = []
        existing.extend(alerts)
        # Keep last 100 alerts
        ALERT_FILE.write_text(json.dumps(existing[-100:], indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="GWW3 Task Watchdog")
    parser.add_argument("--daemon", action="store_true", help="Run every 5 minutes")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument("--interval", type=int, default=300, help="Daemon interval (seconds)")
    args = parser.parse_args()

    while True:
        try:
            driver = get_driver()
            alerts = check_zombie_tasks(driver, dry_run=args.dry_run)
            status = get_pipeline_status(driver)
            write_status(status, alerts)

            if alerts:
                log.warning(f"Processed {len(alerts)} zombie task(s)")
            else:
                log.info(f"OK — {status['task_counts']}")

            driver.close()
        except Exception as e:
            log.error(f"Watchdog error: {e}")

        if not args.daemon:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
