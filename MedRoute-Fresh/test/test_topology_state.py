import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdn"))
from topology_state import TopologyState


class TopologyStateTests(unittest.TestCase):
    def test_duplicate_and_stale_events_do_not_restore_failed_link(self):
        state = TopologyState(clock=lambda: 20)
        state.switch_up(1, 1); state.switch_up(2, 2)
        state.link_up(1, 2, 3, 4, timestamp=10)
        state.link_down(1, 2, 3, 4, timestamp=15)
        self.assertFalse(state.link_up(1, 2, 3, 4, timestamp=14))
        self.assertEqual(state.snapshot()["links"][0]["status"], "down")

    def test_switch_failure_invalidates_attached_edges_and_host_attachment(self):
        state = TopologyState()
        state.switch_up(1, 1); state.switch_up(2, 2); state.link_up(1, 2, 1, 1, timestamp=3)
        state.host_seen("aa:bb", 1, 5, timestamp=4); state.switch_down(1, timestamp=5)
        graph = state.snapshot()
        self.assertEqual(graph["links"][0]["status"], "down")
        self.assertEqual(graph["hosts"][0]["switch"], "1")

    def test_simultaneous_link_and_switch_failure_reports_partition_then_rejoins(self):
        state = TopologyState()
        for switch in (1, 2, 3, 4): state.switch_up(switch, switch)
        state.link_up(1, 2, timestamp=5); state.link_up(2, 4, timestamp=6)
        state.link_up(1, 3, timestamp=7); state.link_up(3, 4, timestamp=8)
        self.assertEqual(state.usable_path(1, 4), ["1", "2", "4"])
        state.link_down(1, 2, timestamp=9); state.switch_down(3, timestamp=10)
        self.assertIsNone(state.usable_path(1, 4))
        state.switch_up(3, timestamp=11); state.link_up(1, 3, timestamp=12); state.link_up(3, 4, timestamp=13)
        self.assertEqual(state.usable_path(1, 4), ["1", "3", "4"])

    def test_usable_path_ignores_down_switches_and_edges(self):
        state = TopologyState()
        state.switch_up("a", 1); state.switch_up("b", 2); state.switch_up("c", 3)
        state.link_up("a", "b", timestamp=4); state.link_up("b", "c", timestamp=5)
        self.assertEqual(state.usable_path("a", "c"), ["a", "b", "c"])
        state.switch_down("b", timestamp=6)
        self.assertIsNone(state.usable_path("a", "c"))
