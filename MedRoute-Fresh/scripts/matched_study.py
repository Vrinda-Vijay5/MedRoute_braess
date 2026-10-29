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
    return {"status": "complete" if summary.get("scenario_validation_passed") else "incomplete",
            "live_experiment": summary.get("live_experiment"),
            "selected_route": summary.get("selected_route"),
            "shortcut_verdict": summary.get("shortcut_verdict"),
            "scenario_statistics_file": summary.get("scenario_statistics_file"),
            "all_flow_rules_verified": summary.get("all_flow_rules_verified"),
            "all_telemetry_complete": summary.get("all_telemetry_complete")}


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
    return 0 if all(row["evidence"]["status"] == "complete" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
