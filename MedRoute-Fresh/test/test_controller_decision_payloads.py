import importlib.util
import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
SDN_DIR = ROOT / "sdn"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(SDN_DIR) not in sys.path:
    sys.path.insert(0, str(SDN_DIR))

SPEC = importlib.util.spec_from_file_location("live_experiment", SCRIPTS_DIR / "live_experiment.py")
LIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIVE)

with open(SDN_DIR / "routes.json", encoding="utf-8") as f:
    ROUTES = json.load(f)

with open(SDN_DIR / "classes.json", encoding="utf-8") as f:
    CLASS_CONFIG = json.load(f)

from dataset_workload import load_traffic_catalog


def load_controller_test_catalog():
    """Use recorded synthetic catalog metadata for controller unit tests.

    These assertions exercise decision payload behavior, not workload-source
    provenance. The checked-in LFS input is validated separately by
    test_dataset_workload and may be unavailable in a pointer-only checkout.
    """
    try:
        return load_traffic_catalog(ROOT)
    except ValueError as exc:
        if "Git LFS pointer" not in str(exc):
            raise
    artifact = ROOT / "artifacts" / "smoke-20261029-retry-091029" / "profile_matrix.json"
    matrix = json.loads(artifact.read_text(encoding="utf-8"))
    rows = [profile["catalog"] for profile in matrix["profiles"]]
    return {"source_file": "historical synthetic test fixture", "rows": rows,
            "row_count": len(rows), "sha256": "historical-artifact-metadata"}


TRAFFIC_CATALOG = load_controller_test_catalog()

try:
    from controller import MedRoute
    RYU_AVAILABLE = True
except ModuleNotFoundError:
    RYU_AVAILABLE = False
    MedRoute = None


def make_mock_route_measurement(mode, complete=True, tx_util_pct=10.0, throughput_mbps=15.0):
    route_ports = {
        "baseline": [("s1", 2), ("s2", 2), ("s4", 3)],
        "alternate": [("s1", 3), ("s3", 2), ("s4", 3)],
        "shortcut": [("s1", 2), ("s2", 3), ("s3", 2), ("s4", 3)],
    }
    links = [
        {
            "name": f"{sw}-eth{pt}",
            "switch": sw,
            "port": pt,
            "complete": complete,
            "tx_utilization_pct": tx_util_pct if complete else None,
        }
        for sw, pt in route_ports.get(mode, [("s1", 2)])
    ]
    return {
        "mode": mode,
        "complete": complete,
        "throughput_mbps": throughput_mbps if complete else None,
        "metrics": {"complete": complete, "latency_ms": 10.0, "jitter_ms": 2.0, "packet_loss_pct": 0.0, "cost": 1.0} if complete else None,
        "flow_evidence": {"verified": complete},
        "path_link_utilization": {
            "complete": complete,
            "links": links,
        },
    }


def validate_controller_schema(test_case, payload):
    test_case.assertIsInstance(payload, dict)
    test_case.assertIn(payload.get("selected_route"), ROUTES)
    test_case.assertIn(payload.get("verdict"), ("harmful", "beneficial", "neutral", "inconclusive"))
    test_case.assertIsInstance(payload.get("reason"), str)
    test_case.assertTrue(len(payload["reason"]) > 0)
    test_case.assertIsInstance(payload.get("metrics_used"), dict)
    test_case.assertIsInstance(payload.get("prevention_verified"), bool)

    if RYU_AVAILABLE and MedRoute is not None:
        app = object.__new__(MedRoute)
        app.log = lambda *args, **kwargs: None
        result = app.record_route_decision(payload)
        test_case.assertTrue(result.get("recorded"))


class ControllerDecisionPayloadTests(unittest.TestCase):
    def test_m3_posted_payload_satisfies_controller_schema(self):
        posted_payloads = []
        def mock_request_json(method="GET", value=None, timeout=1, endpoint=LIVE.API):
            if endpoint == LIVE.DECISION_API and method == "POST":
                posted_payloads.append(value)
                return {"recorded": True}
            return {}

        route_measurements = [
            make_mock_route_measurement("baseline", True, 45.0),
            make_mock_route_measurement("alternate", True, 15.0),
            make_mock_route_measurement("shortcut", True, 75.0),
        ]

        with patch.object(LIVE, "measure_route_condition", side_effect=route_measurements), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode"), \
             patch.object(LIVE, "verify_flows", return_value={"verified": True}), \
             patch.object(LIVE, "request_json", side_effect=mock_request_json):

            record = LIVE.run_congestion_route_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=ROUTES, class_config=CLASS_CONFIG
            )

        self.assertEqual(len(posted_payloads), 1)
        payload = posted_payloads[0]

        # 1. Satisfies controller schema
        validate_controller_schema(self, payload)
        self.assertEqual(payload["selected_route"], "alternate")
        self.assertEqual(payload["verdict"], "inconclusive")
        self.assertFalse(payload["prevention_verified"])
        self.assertIn("path_congestion_scores_pct", payload["metrics_used"])
        self.assertEqual(payload["metrics_used"]["path_congestion_scores_pct"]["alternate"], 15.0)

        # 2. Complete and verified
        self.assertTrue(record["complete"])
        self.assertTrue(record["route_selection_verified"])
        self.assertFalse(record["prevention_verified"])

    def test_m3_never_claims_braess_prevention(self):
        posted_payloads = []
        def mock_request_json(method="GET", value=None, timeout=1, endpoint=LIVE.API):
            if endpoint == LIVE.DECISION_API and method == "POST":
                posted_payloads.append(value)
                return {"recorded": True}
            return {}

        # Even when baseline has lowest congestion:
        route_measurements = [
            make_mock_route_measurement("baseline", True, 10.0),
            make_mock_route_measurement("alternate", True, 50.0),
            make_mock_route_measurement("shortcut", True, 70.0),
        ]

        with patch.object(LIVE, "measure_route_condition", side_effect=route_measurements), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode"), \
             patch.object(LIVE, "verify_flows", return_value={"verified": True}), \
             patch.object(LIVE, "request_json", side_effect=mock_request_json):

            record = LIVE.run_congestion_route_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=ROUTES, class_config=CLASS_CONFIG
            )

        self.assertEqual(record["selected_route"], "baseline")
        self.assertFalse(record["prevention_verified"])
        self.assertFalse(record["decision"]["prevention_verified"])
        self.assertFalse(posted_payloads[0]["prevention_verified"])

    def test_m3_complete_remains_false_on_failure(self):
        # Failure 1: Controller recording fails
        route_measurements = [
            make_mock_route_measurement("baseline", True, 10.0),
            make_mock_route_measurement("alternate", True, 50.0),
            make_mock_route_measurement("shortcut", True, 70.0),
        ]
        with patch.object(LIVE, "measure_route_condition", side_effect=route_measurements), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode"), \
             patch.object(LIVE, "verify_flows", return_value={"verified": True}), \
             patch.object(LIVE, "request_json", side_effect=RuntimeError("connection refused")):

            record = LIVE.run_congestion_route_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=ROUTES, class_config=CLASS_CONFIG
            )
        self.assertFalse(record["complete"])
        self.assertFalse(record["decision"]["controller_recorded"])

        # Failure 2: Flow verification fails
        with patch.object(LIVE, "measure_route_condition", side_effect=route_measurements), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode"), \
             patch.object(LIVE, "verify_flows", return_value={"verified": False}), \
             patch.object(LIVE, "request_json", return_value={"recorded": True}):

            record = LIVE.run_congestion_route_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=ROUTES, class_config=CLASS_CONFIG
            )
        self.assertFalse(record["complete"])
        self.assertFalse(record["route_selection_verified"])

    def test_m4_constraint_violation_normalized_and_recorded(self):
        posted_payloads = []
        def mock_request_json(method="GET", value=None, timeout=1, endpoint=LIVE.API):
            if endpoint == LIVE.DECISION_API and method == "POST":
                posted_payloads.append(value)
                return {"recorded": True}
            return {}

        mock_profile_row = {
            "complete": True,
            "offered_rate_bps": 1_000_000,
            "link_utilization": {"links": []},
            "metrics": {
                "complete": True,
                "latency_ms": 15.0,
                "jitter_ms": 3.0,
                "packet_loss_pct": 0.0,
                "throughput_mbps": 1.0,
                "cost": 1.0,
            },
        }

        mock_evaluation = {
            "algorithm": "CBDR",
            "classification": "constraint_violation",
            "decision": "reject_candidate",
            "reason_code": "HARD_CONSTRAINT_VIOLATION",
            "explanation": "EMERGENCY_ALARM latency exceeded 100ms threshold.",
            "current_objective": 1.2,
            "candidate_objective": 2.5,
            "relative_change": 1.08,
            "current_network_cost_pct": 20.0,
            "candidate_network_cost_pct": 50.0,
            "baseline_hard_violations": [],
            "candidate_hard_violations": [{"traffic_class": "EMERGENCY_ALARM", "count": 1}],
        }

        with patch.object(LIVE, "run_catalog_profile_matrix", return_value=[dict(mock_profile_row)]), \
             patch.object(LIVE, "route_congestion_score", return_value=25.0), \
             patch("cbdr.evaluate_class_aware_candidate", return_value=mock_evaluation), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode"), \
             patch.object(LIVE, "verify_flows", return_value={"verified": True}), \
             patch.object(LIVE, "request_json", side_effect=mock_request_json), \
             patch.object(LIVE, "save_json"):

            record = LIVE.run_cbdr_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=ROUTES, class_config=CLASS_CONFIG,
                traffic_catalog=TRAFFIC_CATALOG, qos_enabled=True
            )

        self.assertEqual(len(posted_payloads), 1)
        payload = posted_payloads[0]

        # Valid controller schema
        validate_controller_schema(self, payload)
        # Normalized verdict is harmful
        self.assertEqual(payload["verdict"], "harmful")
        # Original classification is preserved
        self.assertEqual(payload["classification"], "constraint_violation")
        self.assertEqual(payload["original_classification"], "constraint_violation")
        self.assertEqual(payload["reason_code"], "HARD_CONSTRAINT_VIOLATION")
        # Real measured metrics included
        self.assertEqual(payload["metrics_used"]["baseline"]["cost"], 1.2)
        self.assertEqual(payload["metrics_used"]["shortcut"]["cost"], 2.5)
        # Prevention verified when candidate rejected, flows verified, controller recorded
        self.assertTrue(payload["prevention_verified"])
        self.assertTrue(record["prevention_verified"])
        self.assertTrue(record["complete"])

    def test_m4_not_claiming_prevention_when_recording_or_flows_fail(self):
        mock_profile_row = {
            "complete": True,
            "offered_rate_bps": 1_000_000,
            "link_utilization": {"links": []},
            "metrics": {
                "complete": True,
                "latency_ms": 15.0,
                "jitter_ms": 3.0,
                "packet_loss_pct": 0.0,
                "throughput_mbps": 1.0,
                "cost": 1.0,
            },
        }
        mock_evaluation = {
            "algorithm": "CBDR",
            "classification": "constraint_violation",
            "decision": "reject_candidate",
            "reason_code": "HARD_CONSTRAINT_VIOLATION",
            "explanation": "Violation test",
            "current_objective": 1.0,
            "candidate_objective": 2.0,
            "relative_change": 1.0,
            "current_network_cost_pct": 20.0,
            "candidate_network_cost_pct": 50.0,
            "baseline_hard_violations": [],
            "candidate_hard_violations": [{"traffic_class": "EMERGENCY_ALARM", "count": 1}],
        }

        # Case A: Controller recording fails with exception
        with patch.object(LIVE, "run_catalog_profile_matrix", return_value=[dict(mock_profile_row)]), \
             patch.object(LIVE, "route_congestion_score", return_value=25.0), \
             patch("cbdr.evaluate_class_aware_candidate", return_value=dict(mock_evaluation)), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode"), \
             patch.object(LIVE, "verify_flows", return_value={"verified": True}), \
             patch.object(LIVE, "request_json", side_effect=RuntimeError("controller error")), \
             patch.object(LIVE, "save_json"):

            record = LIVE.run_cbdr_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=ROUTES, class_config=CLASS_CONFIG,
                traffic_catalog=TRAFFIC_CATALOG, qos_enabled=True
            )
        self.assertFalse(record["decision"]["controller_recorded"])
        self.assertFalse(record["decision"]["prevention_verified"])
        self.assertFalse(record["prevention_verified"])
        self.assertFalse(record["complete"])

        # Case B: Flow verification fails
        with patch.object(LIVE, "run_catalog_profile_matrix", return_value=[dict(mock_profile_row)]), \
             patch.object(LIVE, "route_congestion_score", return_value=25.0), \
             patch("cbdr.evaluate_class_aware_candidate", return_value=dict(mock_evaluation)), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode"), \
             patch.object(LIVE, "verify_flows", return_value={"verified": False}), \
             patch.object(LIVE, "request_json", return_value={"recorded": True}), \
             patch.object(LIVE, "save_json"):

            record = LIVE.run_cbdr_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=ROUTES, class_config=CLASS_CONFIG,
                traffic_catalog=TRAFFIC_CATALOG, qos_enabled=True
            )
        self.assertFalse(record["decision"]["flows_verified"])
        self.assertFalse(record["decision"]["route_selection_verified"])
        self.assertFalse(record["decision"]["prevention_verified"])
        self.assertFalse(record["prevention_verified"])
        self.assertFalse(record["complete"])


if __name__ == "__main__":
    unittest.main()

