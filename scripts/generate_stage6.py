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


def metric_value(row, traffic_class, field):
    item = row.get("per_class_metrics", {}).get(traffic_class, {})
    value = item.get("throughput_mbps") if field == "throughput_mbps" else \
        (item.get("metrics") or {}).get(field)
    return value if isinstance(value, (int, float)) and math.isfinite(value) else None


def confidence_interval_95(values):
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    margin = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return [mean - margin, mean + margin]


def calculate_scenario_statistics(results, classes):
    output = {}
    for scenario, repetitions in results.get("scenarios", {}).items():
        output[scenario] = {}
        for traffic_class in classes:
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
    statistics_by_scenario = calculate_scenario_statistics(results, classes)

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
             "intervals, calculated from saved scenario repetitions. Missing measurements "
             "are shown as unavailable.", "",
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
