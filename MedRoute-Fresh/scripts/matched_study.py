"""Run a matched M1--M4/ablation study through the existing live runner.

Each condition receives the same seed and topology profile.  This is an
orchestrator only: it records unavailable/failed runs and never synthesizes a
result when Mininet, OVS, or Ryu are absent.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("M1", "M2", "M3", "M4")
ABLATIONS = ("disable_braess_detection", "disable_priority_handling", "disable_link_change_evaluation")
TOPOLOGY_PROFILE_PARAMETERS = {
    "balanced_diamond": {"primary_bw_mbps": 100, "alternate_bw_mbps": 100,
                          "primary_delay": "1ms", "alternate_delay": "1ms"},
    "asymmetric_diamond": {"primary_bw_mbps": 100, "alternate_bw_mbps": 40,
                            "primary_delay": "2ms", "alternate_delay": "5ms"},
    "low_capacity_diamond": {"primary_bw_mbps": 25, "alternate_bw_mbps": 25,
                              "primary_delay": "3ms", "alternate_delay": "3ms"},
}


def study_plan(seeds, include_ablations=True):
    plan = []
    for seed in seeds:
        for method in METHODS:
            plan.append({"method": method, "seed": seed, "ablation": None})
        if include_ablations:
            plan.extend({"method": "M4", "seed": seed, "ablation": name} for name in ABLATIONS)
    return plan


def summarize(run_directory):
    try:
        summary = json.loads((run_directory / "summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "unavailable", "reason": str(exc)}
    # Preserve raw summaries; this compact index makes only explicit evidence
    # comparable and leaves missing metrics as null.
    config = {}
    try:
        config = json.loads((run_directory / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {"status": "complete" if summary.get("scenario_validation_passed") else "incomplete",
            "live_experiment": summary.get("live_experiment"),
            "selected_route": summary.get("selected_route"),
            "shortcut_verdict": summary.get("shortcut_verdict"),
            "scenario_statistics_file": summary.get("scenario_statistics_file"),
            "all_flow_rules_verified": summary.get("all_flow_rules_verified"),
            "all_telemetry_complete": summary.get("all_telemetry_complete"),
            "topology_profile": config.get("topology_profile"),
            "topology_profile_parameters": config.get("topology_profile_parameters"),
            "method": (config.get("selected_method") or {}).get("method_id"),
            "evidence_files": sorted(path.name for path in run_directory.iterdir())
            if run_directory.exists() else []}


def _metric(stats, name):
    value = stats.get(name) if isinstance(stats, dict) else None
    if not isinstance(value, dict) or value.get("complete") is not True:
        return {"value": None, "standard_deviation": None, "n": value.get("n") if isinstance(value, dict) else None,
                "available": False}
    return {"value": value.get("mean"), "standard_deviation": value.get("standard_deviation"),
            "n": value.get("n"), "available": value.get("mean") is not None}


def _scenario_rows(run_directory, condition):
    try:
        results = json.loads((run_directory / "scenario_results.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = []
    for scenario, stats in (results.get("statistics_from_saved_measurements") or {}).items():
        classes = stats.get("classes") or {}
        critical = classes.get("ECG") or classes.get("ICU") or {}
        background = classes.get("BACKGROUND") or {}
        fairness = stats.get("throughput_fairness") or {}
        rows.append({
            "method": condition.get("method") or "unavailable",
            "seed": condition.get("seed"),
            "ablation": condition.get("ablation"),
            "scenario": scenario,
            "status": condition.get("evidence", {}).get("status", "unavailable"),
            "critical_class": "ECG" if classes.get("ECG") else ("ICU" if classes.get("ICU") else None),
            "metrics": {
                "critical_latency_avg_ms": _metric(critical, "latency_ms"),
                "critical_p95_ms": {"value": (critical.get("tail_latency") or {}).get("p95_ms"),
                                    "available": (critical.get("tail_latency") or {}).get("p95_ms") is not None},
                "critical_p99_ms": {"value": (critical.get("tail_latency") or {}).get("p99_ms"),
                                    "available": (critical.get("tail_latency") or {}).get("p99_ms") is not None},
                "critical_packet_loss_pct": _metric(critical, "packet_loss_pct"),
                "critical_jitter_ms": _metric(critical, "jitter_ms"),
                "critical_throughput_mbps": _metric(critical, "throughput_mbps"),
                "critical_deadline_violation_pct": {"value": (critical.get("tail_latency") or {}).get("deadline_miss_rate_pct"),
                                                     "available": (critical.get("tail_latency") or {}).get("deadline_miss_rate_pct") is not None},
                "noncritical_throughput_mbps": _metric(background, "throughput_mbps"),
                "fairness_index": {"value": fairness.get("jain_index"), "available": fairness.get("jain_index") is not None},
                "route_changes": {"value": None, "available": False, "reason": "not measured by scenario statistics"},
                "recovery_time_ms": {"value": None, "available": False, "reason": "not separately measured"},
                "controller_overhead_ms": {"value": None, "available": False, "reason": "not measured"},
            },
            "source_file": "scenario_results.json",
        })
    return rows


def write_comparison_report(output_dir, result):
    rows = []
    for condition in result.get("conditions", []):
        rows.extend(_scenario_rows(output_dir / condition["run_directory"], condition))
    report = {
        "kind": "matched_live_comparison",
        "measurement_type": "LIVE EXPERIMENT",
        "topology_profile": result["topology_profile"],
        "topology_profile_parameters": TOPOLOGY_PROFILE_PARAMETERS.get(result["topology_profile"]),
        "topology_structure": {"hosts": 6, "switches": 4, "route_ports_fixed": True},
        "seeds": result["seeds"], "repetitions": result["repetitions"],
        "conditions": result["conditions"], "rows": rows,
        "missing_value_policy": "Unavailable measurements remain null; no zero substitution.",
        "braess_claim_policy": "Prevention is claimed only when saved live evidence verifies harmful rejection and baseline installation.",
    }
    (output_dir / "comparison_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Matched, seed-paired MedRoute study runner")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seeds", required=True, type=int, nargs="+", help="at least two distinct non-negative seeds")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--topology-profile", default="balanced_diamond")
    parser.add_argument("--skip-ablations", action="store_true")
    args = parser.parse_args()
    if len(set(args.seeds)) < 2 or min(args.seeds) < 0: parser.error("provide at least two distinct non-negative seeds")
    if args.output_dir.exists(): parser.error("output directory already exists")
    args.output_dir.mkdir(parents=True)
    rows = []
    for condition in study_plan(args.seeds, not args.skip_ablations):
        label = "{method}-seed{seed}".format(**condition)
        if condition["ablation"]: label += "-" + condition["ablation"]
        run_directory = args.output_dir / label
        command = [sys.executable, str(ROOT / "scripts" / "live_experiment.py"),
                   "--evidence-dir", str(run_directory), "--method", condition["method"],
                   "--seed", str(condition["seed"]), "--repetitions", str(args.repetitions),
                   "--topology-profile", args.topology_profile]
        if condition["ablation"]: command.extend(["--ablation", condition["ablation"]])
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        (run_directory / "matched_study.stdout.log").write_text(completed.stdout + completed.stderr, encoding="utf-8") if run_directory.exists() else None
        rows.append({**condition, "run_directory": label, "exit_code": completed.returncode,
                     "evidence": summarize(run_directory)})
    result = {"kind": "matched_live_study", "topology_profile": args.topology_profile,
              "seeds": args.seeds, "repetitions": args.repetitions, "conditions": rows,
              "note": "Only rows with status complete are eligible for comparative analysis; this file does not infer missing results."}
    (args.output_dir / "matched_study.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_comparison_report(args.output_dir, result)
    return 0 if all(row["evidence"]["status"] == "complete" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
