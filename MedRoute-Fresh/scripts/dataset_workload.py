"""Read-only adapter from CICIoMT training-derived profiles to synthetic flows.

The profile file contains aggregate benign traffic characterization, not replayable
packets or clinical class labels. Only this derived JSON is read by the experiment.
"""
import hashlib
import json
import math
import random
from pathlib import Path


PROFILE_FILE = Path("data/CICIoMT2024/processed/workload_profiles.json")
FALLBACK_PROFILE_FILE = Path("data/CICIoMT2024/processed/benign_training_profile.json")
CATALOG_FILE = Path("data/CICIoMT2024/raw/healthcare_traffic_profiles.csv")
TYPICAL_PROFILE = "ciciomt-benign-train-typical"
HIGH_PROFILE = "ciciomt-benign-train-high"


def load_profiles(project_root):
    """Load validated train-only profiles and return dataset provenance."""
    root = Path(project_root)
    path = root / PROFILE_FILE
    if not path.exists():
        path = root / FALLBACK_PROFILE_FILE
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8"))
    if document.get("dataset") != "CICIoMT2024":
        raise ValueError("workload profile does not identify CICIoMT2024")
    profiles = document.get("profiles")
    if profiles is None:
        avg = document.get("feature_summaries", {}).get("AVG", {})
        packet_size = max(1, min(1400, round(avg.get("median", 256)) - 28))
        profiles = {
            TYPICAL_PROFILE: {"split": "train", "offered_rate_bps": 500_000,
                              "packet_size_bytes": packet_size},
            HIGH_PROFILE: {"split": "train", "offered_rate_bps": 20_000_000,
                           "packet_size_bytes": packet_size}
        }
    if not document.get("train_source_files") and document.get("source_file"):
        document["train_source_files"] = [document["source_file"]]
    if not document.get("test_source_files_excluded_from_workload_derivation"):
        document["test_source_files_excluded_from_workload_derivation"] = [
            "Benign_test.pcap.csv"
        ]
    required = (TYPICAL_PROFILE, HIGH_PROFILE)
    if not isinstance(profiles, dict) or any(name not in profiles for name in required):
        raise ValueError("workload profile is missing required train profiles")
    for name in required:
        profile = profiles[name]
        rate = profile.get("offered_rate_bps")
        packet_size = profile.get("packet_size_bytes")
        if profile.get("split") != "train":
            raise ValueError("only training-derived workload profiles are allowed")
        if (not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0 or
                not isinstance(packet_size, int) or packet_size <= 0):
            raise ValueError("workload profile has invalid offered rate or packet size")
    profile_version = document.get("profile_version")
    if profile_version is None or (isinstance(profile_version, str) and not profile_version.strip()):
        profile_version = "unspecified"
    source_kind = document.get("source_kind")
    if source_kind is None or (isinstance(source_kind, str) and not source_kind.strip()):
        source_kind = "training-derived aggregate profile"
    return {"dataset": document["dataset"],
            "profile_version": profile_version,
            "source_kind": source_kind,
            "source_file": str(path.relative_to(root)).replace("\\", "/"),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "train_source_files": document["train_source_files"],
            "test_source_files_excluded_from_workload_derivation":
                document["test_source_files_excluded_from_workload_derivation"],
            "limitations": document.get("limitations", []),
            "profiles": {name: profiles[name] for name in required}}


def load_traffic_catalog(project_root):
    """Load the supplied synthetic healthcare workload catalog for traceability."""
    import csv
    path = Path(project_root) / CATALOG_FILE
    if not path.exists():
        raise ValueError("healthcare traffic catalog is missing: {}".format(path))
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {"traffic_type", "criticality", "transport_protocol",
                "destination_port", "offered_rate_bps", "packet_size_bytes",
                "duration_seconds"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("healthcare traffic catalog has an invalid schema")
    for row in rows:
        for field in required:
            if not row.get(field):
                raise ValueError("healthcare traffic catalog has a blank {}".format(field))
    return {"source_file": str(CATALOG_FILE).replace("\\", "/"),
            "rows": rows, "row_count": len(rows),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def build_scenario_workloads(provenance, scenario_plan, class_names, bottleneck_mbps,
                             random_seed=None):
    """Build deterministic scenario flow settings from the saved train profiles.

    The intentional background overload is derived as bottleneck capacity plus the
    nominal offered rates of all other classes. This makes total offered demand
    exceed the bottleneck by the modeled non-background demand, without a fixed
    scenario rate multiplier.
    """
    if not isinstance(bottleneck_mbps, (int, float)) or not math.isfinite(bottleneck_mbps) or bottleneck_mbps <= 0:
        raise ValueError("bottleneck capacity must be a positive finite number")
    profiles = provenance["profiles"]
    typical, high = profiles[TYPICAL_PROFILE], profiles[HIGH_PROFILE]
    if random_seed is not None and (isinstance(random_seed, bool) or
            not isinstance(random_seed, int) or random_seed < 0):
        raise ValueError("random_seed must be a non-negative integer or None")
    output = {}
    for scenario, spec in scenario_plan.items():
        heavy = bool(spec.get("heavy_background"))
        flows = {}
        for class_name in class_names:
            selected_name, selected = ((HIGH_PROFILE, high)
                                       if heavy and class_name == "BACKGROUND"
                                       else (TYPICAL_PROFILE, typical))
            base_bps = selected["offered_rate_bps"]
            seed_material = "{}:{}:{}".format(random_seed, scenario, class_name)
            stable_seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
            rate_factor = random.Random(stable_seed).uniform(0.9, 1.1)
            offered_rate = round(base_bps * rate_factor) if random_seed is not None else base_bps
            flows[class_name] = {
                "dataset_profile": selected_name,
                "dataset_base_rate_bps": base_bps,
                "dataset_packet_size_bytes": selected["packet_size_bytes"],
                "seed_rate_factor": rate_factor,
                "offered_rate_bps": offered_rate,
                "offered_load_mbps": offered_rate / 1_000_000,
            }
        if spec.get("emergency_surge"):
            for name, multiplier in (("ECG", 40), ("ICU", 30)):
                if name in flows:
                    profile = class_names[name]
                    surged = max(flows[name]["offered_rate_bps"],
                                 int(multiplier * typical["offered_rate_bps"]))
                    flows[name]["offered_rate_bps"] = surged
                    flows[name]["offered_load_mbps"] = surged / 1_000_000
                    flows[name]["emergency_surge_multiplier"] = multiplier
                    flows[name]["emergency_surge_rate_cap_mbps"] = profile["max_rate_mbps"]
        if heavy and "BACKGROUND" in flows:
            critical_demand_bps = sum(flow["offered_rate_bps"]
                                      for name, flow in flows.items()
                                      if name != "BACKGROUND")
            background = flows["BACKGROUND"]
            background["offered_rate_bps"] = (
                bottleneck_mbps * 1_000_000 + critical_demand_bps)
            background["offered_load_mbps"] = background["offered_rate_bps"] / 1_000_000
        for flow in flows.values():
            flow["scenario_scale_factor"] = (
                flow["offered_rate_bps"] / flow["dataset_base_rate_bps"])
        output[scenario] = flows
    return output
