import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("live_experiment", ROOT / "scripts" / "live_experiment.py")
LIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIVE)


def samples(values):
    return [{"timestamp": 1000 + i, "rtt_ms": value, "returncode": 0} for i, value in enumerate(values)]


class LiveMetricTests(unittest.TestCase):
    def test_controller_metrics_endpoint_is_not_nested_under_mode(self):
        self.assertEqual(LIVE.METRICS_API, "http://127.0.0.1:8080/medroute/metrics")

    def test_openflow_port_stats_produce_directional_link_utilization(self):
        before = {"timestamp": 10, "switches": {}}
        after = {"timestamp": 12, "switches": {}}
        for (switch, port), _peer in LIVE.PORT_PEERS.items():
            before["switches"].setdefault(switch, {})[port] = {"rx_bytes": 1000, "tx_bytes": 2000}
            after["switches"].setdefault(switch, {})[port] = {"rx_bytes": 101000, "tx_bytes": 202000}
        parsed = LIVE.parse_port_stats("port 1: rx pkts=1, bytes=1234, drop=0\n    tx pkts=2, bytes=5678, drop=0")
        self.assertEqual(parsed[1], {"rx_bytes": 1234, "tx_bytes": 5678})
        result = LIVE.calculate_link_utilization(before, after, 100)
        self.assertTrue(result["complete"])
        self.assertEqual(result["links"][0]["rx_mbps"], 0.4)
        self.assertEqual(result["links"][0]["tx_mbps"], 0.8)
        shaped = LIVE.calculate_link_utilization(
            before, after, 100, {("s1", 2): 20})
        s1_s2 = next(link for link in shaped["links"]
                     if link["switch"] == "s1" and link["port"] == 2)
        self.assertEqual(s1_s2["capacity_mbps"], 20)
        self.assertEqual(s1_s2["tx_utilization_pct"], 4.0)

    def test_missing_or_reset_port_counters_remain_unavailable(self):
        before = {"timestamp": 10, "switches": {"s1": {1: {"rx_bytes": 100, "tx_bytes": 100}}}}
        after = {"timestamp": 11, "switches": {"s1": {1: {"rx_bytes": 50, "tx_bytes": 200}}}}
        result = LIVE.calculate_link_utilization(before, after, 100)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["links"][0]["rx_mbps"])
        self.assertIsNone(result["links"][1]["rx_mbps"])

    def test_cost_uses_latency_jitter_and_packet_loss(self):
        base = LIVE.summarize_samples(samples([10, 11, 10, 11, 10]))
        slower = LIVE.summarize_samples(samples([15, 16, 15, 16, 15]))
        jittery = LIVE.summarize_samples(samples([10, 18, 10, 18, 10]))
        self.assertTrue(base["complete"])
        self.assertGreater(slower["cost"], base["cost"])
        self.assertGreater(jittery["cost"], base["cost"])
        lost = samples([10, 11, 10, 11, 10])
        lost[-1]["rtt_ms"] = None
        loss = LIVE.summarize_samples(lost)
        self.assertEqual(loss["packet_loss_pct"], 20)
        self.assertTrue(loss["complete"])
        self.assertGreater(loss["cost"], base["cost"])

    def test_too_few_replies_or_jitter_pairs_is_incomplete(self):
        few = samples([10, 11, 10, 11, 10])
        for i in range(3):
            few[i]["rtt_ms"] = None
        self.assertFalse(LIVE.summarize_samples(few)["complete"])

    def test_scenario_probe_window_can_measure_latency_with_heavy_probe_loss(self):
        probes = [{"timestamp": 1000 + i * 0.1,
                   "rtt_ms": 10 + (i % 2) if i < 20 else None}
                  for i in range(LIVE.SCENARIO_PING_SAMPLES)]
        result = LIVE.summarize_samples(
            probes, expected_samples=LIVE.SCENARIO_PING_SAMPLES)
        self.assertTrue(result["complete"])
        self.assertEqual(result["packet_loss_pct"], 80.0)
        self.assertEqual(result["latency_ms"], 10.5)

    def test_scenario_requires_class_flow_counters_and_expected_queue_actions(self):
        class_config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        lines = []
        for name, profile in class_config["classes"].items():
            lines.append("cookie=0x1, n_packets=12, n_bytes=1200, priority=300,udp,in_port=1,"
                         "nw_src=10.0.0.1,nw_dst=10.0.0.2,tp_dst={},"
                         "actions=set_queue:{},output:2".format(
                             profile["udp_port"], profile["queue_id"]))
        result = LIVE.parse_scenario_flow_usage("\n".join(lines), class_config, True)
        self.assertTrue(result["complete"])
        for name in class_config["classes"]:
            self.assertEqual(result["classes"][name]["packets"], 12)
            self.assertTrue(result["classes"][name]["complete"])

        no_hits = LIVE.parse_scenario_flow_usage(
            "\n".join(line.replace("n_packets=12", "n_packets=0") for line in lines),
            class_config, True)
        self.assertFalse(no_hits["complete"])

        unprioritized = LIVE.parse_scenario_flow_usage(
            "\n".join(line.replace("actions=set_queue:{},".format(profile["queue_id"]),
                             "actions=")
                      for line, profile in zip(lines, class_config["classes"].values())),
            class_config, False)
        self.assertTrue(unprioritized["complete"])

    def test_shortcut_decision_uses_composite_cost_and_incomplete_is_inconclusive(self):
        def stage(values):
            metric = LIVE.summarize_samples(samples(values))
            return {"valid_count": 5, "samples": samples(values), "metrics": metric}
        now = 1004
        baseline = stage([10, 11, 10, 11, 10])
        harmful = stage([20, 21, 20, 21, 20])
        self.assertEqual(LIVE.classify(baseline, harmful, now)["verdict"], "harmful")
        harmful["metrics"] = {"complete": False, "cost": None}
        self.assertEqual(LIVE.classify(baseline, harmful, now)["verdict"], "inconclusive")

    def test_route_decision_rejects_incomplete_fresh_pair_measurement(self):
        baseline_samples = samples([10, 11, 10, 11, 10])
        shortcut_samples = samples([20, 21, 20, 21, 20])
        baseline = {"valid_count": 5, "samples": baseline_samples,
                    "metrics": LIVE.summarize_samples(baseline_samples),
                    "decision_probe": {"complete": False}}
        shortcut = {"valid_count": 5, "samples": shortcut_samples,
                    "metrics": LIVE.summarize_samples(shortcut_samples),
                    "decision_probe": {"complete": True}}
        self.assertEqual(LIVE.classify(baseline, shortcut, 1004)["verdict"], "inconclusive")

    def test_paired_route_decisions_cover_harmful_beneficial_and_neutral(self):
        def stage(values):
            probe_samples = samples(values)
            return {"valid_count": 5, "samples": probe_samples,
                    "metrics": LIVE.summarize_samples(probe_samples),
                    "decision_probe": {"complete": True}}
        baseline = stage([10, 11, 10, 11, 10])
        self.assertEqual(LIVE.classify(baseline, stage([20, 21, 20, 21, 20]), 1004)["verdict"], "harmful")
        self.assertEqual(LIVE.classify(baseline, stage([5, 6, 5, 6, 5]), 1004)["verdict"], "beneficial")
        self.assertEqual(LIVE.classify(baseline, stage([10.2, 11.2, 10.2, 11.2, 10.2]), 1004)["verdict"], "neutral")

    def test_harmful_shortcut_prevention_requires_measured_baseline_forwarding(self):
        self.assertTrue(LIVE.harmful_shortcut_prevented(
            "harmful", "baseline", True, True, True))
        self.assertFalse(LIVE.harmful_shortcut_prevented(
            "harmful", "shortcut", True, True, True))
        self.assertFalse(LIVE.harmful_shortcut_prevented(
            "harmful", "baseline", False, True, True))
        self.assertFalse(LIVE.harmful_shortcut_prevented(
            "harmful", "baseline", True, False, True))
        self.assertFalse(LIVE.harmful_shortcut_prevented(
            "harmful", "baseline", True, True, False))

    def test_completion_accepts_saved_stage_and_paired_measurement_shapes(self):
        self.assertTrue(LIVE.stage_measurement_complete(
            {"complete": True, "metrics": {"complete": True}}))
        self.assertTrue(LIVE.stage_measurement_complete(
            {"metrics": {"complete": True}}))
        self.assertFalse(LIVE.stage_measurement_complete(
            {"metrics": {"complete": False}}))
        self.assertFalse(LIVE.stage_measurement_complete({}))

    def test_scenario_statistics_use_saved_repetition_values_and_report_sample_stddev(self):
        rows = []
        for value in (1.0, 2.0, 3.0):
            rows.append({"per_class_metrics": {"ECG": {
                "complete": True,
                "metrics": {"latency_ms": value, "jitter_ms": value + 1,
                            "packet_loss_pct": 0.0},
                "throughput_mbps": value + 2}}})
        class_config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        result = LIVE.summarize_scenario_repetitions(rows, class_config)
        latency = result["classes"]["ECG"]["latency_ms"]
        self.assertEqual(latency["n"], 3)
        self.assertEqual(latency["mean"], 2.0)
        self.assertEqual(latency["standard_deviation"], 1.0)
        self.assertTrue(latency["complete"])


if __name__ == "__main__":
    unittest.main()
