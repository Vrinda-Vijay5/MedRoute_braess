"""Pure helpers for deterministic MedRoute class rules and OVS HTB queues."""
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLASS_NAMES = ("ECG", "ICU", "WEARABLE", "BACKGROUND")
UNKNOWN_CLASS = "BACKGROUND"
DEFAULT_ROUTE_PRIORITY = 100
DSCP_RULE_PRIORITY = 200
PORT_RULE_PRIORITY = 300


def load_classes(path=None):
    with open(path or ROOT / "classes.json", encoding="utf-8") as stream:
        config = json.load(stream)
    validate_classes(config)
    return config


def validate_classes(config):
    classes = config.get("classes", {})
    if set(classes) != set(CLASS_NAMES):
        raise ValueError("classes must define ECG, ICU, WEARABLE, and BACKGROUND exactly")
    if config.get("classification", {}).get("unknown_class") != UNKNOWN_CLASS:
        raise ValueError("unknown traffic must use the conservative BACKGROUND class")
    capacity = config.get("link_capacity_mbps")
    if not isinstance(capacity, (int, float)) or capacity <= 0:
        raise ValueError("link_capacity_mbps must be positive")
    seen_ports, seen_dscp, seen_queues = set(), set(), set()
    minimum_total = 0
    for name in CLASS_NAMES:
        profile = classes[name]
        for key, low, high in (("dscp", 0, 63), ("tcp_port", 1, 65535),
                                ("udp_port", 1, 65535), ("queue_id", 1, 65535)):
            value = profile.get(key)
            if not isinstance(value, int) or not low <= value <= high:
                raise ValueError("{}.{} is outside its valid range".format(name, key))
        if profile["tcp_port"] in seen_ports or profile["udp_port"] in seen_ports:
            raise ValueError("transport service ports must be unique across classes")
        if profile["dscp"] in seen_dscp:
            raise ValueError("DSCP values must be unique across classes")
        if profile["queue_id"] in seen_queues:
            raise ValueError("queue IDs must be unique")
        seen_ports.update((profile["tcp_port"], profile["udp_port"]))
        seen_dscp.add(profile["dscp"])
        seen_queues.add(profile["queue_id"])
        minimum = profile.get("min_rate_mbps")
        maximum = profile.get("max_rate_mbps")
        if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
            raise ValueError("{} requires numeric min_rate_mbps and max_rate_mbps".format(name))
        if minimum <= 0 or maximum < minimum or maximum > capacity:
            raise ValueError("{} has invalid HTB rate bounds".format(name))
        minimum_total += minimum
        for key in ("latency_sensitivity", "loss_sensitivity"):
            value = profile.get(key)
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError("{}.{} must be between 0 and 1".format(name, key))
    if minimum_total > capacity:
        raise ValueError("sum of class minimum rates exceeds link capacity")
    if seen_queues != set(range(1, len(CLASS_NAMES) + 1)):
        raise ValueError("queue IDs must be the contiguous criticality order 1 through 4")
    return True


def _route_match(dpid, in_port, src, dst):
    return {"eth_type": 0x0800, "ipv4_src": src, "ipv4_dst": dst,
            "in_port": in_port}


def flow_specs(route_rows, config):
    """Create deterministic route/class rule specs consumed by the Ryu app.

    Service-port rules outrank DSCP rules. Any routed packet unmatched by either
    classifier is explicitly sent through the BACKGROUND queue.
    """
    classes = config["classes"]
    background_queue = classes[UNKNOWN_CLASS]["queue_id"]
    specs = []
    for dpid, in_port, out_port, src, dst in route_rows:
        base_match = _route_match(dpid, in_port, src, dst)
        specs.append({"dpid": dpid, "priority": DEFAULT_ROUTE_PRIORITY,
                      "match": base_match, "queue_id": background_queue,
                      "out_port": out_port, "traffic_class": UNKNOWN_CLASS,
                      "classifier": "default"})
        for name in CLASS_NAMES:
            profile = classes[name]
            class_rank = len(CLASS_NAMES) - profile["queue_id"]
            specs.append({"dpid": dpid, "priority": DSCP_RULE_PRIORITY + class_rank,
                          "match": {**base_match, "ip_dscp": profile["dscp"]},
                          "queue_id": profile["queue_id"], "out_port": out_port,
                          "traffic_class": name, "classifier": "dscp"})
            for protocol, port_key, proto_number in (("tcp", "tcp_port", 6),
                                                     ("udp", "udp_port", 17)):
                for field in (protocol + "_src", protocol + "_dst"):
                    specs.append({"dpid": dpid,
                                  "priority": PORT_RULE_PRIORITY + class_rank,
                                  "match": {**base_match, "ip_proto": proto_number,
                                            field: profile[port_key]},
                                  "queue_id": profile["queue_id"], "out_port": out_port,
                                  "traffic_class": name, "classifier": "transport_port"})
    return specs


def flow_action_specs(spec, qos_enabled=True):
    """Describe output actions, omitting set_queue for no-priority experiments."""
    actions = []
    if qos_enabled:
        actions.append(("set_queue", spec["queue_id"]))
    actions.append(("output", spec["out_port"]))
    return actions


def queue_command(port_name, config, capacity_override_mbps=None):
    """Build attached HTB queues, optionally scaling rates for a test bottleneck."""
    base_capacity = config["link_capacity_mbps"]
    capacity_mbps = (base_capacity if capacity_override_mbps is None
                     else capacity_override_mbps)
    if (not isinstance(capacity_mbps, (int, float)) or capacity_mbps <= 0 or
            capacity_mbps > base_capacity):
        raise ValueError("HTB capacity override must be positive and no greater than the link rate")
    rate_scale = capacity_mbps / base_capacity
    capacity_bps = int(capacity_mbps * 1_000_000)
    command = ["ovs-vsctl"]
    refs = []
    # Flows in the no-prioritization scenario intentionally omit set_queue.
    # OVS sends those packets through queue 0, so configure that default queue
    # too; otherwise the experiment's shared egress cap is not applied equally
    # to the no-priority and per-class-priority scenarios.
    default_ref = "@q0"
    command.extend(("--", "--id=" + default_ref, "create", "Queue",
                    "other-config:min-rate=0",
                    "other-config:max-rate={}".format(capacity_bps),
                    "other-config:priority={}".format(len(CLASS_NAMES))))
    refs.append((0, default_ref))
    for name in CLASS_NAMES:
        profile = config["classes"][name]
        ref = "@q{}".format(profile["queue_id"])
        refs.append((profile["queue_id"], ref))
        command.extend(("--", "--id=" + ref, "create", "Queue",
                        "other-config:min-rate={}".format(int(profile["min_rate_mbps"] * rate_scale * 1_000_000)),
                        "other-config:max-rate={}".format(int(profile["max_rate_mbps"] * rate_scale * 1_000_000)),
                        "other-config:priority={}".format(profile["queue_id"] - 1)))
    command.extend(("--", "--id=@medroute_qos", "create", "QoS", "type=linux-htb",
                    "other-config:max-rate={}".format(capacity_bps)))
    command.extend("queues:{}={}".format(queue_id, ref) for queue_id, ref in refs)
    command.extend(("--", "set", "Port", port_name, "qos=@medroute_qos"))
    return command


def configure_switch_queues(switch_name, config, runner=None):
    """Attach HTB queues to every current OVS interface on one experiment switch."""
    validate_classes(config)
    run = runner or subprocess.run
    listed = run(["ovs-vsctl", "list-ports", switch_name], capture_output=True,
                 text=True, check=True)
    ports = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    if not ports:
        raise RuntimeError("no OVS ports found for {} while attaching class queues".format(switch_name))
    for port_name in ports:
        run(queue_command(port_name, config), capture_output=True, text=True, check=True)
    return {"switch": switch_name, "ports": ports,
            "queues": {name: config["classes"][name]["queue_id"] for name in CLASS_NAMES}}
