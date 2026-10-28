import importlib.util
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("medroute_qos", ROOT / "sdn" / "qos.py")
QOS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QOS)
CLASSES = QOS.load_classes()
ROUTES = [[2, 1, 2, "10.0.0.1", "10.0.0.2"],
          [2, 2, 1, "10.0.0.2", "10.0.0.1"]]


class QosTests(unittest.TestCase):
    def test_class_profiles_are_unique_and_rates_fit_the_link(self):
        self.assertTrue(QOS.validate_classes(CLASSES))
        invalid = {**CLASSES, "classes": {**CLASSES["classes"],
                  "ICU": {**CLASSES["classes"]["ICU"], "tcp_port": 5101}}}
        with self.assertRaisesRegex(ValueError, "ports must be unique"):
            QOS.validate_classes(invalid)

    def test_rules_cover_service_ports_dscp_and_conservative_default(self):
        rules = QOS.flow_specs(ROUTES, CLASSES)
        self.assertTrue(any(r["classifier"] == "default" and
                            r["queue_id"] == CLASSES["classes"]["BACKGROUND"]["queue_id"]
                            for r in rules))
        self.assertTrue(any(r["classifier"] == "dscp" and
                            r["match"].get("ip_dscp") == 46 and r["queue_id"] == 1
                            for r in rules))
        self.assertTrue(any(r["classifier"] == "transport_port" and
                            r["match"].get("tcp_dst") == 5101 and r["queue_id"] == 1
                            for r in rules))
        self.assertTrue(any(r["classifier"] == "transport_port" and
                            r["match"].get("udp_src") == 5103 and r["queue_id"] == 3
                            for r in rules))
        self.assertGreater(QOS.PORT_RULE_PRIORITY, QOS.DSCP_RULE_PRIORITY)

    def test_qos_toggle_removes_and_restores_set_queue_actions(self):
        spec = next(r for r in QOS.flow_specs(ROUTES, CLASSES)
                    if r["traffic_class"] == "ECG")
        self.assertEqual(QOS.flow_action_specs(spec, True),
                         [("set_queue", 1), ("output", spec["out_port"])])
        self.assertEqual(QOS.flow_action_specs(spec, False),
                         [("output", spec["out_port"])])

    def test_ovs_queue_command_attaches_htb_queues_to_the_interface(self):
        command = QOS.queue_command("s2-eth1", CLASSES)
        joined = " ".join(command)
        self.assertIn("create QoS type=linux-htb", joined)
        self.assertIn("other-config:priority=0", joined)
        self.assertIn("other-config:priority=3", joined)
        self.assertIn("queues:1=@q1", joined)
        self.assertIn("queues:4=@q4", joined)
        self.assertIn("queues:0=@q0", joined)
        self.assertIn("other-config:max-rate=100000000", joined)
        self.assertIn("set Port s2-eth1 qos=@medroute_qos", joined)

    def test_experiment_bottleneck_scales_htb_guarantees_and_caps(self):
        command = QOS.queue_command("s1-eth2", CLASSES, capacity_override_mbps=20)
        joined = " ".join(command)
        self.assertIn("other-config:max-rate=20000000", joined)
        self.assertIn("queues:0=@q0", joined)
        self.assertIn("other-config:max-rate=20000000", joined)
        self.assertIn("other-config:min-rate=4000000", joined)
        self.assertIn("other-config:max-rate=10000000", joined)
        self.assertIn("other-config:min-rate=1000000", joined)
        self.assertIn("other-config:max-rate=4000000", joined)
        with self.assertRaisesRegex(ValueError, "capacity override"):
            QOS.queue_command("s1-eth2", CLASSES, capacity_override_mbps=101)

    def test_switch_configuration_visits_each_discovered_port(self):
        calls = []

        def runner(args, **kwargs):
            calls.append(args)
            output = "s2-eth1\ns2-eth2\n" if args[1:2] == ["list-ports"] else ""
            return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

        result = QOS.configure_switch_queues("s2", CLASSES, runner=runner)
        self.assertEqual(result["ports"], ["s2-eth1", "s2-eth2"])
        self.assertEqual(len(calls), 3)
        self.assertTrue(all("set" in call and "Port" in call for call in calls[1:]))


if __name__ == "__main__":
    unittest.main()
