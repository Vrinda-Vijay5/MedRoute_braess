#!/usr/bin/env python3
"""Create Stage 6 charts and a concise report from saved scenario measurements."""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path


METRICS = {
    "latency_ms": ("Per class latency across scenarios", "Latency (ms)"),
    "throughput_mbps": ("Per class throughput across scenarios", "Throughput (Mbps)"),
    "packet_loss_pct": ("Per class packet loss across scenarios", "Packet loss (%)"),
    "jitter_ms": ("Per class jitter across scenarios", "Jitter (ms)"),
}
_T_975 = (None, 12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365,
          2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
          2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069,
          2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042)


def metric_value(row, traffic_class, field):
    item = row.get("per_class_metrics", {}).get(traffic_class, {})
    value = item.get("throughput_mbps") if field == "throughput_mbps" else \
        (item.get("metrics") or {}).get(field)
    if (not isinstance(value, (int, float)) or isinstance(value, bool) or
            not math.isfinite(value) or value < 0 or
            (field == "packet_loss_pct" and value > 100)):
        return None
    return value


def confidence_interval_95(values):
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    degrees = len(values) - 1
    critical = _T_975[degrees] if degrees < len(_T_975) else 1.96
    margin = critical * statistics.stdev(values) / math.sqrt(len(values))
    return [mean - margin, mean + margin]


def calculate_scenario_statistics(results, classes):
    class_profiles = classes if isinstance(classes, dict) else {}
    class_names = list(class_profiles) if class_profiles else list(classes)
    output = {}
    for scenario, repetitions in results.get("scenarios", {}).items():
        output[scenario] = {}
        for traffic_class in class_names:
            output[scenario][traffic_class] = {}
            for field in METRICS:
                values = [value for row in repetitions
                          if (value := metric_value(row, traffic_class, field)) is not None]
                statistic = {
                    "n": len(values),
                    "mean": statistics.mean(values) if values else None,
                    "standard_deviation": statistics.stdev(values) if len(values) > 1 else None,
                }
                if len(values) > 1:
                    statistic["confidence_interval_95"] = confidence_interval_95(values)
                output[scenario][traffic_class][field] = statistic
            profile = class_profiles.get(traffic_class, {})
            objectives = profile.get("objectives", {}) if isinstance(profile, dict) else {}
            if not isinstance(objectives, dict):
                objectives = {}
            raw_probes = []
            for repetition in repetitions:
                per_class = repetition.get("per_class_metrics", {}).get(traffic_class, {})
                probes = per_class.get("ping_samples")
                if isinstance(probes, list):
                    raw_probes.extend(probes)
            valid_rtts = [probe["rtt_ms"] for probe in raw_probes
                if isinstance(probe, dict) and
                isinstance(probe.get("rtt_ms"), (int, float)) and
                not isinstance(probe.get("rtt_ms"), bool) and
                math.isfinite(probe["rtt_ms"]) and probe["rtt_ms"] >= 0]
            valid_rtts.sort()
            def valid_target(key, low, high=None):
                value = objectives.get(key)
                if (not isinstance(value, (int, float)) or isinstance(value, bool) or
                        not math.isfinite(value) or value < low or
                        (high is not None and value > high)):
                    return None
                return value
            deadline = valid_target("delay_deadline_ms", 0)
            if deadline == 0:
                deadline = None
            max_loss = valid_target("max_packet_loss_pct", 0, 100)
            min_reliability = valid_target("min_reliability_pct", 0, 100)
            p95 = valid_rtts[max(0, math.ceil(.95 * len(valid_rtts)) - 1)] if valid_rtts else None
            p99 = valid_rtts[max(0, math.ceil(.99 * len(valid_rtts)) - 1)] if valid_rtts else None
            misses = (len(raw_probes) - sum(rtt <= deadline for rtt in valid_rtts)
                      if deadline is not None and raw_probes else None)
            loss_stats = output[scenario][traffic_class]["packet_loss_pct"]
            loss_complete = bool(repetitions) and loss_stats["n"] == len(repetitions)
            mean_loss = loss_stats["mean"] if loss_stats["n"] else None
            delivery = 100 - mean_loss if loss_complete and mean_loss is not None else None
            output[scenario][traffic_class]["tail_latency"] = {
                "sample_count": len(valid_rtts), "probe_count": len(raw_probes),
                "p95_ms": p95, "p99_ms": p99, "deadline_ms": deadline,
                "deadline_miss_count": misses,
                "deadline_miss_rate_pct": 100 * misses / len(raw_probes)
                    if misses is not None else None,
                "delay_target_met": (misses == 0 if misses is not None else None),
                "mean_packet_loss_pct": mean_loss,
                "loss_observation_count": loss_stats["n"],
                "max_packet_loss_pct": max_loss,
                "packet_loss_target_met": (mean_loss <= max_loss
                    if loss_complete and mean_loss is not None and max_loss is not None else None),
                "receiver_delivery_reliability_pct": delivery,
                "min_reliability_pct": min_reliability,
                "reliability_target_met": (delivery >= min_reliability
                    if delivery is not None and min_reliability is not None else None),
                "target_source": objectives.get("target_source", "unspecified")}
        rates = [output[scenario][name]["throughput_mbps"]["mean"]
                 for name in class_names]
        fairness_complete = bool(repetitions) and bool(class_names) and all(
            output[scenario][name]["throughput_mbps"]["n"] == len(repetitions) and
            output[scenario][name]["throughput_mbps"]["mean"] is not None
            for name in class_names)
        denominator = len(rates) * sum(rate * rate for rate in rates
                                      if rate is not None) if rates else 0
        output[scenario]["_throughput_fairness"] = {
            "metric": "jain_fairness_index", "n_classes": sum(
                output[scenario][name]["throughput_mbps"]["n"] == len(repetitions)
                and bool(repetitions) for name in class_names),
            "expected_classes": len(class_names),
            "complete": fairness_complete and denominator > 0,
            "jain_index": (sum(rates) ** 2 / denominator)
                if fairness_complete and denominator > 0 else None}
    return output


def format_stat(stat, suffix=""):
    if not stat or stat["n"] == 0:
        return "Unavailable"
    mean = "{:.3f}".format(stat["mean"])
    if stat["standard_deviation"] is None:
        return mean + suffix + " (n=1; SD unavailable)"
    return "{} ± {:.3f}{} (n={})".format(
        mean, stat["standard_deviation"], suffix, stat["n"])


def generate(evidence_dir):
    evidence_dir = Path(evidence_dir).resolve()
    config_path = evidence_dir / "config.json"
    results_path = evidence_dir / "scenario_results.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    class_config = config.get("traffic_classes", {}).get("classes", {})
    classes = list(class_config)
    statistics_by_scenario = calculate_scenario_statistics(results, class_config)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required to generate Stage 6 charts: {}".format(exc)) from exc

    scenarios = list(results.get("scenarios", {}))
    for field, (title, ylabel) in METRICS.items():
        fig, axis = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
        has_values = False
        x_values = list(range(len(scenarios)))
        for traffic_class in classes:
            means, errors = [], []
            for scenario in scenarios:
                stat = statistics_by_scenario[scenario][traffic_class][field]
                means.append(stat["mean"] if stat["n"] else float("nan"))
                if stat["standard_deviation"] is not None:
                    errors.append((scenarios.index(scenario), stat["mean"],
                                   stat["standard_deviation"]))
                has_values = has_values or stat["n"] > 0
            axis.plot(x_values, means, marker="o", linewidth=1.8, label=traffic_class)
            for index, mean, deviation in errors:
                axis.errorbar(index, mean, yerr=deviation, fmt="none", capsize=3)
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.set_xticks(x_values, [name.replace("_", "\n") for name in scenarios])
        axis.grid(axis="y", alpha=0.25)
        if classes:
            axis.legend(title="Traffic class")
        if not has_values:
            axis.text(0.5, 0.5, "No saved measurements available", ha="center",
                      va="center", transform=axis.transAxes)
        fig.savefig(evidence_dir / ("plot_" + field + ".png"), dpi=160)
        plt.close(fig)

    columns = ["Scenario", "Class", "Latency ms", "Throughput Mbps",
               "Loss %", "Jitter ms"]
    lines = ["# Stage 6 experiment summary", "",
             "Mean ± sample standard deviation and approximate 95% normal confidence "
             "intervals using Student-t critical values through 30 degrees of freedom "
             "and a normal approximation above that; calculated from saved run-level repetitions. "
             "Missing measurements are shown as unavailable.", "",
             "| " + " | ".join(columns) + " |",
             "|" + "|".join(["---"] * len(columns)) + "|"]
    suffix = {"latency_ms": " ms", "throughput_mbps": " Mbps",
              "packet_loss_pct": "%", "jitter_ms": " ms"}
    for scenario in scenarios:
        for traffic_class in classes:
            metrics = statistics_by_scenario[scenario][traffic_class]
            cells = [scenario, traffic_class] + [
                format_stat(metrics[field], suffix[field]) for field in
                ("latency_ms", "throughput_mbps", "packet_loss_pct", "jitter_ms")]
            lines.append("| " + " | ".join(cells) + " |")
        lines.extend(["", "### Tail latency and configured service objectives", "",
                      "Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.", "",
                      "| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |", "|---|---:|---:|---:|---:|---|---:|---|---:|---|"])
        for traffic_class in classes:
            def cell(value, suffix=""):
                return "Unavailable" if value is None else "{:.3f}{}".format(value, suffix)
            tail = statistics_by_scenario[scenario][traffic_class]["tail_latency"]
            def state(value):
                return "Unavailable" if value is None else "met" if value else "missed"
            lines.append("| {} | {}/{} | {} | {} | {}/{} ({}) | {} | {} | {} | {} | {} |".format(
                traffic_class, tail["sample_count"], tail["probe_count"],
                cell(tail.get("p95_ms"), " ms"),
                cell(tail.get("p99_ms"), " ms"),
                tail.get("deadline_miss_count") if tail.get("deadline_miss_count") is not None else "Unavailable",
                tail.get("probe_count", 0), cell(tail.get("deadline_miss_rate_pct"), "%"),
                state(tail.get("delay_target_met")),
                cell(tail.get("receiver_delivery_reliability_pct"), "%"),
                state(tail.get("reliability_target_met")),
                cell(tail.get("mean_packet_loss_pct"), "%"),
                state(tail.get("packet_loss_target_met"))))
        fairness = statistics_by_scenario[scenario]["_throughput_fairness"]
        lines.extend(["", "Jain throughput fairness index: {} ({}/{} classes with complete throughput).".format(
            "Unavailable" if fairness.get("jain_index") is None else
            "{:.4f}".format(fairness["jain_index"]), fairness.get("n_classes", 0),
            fairness.get("expected_classes", 0)), ""])
    if config.get("dataset_used") is True:
        dataset = config.get("dataset_workload", {})
        scenario_policy = config.get("scenario_workload", {})
        lines.extend(["", "## Workload provenance", "",
                      "Dataset: {} · profile version {} · source {} · SHA-256 {}.".format(
                          dataset.get("dataset", "Unavailable"),
                          dataset.get("profile_version", "Unavailable"),
                          scenario_policy.get("dataset_profile_file", "Unavailable"),
                          dataset.get("source_sha256", "Unavailable")),
                      "Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.", ""])
    else:
        lines.extend(["", "## Workload provenance", "",
                      "Dataset-derived workload profiles were not used in this run.", ""])
    report = "\n".join(lines) + "\n"
    (evidence_dir / "experiment_report.md").write_text(report, encoding="utf-8")
    return ["plot_{}.png".format(field) for field in METRICS] + ["experiment_report.md"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_dir", type=Path,
                        help="run directory containing config.json and scenario_results.json")
    args = parser.parse_args()
    try:
        for name in generate(args.evidence_dir):
            print(name)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, RuntimeError) as exc:
        print("Stage 6 artifact generation failed: {}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
