import importlib.util
import json
import pathlib
import unittest
from unittest.mock import MagicMock, patch

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
        decision = LIVE.classify(baseline, harmful, now)
        self.assertEqual(decision["verdict"], "harmful")
        self.assertEqual(
            decision["structured_evaluation"]["route_installation_verification_status"],
            "pending_controller_action")
        self.assertEqual(
            decision["structured_evaluation"]["fairness"]["reason"],
            "aggregate_route_probe_has_no_per_class_throughput")
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

    def test_repeated_decision_summary_does_not_mask_later_harmful_candidate(self):
        trials = [
            {"repetition": 1, "complete": True, "decision": {
                "verdict": "neutral", "controller_recorded": True,
                "route_selection_verified": True, "prevention_verified": False}},
            {"repetition": 2, "complete": True, "decision": {
                "verdict": "harmful", "controller_recorded": True,
                "route_selection_verified": True, "prevention_verified": True}},
        ]
        summary = LIVE.summarize_repeated_decisions(trials)
        self.assertEqual(summary["live_experiment"], "harmful_shortcut_prevented")
        self.assertEqual(summary["harmful_candidate_count"], 1)
        self.assertEqual(summary["prevention_verified_count"], 1)
        self.assertEqual(summary["aggregate_verdict"], "mixed")
        trials[1]["decision"]["prevention_verified"] = False
        failed = LIVE.summarize_repeated_decisions(trials)
        self.assertEqual(failed["live_experiment"], "prevention_failed")
        self.assertFalse(failed["passed"])

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

    def test_tail_percentiles_use_nearest_rank_and_lost_probes_miss_deadline(self):
        class_config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        rows = [{"per_class_metrics": {"ECG": {
            "ping_samples": [{"rtt_ms": float(i)} for i in range(1, 100)] +
                            [{"rtt_ms": None}],
            "metrics": {"packet_loss_pct": 0.0}, "throughput_mbps": 1.0}}}]
        result = LIVE.summarize_scenario_repetitions(rows, class_config)
        tail = result["classes"]["ECG"]["tail_latency"]
        self.assertEqual((tail["p95_ms"], tail["p99_ms"]), (95.0, 99.0))
        self.assertEqual(tail["probe_count"], 100)
        self.assertEqual(tail["deadline_miss_count"], 1)  # The lost probe is a miss.
        self.assertEqual(tail["deadline_miss_rate_pct"], 1.0)

        rows[0]["per_class_metrics"]["ECG"]["ping_samples"] = [
            {"rtt_ms": None}, {"rtt_ms": None}]
        result = LIVE.summarize_scenario_repetitions(rows, class_config)
        tail = result["classes"]["ECG"]["tail_latency"]
        self.assertIsNone(tail["p95_ms"])
        self.assertEqual(tail["deadline_miss_count"], 2)
        self.assertEqual(tail["deadline_miss_rate_pct"], 100.0)

    def test_loss_and_reliability_objectives_are_unavailable_when_a_repetition_is_missing(self):
        class_config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        rows = [
            {"per_class_metrics": {"ECG": {"metrics": {"packet_loss_pct": 0.0}, "throughput_mbps": 1.0}}},
            {"per_class_metrics": {"ECG": {"metrics": {"packet_loss_pct": None}, "throughput_mbps": 1.0}}},
        ]
        result = LIVE.summarize_scenario_repetitions(rows, class_config)
        tail = result["classes"]["ECG"]["tail_latency"]
        self.assertIsNone(tail["receiver_delivery_reliability_pct"])
        self.assertIsNone(tail["packet_loss_target_met"])
        self.assertIsNone(tail["reliability_target_met"])

    def test_fairness_requires_all_class_throughputs_and_handles_zero_total(self):
        class_config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        rows = [{"per_class_metrics": {name: {"throughput_mbps": 1.0}
                                        for name in class_config["classes"]}}]
        result = LIVE.summarize_scenario_repetitions(rows, class_config)
        self.assertEqual(result["throughput_fairness"]["jain_index"], 1.0)
        del rows[0]["per_class_metrics"]["BACKGROUND"]
        result = LIVE.summarize_scenario_repetitions(rows, class_config)
        self.assertIsNone(result["throughput_fairness"]["jain_index"])
        self.assertFalse(result["throughput_fairness"]["complete"])
        rows[0]["per_class_metrics"]["BACKGROUND"] = {"throughput_mbps": 0.0}
        for name in class_config["classes"]:
            rows[0]["per_class_metrics"][name]["throughput_mbps"] = 0.0
        result = LIVE.summarize_scenario_repetitions(rows, class_config)
        self.assertIsNone(result["throughput_fairness"]["jain_index"])
        self.assertEqual(result["throughput_fairness"]["unavailable_reason"],
                         "total_throughput_is_zero")

    def test_telemetry_summary_distinguishes_required_and_optional_metrics(self):
        records = {
            "baseline": {"metrics": {"complete": True}},
            "shortcut": {"metrics": {"complete": True}},
            "prevention": {"metrics": {"complete": True}},
        }
        scenario_statistics = {
            "normal": {"throughput_fairness": {"complete": True}},
        }
        scenario_repetitions = {
            "normal": [{"queue_occupancy": {"complete": True}}],
        }
        result = LIVE.summarize_telemetry_completeness(
            records.values(), scenario_statistics, scenario_repetitions,
            [{"fairness": {"status": "unavailable"}}])
        self.assertTrue(result["required_telemetry_complete"])
        self.assertFalse(result["optional_telemetry"]["candidate_evaluation_fairness"])
        self.assertTrue(result["optional_telemetry"]["scenario_throughput_fairness"])
        self.assertFalse(result["optional_telemetry_complete"])
        self.assertFalse(result["all_telemetry_complete"])

    def test_telemetry_summary_requires_optional_metrics_when_applicable(self):
        records = {"baseline": {"metrics": {"complete": True}}}
        result = LIVE.summarize_telemetry_completeness(
            records.values(), {}, {}, [])
        self.assertTrue(result["required_telemetry_complete"])
        self.assertFalse(result["optional_telemetry_complete"])
        self.assertFalse(result["all_telemetry_complete"])


    def test_required_telemetry_rejects_missing_or_incomplete_stages(self):
        scenarios = {}
        repetitions = {}

        missing = LIVE.summarize_telemetry_completeness(
            [], scenarios, repetitions)
        self.assertFalse(missing["required_telemetry_complete"])

        incomplete = LIVE.summarize_telemetry_completeness(
            [{"complete": False, "metrics": {"complete": False}}],
            scenarios, repetitions)
        self.assertFalse(incomplete["required_telemetry_complete"])

        complete = LIVE.summarize_telemetry_completeness(
            [{"complete": True, "metrics": None}],
            scenarios, repetitions)
        self.assertTrue(complete["required_telemetry_complete"])

    def test_repeated_decisions_reject_incomplete_harmful_prevention(self):
        trials = [{
            "repetition": 1,
            "complete": True,
            "decision": {
                "verdict": "harmful",
                "controller_recorded": True,
                "route_selection_verified": True,
                "prevention_verified": False,
            },
        }]

        summary = LIVE.summarize_repeated_decisions(trials)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["harmful_candidate_count"], 1)
        self.assertEqual(summary["prevention_verified_count"], 0)
        self.assertEqual(summary["live_experiment"], "prevention_failed")

    def test_full_route_verification_accepts_all_saved_modes(self):
        routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))
        for mode, rows in routes.items():
            flows = []
            for dpid, in_port, out_port, source, destination in rows:
                flows.append(LIVE.parse_openflow_flow_line(
                    "cookie=0x{:016x}, priority=100,ip,dl_type=0x0800,".format(LIVE.MEDROUTE_COOKIE) +
                    "nw_src={},nw_dst={},in_port={} actions=output:{}".format(
                        source, destination, in_port, out_port), "s{}".format(dpid)))
            result = LIVE._expected_route_evidence(flows, mode, routes)
            self.assertTrue(result["verified"], mode)
            self.assertEqual(len(result["matched_rules"]), len(rows))

    def test_full_route_verification_fails_closed_for_missing_wrong_and_ambiguous_rules(self):
        routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))
        rows = routes["baseline"]

        def fixture(row, out=None, source=None, in_port=None):
            dpid, original_in, original_out, original_source, destination = row
            return LIVE.parse_openflow_flow_line(
                "cookie=0x{:016x}, priority=100,ip,dl_type=0x0800,nw_src={},".format(
                    LIVE.MEDROUTE_COOKIE, source or original_source) +
                "nw_dst={},in_port={} actions=output:{}".format(
                    destination,
                    original_in if in_port is None else in_port,
                    original_out if out is None else out), "s{}".format(dpid))

        base = [fixture(row) for row in rows]
        self.assertTrue(LIVE._expected_route_evidence(base, "baseline", routes)["verified"])
        self.assertFalse(LIVE._expected_route_evidence(base[:-1], "baseline", routes)["verified"])
        self.assertFalse(LIVE._expected_route_evidence(
            [fixture(rows[0], in_port=99)] + base[1:], "baseline", routes)["verified"])
        self.assertFalse(LIVE._expected_route_evidence(
            [fixture(rows[0], out=99)] + base[1:], "baseline", routes)["verified"])
        self.assertFalse(LIVE._expected_route_evidence(
            [fixture(rows[0], source="10.0.0.99")] + base[1:],
            "baseline", routes)["verified"])
        ambiguous = base + [base[0].copy()]
        self.assertFalse(LIVE._expected_route_evidence(
            ambiguous, "baseline", routes)["verified"])

    def test_route_verification_rejects_owned_extras_priority_and_extra_outputs(self):
        routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))

        def flow(row, priority=100, output=None, cookie=None, extra_output=None):
            dpid, in_port, out_port, source, destination = row
            selected_output = out_port if output is None else output
            outputs = str(selected_output)
            if extra_output is not None:
                outputs += ",output:{}".format(extra_output)
            return LIVE.parse_openflow_flow_line(
                "cookie=0x{:016x}, priority={},ip,nw_src={},nw_dst={},in_port={} "
                "actions=output:{}".format(
                    LIVE.MEDROUTE_COOKIE if cookie is None else cookie,
                    priority, source, destination, in_port, outputs),
                "s{}".format(dpid))

        baseline = [flow(row) for row in routes["baseline"]]
        extra = flow(routes["alternate"][0])
        result = LIVE._expected_route_evidence(baseline + [extra], "baseline", routes)
        self.assertFalse(result["verified"])
        self.assertEqual(len(result["unexpected_rules"]), 1)

        wrong_priority = [flow(routes["baseline"][0], priority=101)] + baseline[1:]
        result = LIVE._expected_route_evidence(wrong_priority, "baseline", routes)
        self.assertFalse(result["verified"])
        self.assertEqual(len(result["missing_rules"]), 1)
        self.assertEqual(len(result["unexpected_rules"]), 1)

        extra_output = [flow(routes["baseline"][0], extra_output=99)] + baseline[1:]
        result = LIVE._expected_route_evidence(extra_output, "baseline", routes)
        self.assertFalse(result["verified"])
        self.assertEqual(len(result["missing_rules"]), 1)
        self.assertEqual(len(result["unexpected_rules"]), 1)

        duplicate = baseline + [baseline[0]]
        result = LIVE._expected_route_evidence(duplicate, "baseline", routes)
        self.assertFalse(result["verified"])
        self.assertEqual(len(result["ambiguous_rules"]), 1)

        lldp = LIVE.parse_openflow_flow_line(
            "cookie=0x0, priority=50,dl_dst=01:80:c2:00:00:0e actions=output:LOCAL", "s1")
        self.assertIsNotNone(lldp)
        self.assertTrue(LIVE._expected_route_evidence(
            baseline + [lldp], "baseline", routes)["verified"])

    def test_class_queue_verification_requires_actual_class_match_and_queue_action(self):
        routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))
        config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        flows = []
        for spec in LIVE.flow_specs(routes["baseline"], config):
            match = spec["match"]
            tokens = ["cookie=0x1", "priority={}".format(spec["priority"]),
                      "ip", "dl_type=0x0800", "nw_src={}".format(match["ipv4_src"]),
                      "nw_dst={}".format(match["ipv4_dst"]),
                      "in_port={}".format(match["in_port"])]
            if "ip_dscp" in match:
                tokens.append("nw_tos=0x{:x}/0xfc".format(match["ip_dscp"] << 2))
            if "ip_proto" in match:
                tokens.append("ip_proto={}".format(match["ip_proto"]))
            for key in ("tcp_src", "tcp_dst", "udp_src", "udp_dst"):
                if key in match:
                    tokens.append("tp_{}={}".format(key.split("_", 1)[1], match[key]))
            flows.append(LIVE.parse_openflow_flow_line(
                ",".join(tokens) + " actions=set_queue:{},output:{}".format(
                    spec["queue_id"], spec["out_port"]), "s{}".format(spec["dpid"])))
        result = LIVE._class_queue_evidence(flows, "baseline", routes, config)
        self.assertTrue(result["verified"])
        self.assertEqual(result["missing_rules"], [])
        wrong_queue = [dict(flow, queues=list(flow["queues"])) for flow in flows]
        wrong_queue[1]["queues"] = [99]
        self.assertFalse(LIVE._class_queue_evidence(
            wrong_queue, "baseline", routes, config)["verified"])
        self.assertFalse(LIVE._class_queue_evidence(
            flows[2:], "baseline", routes, config)["verified"])

    def test_parser_matches_real_ovs_protocol_tokens_and_action_order(self):
        routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))
        config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        specs = LIVE.flow_specs(routes["baseline"], config)
        tcp_src_spec = next(spec for spec in specs
                            if spec["dpid"] == 2 and spec["classifier"] == "transport_port"
                            and "tcp_src" in spec["match"])
        tcp_dst_spec = next(spec for spec in specs
                            if spec["dpid"] == 2 and spec["classifier"] == "transport_port"
                            and "tcp_dst" in spec["match"])
        udp_src_spec = next(spec for spec in specs
                            if spec["dpid"] == 2 and spec["classifier"] == "transport_port"
                            and "udp_src" in spec["match"])
        udp_dst_spec = next(spec for spec in specs
                            if spec["dpid"] == 2 and spec["classifier"] == "transport_port"
                            and "udp_dst" in spec["match"])
        dscp_spec = next(spec for spec in specs
                         if spec["dpid"] == 2 and spec["classifier"] == "dscp")
        tcp_src = LIVE.parse_openflow_flow_line(
            "priority=303,tcp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=set_queue:1,output:2", "s2")
        tcp_dst = LIVE.parse_openflow_flow_line(
            "priority=303,tcp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_dst=5101 actions=set_queue:1,output:2", "s2")
        udp_src = LIVE.parse_openflow_flow_line(
            "priority=303,udp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=set_queue:1,output:2", "s2")
        udp_dst = LIVE.parse_openflow_flow_line(
            "priority=303,udp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_dst=5101 actions=set_queue:1,output:2", "s2")
        dscp = LIVE.parse_openflow_flow_line(
            "priority=203,ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "nw_tos=184 actions=set_queue:1,output:2", "s2")
        default = LIVE.parse_openflow_flow_line(
            "priority=100,ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "actions=set_queue:4,output:2", "s2")

        self.assertIsNone(tcp_src["eth_type"])
        self.assertEqual((tcp_src["ip_proto"], tcp_src["tcp_src"]), (6, 5101))
        self.assertIsNone(tcp_src["udp_src"])
        self.assertEqual((tcp_dst["ip_proto"], tcp_dst["tcp_dst"]), (6, 5101))
        self.assertEqual((udp_src["ip_proto"], udp_src["udp_src"]), (17, 5101))
        self.assertEqual((udp_dst["ip_proto"], udp_dst["udp_dst"]), (17, 5101))
        self.assertEqual(dscp["ip_dscp"], 46)
        self.assertTrue(default["default_route_rule"])
        for flow, spec in ((tcp_src, tcp_src_spec), (tcp_dst, tcp_dst_spec),
                           (udp_src, udp_src_spec), (udp_dst, udp_dst_spec),
                           (dscp, dscp_spec)):
            self.assertTrue(LIVE._flow_matches_spec(flow, spec))

        missing_protocol = LIVE.parse_openflow_flow_line(
            "priority=303,ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=set_queue:1,output:2", "s2")
        wrong_protocol = LIVE.parse_openflow_flow_line(
            "priority=303,udp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=set_queue:1,output:2", "s2")
        wrong_queue = LIVE.parse_openflow_flow_line(
            "priority=303,tcp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=set_queue:2,output:2", "s2")
        wrong_output = LIVE.parse_openflow_flow_line(
            "priority=303,tcp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=set_queue:1,output:3", "s2")
        wrong_switch = LIVE.parse_openflow_flow_line(
            "priority=303,tcp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=set_queue:1,output:2", "s3")
        reversed_actions = LIVE.parse_openflow_flow_line(
            "priority=303,tcp,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2,"
            "tp_src=5101 actions=output:2,set_queue:1", "s2")
        self.assertIsNone(missing_protocol["ip_proto"])
        self.assertFalse(LIVE._flow_matches_spec(missing_protocol, tcp_src_spec))
        self.assertFalse(LIVE._flow_matches_spec(wrong_protocol, tcp_src_spec))
        self.assertFalse(LIVE._flow_matches_spec(wrong_queue, tcp_src_spec))
        self.assertFalse(LIVE._flow_matches_spec(wrong_output, tcp_src_spec))
        self.assertFalse(LIVE._flow_matches_spec(wrong_switch, tcp_src_spec))
        self.assertFalse(LIVE._flow_matches_spec(reversed_actions, tcp_src_spec))
        self.assertIsNone(LIVE.parse_openflow_flow_line(
            "priority=303,tcp,in_port=1,nw_src=10.0.0.1"))

        ipv6 = LIVE.parse_openflow_flow_line("priority=10,ipv6 actions=output:1", "s1")
        icmp = LIVE.parse_openflow_flow_line("priority=10,icmp actions=output:1", "s1")
        self.assertEqual(ipv6["eth_type"], 0x86DD)
        self.assertEqual(icmp["ip_proto"], 1)

    def test_m3_expected_route_minimum_ties_and_incomplete_fallback(self):
        routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))

        def row(mode, value, complete=True):
            links = [{"switch": "s{}".format(dpid), "port": out,
                      "complete": complete, "tx_utilization_pct": value}
                     for dpid, _in, out, src, dst in routes[mode]
                     if src == "10.0.0.1" and dst == "10.0.0.2"]
            return {"mode": mode, "complete": complete,
                    "path_link_utilization": {"complete": complete, "links": links}}

        result = LIVE.derive_expected_congestion_route(
            [row("baseline", 20), row("alternate", 10), row("shortcut", 30)], routes)
        self.assertEqual(result["selected_route"], "alternate")
        tie = LIVE.derive_expected_congestion_route(
            [row("baseline", 10), row("alternate", 10), row("shortcut", 20)], routes)
        self.assertEqual(tie["selected_route"], "alternate")
        incomplete = LIVE.derive_expected_congestion_route(
            [row("baseline", 10), row("alternate", 10, False), row("shortcut", 20)], routes)
        self.assertEqual(incomplete["selected_route"], "baseline")
        self.assertFalse(incomplete["complete"])
        self.assertFalse(LIVE.route_selection_matches(
            {"selected_route": "alternate"}, "baseline"))

    def test_braess_expected_route_mapping_is_independent(self):
        self.assertEqual(LIVE.expected_braess_route({"verdict": "harmful"}), "baseline")
        self.assertEqual(LIVE.expected_braess_route({"verdict": "beneficial"}), "shortcut")
        self.assertEqual(LIVE.expected_braess_route({
            "verdict": "neutral", "structured_evaluation": {
                "decision": "accept_candidate"}}), "shortcut")
        self.assertEqual(LIVE.expected_braess_route({"verdict": "inconclusive"}), "baseline")

    def test_prevention_requires_full_forwarding_and_controller_recording(self):
        self.assertTrue(LIVE.harmful_shortcut_prevented(
            "harmful", "baseline", True, True, True))
        self.assertFalse(LIVE.harmful_shortcut_prevented(
            "harmful", "baseline", True, True, False))
        self.assertFalse(LIVE.harmful_shortcut_prevented(
            "harmful", "baseline", True, False, True))

    def _guard_policy(self):
        return json.loads((ROOT / "config" / "healthcare_qos.json").read_text(
            encoding="utf-8"))

    def _guard_evaluation(self, overrides=None, classification="beneficial",
                          decision="accept_candidate"):
        policy = self._guard_policy()
        evaluations = {
            name: {"classification": "beneficial", "relative_change": -0.10,
                   "baseline_cost": 1.0, "candidate_cost": 0.9,
                   "constraint_violations": [], "reason_code": "IMPROVED"}
            for name in policy["classes"]}
        evaluations.update(overrides or {})
        return policy, {
            "classification": classification,
            "decision": decision,
            "reason_code": "WEIGHTED_CBDR_OBJECTIVE_IMPROVEMENT",
            "explanation": "aggregate result",
            "class_evaluations": evaluations,
        }

    def test_critical_guard_rejects_aggregate_benefit_with_emergency_harm(self):
        policy, evaluation = self._guard_evaluation({
            "EMERGENCY_ALARM": {"classification": "harmful",
                                "relative_change": 0.0937,
                                "baseline_cost": 1.0, "candidate_cost": 1.0937,
                                "constraint_violations": []}})
        guarded = LIVE.apply_critical_class_guard(evaluation, policy)
        self.assertEqual(guarded["decision"], "reject_candidate")
        self.assertEqual(guarded["classification"], "harmful")
        self.assertEqual(guarded["reason_code"], "CRITICAL_CLASS_DEGRADATION")
        self.assertEqual(guarded["critical_class_guard"]["triggering_classes"][0][
            "traffic_class"], "EMERGENCY_ALARM")

    def test_critical_guard_rejects_aggregate_benefit_with_icu_harm(self):
        policy, evaluation = self._guard_evaluation({
            "CRITICAL_PHYSIOLOGICAL_TELEMETRY": {
                "classification": "harmful", "relative_change": 0.224,
                "baseline_cost": 1.0, "candidate_cost": 1.224,
                "constraint_violations": []}})
        guarded = LIVE.apply_critical_class_guard(evaluation, policy)
        self.assertEqual(guarded["decision"], "reject_candidate")
        self.assertEqual(guarded["critical_class_guard"]["reason_code"],
                         "CRITICAL_CLASS_DEGRADATION")

    def test_critical_guard_records_both_protected_harms(self):
        policy, evaluation = self._guard_evaluation({
            "EMERGENCY_ALARM": {"classification": "harmful",
                                "relative_change": 0.09,
                                "constraint_violations": []},
            "CRITICAL_PHYSIOLOGICAL_TELEMETRY": {
                "classification": "harmful", "relative_change": 0.22,
                "constraint_violations": []}})
        guarded = LIVE.apply_critical_class_guard(evaluation, policy)
        self.assertEqual([item["traffic_class"] for item in
                          guarded["critical_class_guard"]["triggering_classes"]],
                         ["EMERGENCY_ALARM", "CRITICAL_PHYSIOLOGICAL_TELEMETRY"])

    def test_critical_guard_preserves_beneficial_acceptance_when_protected_classes_are_safe(self):
        policy, evaluation = self._guard_evaluation({
            "EMERGENCY_ALARM": {"classification": "neutral",
                                "relative_change": 0.01,
                                "constraint_violations": []},
            "CRITICAL_PHYSIOLOGICAL_TELEMETRY": {
                "classification": "beneficial", "relative_change": -0.08,
                "constraint_violations": []}})
        guarded = LIVE.apply_critical_class_guard(evaluation, policy)
        self.assertEqual(guarded["decision"], "accept_candidate")
        self.assertFalse(guarded["critical_class_guard"]["triggered"])

    def test_critical_guard_preserves_aggregate_neutral_and_harmful_policy(self):
        policy, neutral = self._guard_evaluation(
            classification="neutral", decision="retain_baseline")
        self.assertEqual(LIVE.apply_critical_class_guard(neutral, policy)["decision"],
                         "retain_baseline")
        policy, harmful = self._guard_evaluation(
            classification="harmful", decision="reject_candidate")
        self.assertEqual(LIVE.apply_critical_class_guard(harmful, policy)["decision"],
                         "reject_candidate")

    def test_critical_guard_rejects_protected_hard_constraint_violation(self):
        policy, evaluation = self._guard_evaluation({
            "EMERGENCY_ALARM": {
                "classification": "constraint_violation",
                "relative_change": 0.02,
                "constraint_violations": [{"metric": "latency_ms", "violated": True}]}})
        guarded = LIVE.apply_critical_class_guard(evaluation, policy)
        self.assertEqual(guarded["classification"], "constraint_violation")
        self.assertEqual(guarded["decision"], "reject_candidate")
        self.assertEqual(guarded["reason_code"],
                         "CRITICAL_CLASS_HARD_CONSTRAINT_VIOLATION")

    def test_critical_guard_disabled_preserves_existing_ablation_behavior(self):
        policy, evaluation = self._guard_evaluation({
            "EMERGENCY_ALARM": {"classification": "harmful",
                                "relative_change": 0.10,
                                "constraint_violations": []}})
        guarded = LIVE.apply_critical_class_guard(evaluation, policy, enabled=False)
        self.assertEqual(guarded["decision"], "accept_candidate")
        self.assertFalse(guarded["critical_class_guard"]["enabled"])

    def test_guarded_decision_is_recorded_and_baseline_is_installed(self):
        policy = self._guard_policy()
        class_names = list(policy["classes"])
        evaluations = {
            name: {"classification": "beneficial", "relative_change": -0.10,
                   "baseline_cost": 1.0, "candidate_cost": 0.9,
                   "constraint_violations": []}
            for name in class_names}
        evaluations["EMERGENCY_ALARM"] = {
            "classification": "harmful", "relative_change": 0.0937,
            "baseline_cost": 1.0, "candidate_cost": 1.0937,
            "constraint_violations": []}
        mock_evaluation = {
            "algorithm": "CBDR", "classification": "beneficial",
            "decision": "accept_candidate",
            "reason_code": "WEIGHTED_CBDR_OBJECTIVE_IMPROVEMENT",
            "explanation": "aggregate improvement",
            "current_objective": 1.2, "candidate_objective": 0.9,
            "relative_change": -0.25, "current_network_cost_pct": 20.0,
            "candidate_network_cost_pct": 15.0,
            "class_evaluations": evaluations,
            "baseline_hard_violations": [], "candidate_hard_violations": []}
        routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))
        class_config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
        traffic_catalog = {"rows": [{"traffic_type": name} for name in (
            "ECG", "ICU", "TELEMEDICINE", "EHR", "IMAGING", "CCTV")]}
        profile_row = {
            "complete": True, "offered_rate_bps": 1_000_000,
            "link_utilization": {"links": []},
            "metrics": {"complete": True, "latency_ms": 15.0,
                        "jitter_ms": 3.0, "packet_loss_pct": 0.0,
                        "throughput_mbps": 1.0, "cost": 1.0}}
        posted = []
        mode_calls = []

        def request(method="GET", value=None, timeout=1, endpoint=LIVE.API):
            if method == "POST" and endpoint == LIVE.DECISION_API:
                posted.append(value)
                return {"recorded": True}
            return {}

        with patch.object(LIVE, "run_catalog_profile_matrix",
                          return_value=[dict(profile_row)]), \
             patch("cbdr.evaluate_class_aware_candidate",
                   return_value=mock_evaluation), \
             patch.object(LIVE, "route_congestion_score", return_value=25.0), \
             patch.object(LIVE, "set_shortcut_link"), \
             patch.object(LIVE, "set_mode",
                          side_effect=lambda mode, reason: mode_calls.append(mode)), \
             patch.object(LIVE, "verify_flows",
                          return_value={"verified": True, "mode": "baseline"}), \
             patch.object(LIVE, "request_json", side_effect=request), \
             patch.object(LIVE, "save_json"):
            record = LIVE.run_cbdr_repetition(
                net=MagicMock(), repetition=1, shortcut_link=MagicMock(),
                evidence_dir=pathlib.Path("."), routes=routes,
                class_config=class_config, traffic_catalog=traffic_catalog,
                qos_enabled=True)

        self.assertEqual(len(posted), 1)
        self.assertEqual(posted[0]["selected_route"], "baseline")
        self.assertEqual(posted[0]["aggregate_classification"], "beneficial")
        self.assertEqual(posted[0]["classification"], "harmful")
        self.assertEqual(posted[0]["reason_code"], "CRITICAL_CLASS_DEGRADATION")
        self.assertEqual(mode_calls[-1], "baseline")
        self.assertEqual(record["decision"]["selected_route"], "baseline")
        self.assertTrue(record["decision"]["controller_recorded"])
        self.assertTrue(record["decision"]["route_selection_verified"])
        self.assertTrue(record["prevention_verified"])


if __name__ == "__main__":
    unittest.main()
