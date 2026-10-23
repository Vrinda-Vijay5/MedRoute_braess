#!/usr/bin/env python3
"""Owned-resource Mininet/Ryu demonstration using derived CICIoMT workloads."""
import argparse
import json
import math
import os
import re
import signal
import statistics
import subprocess
import sys
import traceback
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ROOT / "sdn") not in sys.path:
    sys.path.insert(0, str(ROOT / "sdn"))
from qos import queue_command
from dataset_workload import build_scenario_workloads, load_profiles, load_traffic_catalog

API = "http://127.0.0.1:8080/medroute/mode"
METRICS_API = "http://127.0.0.1:8080/medroute/metrics"
DECISION_API = "http://127.0.0.1:8080/medroute/decision"
QOS_API = "http://127.0.0.1:8080/medroute/qos"
EXPECTED_DPIDS = [1, 2, 3, 4]
SAMPLES = 5
SCENARIO_PING_SAMPLES = 100
MAX_AGE = 30.0
THRESHOLD = 0.05
SCENARIO_REPETITIONS = 3
SCENARIO_BOTTLENECK_PORT = "s1-eth2"
SCENARIO_BOTTLENECK_CAPACITY_MBPS = 20
SCENARIO_PLAN = {
    "baseline_no_prioritization": {"qos_enabled": False, "heavy_background": False},
    "class_prioritization_no_congestion": {"qos_enabled": True, "heavy_background": False},
    "heavy_background_no_prioritization": {"qos_enabled": False, "heavy_background": True},
    "heavy_background_with_prioritization": {"qos_enabled": True, "heavy_background": True},
}
# Explicit policy references, independent of measured stage values.
COST_REFERENCES = {"latency_ms": 20.0, "jitter_ms": 5.0, "packet_loss_pct": 1.0}


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def diagnostic_command(args):
    """Capture read-only host state when a live run fails."""
    try:
        proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=4)
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as exc:
        return {"error": type(exc).__name__ + ": " + str(exc)}


def request_json(method="GET", value=None, timeout=1, endpoint=API):
    data = None if value is None else json.dumps(value).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, method=method,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_controller(process, timeout=25):
    deadline = time.monotonic() + timeout
    last = "not ready"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Ryu exited during startup")
        try:
            state = request_json(timeout=1)
            if state.get("mode") == "baseline":
                return state
        except urllib.error.HTTPError as exc:
            if exc.code >= 500:
                raise RuntimeError("controller readiness returned HTTP {}".format(exc.code)) from exc
            last = str(exc)
        except Exception as exc:  # readiness polling only
            last = str(exc)
        time.sleep(.25)
    raise TimeoutError("Ryu REST API readiness timeout: " + last)


def wait_switches(timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = request_json(timeout=1)
        if state.get("active_dpids") == EXPECTED_DPIDS:
            return state
        time.sleep(.25)
    raise TimeoutError("expected four connected OVS switches; last state=" + repr(state))


def set_mode(mode, reason):
    result = request_json("POST", {"mode": mode, "reason": reason}, timeout=3)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = request_json(timeout=1)
        if current.get("mode") == mode and current.get("active_dpids") == EXPECTED_DPIDS:
            return result
        time.sleep(.1)
    raise TimeoutError("controller did not report mode " + mode)


def set_qos_enabled(enabled):
    result = request_json("POST", {"enabled": enabled}, timeout=3, endpoint=QOS_API)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = request_json(timeout=1, endpoint=QOS_API)
        if state.get("qos_enabled") is enabled and state.get("active_dpids") == EXPECTED_DPIDS:
            return result
        time.sleep(.1)
    raise TimeoutError("controller did not report QoS enabled=" + str(enabled))


def verify_flows(stage, mode, evidence_dir, routes, class_config):
    expected = next(row for row in routes[mode] if row[0] == 2 and row[3] == "10.0.0.1")
    marker = "in_port=" + str(expected[1])
    action = "output:" + str(expected[2])
    queue_ids = sorted(profile["queue_id"] for profile in class_config["classes"].values())
    qos_enabled = request_json(timeout=2, endpoint=QOS_API).get("qos_enabled")
    deadline = time.monotonic() + 5
    captured, error = [], ""
    while time.monotonic() < deadline:
        captured = []
        error = ""
        for switch in ("s1", "s2", "s3", "s4"):
            proc = subprocess.run(["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", switch],
                cwd=ROOT, capture_output=True, text=True, timeout=8)
            if proc.returncode:
                error = "ovs-ofctl failed for " + switch + ": " + proc.stderr
                break
            captured.append("### " + switch + "\n" + proc.stdout)
        lines = [line for block in captured for line in block.splitlines()]
        route_ok = len(captured) == 4 and any(marker in line and action in line
                                               for line in captured[1].splitlines())
        seen_queues = {int(value) for line in lines
                       for value in re.findall(r"set_queue:(\d+)", line)}
        queue_actions_ok = (set(queue_ids).issubset(seen_queues) if qos_enabled else not seen_queues)
        if route_ok and queue_actions_ok:
            break
        time.sleep(.2)
    text = "\n".join(captured)
    (evidence_dir / ("flows_" + stage + ".txt")).write_text(text, encoding="utf-8")
    if error:
        raise RuntimeError(error)
    if len(captured) != 4 or not any(marker in line and action in line for line in captured[1].splitlines()):
        raise RuntimeError("installed OpenFlow evidence does not show expected s2 route " + mode)
    if qos_enabled and not set(queue_ids).issubset(seen_queues):
        raise RuntimeError("installed OpenFlow evidence is missing configured QoS queues: " +
                           repr(sorted(set(queue_ids) - seen_queues)))
    if not qos_enabled and seen_queues:
        raise RuntimeError("QoS-disabled scenario still has queue actions: " + repr(sorted(seen_queues)))
    qos_evidence = ["### HTB attachments"]
    attached = 0
    for switch in ("s1", "s2", "s3", "s4"):
        ports = subprocess.run(["ovs-vsctl", "list-ports", switch], cwd=ROOT,
                               capture_output=True, text=True, timeout=8, check=True).stdout.splitlines()
        for port in (value.strip() for value in ports if value.strip()):
            qos_id = subprocess.run(["ovs-vsctl", "get", "Port", port, "qos"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=8, check=True).stdout.strip()
            if not qos_id or qos_id == "[]":
                raise RuntimeError("QoS is not attached to OVS port " + port)
            qos_type = subprocess.run(["ovs-vsctl", "get", "QoS", qos_id, "type"], cwd=ROOT,
                                      capture_output=True, text=True, timeout=8, check=True).stdout.strip().strip('"')
            queues = subprocess.run(["ovs-vsctl", "get", "QoS", qos_id, "queues"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=8, check=True).stdout
            attached_ids = {int(value) for value in re.findall(r"(?:^|[, {])(\d+)\s*=", queues)}
            if qos_type != "linux-htb" or not set(queue_ids).issubset(attached_ids):
                raise RuntimeError("HTB queue set is incomplete on OVS port " + port)
            qos_evidence.append("{} qos={} type={} queues={}".format(port, qos_id, qos_type,
                                                                        sorted(attached_ids)))
            attached += 1
    text += "\n" + "\n".join(qos_evidence) + "\n"
    (evidence_dir / ("flows_" + stage + ".txt")).write_text(text, encoding="utf-8")
    return {"mode": mode, "s2_h1_egress": expected[2], "verified": True,
            "qos_enabled": qos_enabled, "queue_actions_verified": queue_actions_ok,
            "queue_ids_seen": sorted(seen_queues),
            "htb_ports_verified": attached}


def configure_scenario_bottleneck(enabled, class_config):
    """Shape S1's S2-facing egress only during the two congestion scenarios."""
    capacity = (SCENARIO_BOTTLENECK_CAPACITY_MBPS if enabled
                else class_config["link_capacity_mbps"])
    override = capacity if capacity < class_config["link_capacity_mbps"] else None
    command = queue_command(SCENARIO_BOTTLENECK_PORT, class_config, override)
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=12)
    if proc.returncode:
        raise RuntimeError("failed to configure scenario HTB bottleneck: " + proc.stderr)
    qos_id = subprocess.run(["ovs-vsctl", "get", "Port", SCENARIO_BOTTLENECK_PORT, "qos"],
        cwd=ROOT, capture_output=True, text=True, timeout=8, check=True).stdout.strip()
    raw_rate = subprocess.run(["ovs-vsctl", "get", "QoS", qos_id, "other-config:max-rate"],
        cwd=ROOT, capture_output=True, text=True, timeout=8, check=True).stdout
    match = re.search(r"\d+", raw_rate)
    observed_capacity = int(match.group(0)) / 1_000_000 if match else None
    if observed_capacity != capacity:
        raise RuntimeError("scenario bottleneck rate mismatch: expected {} Mbps, observed {}".format(
            capacity, observed_capacity))
    return {"port": SCENARIO_BOTTLENECK_PORT,
            "capacity_mbps": capacity, "verified": True}


def parse_scenario_flow_usage(flow_dump, class_config, qos_enabled):
    """Confirm each scenario UDP service packet hit its class rule and queue."""
    classes = {}
    for name, profile in class_config["classes"].items():
        packets = byte_count = 0
        observed_queues = set()
        for line in flow_dump.splitlines():
            if ("udp," not in line or "nw_src=10.0.0.1" not in line or
                    "nw_dst=10.0.0.2" not in line or
                    not re.search(r"(?:^|,)tp_dst={}(?:,|\s)".format(profile["udp_port"]), line)):
                continue
            packet_match = re.search(r"n_packets=(\d+)", line)
            byte_match = re.search(r"n_bytes=(\d+)", line)
            if packet_match:
                packets += int(packet_match.group(1))
            if byte_match:
                byte_count += int(byte_match.group(1))
            observed_queues.update(int(value) for value in
                                   re.findall(r"set_queue:(\d+)", line))
        expected_queue = profile["queue_id"] if qos_enabled else None
        queue_match = (expected_queue in observed_queues if qos_enabled
                       else not observed_queues)
        classes[name] = {"packets": packets, "bytes": byte_count,
                         "expected_queue_id": expected_queue,
                         "observed_queue_ids": sorted(observed_queues),
                         "complete": packets > 0 and queue_match}
    return {"classes": classes,
            "complete": all(item["complete"] for item in classes.values())}


def collect_scenario_flow_usage(scenario, repetition, evidence_dir,
                                class_config, qos_enabled):
    proc = subprocess.run(["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", "s1"],
                          cwd=ROOT, capture_output=True, text=True, timeout=8)
    if proc.returncode:
        raise RuntimeError("post-traffic OpenFlow stats failed for s1: " + proc.stderr)
    (evidence_dir / ("flows_traffic_{}_r{}.txt".format(scenario, repetition))) \
        .write_text(proc.stdout, encoding="utf-8")
    return parse_scenario_flow_usage(proc.stdout, class_config, qos_enabled)


def ping_sample(host, tos=None):
    started = time.time()
    command = ["ping", "-n", "-c", "1", "-W", "2"]
    if tos is not None:
        command.extend(["-Q", str(tos)])
    command.append("10.0.0.2")
    proc = host.popen(command,
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        output, _ = proc.communicate(timeout=4)
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
    match = re.search(r"time[=<]([0-9.]+)\s*ms", output)
    rtt = float(match.group(1)) if proc.returncode == 0 and match else None
    return {"timestamp": started, "rtt_ms": rtt, "returncode": proc.returncode,
            "output": output.strip()}


def summarize_samples(samples, expected_samples=SAMPLES):
    """Summarize probes: median RTT, median adjacent RTT delta, and loss %.

    Jitter uses adjacent successful probe pairs. At least three replies and two
    adjacent pairs are required; observed loss remains part of the composite.
    """
    if not isinstance(expected_samples, int) or expected_samples <= 0 or len(samples) != expected_samples:
        return None
    for sample in samples:
        if not isinstance(sample, dict) or "rtt_ms" not in sample or "timestamp" not in sample:
            return None
        rtt, stamp = sample.get("rtt_ms"), sample.get("timestamp")
        if not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
            return None
        if rtt is not None and (not isinstance(rtt, (int, float)) or not math.isfinite(rtt) or rtt < 0):
            return None
    values = [s["rtt_ms"] for s in samples if s["rtt_ms"] is not None]
    loss = 100.0 * (expected_samples - len(values)) / expected_samples
    if len(values) < 3:
        return {"complete": False, "latency_ms": None, "jitter_ms": None, "packet_loss_pct": loss, "cost": None}
    latency = statistics.median(values)
    adjacent = [abs(samples[i]["rtt_ms"] - samples[i-1]["rtt_ms"])
                for i in range(1, len(samples))
                if samples[i]["rtt_ms"] is not None and samples[i-1]["rtt_ms"] is not None]
    if len(adjacent) < 2:
        return {"complete": False, "latency_ms": latency, "jitter_ms": None, "packet_loss_pct": loss, "cost": None}
    jitter = statistics.median(adjacent)
    cost = (latency / COST_REFERENCES["latency_ms"] + jitter / COST_REFERENCES["jitter_ms"] +
            loss / COST_REFERENCES["packet_loss_pct"]) / 3.0
    return {"complete": True, "latency_ms": latency, "jitter_ms": jitter,
            "packet_loss_pct": loss, "cost": cost}


PORT_PEERS = {
    ("s1", 1): "h1", ("s1", 2): "s2-eth1", ("s1", 3): "s3-eth1",
    ("s1", 6): "h3", ("s1", 7): "h4",
    ("s2", 1): "s1-eth2", ("s2", 2): "s4-eth1", ("s2", 3): "s3-eth3",
    ("s3", 1): "s1-eth3", ("s3", 2): "s4-eth2", ("s3", 3): "s2-eth3",
    ("s4", 1): "s2-eth2", ("s4", 2): "s3-eth2", ("s4", 3): "h2",
    ("s4", 4): "h5", ("s4", 5): "h6",
}


def parse_port_stats(output):
    """Parse OpenFlow ovs-ofctl dump-ports counters without filling gaps."""
    ports = {}
    current = None
    for line in output.splitlines():
        header = re.search(r"\bport\s+(\d+):", line)
        if header:
            current = int(header.group(1))
            ports[current] = {}
        if current is None:
            continue
        byte_count = re.search(r"bytes=(\d+)", line)
        if byte_count and re.search(r"\brx\s+pkts=", line):
            ports[current]["rx_bytes"] = int(byte_count.group(1))
        if byte_count and re.search(r"\btx\s+pkts=", line):
            ports[current]["tx_bytes"] = int(byte_count.group(1))
    return {port: counters for port, counters in ports.items()
            if "rx_bytes" in counters and "tx_bytes" in counters}


def collect_port_snapshot():
    snapshot = {}
    for switch in ("s1", "s2", "s3", "s4"):
        proc = subprocess.run(["ovs-ofctl", "-O", "OpenFlow13", "dump-ports", switch],
                              cwd=ROOT, capture_output=True, text=True, timeout=8)
        if proc.returncode:
            raise RuntimeError("OpenFlow port stats failed for {}: {}".format(switch, proc.stderr))
        snapshot[switch] = parse_port_stats(proc.stdout)
    return {"timestamp": time.time(), "switches": snapshot}


def calculate_link_utilization(before, after, capacity_mbps, capacity_overrides=None):
    """Calculate directional Mbps/utilization from two real port-stat snapshots."""
    interval = after["timestamp"] - before["timestamp"]
    capacity_overrides = capacity_overrides or {}
    links, complete = [], interval > 0
    for (switch, port), peer in PORT_PEERS.items():
        link_capacity = capacity_overrides.get((switch, port), capacity_mbps)
        old = before["switches"].get(switch, {}).get(port)
        new = after["switches"].get(switch, {}).get(port)
        valid = (old is not None and new is not None and interval > 0 and
                 new["rx_bytes"] >= old["rx_bytes"] and new["tx_bytes"] >= old["tx_bytes"])
        if valid:
            rx_mbps = 8 * (new["rx_bytes"] - old["rx_bytes"]) / interval / 1_000_000
            tx_mbps = 8 * (new["tx_bytes"] - old["tx_bytes"]) / interval / 1_000_000
            rx_pct, tx_pct = rx_mbps / link_capacity * 100, tx_mbps / link_capacity * 100
        else:
            rx_mbps = tx_mbps = rx_pct = tx_pct = None
            complete = False
        links.append({"name": "{}-eth{} <-> {}".format(switch, port, peer),
                      "switch": switch, "port": port, "peer": peer,
                      "capacity_mbps": link_capacity,
                      "rx_mbps": rx_mbps, "tx_mbps": tx_mbps,
                      "rx_utilization_pct": rx_pct, "tx_utilization_pct": tx_pct,
                      "complete": valid})
    return {"complete": complete, "interval_seconds": interval if interval > 0 else None,
            "capacity_mbps": capacity_mbps, "links": links}


def sample_class_traffic(net, traffic_class, profile):
    """Run a real TCP class flow alongside DSCP-marked ICMP probes."""
    h1, h2 = net.get("h1", "h2")
    port, tos = profile["tcp_port"], profile["dscp"] << 2
    started = time.time()
    server = h2.popen(["iperf3", "-s", "-1", "-p", str(port)],
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(.3)
    if server.poll() is not None:
        return {"traffic_class": traffic_class, "queue_id": profile["queue_id"],
                "dscp": profile["dscp"], "service_port": port, "complete": False,
                "metrics": None, "throughput_mbps": None, "samples": [],
                "timestamp": time.time(), "error": "iperf3 class server failed to start"}

    client = None
    samples = []
    client_output = ""
    error = None
    try:
        client = h1.popen(["iperf3", "-c", "10.0.0.2", "-p", str(port),
                           "-t", "4", "-J", "-S", str(tos)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(SAMPLES):
            samples.append(ping_sample(h1, tos=tos))
            time.sleep(.15)
        try:
            client_output, _ = client.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            client.terminate()
            client_output, _ = client.communicate(timeout=2)
            error = "iperf3 class client timed out"
        try:
            server.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            server.terminate()
            server.communicate(timeout=2)
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)
    finally:
        for proc in (client, server):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()

    metrics = summarize_samples(samples) if len(samples) == SAMPLES else None
    throughput_bps = None
    if client is not None and client.returncode == 0:
        try:
            result = json.loads(client_output)
            throughput_bps = result.get("end", {}).get("sum_received", {}).get("bits_per_second")
            if throughput_bps is None:
                throughput_bps = result.get("end", {}).get("sum_sent", {}).get("bits_per_second")
            if not isinstance(throughput_bps, (int, float)) or throughput_bps <= 0:
                throughput_bps = None
        except (json.JSONDecodeError, AttributeError):
            throughput_bps = None
    complete = bool(metrics and metrics["complete"] and throughput_bps is not None and error is None)
    if not complete and error is None:
        error = "incomplete class telemetry or missing positive throughput"
    return {"traffic_class": traffic_class, "queue_id": profile["queue_id"],
            "dscp": profile["dscp"], "tos": tos, "service_port": port,
            "complete": complete, "metrics": metrics,
            "throughput_mbps": throughput_bps / 1_000_000 if throughput_bps is not None else None,
            "iperf_bits_per_second": throughput_bps, "samples": samples,
            "timestamp": time.time(), "duration_seconds": time.time() - started,
            "error": error}


def collect_class_metrics(net, class_config):
    try:
        before = collect_port_snapshot()
    except Exception as exc:
        before = None
        link_error = type(exc).__name__ + ": " + str(exc)
    else:
        link_error = None
    per_class = {
        name: sample_class_traffic(net, name, profile)
        for name, profile in class_config["classes"].items()
    }
    if before is not None:
        try:
            after = collect_port_snapshot()
            links = calculate_link_utilization(before, after, class_config["link_capacity_mbps"])
        except Exception as exc:
            links = {"complete": False, "interval_seconds": None,
                     "capacity_mbps": class_config["link_capacity_mbps"],
                     "links": [], "error": type(exc).__name__ + ": " + str(exc)}
    else:
        links = {"complete": False, "interval_seconds": None,
                 "capacity_mbps": class_config["link_capacity_mbps"],
                 "links": [], "error": link_error}
    return per_class, links


def sample_stage(net, stage, mode, evidence_dir, routes, class_config):
    set_mode(mode, "stage " + stage)
    flows = verify_flows(stage, mode, evidence_dir, routes, class_config)
    h1, h2 = net.get("h1", "h2")
    server = h2.popen(["iperf3", "-s", "-1"], stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, text=True)
    time.sleep(.4)
    if server.poll() is not None:
        raise RuntimeError("iperf3 server failed to start")
    client = None
    samples = []
    client_output, server_output = "", ""
    try:
        client = h1.popen(["iperf3", "-c", "10.0.0.2", "-t", "4", "-J"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(SAMPLES):
            samples.append(ping_sample(h1))
            time.sleep(.15)
        try:
            client_output, _ = client.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            client.terminate()
            client_output, _ = client.communicate(timeout=2)
        try:
            server_output, _ = server.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            server.terminate()
            server_output, _ = server.communicate(timeout=2)
    finally:
        for proc in (client, server):
            if proc is None:
                continue
            if proc.poll() is None:
                proc.terminate()
                try:
                    output, _ = proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    output, _ = proc.communicate()
                if proc is client and not client_output:
                    client_output = output or ""
                elif proc is server and not server_output:
                    server_output = output or ""
    if client is None or client.returncode != 0 or server.returncode != 0:
        raise RuntimeError("iperf3 traffic generation failed; client=" + str(client.returncode) +
                           " server=" + str(server.returncode))
    try:
        iperf_json = json.loads(client_output)
        throughput = iperf_json.get("end", {}).get("sum_received", {}).get("bits_per_second")
        if throughput is None:
            throughput = iperf_json.get("end", {}).get("sum_sent", {}).get("bits_per_second")
        if not isinstance(throughput, (int, float)) or throughput <= 0:
            raise ValueError("missing positive throughput")
    except (json.JSONDecodeError, ValueError, AttributeError) as exc:
        raise RuntimeError("iperf3 did not provide valid throughput evidence: " + str(exc))
    valid = [s["rtt_ms"] for s in samples if s["rtt_ms"] is not None]
    metrics = summarize_samples(samples)
    per_class_metrics, link_utilization = collect_class_metrics(net, class_config)
    metrics_payload = {"stage": stage, "collected_at": time.time(),
                       "per_class_metrics": per_class_metrics,
                       "link_utilization": link_utilization}
    try:
        published = request_json("POST", metrics_payload, timeout=3,
                                 endpoint=METRICS_API)
        controller_metrics = request_json(timeout=2, endpoint=METRICS_API)
        rest_publication = {"complete": bool(published.get("accepted") and
                                             controller_metrics.get("fresh") and
                                             controller_metrics.get("measurements", {}).get("stage") == stage),
                            "response": published,
                            "route_decision": controller_metrics.get("route_decision")}
        if not rest_publication["complete"]:
            rest_publication["error"] = "controller metrics endpoint returned missing or stale data"
    except Exception as exc:
        rest_publication = {"complete": False,
                            "error": type(exc).__name__ + ": " + str(exc)}
        controller_metrics = None
    result = {"stage": stage, "mode": mode, "samples": samples,
              "sample_count": len(samples), "valid_count": len(valid),
              "metrics": metrics,
              "complete": bool(metrics and metrics.get("complete") and
                               flows.get("verified") and throughput is not None),
              "per_class_metrics": per_class_metrics,
              "link_utilization": link_utilization,
              "controller_metrics": rest_publication,
              "median_rtt_ms": metrics["latency_ms"] if metrics and metrics["complete"] else None,
              "flow_evidence": flows,
              "iperf_bits_per_second": throughput,
              "iperf_client_returncode": client.returncode,
              "iperf_server_returncode": server.returncode,
              "iperf_client_output": client_output, "iperf_server_output": server_output}
    save_json(evidence_dir / ("measurements_" + stage + ".json"), result)
    return result


def measure_route_condition(net, mode, shortcut_link, evidence_dir, routes, class_config):
    """Take a fresh paired-decision sample under the same generated TCP load."""
    set_shortcut_link(shortcut_link, mode == "shortcut")
    set_mode(mode, "paired route comparison")
    flows = verify_flows("decision_" + mode, mode, evidence_dir, routes, class_config)
    h1, h2 = net.get("h1", "h2")
    server = h2.popen(["iperf3", "-s", "-1"], stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, text=True)
    time.sleep(.3)
    if server.poll() is not None:
        return {"mode": mode, "samples": [], "valid_count": 0,
                "metrics": None, "throughput_mbps": None,
                "flow_evidence": flows, "complete": False,
                "error": "paired iperf3 server failed to start"}
    client = h1.popen(["iperf3", "-c", "10.0.0.2", "-t", "4", "-J"],
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    samples = []
    client_output = ""
    try:
        for _ in range(SAMPLES):
            samples.append(ping_sample(h1))
            time.sleep(.15)
        try:
            client_output, _ = client.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            client.terminate()
            client_output, _ = client.communicate(timeout=2)
        try:
            server.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            server.terminate()
            server.communicate(timeout=2)
    finally:
        for proc in (client, server):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
    throughput = None
    if client.returncode == 0:
        try:
            end = json.loads(client_output).get("end", {})
            bps = end.get("sum_received", {}).get("bits_per_second")
            if bps is None:
                bps = end.get("sum_sent", {}).get("bits_per_second")
            if isinstance(bps, (int, float)) and math.isfinite(bps) and bps > 0:
                throughput = bps / 1_000_000
        except (json.JSONDecodeError, AttributeError):
            pass
    metrics = summarize_samples(samples)
    valid_count = sum(sample["rtt_ms"] is not None for sample in samples)
    complete = bool(metrics and metrics["complete"] and throughput is not None and flows["verified"])
    return {"mode": mode, "samples": samples, "valid_count": valid_count,
            "metrics": metrics, "throughput_mbps": throughput,
            "flow_evidence": flows, "complete": complete,
            "error": None if complete else "incomplete paired route telemetry"}


def sample_scenario_traffic(net, scenario, repetition, qos_enabled,
                            heavy_background, evidence_dir, routes, class_config,
                            bottleneck_evidence, workload):
    """Run simultaneous DSCP-marked UDP classes from training-derived profiles."""
    set_qos_enabled(qos_enabled)
    set_mode("baseline", "scenario {} repetition {}".format(scenario, repetition))
    flows = verify_flows(scenario + "_r" + str(repetition), "baseline", evidence_dir,
                         routes, class_config)
    h1, h2 = net.get("h1", "h2")
    before = collect_port_snapshot()
    servers, clients, pings, ping_started = {}, {}, {}, {}
    outputs = {}
    duration = 4
    for name, profile in class_config["classes"].items():
        port = profile["udp_port"]
        servers[name] = h2.popen(["iperf3", "-s", "-1", "-p", str(port)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(.35)
    for name, profile in class_config["classes"].items():
        port, tos = profile["udp_port"], profile["dscp"] << 2
        flow_workload = workload[name]
        offered_mbps = flow_workload["offered_load_mbps"]
        clients[name] = h1.popen(["iperf3", "-c", "10.0.0.2", "-p", str(port),
            "-u", "-b", "{}M".format(offered_mbps),
            "-l", str(flow_workload["dataset_packet_size_bytes"]),
            "-t", str(duration), "-J", "--get-server-output", "-S", str(tos)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        ping_started[name] = time.time()
        pings[name] = h1.popen(["ping", "-n", "-c", str(SCENARIO_PING_SAMPLES), "-i", "0.1", "-W", "2",
                                "-Q", str(tos), "10.0.0.2"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    class_results = {}
    try:
        for name, proc in pings.items():
            try:
                outputs["ping_" + name], _ = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                outputs["ping_" + name], _ = proc.communicate()
        for name, proc in clients.items():
            try:
                outputs["client_" + name], _ = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.terminate()
                outputs["client_" + name], _ = proc.communicate(timeout=2)
        for name, proc in servers.items():
            try:
                outputs["server_" + name], _ = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                proc.terminate()
                outputs["server_" + name], _ = proc.communicate(timeout=2)
    finally:
        for proc in list(pings.values()) + list(clients.values()) + list(servers.values()):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
    for name, profile in class_config["classes"].items():
        flow_workload = workload[name]
        raw = outputs.get("ping_" + name, "")
        observed = {int(sequence): float(value) for sequence, value in re.findall(
            r"icmp_seq=(\d+).*?time[=<]([0-9.]+)\s*ms", raw)}
        samples = [{"timestamp": ping_started[name] + (i - 1) * .1,
                    "rtt_ms": observed.get(i)} for i in range(1, SCENARIO_PING_SAMPLES + 1)]
        ping_metrics = summarize_samples(samples, expected_samples=SCENARIO_PING_SAMPLES)
        received_mbps = udp_loss = None
        try:
            result = json.loads(outputs.get("client_" + name, ""))
            server_output = result.get("server_output_text")
            receiver_result = {}
            if isinstance(server_output, str):
                try:
                    receiver_result = json.loads(server_output)
                except json.JSONDecodeError:
                    receiver_result = {}
            receiver_end = receiver_result.get("end", {})
            end = (receiver_end.get("sum_received") or receiver_end.get("sum") or
                   result.get("end", {}).get("sum_received", {}))
            bps = end.get("bits_per_second")
            loss_value = end.get(" lost_percent")
            if loss_value is None:
                loss_value = end.get("lost_percent")
            if (not isinstance(bps, (int, float)) or
                    not isinstance(loss_value, (int, float))) and isinstance(server_output, str):
                match = re.search(
                    r"([0-9.]+)\s+([KMG])bits/sec.*?\(([0-9.]+)%\).*receiver\s*$",
                    server_output, re.MULTILINE)
                if match:
                    multiplier = {"K": 1_000, "M": 1_000_000, "G": 1_000_000_000}[match.group(2)]
                    bps = float(match.group(1)) * multiplier
                    loss_value = float(match.group(3))
            if isinstance(bps, (int, float)) and math.isfinite(bps) and bps >= 0:
                received_mbps = bps / 1_000_000
            if isinstance(loss_value, (int, float)) and math.isfinite(loss_value) and 0 <= loss_value <= 100:
                udp_loss = loss_value
        except (json.JSONDecodeError, AttributeError):
            pass
        latency = ping_metrics.get("latency_ms") if ping_metrics else None
        jitter = ping_metrics.get("jitter_ms") if ping_metrics else None
        complete = latency is not None and jitter is not None and udp_loss is not None and received_mbps is not None
        cost = ((latency / COST_REFERENCES["latency_ms"] +
                 jitter / COST_REFERENCES["jitter_ms"] +
                 udp_loss / COST_REFERENCES["packet_loss_pct"]) / 3) if complete else None
        class_results[name] = {"complete": complete,
            "metrics": {"complete": complete, "latency_ms": latency, "jitter_ms": jitter,
                        "packet_loss_pct": udp_loss, "ping_packet_loss_pct":
                            ping_metrics.get("packet_loss_pct") if ping_metrics else None,
                        "cost": cost},
            "throughput_mbps": received_mbps,
            **flow_workload,
            "dscp": profile["dscp"], "udp_port": profile["udp_port"],
            "queue_id": profile["queue_id"] if qos_enabled else None,
            "ping_samples": samples,
            "error": None if complete else "incomplete class scenario telemetry"}
    class_flow_usage = collect_scenario_flow_usage(
        scenario, repetition, evidence_dir, class_config, qos_enabled)
    flows["class_traffic_usage"] = class_flow_usage
    after = collect_port_snapshot()
    capacity_overrides = ({("s1", 2): SCENARIO_BOTTLENECK_CAPACITY_MBPS}
                          if heavy_background else {})
    links = calculate_link_utilization(before, after,
        class_config["link_capacity_mbps"], capacity_overrides)
    record = {"scenario": scenario, "repetition": repetition,
        "qos_enabled": qos_enabled, "heavy_background": heavy_background,
        "route": "baseline", "duration_seconds": duration,
        "latency_probe_count": SCENARIO_PING_SAMPLES,
        "bottleneck": bottleneck_evidence,
        "per_class_metrics": class_results, "link_utilization": links,
        "flow_evidence": flows,
        "complete": (all(item["complete"] for item in class_results.values()) and
                     links["complete"] and class_flow_usage["complete"]),
        "raw_process_output": outputs}
    save_json(evidence_dir / ("scenario_{}_r{}.json".format(scenario, repetition)), record)
    return record


def run_braess_repetition(net, repetition, shortcut_link, evidence_dir, routes, class_config):
    set_qos_enabled(True)
    baseline = measure_route_condition(net, "baseline", shortcut_link, evidence_dir, routes, class_config)
    shortcut = measure_route_condition(net, "shortcut", shortcut_link, evidence_dir, routes, class_config)
    decision = classify(baseline, shortcut)
    if not decision.get("reason"):
        decision["reason"] = ("shortcut cost exceeded baseline by more than {:.0%} threshold".format(THRESHOLD)
            if decision["verdict"] == "harmful" else
            "shortcut cost was more than {:.0%} below baseline".format(THRESHOLD)
            if decision["verdict"] == "beneficial" else
            "shortcut cost was within the {:.0%} neutral band".format(THRESHOLD))
    selected = decision["mode"]
    prevention = measure_route_condition(net, selected, shortcut_link,
                                         evidence_dir, routes, class_config)
    flows_verified = all(item["flow_evidence"]["verified"]
                         for item in (baseline, shortcut, prevention))
    route_selection_verified = bool(
        (selected == decision["mode"] or
         decision["verdict"] == "inconclusive" and selected == "baseline") and flows_verified)
    decision_record = {"repetition": repetition, "verdict": decision["verdict"],
        "selected_route": selected, "reason": decision["reason"],
        "threshold_fraction": THRESHOLD,
        "metrics_used": {"baseline": baseline["metrics"], "shortcut": shortcut["metrics"]},
        "prevention_metrics": prevention["metrics"],
        "prevention_verified": harmful_shortcut_prevented(
            decision["verdict"], selected, prevention["complete"], flows_verified, True),
        "route_selection_verified": route_selection_verified, "flows_verified": flows_verified,
        "sample_timestamps": {"baseline": [x["timestamp"] for x in baseline["samples"]],
            "shortcut": [x["timestamp"] for x in shortcut["samples"]]}}
    try:
        posted = request_json("POST", decision_record, timeout=3, endpoint=DECISION_API)
        decision_record["controller_recorded"] = bool(posted.get("recorded"))
    except Exception as exc:
        decision_record["controller_recorded"] = False
        decision_record["controller_error"] = type(exc).__name__ + ": " + str(exc)
    # Prevention is a route control claim: after a harmful candidate measurement,
    # confirm that the selected baseline route is actually installed and that the
    # follow-up telemetry and controller decision record are present. The follow-up
    # cost is reported, but a noisy new sample must not invalidate forwarding proof.
    decision_record["prevention_verified"] = bool(
        decision_record["prevention_verified"] and decision_record["controller_recorded"])
    return {"repetition": repetition, "baseline": baseline, "shortcut": shortcut,
            "prevention": prevention, "decision": decision_record,
            "complete": all(item["complete"] for item in (baseline, shortcut, prevention)),
            "prevention_verified": decision_record["prevention_verified"] and
                                  decision_record["controller_recorded"]}


def summarize_scenario_repetitions(repetitions, class_config):
    summary = {"repetition_count": len(repetitions), "classes": {}}
    fields = ("latency_ms", "jitter_ms", "packet_loss_pct", "throughput_mbps")
    def stats(values):
        return {"n": len(values), "mean": statistics.mean(values) if values else None,
                "standard_deviation": statistics.stdev(values) if len(values) > 1 else None,
                "complete": len(values) == len(repetitions) and bool(repetitions)}
    for traffic_class in class_config["classes"]:
        summary["classes"][traffic_class] = {}
        for field in fields:
            values = []
            for repetition in repetitions:
                item = repetition.get("per_class_metrics", {}).get(traffic_class, {})
                value = ((item.get("metrics") or {}).get(field) if field != "throughput_mbps"
                         else item.get(field))
                if isinstance(value, (int, float)) and math.isfinite(value):
                    values.append(value)
            summary["classes"][traffic_class][field] = stats(values)
    links = {}
    for repetition in repetitions:
        for link in repetition.get("link_utilization", {}).get("links", []):
            entry = links.setdefault(link["name"], {"rx_mbps": [], "tx_mbps": [],
                "rx_utilization_pct": [], "tx_utilization_pct": []})
            for field in entry:
                value = link.get(field)
                if isinstance(value, (int, float)) and math.isfinite(value):
                    entry[field].append(value)
    summary["links"] = {name: {field: stats(values) for field, values in fields.items()}
                        for name, fields in links.items()}
    return summary


def summarize_braess_repetitions(repetitions):
    output = {"repetition_count": len(repetitions), "verdict_counts": {},
              "prevention_verified_count": sum(bool(item.get("prevention_verified"))
                                                for item in repetitions),
              "costs": {}}
    for item in repetitions:
        verdict = item.get("decision", {}).get("verdict", "unavailable")
        output["verdict_counts"][verdict] = output["verdict_counts"].get(verdict, 0) + 1
    for route in ("baseline", "shortcut", "prevention"):
        values = []
        for row in repetitions:
            metrics = row.get(route, {}).get("metrics") or {}
            value = metrics.get("cost")
            if isinstance(value, (int, float)) and math.isfinite(value):
                values.append(value)
        entry = {"n": len(values),
            "mean": statistics.mean(values) if values else None,
            "standard_deviation": statistics.stdev(values) if len(values) > 1 else None}
        if len(values) > 1:
            entry["confidence_interval_95"] = [
                entry["mean"] - 1.96 * entry["standard_deviation"] / math.sqrt(len(values)),
                entry["mean"] + 1.96 * entry["standard_deviation"] / math.sqrt(len(values))
            ]
        output["costs"][route] = entry
    return output


def harmful_shortcut_prevented(verdict, selected_route, prevention_complete,
                               flows_verified, controller_recorded):
    """Return whether a harmful shortcut was measurably rejected and baseline restored."""
    return bool(verdict == "harmful" and selected_route == "baseline" and
                prevention_complete and flows_verified and controller_recorded)


def stage_measurement_complete(stage):
    """Read completion from either a paired route result or a saved stage result."""
    if stage.get("complete") is True:
        return True
    metrics = stage.get("metrics")
    return bool(isinstance(metrics, dict) and metrics.get("complete") is True)


def set_shortcut_link(link, enabled):
    state = "up" if enabled else "down"
    link.intf1.ifconfig(state)
    link.intf2.ifconfig(state)


def set_link_state(link, enabled):
    state = "up" if enabled else "down"
    link.intf1.ifconfig(state)
    link.intf2.ifconfig(state)


def run_link_failure_recovery(net, failed_link, shortcut_link, evidence_dir,
                              routes, class_config):
    """Verify the alternate route while the primary inter-switch link is down."""
    set_shortcut_link(shortcut_link, True)
    set_link_state(failed_link, False)
    try:
        set_mode("recovery", "primary link failure recovery")
        flows = verify_flows("failure_recovery", "recovery", evidence_dir,
                             routes, class_config)
        h1, h2 = net.get("h1", "h2")
        probe = h1.cmd("ping -n -c 3 -W 2 10.0.0.2")
        received_match = re.search(r"(\d+) received", probe)
        received = int(received_match.group(1)) if received_match else 0
        result = {
            "failed_link": [failed_link.intf1.name, failed_link.intf2.name],
            "selected_route": "recovery",
            "connectivity": {"received": received, "probe": probe},
            "flows_verified": flows["verified"],
            "complete": received >= 1 and flows["verified"],
        }
        save_json(evidence_dir / "failure_recovery.json", result)
        if not result["complete"]:
            raise RuntimeError("link-failure recovery did not preserve connectivity")
        return result
    finally:
        set_link_state(failed_link, True)
        set_shortcut_link(shortcut_link, False)


def classify(baseline, candidate, now=None):
    now = time.time() if now is None else now
    for record in (baseline, candidate):
        paired = record.get("decision_probe")
        if paired is not None and not paired.get("complete"):
            return {"verdict": "inconclusive", "mode": "baseline",
                    "reason": "paired route measurement incomplete"}
        samples = record.get("samples", [])
        if len(samples) != SAMPLES:
            return {"verdict": "inconclusive", "mode": "baseline", "reason": "incomplete probe set"}
        if not isinstance(record.get("valid_count"), int) or record["valid_count"] < 3:
            return {"verdict": "inconclusive", "mode": "baseline", "reason": "too few successful RTT samples"}
        if any(not isinstance(s, dict) or "rtt_ms" not in s or "timestamp" not in s or
               not isinstance(s["timestamp"], (int, float)) or not math.isfinite(s["timestamp"]) or
               (s["rtt_ms"] is not None and (not isinstance(s["rtt_ms"], (int, float)) or
                not math.isfinite(s["rtt_ms"]) or s["rtt_ms"] < 0)) for s in samples):
            return {"verdict": "inconclusive", "mode": "baseline", "reason": "invalid RTT telemetry"}
        if any(now - s["timestamp"] > MAX_AGE or now < s["timestamp"] for s in samples):
            return {"verdict": "inconclusive", "mode": "baseline", "reason": "stale RTT samples"}
    bm, cm = baseline.get("metrics"), candidate.get("metrics")
    if not bm or not cm or not bm.get("complete") or not cm.get("complete"):
        return {"verdict": "inconclusive", "mode": "baseline", "reason": "incomplete latency, jitter, or packet-loss metrics"}
    b, c = bm.get("cost"), cm.get("cost")
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in (b, c)):
        return {"verdict": "inconclusive", "mode": "baseline", "reason": "invalid cost telemetry"}
    if b == 0:
        return {"verdict": "inconclusive", "mode": "baseline", "reason": "baseline cost is zero; relative comparison undefined"}
    ratio = c / b
    if ratio > 1 + THRESHOLD:
        return {"verdict": "harmful", "mode": "baseline", "ratio": ratio}
    if ratio < 1 - THRESHOLD:
        return {"verdict": "beneficial", "mode": "shortcut", "ratio": ratio}
    return {"verdict": "neutral", "mode": "shortcut", "ratio": ratio}


def run_catalog_profile_matrix(net, traffic_catalog, class_config, evidence_dir,
                               routes):
    """Exercise each catalog profile through its deterministic MedRoute class.

    Catalog ports are metadata and are not controller policy ports. Each profile
    therefore uses the existing policy port/DSCP for its mapped class, while the
    original catalog values remain recorded for provenance.
    """
    set_qos_enabled(True)
    set_mode("baseline", "catalog profile matrix")
    h1, h2 = net.get("h1", "h2")
    results = []
    for row in traffic_catalog["rows"]:
        score = float(row["criticality"]) * 20
        traffic_class = ("ECG" if score >= 90 else "ICU" if score >= 70 else
                         "WEARABLE" if score >= 40 else "BACKGROUND")
        policy = class_config["classes"][traffic_class]
        stage = "catalog_" + str(row["traffic_type"]).lower()
        flow_evidence = verify_flows(stage, "baseline", evidence_dir, routes,
                                     class_config)
        port = int(policy["udp_port"])
        tos = int(policy["dscp"]) << 2
        duration = max(2, min(4, int(float(row["duration_seconds"]))))
        server = h2.popen(["iperf3", "-s", "-1", "-p", str(port)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
        time.sleep(.25)
        client = h1.popen([
            "iperf3", "-c", "10.0.0.2", "-p", str(port), "-u",
            "-b", "{}M".format(float(row["offered_rate_bps"]) / 1_000_000),
            "-l", str(int(row["packet_size_bytes"])), "-t", str(duration),
            "-J", "--get-server-output", "-S", str(tos)
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        ping = h1.popen(["ping", "-n", "-c", "20", "-i", "0.1", "-W", "2",
                         "-Q", str(tos), "10.0.0.2"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True)
        try:
            try:
                ping_output, _ = ping.communicate(timeout=12)
            except subprocess.TimeoutExpired:
                ping.kill()
                ping_output, _ = ping.communicate()
            try:
                client_output, _ = client.communicate(timeout=duration + 8)
            except subprocess.TimeoutExpired:
                client.terminate()
                client_output, _ = client.communicate(timeout=3)
            try:
                server_output, _ = server.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                server.terminate()
                server_output, _ = server.communicate(timeout=2)
        finally:
            for proc in (ping, client, server):
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.communicate()
        observed = [float(value) for value in re.findall(
            r"icmp_seq=\d+.*?time[=<]([0-9.]+)\s*ms", ping_output)]
        samples = [{"timestamp": time.time(), "rtt_ms": value}
                   for value in observed]
        ping_metrics = summarize_samples(
            samples, expected_samples=max(1, len(observed)))
        received_mbps = udp_loss = None
        try:
            payload = json.loads(client_output)
            server_text = payload.get("server_output_text")
            receiver = {}
            if isinstance(server_text, str):
                try:
                    receiver = json.loads(server_text)
                except json.JSONDecodeError:
                    receiver = {}
            end = (receiver.get("end", {}).get("sum_received") or
                   receiver.get("end", {}).get("sum") or
                   payload.get("end", {}).get("sum_received", {}))
            bps = end.get("bits_per_second")
            loss = end.get(" lost_percent", end.get("lost_percent"))
            if (not isinstance(bps, (int, float)) or
                    not isinstance(loss, (int, float))) and isinstance(server_text, str):
                match = re.search(
                    r"([0-9.]+)\s+([KMG])bits/sec.*?\(([0-9.]+)%\).*receiver\s*$",
                    server_text, re.MULTILINE)
                if match:
                    bps = float(match.group(1)) * {
                        "K": 1_000, "M": 1_000_000, "G": 1_000_000_000
                    }[match.group(2)]
                    loss = float(match.group(3))
            if isinstance(bps, (int, float)) and bps >= 0:
                received_mbps = bps / 1_000_000
            if isinstance(loss, (int, float)) and 0 <= loss <= 100:
                udp_loss = loss
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        latency = ping_metrics.get("latency_ms") if ping_metrics else None
        jitter = ping_metrics.get("jitter_ms") if ping_metrics else None
        complete = bool(flow_evidence.get("verified") and latency is not None and
                        jitter is not None and received_mbps is not None and
                        udp_loss is not None)
        results.append({
            "profile": row["traffic_type"],
            "catalog": row,
            "selected_class": traffic_class,
            "criticality_score": score,
            "policy_port": port,
            "policy_dscp": int(policy["dscp"]),
            "expected_queue_id": policy["queue_id"],
            "flow_evidence": flow_evidence,
            "metrics": {
                "complete": complete, "latency_ms": latency,
                "jitter_ms": jitter, "packet_loss_pct": udp_loss,
                "throughput_mbps": received_mbps,
                "ping_packet_loss_pct": ping_metrics.get("packet_loss_pct")
                    if ping_metrics else None
            },
            "complete": complete,
            "raw_process_output": {
                "ping": ping_output, "client": client_output,
                "server": server_output
            },
            "execution_status": "passed" if complete else "incomplete_telemetry"
        })
    save_json(evidence_dir / "profile_matrix.json", {
        "source": traffic_catalog["source_file"],
        "source_sha256": traffic_catalog["sha256"],
        "mapping_policy": "catalog criticality * 20 mapped to the existing four "
                           "MedRoute policy classes; catalog ports remain metadata",
        "profiles": results,
        "all_profiles_executed": len(results) == traffic_catalog["row_count"],
        "all_profiles_complete": all(row["complete"] for row in results)
    })
    return results


def main():
    def terminate_cleanly(signum, frame):
        raise SystemExit("received signal " + str(signum))
    signal.signal(signal.SIGTERM, terminate_cleanly)
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--skip-failure-recovery", action="store_true",
                        help="skip the controlled primary-link failure demonstration")
    args = parser.parse_args()
    out = args.evidence_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    class_config = json.loads((ROOT / "sdn" / "classes.json").read_text(encoding="utf-8"))
    dataset_provenance = load_profiles(ROOT)
    traffic_catalog = load_traffic_catalog(ROOT)
    scenario_workloads = build_scenario_workloads(
        dataset_provenance, SCENARIO_PLAN, class_config["classes"],
        SCENARIO_BOTTLENECK_CAPACITY_MBPS)
    save_json(out / "dataset_workload.json", {
        "provenance": dataset_provenance,
        "catalog": traffic_catalog,
        "workload_by_scenario_and_class": scenario_workloads,
        "mapping_policy": "All classes use the training median profile by default; BACKGROUND uses the training p75 profile when a congestion scenario is requested. In heavy scenarios its synthetic offered rate is derived as bottleneck capacity plus the other classes' nominal dataset-profile rates. This creates demand above capacity; it is not presented as dataset-native traffic.",
        "raw_packet_replay": False,
        "clinical_labels_from_dataset": False,
    })
    criticality_trace = []
    for row in traffic_catalog["rows"]:
        score = float(row["criticality"]) * 20
        traffic_class = ("ECG" if score >= 90 else "ICU" if score >= 70 else
                         "WEARABLE" if score >= 40 else "BACKGROUND")
        policy = class_config["classes"][traffic_class]
        criticality_trace.append({
            "input_profile": row["traffic_type"],
            "criticality_score": score,
            "selected_class": traffic_class,
            "service_port": int(row["destination_port"]),
            "catalog_rate_bps": int(row["offered_rate_bps"]),
            "catalog_packet_size_bytes": int(row["packet_size_bytes"]),
            "expected_queue_id": policy["queue_id"],
            "classification_source": "synthetic_catalog_criticality",
            "clinical_input": False
        })
    save_json(out / "criticality_trace.json", {
        "source": traffic_catalog["source_file"],
        "source_sha256": traffic_catalog["sha256"],
        "policy": "score = catalog criticality * 20; deterministic class thresholds; no ML",
        "records": criticality_trace
    })
    config = {"topology": "4-switch diamond; S2-S3 shortcut physically down at baseline, enabled for candidate and recovery",
              "demand": "synthetic iperf3 TCP plus 5 route probes and 50 per-class scenario probes",
              "stages": ["failure_recovery", "baseline", "shortcut", "prevention"], "threshold_fraction": THRESHOLD,
              "cost_formula": "(latency_ms/20 + jitter_ms/5 + packet_loss_pct/1)/3; relative stage cost threshold 5%",
              "cost_references": COST_REFERENCES,
              "metric_methods": {"latency_ms": "median successful one-packet ping RTT", "jitter_ms": "median absolute difference for adjacent successful RTT pairs; at least two pairs", "packet_loss_pct": "100 * lost probes / 5"},
              "required_samples": SAMPLES, "max_sample_age_seconds": MAX_AGE,
              "traffic_classes": class_config,
              "required_scenarios": SCENARIO_PLAN,
              "required_repetitions_per_scenario": SCENARIO_REPETITIONS,
              "scenario_workload": {"traffic": "simultaneous DSCP-marked UDP flows using CICIoMT2024 training-derived synthetic rate and packet-size profiles",
                  "dataset_profile_file": dataset_provenance["source_file"],
                  "dataset_profile_version": dataset_provenance["profile_version"],
                  "workload_by_scenario_and_class": scenario_workloads,
                  "heavy_background_rate_policy": "configured bottleneck capacity plus the other classes' nominal training-profile offered rates; the resulting synthetic rate is scaled from the selected training-derived high profile rate",
                  "congestion_bottleneck": {"port": SCENARIO_BOTTLENECK_PORT,
                      "capacity_mbps": SCENARIO_BOTTLENECK_CAPACITY_MBPS,
                      "active_only_in_heavy_background_scenarios": True},
                  "scenario_ping_probe_count": SCENARIO_PING_SAMPLES,
                  "measurement": "per-class median RTT, adjacent RTT jitter, iperf UDP loss and received throughput; OpenFlow port-counter link utilization"},
              "dataset_used": True,
              "dataset_workload": {key: value for key, value in dataset_provenance.items()
                                   if key != "profiles"},
              "traffic_catalog": traffic_catalog,
              "dataset_interpretation": "training-derived aggregate benign traffic profiles shape synthetic scenario offered rates and UDP packet sizes; raw packet replay and healthcare labels are not inferred",
              "acceptance": "if harmful, verify the selected baseline route using complete follow-up telemetry, the recorded controller decision, and matching baseline OpenFlow actions; retain measured follow-up cost separately. For neutral or beneficial decisions, verify the actual route matches the selected mode"}
    save_json(out / "config.json", config)
    routes = json.loads((ROOT / "sdn" / "routes.json").read_text(encoding="utf-8"))
    os.environ["MEDROUTE_LOG"] = str(out / "controller.jsonl")
    ryu = None
    net = None
    summary = {"live_experiment": "infrastructure_failure", "live_prevention_verified": False}
    details = {}
    try:
        from mininet.net import Mininet
        from mininet.node import RemoteController
        from mininet.link import TCLink
        sys.path.insert(0, str(ROOT / "sdn"))
        from topology import MedRouteTopo
        with (out / "ryu.stdout.log").open("w", encoding="utf-8") as log:
            ryu = subprocess.Popen(["ryu-manager", "--ofp-tcp-listen-port", "6653",
                "--wsapi-port", "8080", "sdn/controller.py"], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
            wait_controller(ryu)
            net = Mininet(topo=MedRouteTopo(), controller=None, link=TCLink,
                          autoSetMacs=True, build=True)
            net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
            net.start()
            wait_switches()
            shortcut_link = next(link for link in net.links if
                {link.intf1.node.name, link.intf2.node.name} == {"s2", "s3"})
            failed_link = next(link for link in net.links if
                {link.intf1.node.name, link.intf2.node.name} == {"s1", "s2"})
            set_shortcut_link(shortcut_link, False)
            h1, h2 = net.get("h1", "h2")
            h1.setARP("10.0.0.2", "00:00:00:00:00:02")
            h2.setARP("10.0.0.1", "00:00:00:00:00:01")
            connectivity_probe = h1.cmd("ping -n -c 3 -W 2 10.0.0.2")
            (out / "baseline-connectivity.txt").write_text(
                "=== h1 ping h2 ===\n" + connectivity_probe +
                "\n=== h1 routes ===\n" + h1.cmd("ip route") +
                "\n=== h1 neighbors ===\n" + h1.cmd("ip neigh") +
                "\n=== baseline flows ===\n" + "\n".join(
                    "### {}\n{}".format(switch, subprocess.run(
                        ["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", switch],
                        cwd=ROOT, capture_output=True, text=True, timeout=8).stdout)
                    for switch in ("s1", "s2", "s4")),
                encoding="utf-8")
            received_match = re.search(r"(\d+) received", connectivity_probe)
            if not received_match or int(received_match.group(1)) < 1:
                raise RuntimeError("baseline connectivity probe failed; see baseline-connectivity.txt")
            if args.skip_failure_recovery:
                recovery = {"enabled": False, "complete": None,
                            "reason": "controlled failure check disabled by command line"}
            else:
                recovery = {"enabled": True, **run_link_failure_recovery(
                    net, failed_link, shortcut_link, out, routes, class_config)}
            baseline = sample_stage(net, "baseline", "baseline", out, routes, class_config)
            set_shortcut_link(shortcut_link, True)
            candidate = sample_stage(net, "shortcut", "shortcut", out, routes, class_config)
            paired_baseline = measure_route_condition(net, "baseline", shortcut_link,
                                                       out, routes, class_config)
            paired_candidate = measure_route_condition(net, "shortcut", shortcut_link,
                                                       out, routes, class_config)
            for record, paired in ((baseline, paired_baseline), (candidate, paired_candidate)):
                record["stage_samples"] = record["samples"]
                record["stage_metrics"] = record["metrics"]
                record["decision_probe"] = paired
                record["samples"] = paired["samples"]
                record["sample_count"] = len(paired["samples"])
                record["valid_count"] = paired["valid_count"]
                record["metrics"] = paired["metrics"]
            decision = classify(baseline, candidate)
            if not decision.get("reason"):
                decision["reason"] = ("shortcut cost exceeded baseline by more than {:.0%} threshold".format(THRESHOLD)
                    if decision["verdict"] == "harmful" else
                    "shortcut cost was more than {:.0%} below baseline".format(THRESHOLD)
                    if decision["verdict"] == "beneficial" else
                    "shortcut cost was within the {:.0%} neutral band".format(THRESHOLD))
            prevention_mode = decision["mode"]
            set_mode(prevention_mode, "measurement decision: " + decision["verdict"])
            prevention = sample_stage(net, "prevention", prevention_mode, out, routes, class_config)
            records = {"baseline": baseline, "shortcut": candidate, "prevention": prevention}
            save_json(out / "measurements.json", records)
            verified = all(records[s]["flow_evidence"]["verified"] for s in records)
            complete = all(records[s]["metrics"] and records[s]["metrics"]["complete"] for s in records)
            passed = False
            if not complete:
                live_status = "inconclusive"
            elif decision["verdict"] == "harmful":
                passed = False
                live_status = "prevention_failed"
            else:
                passed = decision["verdict"] != "inconclusive" and prevention_mode == decision["mode"] and verified
                live_status = "shortcut_not_harmful_under_test" if passed else "inconclusive"
            decision_record = {"repetition": 1, "verdict": decision["verdict"], "selected_route": prevention_mode,
                "reason": decision["reason"], "threshold_fraction": THRESHOLD,
                "metrics_used": {"baseline": baseline["metrics"], "shortcut": candidate["metrics"]},
                "sample_timestamps": {
                    "baseline": [sample["timestamp"] for sample in baseline["samples"]],
                    "shortcut": [sample["timestamp"] for sample in candidate["samples"]]},
                "prevention_verified": harmful_shortcut_prevented(
                    decision["verdict"], prevention_mode,
                    stage_measurement_complete(prevention), verified, True),
                "route_selection_verified": bool(prevention_mode == decision["mode"] and verified),
                "flows_verified": verified,
                "prevention_metrics": prevention["metrics"]}
            try:
                controller_decision = request_json("POST", decision_record, timeout=3,
                                                   endpoint=DECISION_API)
                decision_record["controller_recorded"] = bool(controller_decision.get("recorded"))
            except Exception as exc:
                decision_record["controller_recorded"] = False
                decision_record["controller_error"] = type(exc).__name__ + ": " + str(exc)
            decision_record["prevention_verified"] = bool(
                decision_record["prevention_verified"] and
                decision_record["controller_recorded"])
            if decision["verdict"] == "harmful":
                passed = decision_record["prevention_verified"]
                live_status = "harmful_shortcut_prevented" if passed else "prevention_failed"
            if not decision_record["controller_recorded"]:
                passed = False
                live_status = "decision_recording_failed"
            braess_repetitions = [{"repetition": 1, "baseline": baseline,
                "shortcut": candidate, "prevention": prevention, "decision": decision_record,
                "complete": complete,
                "prevention_verified": decision_record["prevention_verified"]}]
            for repetition in range(2, SCENARIO_REPETITIONS + 1):
                braess_repetitions.append(run_braess_repetition(
                    net, repetition, shortcut_link, out, routes, class_config))
            scenario_repetitions = {}
            scenario_statistics = {}
            scenario_validation = True
            scenario_validation_errors = []
            for scenario, spec in SCENARIO_PLAN.items():
                bottleneck_evidence = configure_scenario_bottleneck(
                    spec["heavy_background"], class_config)
                rows = []
                for repetition in range(1, SCENARIO_REPETITIONS + 1):
                    set_shortcut_link(shortcut_link, False)
                    rows.append(sample_scenario_traffic(net, scenario, repetition,
                        spec["qos_enabled"], spec["heavy_background"], out, routes,
                        class_config, bottleneck_evidence,
                        scenario_workloads[scenario]))
                scenario_repetitions[scenario] = rows
                saved_rows = [json.loads((out / "scenario_{}_r{}.json".format(scenario, i)).read_text(encoding="utf-8"))
                              for i in range(1, SCENARIO_REPETITIONS + 1)]
                scenario_statistics[scenario] = summarize_scenario_repetitions(saved_rows, class_config)
                for row in rows:
                    flow_evidence = row.get("flow_evidence", {})
                    if not row.get("complete"):
                        usage = flow_evidence.get("class_traffic_usage", {})
                        flow_failure_count = 0
                        for name, detail in usage.get("classes", {}).items():
                            if not detail.get("complete"):
                                flow_failure_count += 1
                                scenario_validation_errors.append(
                                    "{} r{} {} flow did not hit expected queue: packets={}, expected={}, observed={}".format(
                                        scenario, row.get("repetition"), name,
                                        detail.get("packets"), detail.get("expected_queue_id"),
                                        detail.get("observed_queue_ids")))
                        if not usage or flow_failure_count == 0:
                            scenario_validation_errors.append(
                                "{} r{} incomplete telemetry or flow evidence".format(
                                    scenario, row.get("repetition")))
                    if (not flow_evidence.get("verified") or
                            flow_evidence.get("qos_enabled") != spec["qos_enabled"]):
                        scenario_validation_errors.append(
                            "{} r{} route/QoS configuration evidence mismatch".format(
                                scenario, row.get("repetition")))
                scenario_validation = scenario_validation and all(row["complete"] and
                    row["flow_evidence"]["verified"] and
                    row["flow_evidence"]["qos_enabled"] == spec["qos_enabled"] for row in rows)
            configure_scenario_bottleneck(False, class_config)
            profile_matrix = run_catalog_profile_matrix(
                net, traffic_catalog, class_config, out, routes)
            if not all(row.get("complete") for row in profile_matrix):
                scenario_validation = False
                scenario_validation_errors.extend(
                    "catalog profile {} has incomplete live execution or forwarding evidence".format(
                        row.get("profile"))
                    for row in profile_matrix if not row.get("complete"))
            # Restore the ordinary route port rate before final route verification and cleanup.
            configure_scenario_bottleneck(False, class_config)
            for trial in braess_repetitions:
                decision_entry = trial["decision"]
                if trial["repetition"] == 1 and not decision_entry.get("controller_recorded"):
                    continue
                if trial["repetition"] > 1 and not decision_entry.get("controller_recorded"):
                    scenario_validation = False
                    scenario_validation_errors.append(
                        "Braess r{} decision was not recorded by controller".format(
                            trial["repetition"]))
                if (decision_entry.get("verdict") == "harmful" and
                        not decision_entry.get("prevention_verified")):
                    scenario_validation_errors.append(
                        "Braess r{} harmful shortcut did not meet prevention verification".format(
                            trial["repetition"]))
                if not trial.get("complete") or not decision_entry.get("route_selection_verified"):
                    scenario_validation_errors.append(
                        "Braess r{} has incomplete metrics or route selection evidence".format(
                            trial["repetition"]))
            scenario_validation = scenario_validation and all(
                row.get("complete") and row.get("decision", {}).get("controller_recorded") and
                row.get("decision", {}).get("route_selection_verified") and
                (row.get("decision", {}).get("verdict") != "harmful" or
                 row.get("decision", {}).get("prevention_verified"))
                for row in braess_repetitions)
            braess_statistics = summarize_braess_repetitions(braess_repetitions)
            scenario_result = {"required_repetitions": SCENARIO_REPETITIONS,
                "scenarios": scenario_repetitions,
                "statistics_from_saved_measurements": scenario_statistics,
                "braess_shortcut_repetitions": braess_repetitions,
                "braess_statistics": braess_statistics,
                "validation_errors": scenario_validation_errors,
                "validation_passed": bool(scenario_validation)}
            save_json(out / "scenario_results.json", scenario_result)
            selected_final = braess_repetitions[-1]["decision"]["selected_route"]
            set_shortcut_link(shortcut_link, selected_final == "shortcut")
            set_mode(selected_final, "restore final repeated Braess decision")
            final_route_evidence = verify_flows("final_selected", selected_final,
                                                out, routes, class_config)
            if not scenario_validation:
                live_status = "scenario_validation_failed"
            decisions = {"shortcut_decision": decision, "route_decision": decision_record,
                         "prevention_mode": prevention_mode,
                         "baseline_cost": baseline["metrics"]["cost"] if baseline["metrics"] else None,
                         "shortcut_cost": candidate["metrics"]["cost"] if candidate["metrics"] else None,
                         "prevention_cost": prevention["metrics"]["cost"] if prevention["metrics"] else None}
            save_json(out / "decisions.json", decisions)
            summary = {"live_experiment": live_status, "live_prevention_verified": bool(passed and decision["verdict"] == "harmful"),
                       "failure_recovery": recovery,
                       "dataset_used": True,
                       "dataset_profile_version": dataset_provenance["profile_version"],
                       "dataset_profile_sha256": dataset_provenance["source_sha256"],
                       "shortcut_verdict": decision["verdict"], "all_flow_rules_verified": verified,
                       "all_telemetry_complete": complete,
                       "baseline_metrics": baseline["metrics"], "shortcut_metrics": candidate["metrics"],
                       "prevention_metrics": prevention["metrics"],
                       "route_decision": decision_record,
                       "decision_metrics_used": decision_record["metrics_used"],
                       "selected_route": prevention_mode,
                       "scenario_repetitions": {name: len(rows) for name, rows in scenario_repetitions.items()},
                       "catalog_profile_matrix": {
                           "profiles": len(profile_matrix),
                           "complete": all(row.get("complete") for row in profile_matrix),
                           "file": "profile_matrix.json"
                       },
                       "braess_repetitions": len(braess_repetitions),
                       "scenario_validation_passed": bool(scenario_validation),
                       "scenario_validation_errors": scenario_validation_errors,
                       "scenario_statistics_file": "scenario_results.json",
                       "braess_prevention_verified_repetitions": braess_statistics["prevention_verified_count"],
                       "final_repeated_route": selected_final,
                       "final_route_verified": final_route_evidence["verified"],
                       "controller_metrics_published": all(
                           bool(records[key].get("controller_metrics", {}).get("complete"))
                           for key in records),
                       "per_class_metrics_complete": all(
                           all(bool(item.get("complete")) for item in records[key]["per_class_metrics"].values())
                           for key in records),
                       "link_utilization_complete": all(
                           bool(records[key].get("link_utilization", {}).get("complete"))
                           for key in records)}
            (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            try:
                subprocess.run([sys.executable, str(ROOT / "scripts" / "build_evidence_db.py"),
                                str(out)], check=True, cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                summary["evidence_database"] = "evidence.sqlite"
                (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                  encoding="utf-8")
            except (OSError, subprocess.CalledProcessError) as exc:
                summary["evidence_database"] = None
                summary["evidence_database_error"] = str(exc)
                (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                  encoding="utf-8")
            return 0 if passed and scenario_validation else 2
    except Exception as exc:
        summary.update({"error": type(exc).__name__ + ": " + str(exc), "live_prevention_verified": False})
        details["traceback"] = traceback.format_exc()
        details["host_links_at_failure"] = diagnostic_command(["ip", "-o", "link", "show"])
        details["ovs_bridges_at_failure"] = diagnostic_command(["ovs-vsctl", "show"])
        if net is not None:
            try:
                details["mininet_interfaces"] = [
                    {"intf1": link.intf1.name, "intf2": link.intf2.name}
                    for link in net.links]
            except Exception as diagnostic_error:
                details["mininet_interfaces_error"] = (
                    type(diagnostic_error).__name__ + ": " + str(diagnostic_error))
        (out / "error.txt").write_text(json.dumps(details, indent=2) + "\n", encoding="utf-8")
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return 2
    finally:
        if net is not None:
            try:
                net.stop()
            except Exception as exc:
                (out / "cleanup_error.txt").write_text(str(exc), encoding="utf-8")
        if ryu is not None and ryu.poll() is None:
            ryu.terminate()
            try:
                ryu.wait(timeout=5)
            except subprocess.TimeoutExpired:
                ryu.kill()
                ryu.wait()


if __name__ == "__main__":
    raise SystemExit(main())
