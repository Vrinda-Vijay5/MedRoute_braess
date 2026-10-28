"""Ryu OpenFlow 1.3 route actuator for the MedRoute four-switch diamond.

The experiment coordinator supplies a mode only after validating paired, fresh
RTT telemetry. This app translates that mode into IPv4 forwarding entries.
"""
import json
import math
import os
import sys
import time

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from webob import Response

H1, H2 = "10.0.0.1", "10.0.0.2"
MEDROUTE_COOKIE = 0x4D52000000000001
MEDROUTE_COOKIE_MASK = 0xFFFFFFFF00000000
sys.path.insert(0, os.path.dirname(__file__))
from qos import configure_switch_queues, flow_action_specs, flow_specs, load_classes

with open(os.path.join(os.path.dirname(__file__), "routes.json"), encoding="utf-8") as stream:
    ROUTES = json.load(stream)
CLASS_CONFIG = load_classes()


def classify_traffic(payload):
    """Apply the deterministic precedence used by the installed OpenFlow rules."""
    if not isinstance(payload, dict):
        raise ValueError("classification input must be an object")
    dscp = payload.get("dscp")
    source_port, destination_port = payload.get("source_port"), payload.get("destination_port")
    for value in (dscp, source_port, destination_port):
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError("dscp and ports must be non-negative integers")
    score = payload.get("criticality_score")
    if score is not None and (not isinstance(score, (int, float)) or not math.isfinite(score)
                              or score < 0 or score > 100):
        raise ValueError("criticality_score must be between 0 and 100")
    selected, reason = None, "default"
    for name, profile in CLASS_CONFIG["classes"].items():
        if source_port in (profile["tcp_port"], profile["udp_port"]) or \
                destination_port in (profile["tcp_port"], profile["udp_port"]):
            selected, reason = name, "transport_port"
            break
    if selected is None and dscp is not None:
        for name, profile in CLASS_CONFIG["classes"].items():
            if dscp == profile["dscp"]:
                selected, reason = name, "ipv4_dscp"
                break
    if selected is None:
        selected = "BACKGROUND"
    if score is not None and reason == "default":
        selected = ("ECG" if score >= 90 else "ICU" if score >= 70 else
                    "WEARABLE" if score >= 40 else "BACKGROUND")
        reason = "patient_criticality"
    return {"traffic_class": selected, "queue_id": CLASS_CONFIG["classes"][selected]["queue_id"],
            "criticality_score": score, "classifier": reason}


class MedRoute(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {"wsgi": WSGIApplication}

    def __init__(self, *args, **kwargs):
        wsgi = kwargs["wsgi"]
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self.mode = "baseline"
        self.qos_enabled = True
        self.route_decision = {"timestamp": time.time(), "selected_route": self.mode,
                               "reason": "controller startup", "previous_route": None}
        self.latest_measurements = None
        self.latest_measurements_received_at = None
        self.log_path = os.environ.get("MEDROUTE_LOG", "artifacts/controller.jsonl")
        wsgi.register(MedRouteRest, {"app": self})

    def log(self, event, **fields):
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        record = {"timestamp": time.time(), "event": event, **fields}
        with open(self.log_path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
        self.logger.info("MEDROUTE %s", json.dumps(record))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        parser, of = dp.ofproto_parser, dp.ofproto
        queues = configure_switch_queues("s{}".format(dp.id), CLASS_CONFIG)
        miss = parser.OFPFlowMod(
            datapath=dp, priority=0, match=parser.OFPMatch(),
            instructions=[parser.OFPInstructionActions(of.OFPIT_APPLY_ACTIONS,
                [parser.OFPActionOutput(of.OFPP_CONTROLLER, of.OFPCML_NO_BUFFER)])])
        dp.send_msg(miss)
        self.install_routes(dp)
        self.log("switch_connected", dpid=dp.id, mode=self.mode,
                 qos_queues=queues["queues"], qos_ports=queues["ports"])

    def install_routes(self, dp):
        parser, of = dp.ofproto_parser, dp.ofproto
        delete = parser.OFPFlowMod(datapath=dp, cookie=MEDROUTE_COOKIE,
            cookie_mask=MEDROUTE_COOKIE_MASK, table_id=of.OFPTT_ALL,
            command=of.OFPFC_DELETE, out_port=of.OFPP_ANY,
            out_group=of.OFPG_ANY, match=parser.OFPMatch())
        dp.send_msg(delete)
        # Unknown destinations and unmatched traffic are explicitly dropped.
        dp.send_msg(parser.OFPFlowMod(datapath=dp, cookie=MEDROUTE_COOKIE,
            table_id=0, priority=1, match=parser.OFPMatch(), instructions=[]))
        installed = []
        for spec in flow_specs(ROUTES[self.mode], CLASS_CONFIG):
            if spec["dpid"] != dp.id:
                continue
            match = parser.OFPMatch(**spec["match"])
            actions = [parser.OFPActionSetQueue(value) if kind == "set_queue"
                       else parser.OFPActionOutput(value)
                       for kind, value in flow_action_specs(spec, self.qos_enabled)]
            dp.send_msg(parser.OFPFlowMod(datapath=dp, cookie=MEDROUTE_COOKIE,
                table_id=0, priority=spec["priority"], match=match,
                instructions=[parser.OFPInstructionActions(of.OFPIT_APPLY_ACTIONS, actions)]))
            installed.append(spec)
        dp.send_msg(parser.OFPBarrierRequest(dp))
        return installed

    def set_mode(self, mode, reason="experiment coordinator"):
        if mode not in ROUTES:
            raise ValueError("mode must be one of: " + ", ".join(sorted(ROUTES)))
        previous = self.mode
        self.mode = mode
        self.route_decision = {"timestamp": time.time(), "selected_route": mode,
                               "reason": reason, "previous_route": previous}
        installed = []
        for dp in list(self.datapaths.values()):
            installed.extend(self.install_routes(dp))
        self.log("forwarding_mode_changed", previous=previous, mode=mode, reason=reason,
                 active_dpids=sorted(self.datapaths),
                 class_rule_count=len(installed),
                 queue_map={name: profile["queue_id"]
                            for name, profile in CLASS_CONFIG["classes"].items()})
        return {"mode": self.mode, "active_dpids": sorted(self.datapaths),
                "rules": len(ROUTES[self.mode])}

    def set_qos_enabled(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")
        self.qos_enabled = enabled
        installed = []
        for dp in list(self.datapaths.values()):
            installed.extend(self.install_routes(dp))
        self.log("qos_mode_changed", enabled=enabled, active_dpids=sorted(self.datapaths),
                 class_rule_count=len(installed))
        return {"qos_enabled": enabled, "active_dpids": sorted(self.datapaths)}

    def publish_measurements(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("stage"), str):
            raise ValueError("stage is required")
        collected_at = payload.get("collected_at")
        if not isinstance(collected_at, (int, float)) or not math.isfinite(collected_at):
            raise ValueError("collected_at must be a finite timestamp")
        age = time.time() - collected_at
        if age < 0 or age > 30:
            raise ValueError("collected_at is stale or in the future")
        per_class = payload.get("per_class_metrics")
        if not isinstance(per_class, dict):
            raise ValueError("per_class_metrics must be an object")
        known = set(CLASS_CONFIG["classes"])
        if not set(per_class).issubset(known):
            raise ValueError("per_class_metrics contains an unknown traffic class")
        for name, record in per_class.items():
            if not isinstance(record, dict) or not isinstance(record.get("complete"), bool):
                raise ValueError(name + " must include an explicit completeness flag")
            metrics = record.get("metrics")
            if metrics is not None and not isinstance(metrics, dict):
                raise ValueError(name + " metrics must be an object or null")
            for field in ("latency_ms", "jitter_ms", "packet_loss_pct"):
                value = (metrics or {}).get(field)
                if value is not None and (not isinstance(value, (int, float)) or
                                          not math.isfinite(value) or value < 0):
                    raise ValueError(name + " has invalid " + field)
            throughput = record.get("throughput_mbps")
            if throughput is not None and (not isinstance(throughput, (int, float)) or
                                             not math.isfinite(throughput) or throughput < 0):
                raise ValueError(name + " has invalid throughput_mbps")
            if record["complete"] and (not metrics or
                    any(metrics.get(field) is None for field in
                        ("latency_ms", "jitter_ms", "packet_loss_pct")) or throughput is None):
                raise ValueError(name + " is complete but has missing measurements")
        links = payload.get("link_utilization")
        if links is not None and (not isinstance(links, dict) or
                                  not isinstance(links.get("complete"), bool)):
            raise ValueError("link_utilization must include an explicit completeness flag")
        self.latest_measurements = payload
        self.latest_measurements_received_at = time.time()
        self.log("metrics_published", stage=payload["stage"],
                 per_class=list(per_class), link_metrics_complete=bool(links and links.get("complete")))
        return {"accepted": True, "stage": payload["stage"],
                "class_count": len(per_class),
                "link_utilization_complete": bool(links and links.get("complete"))}

    def record_route_decision(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("decision must be an object")
        selected = payload.get("selected_route")
        if selected not in ROUTES:
            raise ValueError("selected_route must be baseline or shortcut")
        if payload.get("verdict") not in ("harmful", "beneficial", "neutral", "inconclusive"):
            raise ValueError("verdict is invalid")
        if not isinstance(payload.get("reason"), str) or not payload["reason"]:
            raise ValueError("reason is required")
        if not isinstance(payload.get("metrics_used"), dict):
            raise ValueError("metrics_used is required")
        if not isinstance(payload.get("prevention_verified"), bool):
            raise ValueError("prevention_verified must be boolean")
        self.route_decision = {"timestamp": time.time(), **payload}
        self.log("route_decision", **self.route_decision)
        return {"recorded": True, "route_decision": self.route_decision}


class MedRouteRest(ControllerBase):
    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.app = data["app"]

    @route("medroute", "/medroute/mode", methods=["GET", "POST"])
    def mode(self, req, **kwargs):
        if req.method == "GET":
            body = {"mode": self.app.mode, "active_dpids": sorted(self.app.datapaths),
                    "route_decision": self.app.route_decision,
                    "qos_enabled": self.app.qos_enabled}
            return Response(content_type="application/json", body=json.dumps(body).encode("utf-8"))
        try:
            payload = json.loads(req.body.decode("utf-8"))
            result = self.app.set_mode(payload["mode"], payload.get("reason", "coordinator"))
            return Response(content_type="application/json", body=json.dumps(result).encode("utf-8"))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            return Response(status=400, content_type="application/json",
                            body=json.dumps({"error": str(exc)}).encode("utf-8"))

    @route("medroute_metrics", "/medroute/metrics", methods=["GET", "POST"])
    def metrics(self, req, **kwargs):
        if req.method == "GET":
            received = self.app.latest_measurements_received_at
            fresh = received is not None and time.time() - received <= 30
            body = {"mode": self.app.mode, "route_decision": self.app.route_decision,
                    "measurements": self.app.latest_measurements,
                    "received_at": received, "fresh": fresh}
            return Response(content_type="application/json", body=json.dumps(body).encode("utf-8"))
        try:
            payload = json.loads(req.body.decode("utf-8"))
            result = self.app.publish_measurements(payload)
            return Response(content_type="application/json",
                            body=json.dumps(result).encode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            return Response(status=400, content_type="application/json",
                            body=json.dumps({"error": str(exc)}).encode("utf-8"))

    @route("medroute_decision", "/medroute/decision", methods=["GET", "POST"])
    def decision(self, req, **kwargs):
        if req.method == "POST":
            try:
                payload = json.loads(req.body.decode("utf-8"))
                result = self.app.record_route_decision(payload)
                return Response(content_type="application/json",
                                body=json.dumps(result).encode("utf-8"))
            except (ValueError, json.JSONDecodeError) as exc:
                return Response(status=400, content_type="application/json",
                                body=json.dumps({"error": str(exc)}).encode("utf-8"))
        body = {"mode": self.app.mode, "route_decision": self.app.route_decision}
        return Response(content_type="application/json", body=json.dumps(body).encode("utf-8"))

    @route("medroute_qos", "/medroute/qos", methods=["GET", "POST"])
    def qos(self, req, **kwargs):
        if req.method == "GET":
            body = {"qos_enabled": self.app.qos_enabled,
                    "active_dpids": sorted(self.app.datapaths)}
            return Response(content_type="application/json", body=json.dumps(body).encode("utf-8"))
        try:
            payload = json.loads(req.body.decode("utf-8"))
            result = self.app.set_qos_enabled(payload["enabled"])
            return Response(content_type="application/json", body=json.dumps(result).encode("utf-8"))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            return Response(status=400, content_type="application/json",
                            body=json.dumps({"error": str(exc)}).encode("utf-8"))

    @route("medroute_classify", "/medroute/classify", methods=["POST"])
    def classify(self, req, **kwargs):
        try:
            result = classify_traffic(json.loads(req.body.decode("utf-8")))
            self.app.log("traffic_classified", **result)
            return Response(content_type="application/json",
                            body=json.dumps(result).encode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            return Response(status=400, content_type="application/json",
                            body=json.dumps({"error": str(exc)}).encode("utf-8"))
