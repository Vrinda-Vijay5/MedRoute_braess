import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sdn"))
from cbdr import (ConfigurationError, evaluate_candidate, evaluate_class_aware_candidate, load_config, validate_config)


def record(stamp, latency=20, jitter=5, loss=0.1, throughput=10, route="baseline", **extra):
    return {"topology": "diamond", "route": route, "timestamp": stamp,
            "complete": True, "source": "measured",
            "metrics": {"latency_ms": latency, "jitter_ms": jitter,
                        "packet_loss_pct": loss, "throughput_mbps": throughput}, **extra}


class CbdREvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.now = 1000.0

    def evaluate(self, before, after, **kwargs):
        return evaluate_candidate(current=before, candidate=after,
                                  config=kwargs.pop("config", self.config),
                                  now=self.now, **kwargs)

    def test_beneficial_candidate_is_accepted(self):
        result = self.evaluate(record(999), record(999, latency=10, jitter=2, loss=0.05, route="shortcut"))
        self.assertEqual(result["classification"], "beneficial")
        self.assertEqual(result["decision"], "accept_candidate")
        self.assertEqual(result["classical_braess_paradox"], "not_established_by_measured_route_comparison")

    def test_neutral_candidate_uses_declared_baseline_policy(self):
        result = self.evaluate(record(999), record(999, latency=20.2, route="shortcut"))
        self.assertEqual(result["classification"], "neutral")
        self.assertEqual(result["decision"], "retain_baseline")

    def test_harmful_candidate_is_rejected(self):
        result = self.evaluate(record(999), record(999, latency=30, route="shortcut"))
        self.assertEqual(result["classification"], "harmful")
        self.assertEqual(result["reason_code"], "OBSERVED_CANDIDATE_DEGRADATION")
        self.assertEqual(result["controller_action"], "retain_last_verified_route")

    def test_stale_and_missing_measurements_are_inconclusive(self):
        stale = self.evaluate(record(900), record(999))
        missing = self.evaluate(record(999), None)
        self.assertEqual(stale["reason_code"], "TELEMETRY_STALE_OR_FUTURE_MEASUREMENT")
        self.assertEqual(missing["classification"], "inconclusive")
        self.assertEqual(missing["decision"], "retain_baseline")

    def evaluate_all_classes(self, stamp, *, max_age_seconds):
        current = {
            name: record(stamp, route="baseline")
            for name in self.config["classes"]
        }
        candidate = {
            name: record(stamp, route="shortcut")
            for name in self.config["classes"]
        }
        return evaluate_class_aware_candidate(
            current_by_class=current,
            candidate_by_class=candidate,
            current_network_cost_pct=10.0,
            candidate_network_cost_pct=10.0,
            config=self.config,
            now=self.now,
            max_age_seconds=max_age_seconds,
        )

    def test_class_aware_batch_accepts_complete_measurements_60_seconds_old(self):
        result = self.evaluate_all_classes(940, max_age_seconds=120.0)
        self.assertNotEqual(result["reason_code"], "INCOMPLETE_CLASS_TELEMETRY")
        self.assertEqual(len(result["class_evaluations"]), 6)
        self.assertTrue(all(
            item["classification"] != "inconclusive"
            for item in result["class_evaluations"].values()
        ))

    def test_class_aware_batch_rejects_measurements_older_than_120_seconds(self):
        result = self.evaluate_all_classes(870, max_age_seconds=120.0)
        self.assertEqual(result["classification"], "inconclusive")
        self.assertEqual(result["reason_code"], "INCOMPLETE_CLASS_TELEMETRY")

    def test_class_aware_batch_rejects_future_timestamps(self):
        result = self.evaluate_all_classes(1001, max_age_seconds=120.0)
        self.assertEqual(result["classification"], "inconclusive")
        self.assertEqual(result["reason_code"], "INCOMPLETE_CLASS_TELEMETRY")

    def test_single_pair_default_freshness_limit_remains_30_seconds(self):
        result = self.evaluate(record(940), record(940, route="shortcut"))
        self.assertEqual(result["classification"], "inconclusive")
        self.assertEqual(
            result["reason_code"],
            "TELEMETRY_STALE_OR_FUTURE_MEASUREMENT",
        )

    def test_invalid_inconsistent_measurements_are_inconclusive(self):
        incomplete = record(999)
        incomplete["complete"] = False
        invalid = record(999, loss=101)
        self.assertIn("incomplete", self.evaluate(record(999), incomplete)["reason_code"].lower())
        self.assertEqual(self.evaluate(record(999), invalid)["classification"], "inconclusive")

    def hard_config(self):
        config = copy.deepcopy(self.config)
        objectives = config["classes"]["EMERGENCY_ALARM"]["objectives"]
        objectives["max_latency_ms"] = 100
        objectives["hard_constraint"] = True
        objectives["validated"] = True
        return config

    def test_hard_constraint_overrides_improved_weighted_cost(self):
        result = self.evaluate(
            record(999, latency=200), record(999, latency=150, route="shortcut"),
            config=self.hard_config(), traffic_class="EMERGENCY_ALARM")
        self.assertLess(result["candidate_cost"], result["baseline_cost"])
        self.assertEqual(result["classification"], "constraint_violation")
        self.assertEqual(result["decision"], "reject_candidate")
        self.assertFalse(result["safe_route_exists"])

    def test_strict_mode_fails_closed_without_validated_constraints(self):
        result = self.evaluate(record(999), record(999, latency=10),
                               traffic_class="EMERGENCY_ALARM", constraint_mode="strict")
        self.assertEqual(result["classification"], "inconclusive")
        self.assertEqual(result["reason_code"], "STRICT_CONSTRAINT_NOT_VALIDATED")

    def test_fairness_safeguard_rejects_excessive_drop(self):
        before, after = record(999, jain_fairness=0.95), record(999, latency=10,
            jain_fairness=0.7, route="shortcut")
        result = self.evaluate(before, after, fairness_policy={"max_drop": 0.1})
        self.assertEqual(result["reason_code"], "FAIRNESS_GUARDRAIL_VIOLATION")
        self.assertEqual(result["decision"], "reject_candidate")

    def test_versioned_configuration_has_six_explicit_service_mappings(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["classes"]), 6)
        self.assertEqual(self.config["classes"]["MEDICAL_IMAGING"]["queue_id"], 4)
        self.assertFalse(self.config["classes"]["MEDICAL_IMAGING"]["objectives"]["validated"])

    def test_invalid_configuration_is_rejected(self):
        config = copy.deepcopy(self.config)
        config["candidate_degradation_threshold"] = float("nan")
        with self.assertRaises(ConfigurationError):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
