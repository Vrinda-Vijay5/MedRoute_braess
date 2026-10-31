import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("matched_study", ROOT / "scripts" / "matched_study.py")
study = importlib.util.module_from_spec(spec); spec.loader.exec_module(study)


class MatchedStudyTests(unittest.TestCase):
    def test_each_seed_has_all_methods_and_independent_ablations(self):
        plan = study.study_plan([7, 8])
        self.assertEqual(len(plan), 14)
        for seed in (7, 8):
            rows = [row for row in plan if row["seed"] == seed]
            self.assertEqual({row["method"] for row in rows if row["ablation"] is None}, set(study.METHODS))
            self.assertEqual({row["ablation"] for row in rows if row["ablation"]}, set(study.ABLATIONS))

    def test_report_preserves_live_metrics_and_missing_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            condition_dir = root / "M1-seed7"
            condition_dir.mkdir()
            (condition_dir / "scenario_results.json").write_text(json.dumps({
                "statistics_from_saved_measurements": {
                    "emergency_surge": {"classes": {"ECG": {
                        "latency_ms": {"complete": True, "mean": 12.5, "standard_deviation": 1.0, "n": 2},
                        "jitter_ms": {"complete": True, "mean": 2.0, "standard_deviation": 0.2, "n": 2},
                        "packet_loss_pct": {"complete": True, "mean": 0.5, "standard_deviation": 0.1, "n": 2},
                        "throughput_mbps": {"complete": True, "mean": 4.0, "standard_deviation": 0.1, "n": 2},
                        "tail_latency": {"p95_ms": 18.0, "p99_ms": 21.0, "deadline_miss_rate_pct": None}
                    }}, "throughput_fairness": {"jain_index": 0.91}}
                }
            }), encoding="utf-8")
            index = {"topology_profile": "balanced_diamond", "seeds": [7], "repetitions": 2,
                     "conditions": [{"method": "M1", "seed": 7, "ablation": None,
                                      "run_directory": "M1-seed7", "evidence": {"status": "complete"}}]}
            report = study.write_comparison_report(root, index)
            row = report["rows"][0]
            self.assertEqual(report["measurement_type"], "LIVE EXPERIMENT")
            self.assertEqual(row["metrics"]["critical_latency_avg_ms"]["value"], 12.5)
            self.assertIsNone(row["metrics"]["critical_deadline_violation_pct"]["value"])
            self.assertFalse(row["metrics"]["recovery_time_ms"]["available"])
