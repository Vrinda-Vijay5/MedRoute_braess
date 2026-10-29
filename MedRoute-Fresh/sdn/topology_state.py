"""Observed SDN topology state with idempotent, ordered event handling.

This module deliberately has no Ryu dependency so its consistency rules can be
unit tested without a controller or Mininet.  Ryu adapters feed it discovered
switch, port, link and host attachment events; simulation graphs never enter it.
"""
import time


class TopologyState:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.switches, self.links, self.hosts = {}, {}, {}
        self.events = []

    @staticmethod
    def _link_key(a, b, a_port=None, b_port=None):
        left, right = (str(a), str(b)) if str(a) <= str(b) else (str(b), str(a))
        ports = (a_port, b_port) if left == str(a) else (b_port, a_port)
        return "%s:%s--%s:%s" % (left, ports[0], right, ports[1])

    def _accept(self, event, timestamp):
        if not isinstance(timestamp, (int, float)):
            timestamp = self.clock()
        previous = self.events[-1]["timestamp"] if self.events else None
        # A delayed event must not resurrect an already newer state.
        if previous is not None and timestamp < previous:
            return False
        self.events.append({"event": event, "timestamp": timestamp})
        self.events = self.events[-200:]
        return True

    def switch_up(self, dpid, timestamp=None):
        key = str(dpid)
        if not self._accept("switch_up", timestamp): return False
        self.switches[key] = {"dpid": key, "status": "up", "observed_at": self.events[-1]["timestamp"]}
        return True

    def switch_down(self, dpid, timestamp=None):
        key = str(dpid)
        if not self._accept("switch_down", timestamp): return False
        if key in self.switches: self.switches[key]["status"] = "down"
        for link in self.links.values():
            if key in (link["source"], link["target"]): link["status"] = "down"
        return True

    def link_up(self, source, target, source_port=None, target_port=None, metrics=None, timestamp=None):
        if not self._accept("link_up", timestamp): return False
        key = self._link_key(source, target, source_port, target_port)
        current = self.links.get(key, {})
        self.links[key] = {**current, "id": key, "source": str(source), "target": str(target),
                           "source_port": source_port, "target_port": target_port, "status": "up",
                           "observed_at": self.events[-1]["timestamp"], "metrics": metrics or current.get("metrics", {})}
        return True

    def link_down(self, source, target, source_port=None, target_port=None, timestamp=None):
        if not self._accept("link_down", timestamp): return False
        key = self._link_key(source, target, source_port, target_port)
        if key in self.links: self.links[key]["status"] = "down"; self.links[key]["observed_at"] = self.events[-1]["timestamp"]
        return True

    def host_seen(self, mac, dpid, port, timestamp=None):
        if not self._accept("host_seen", timestamp): return False
        self.hosts[str(mac)] = {"mac": str(mac), "switch": str(dpid), "port": port,
                                "status": "up", "observed_at": self.events[-1]["timestamp"]}
        return True

    def snapshot(self):
        return {"source": "discovered", "observed_at": self.clock(),
                "switches": sorted(self.switches.values(), key=lambda x: x["dpid"]),
                "links": sorted(self.links.values(), key=lambda x: x["id"]),
                "hosts": sorted(self.hosts.values(), key=lambda x: x["mac"]),
                "recent_events": list(self.events)}

    def usable_path(self, source, target):
        """Return an observed usable switch path, or None for a partition.

        This is deliberately a topology feasibility operation, not a claim that
        the fixed OpenFlow fixture can program arbitrary port mappings.
        """
        source, target = str(source), str(target)
        if self.switches.get(source, {}).get("status") != "up" or self.switches.get(target, {}).get("status") != "up":
            return None
        adjacency = {key: [] for key, value in self.switches.items() if value.get("status") == "up"}
        for link in self.links.values():
            if link.get("status") != "up": continue
            a, b = link["source"], link["target"]
            if a in adjacency and b in adjacency:
                adjacency[a].append(b); adjacency[b].append(a)
        pending, parent = [source], {source: None}
        for node in pending:
            for neighbor in adjacency.get(node, []):
                if neighbor in parent: continue
                parent[neighbor] = node
                if neighbor == target:
                    path = [target]
                    while path[-1] != source: path.append(parent[path[-1]])
                    return list(reversed(path))
                pending.append(neighbor)
        return [source] if source == target else None
