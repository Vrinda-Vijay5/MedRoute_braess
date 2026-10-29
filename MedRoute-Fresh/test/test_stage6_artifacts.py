import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_stage6", ROOT / "scripts" / "generate_stage6.py")
STAGE6 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STAGE6)


class Stage6ArtifactTests(unittest.TestCase):
    def test_small_run_confidence_interval_uses_student_t_critical_value(self):
        interval = STAGE6.confidence_interval_95([1.0, 2.0, 3.0])
        self.assertAlmostEqual(interval[0], -0.484, places=3)
        self.assertAlmostEqual(interval[1], 4.484, places=3)

    def fixture(self):
        rows = []
        for repetition, latency in enumerate((4.0, 5.0, 6.0), start=1):
            rows.append({"repetition": repetition, "per_class_metrics": {
                "ECG": {"metrics": {"latency_ms": latency, "jitter_ms": 1.0,
                                     "packet_loss_pct": 0.0},
                        "ping_samples": [{"rtt_ms": latency}, {"rtt_ms": None}],
                        "throughput_mbps": 2.0},
                "BACKGROUND": {"metrics": {"latency_ms": None, "jitter_ms": None,
                                            "packet_loss_pct": None},
                               "throughput_mbps": None},
            }})
        return {
            "config": {"traffic_classes": {"classes": {
                "ECG": {"objectives": {"delay_deadline_ms": 10,
                                         "max_packet_loss_pct": 1,
                                         "min_reliability_pct": 99}},
                "BACKGROUND": {}}}},
            "results": {"scenarios": {"measured_scenario": rows}},
        }

    def test_statistics_are_calculated_from_saved_repetitions_and_keep_gaps_missing(self):
        fixture = self.fixture()
        stats = STAGE6.calculate_scenario_statistics(
            fixture["results"], fixture["config"]["traffic_classes"]["classes"])
        latency = stats["measured_scenario"]["ECG"]["latency_ms"]
        self.assertEqual(latency["n"], 3)
        self.assertEqual(latency["mean"], 5.0)
        self.assertEqual(latency["standard_deviation"], 1.0)
        missing = stats["measured_scenario"]["BACKGROUND"]["latency_ms"]
        self.assertEqual(missing, {"n": 0, "mean": None, "standard_deviation": None})
        self.assertEqual(STAGE6.format_stat(missing), "Unavailable")
        tail = stats["measured_scenario"]["ECG"]["tail_latency"]
        self.assertEqual(tail["sample_count"], 3)
        self.assertEqual(tail["probe_count"], 6)
        self.assertEqual(tail["deadline_miss_count"], 3)
        self.assertEqual(tail["deadline_miss_rate_pct"], 50.0)
        self.assertEqual(stats["measured_scenario"]["_throughput_fairness"]["jain_index"], None)

    def test_generator_writes_four_pngs_and_report_from_saved_artifacts(self):
        fixture = self.fixture()
        with tempfile.TemporaryDirectory(prefix="medroute-stage6-") as temp:
            directory = pathlib.Path(temp)
            (directory / "config.json").write_text(
                json.dumps(fixture["config"]), encoding="utf-8")
            (directory / "scenario_results.json").write_text(
                json.dumps(fixture["results"]), encoding="utf-8")
            generated = STAGE6.generate(directory)
            self.assertEqual(len([name for name in generated if name.endswith(".png")]), 4)
            for name in generated:
                target = directory / name
                self.assertTrue(target.is_file())
                if name.endswith(".png"):
                    self.assertEqual(target.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            report = (directory / "experiment_report.md").read_text(encoding="utf-8")
            self.assertIn("5.000 ± 1.000 ms (n=3)", report)
            self.assertIn("Unavailable", report)
            self.assertIn("p95 RTT", report)
            self.assertIn("50.000%", report)

    def test_legacy_saved_rows_without_objectives_report_targets_as_unavailable(self):
        fixture = self.fixture()
        del fixture["config"]["traffic_classes"]["classes"]["ECG"]["objectives"]
        stats = STAGE6.calculate_scenario_statistics(
            fixture["results"], fixture["config"]["traffic_classes"]["classes"])
        tail = stats["measured_scenario"]["ECG"]["tail_latency"]
        self.assertEqual(tail["sample_count"], 3)
        self.assertEqual(tail["p95_ms"], 6.0)
        self.assertIsNone(tail["deadline_miss_rate_pct"])
        self.assertIsNone(tail["packet_loss_target_met"])


if __name__ == "__main__":
    unittest.main()
