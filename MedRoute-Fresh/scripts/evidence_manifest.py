"""Write checksummed metadata for a single MedRoute run directory."""
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_FILES = ("config.json", "summary.json", "scenario_results.json",
                 "measurements.json", "controller.jsonl", "decisions.json")


def _git_info(repository):
    def git(*args):
        try:
            safe_root = repository.parent.resolve().as_posix()
            return subprocess.run(["git", "-c", "safe.directory={}".format(safe_root),
                                   "-c", "filter.lfs.process=",
                                   "-c", "filter.lfs.smudge=cat",
                                   "-c", "filter.lfs.required=false", *args],
                                  cwd=repository, capture_output=True, text=True,
                                  timeout=30, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
    return {"revision": git("rev-parse", "HEAD"),
            "working_tree_status": git("status", "--short")}


def _version(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=3, check=False)
        text = (result.stdout or result.stderr).strip().splitlines()
        return text[0] if text else None
    except (OSError, subprocess.SubprocessError):
        return None


def _ryu_manager_path():
    adjacent = Path(sys.executable).with_name("ryu-manager")
    return str(adjacent) if adjacent.is_file() else shutil.which("ryu-manager")


def write_manifest(directory, started_at=None):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    prior_manifest = {}
    if (directory / "manifest.json").is_file():
        try:
            prior_manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prior_manifest = {}
    summary_path = directory / "summary.json"
    summary = {}
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            summary = {"summary_parse_error": True}
    config = {}
    try:
        config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    files = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name in ("manifest.json", "checksums.sha256"):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({"path": path.relative_to(directory).as_posix(),
                      "bytes": path.stat().st_size, "sha256": digest})
    missing = [name for name in EXPECTED_FILES if not (directory / name).is_file()]
    if (directory / "error.txt").exists():
        status = "failed"
    elif missing:
        status = "partial"
    elif summary.get("scenario_validation_passed") is False or summary.get("scenario_validation_errors"):
        status = "completed_with_failed_or_inconclusive_stages"
    elif summary.get("live_experiment") in (
            "harmful_shortcut_prevented", "shortcut_not_harmful_under_test", "method_policy_only"):
        status = "completed"
    else:
        status = "completed_with_result_requiring_review"
    repository = directory.parent.parent if directory.parent.name == "artifacts" else directory.parent
    ryu_manager = _ryu_manager_path()
    manifest = {
        "schema_version": 1,
        "run_id": directory.name,
        "status": status,
        "started_at_utc": started_at or prior_manifest.get("started_at_utc"),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": _git_info(repository),
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "ryu_manager": _version([ryu_manager, "--version"]) if ryu_manager else None,
                        "mininet": _version(["mn", "--version"]),
                        "open_vswitch": _version(["ovs-vsctl", "--version"]),
                        "node": _version(["node", "--version"])},
        "workload_seed": config.get("random_seed"),
        "workload_seed_note": "Seeded offered-rate perturbations are recorded in config.json and dataset_workload.json.",
        "experiment_summary_status": summary.get("live_experiment"),
        "scenario_validation_passed": summary.get("scenario_validation_passed"),
        "scenario_validation_errors": summary.get("scenario_validation_errors", []),
        "missing_expected_files": missing,
        "files": files,
        "resumable": False,
        "resume_limitation": "The current live experiment runner has no checkpoint and resume implementation.",
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                               encoding="utf-8")
    (directory / "checksums.sha256").write_text("".join(
        "{}  {}\n".format(item["sha256"], item["path"]) for item in files),
        encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(write_manifest(args.run_directory), indent=2))
