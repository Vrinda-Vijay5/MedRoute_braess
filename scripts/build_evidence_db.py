#!/usr/bin/env python3
"""Build a queryable SQLite index over one immutable MedRoute evidence run."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE run_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE artifacts (path TEXT PRIMARY KEY, bytes INTEGER NOT NULL, sha256 TEXT NOT NULL);
CREATE TABLE route_decisions (
  repetition INTEGER, verdict TEXT, selected_route TEXT, prevention_verified INTEGER,
  baseline_cost REAL, shortcut_cost REAL, prevention_cost REAL
);
CREATE TABLE scenario_measurements (
  scenario TEXT, repetition INTEGER, traffic_class TEXT, latency_ms REAL,
  jitter_ms REAL, packet_loss_pct REAL, throughput_mbps REAL, complete INTEGER
);
CREATE TABLE resilience (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE profile_matrix (
  profile TEXT PRIMARY KEY, selected_class TEXT, expected_queue_id INTEGER,
  complete INTEGER, latency_ms REAL, jitter_ms REAL,
  packet_loss_pct REAL, throughput_mbps REAL, flow_verified INTEGER
);
"""


def flatten_value(value):
    return json.dumps(value, sort_keys=True) if not isinstance(value, str) else value


def build(directory):
    directory = Path(directory).resolve()
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    results = json.loads((directory / "scenario_results.json").read_text(encoding="utf-8"))
    target = directory / "evidence.sqlite"
    if target.exists():
        target.unlink()
    with sqlite3.connect(target) as db:
        db.executescript(SCHEMA)
        for key, value in summary.items():
            db.execute("INSERT INTO run_metadata VALUES (?, ?)", (key, flatten_value(value)))
        for path in sorted(directory.iterdir()):
            if path == target or not path.is_file():
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            db.execute("INSERT INTO artifacts VALUES (?, ?, ?)",
                       (path.name, path.stat().st_size, digest))
        for row in results.get("braess_shortcut_repetitions", []):
            decision = row.get("decision", {})
            metrics = decision.get("metrics_used", {})
            db.execute("INSERT INTO route_decisions VALUES (?, ?, ?, ?, ?, ?, ?)", (
                row.get("repetition"), decision.get("verdict"),
                decision.get("selected_route"), int(bool(decision.get("prevention_verified"))),
                (metrics.get("baseline") or {}).get("cost"),
                (metrics.get("shortcut") or {}).get("cost"),
                (decision.get("prevention_metrics") or {}).get("cost")))
        for scenario, rows in results.get("scenarios", {}).items():
            for row in rows:
                for traffic_class, item in row.get("per_class_metrics", {}).items():
                    metrics = item.get("metrics") or {}
                    db.execute("INSERT INTO scenario_measurements VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                        scenario, row.get("repetition"), traffic_class,
                        metrics.get("latency_ms"), metrics.get("jitter_ms"),
                        metrics.get("packet_loss_pct"), item.get("throughput_mbps"),
                        int(bool(item.get("complete")))))
        recovery = summary.get("failure_recovery")
        if recovery is not None:
            for key, value in recovery.items():
                db.execute("INSERT INTO resilience VALUES (?, ?)", (key, flatten_value(value)))
        profile_path = directory / "profile_matrix.json"
        if profile_path.exists():
            profile_matrix = json.loads(profile_path.read_text(encoding="utf-8"))
            for row in profile_matrix.get("profiles", []):
                metrics = row.get("metrics") or {}
                flow = row.get("flow_evidence") or {}
                db.execute("INSERT INTO profile_matrix VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    row.get("profile"), row.get("selected_class"),
                    row.get("expected_queue_id"), int(bool(row.get("complete"))),
                    metrics.get("latency_ms"), metrics.get("jitter_ms"),
                    metrics.get("packet_loss_pct"), metrics.get("throughput_mbps"),
                    int(bool(flow.get("verified")))))
        db.commit()
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    print(build(args.evidence_dir))
