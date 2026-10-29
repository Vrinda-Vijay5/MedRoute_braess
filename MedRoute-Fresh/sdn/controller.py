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
from ryu.controller.handler import (CONFIG_DISPATCHER, DEAD_DISPATCHER,
                                    MAIN_DISPATCHER, set_ev_cls)
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from webob import Response

H1, H2 = "10.0.0.1", "10.0.0.2"
MEDROUTE_COOKIE = 0x4D52000000000001
MEDROUTE_COOKIE_MASK = 0xFFFFFFFF00000000
BARRIER_REPLY_TIMEOUT = 2.5
ROUTE_CHANGE_WINDOW_SECONDS = 60
MAX_ROUTE_CHANGES_PER_WINDOW = 12
sys.path.insert(0, os.path.dirname(__file__))
from qos import configure_switch_queues, flow_action_specs, flow_specs, load_classes

with open(os.path.join(os.path.dirname(__file__), "routes.json"), encoding="utf-8") as stream:
    ROUTES = json.load(stream)
CLASS_CONFIG = load_classes()


class RouteInstallError(RuntimeError):
    """Raised when one or more switches did not confirm a route update."""

    def __init__(self, message, operation_id=None, failed_switches=None):
        super().__init__(message)
        self.operation_id = operation_id
        self.failed_switches = failed_switches or {}


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
        self.ready_datapaths = {}
        self._update_lock = hub.Semaphore(1)
        self.barrier_timeout = BARRIER_REPLY_TIMEOUT
        self._next_update_id = 0
        self._pending_requests = {}
        self._active_updates = {}
        self.mode = "baseline"
        self.route_state = "unconfirmed"
        self.qos_enabled = True
        self.qos_state_confirmed = False
        self.last_route_update = None
        self.route_change_history = []
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
        previous = self.datapaths.get(dp.id)
        if previous is not None and previous is not dp:
            self._datapath_disconnected(previous, "datapath replaced by a new connection")
        self.datapaths[dp.id] = dp
        self.ready_datapaths.pop(dp.id, None)
        self._refresh_global_state()
        # Queue setup and route programming can block; do them outside the
        # Ryu app event-dispatch greenlet, then publish readiness on confirmation.
        hub.spawn(self._initialize_datapath, dp)

    def _refresh_global_state(self):
        all_ready = bool(self.datapaths) and all(
            self.ready_datapaths.get(dpid) is dp
            for dpid, dp in self.datapaths.items())
        if all_ready:
            self.route_state = "confirmed"
            self.qos_state_confirmed = True
        elif self.route_state != "unknown":
            self.route_state = "unconfirmed"
            self.qos_state_confirmed = False

    def _new_update(self, datapaths, kind):
        self._next_update_id += 1
        operation = {
            "id": self._next_update_id,
            "kind": kind,
            "datapaths": {id(dp): dp for dp in datapaths},
            "pending_barriers": set(),
            "request_keys": set(),
            "errors": {},
            "flow_mod_count": 0,
            "barrier_count": 0,
            "barrier_confirmation_latency_ms_by_switch": {},
            "event": hub.Event(),
        }
        self._active_updates[operation["id"]] = operation
        return operation

    def _fail_update(self, operation, dp, reason):
        name = "s{}".format(dp.id)
        operation["errors"].setdefault(name, str(reason))
        operation["event"].set()

    def _send_update_message(self, operation, dp, message, is_barrier=False):
        """Register a request XID before sending so errors/replies can be correlated."""
        try:
            dp.set_xid(message)
            key = (id(dp), message.xid)
            if key in self._pending_requests:
                self._fail_update(operation, dp,
                                  "duplicate outstanding OpenFlow XID {}".format(message.xid))
                return False
            self._pending_requests[key] = {
                "operation": operation,
                "datapath": dp,
                "kind": "barrier" if is_barrier else "flow_mod",
                "sent_at": time.monotonic() if is_barrier else None,
            }
            operation["request_keys"].add(key)
            if is_barrier:
                operation["pending_barriers"].add(key)
                operation["barrier_count"] += 1
            else:
                operation["flow_mod_count"] += 1
            dp.send_msg(message)
            return True
        except Exception as exc:
            self._fail_update(operation, dp,
                              "failed to send OpenFlow request: {}".format(exc))
            return False

    def _send_barrier(self, operation, dp):
        return self._send_update_message(
            operation, dp, dp.ofproto_parser.OFPBarrierRequest(dp), is_barrier=True)

    def _finish_update(self, operation, timeout=None):
        timeout = self.barrier_timeout if timeout is None else timeout
        deadline = time.monotonic() + timeout
        operation["event"].wait(timeout)
        # Errors wake the waiter immediately, but outstanding barriers still
        # need to resolve (or time out) so every failed switch is identified.
        while operation["pending_barriers"] and time.monotonic() < deadline:
            operation["event"].clear()
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not operation["event"].wait(remaining):
                break
        if operation["pending_barriers"]:
            for key in list(operation["pending_barriers"]):
                entry = self._pending_requests.get(key)
                if entry is not None:
                    self._fail_update(operation, entry["datapath"],
                                      "barrier reply timed out")
        success = not operation["errors"] and not operation["pending_barriers"]
        for key in operation["request_keys"]:
            if self._pending_requests.get(key, {}).get("operation") is operation:
                self._pending_requests.pop(key, None)
        self._active_updates.pop(operation["id"], None)
        return success

    def _operation_failure(self, operation, default_reason="barrier confirmation incomplete"):
        failures = dict(operation["errors"])
        if operation["pending_barriers"] and not failures:
            for key in operation["pending_barriers"]:
                entry = self._pending_requests.get(key)
                dp = entry["datapath"] if entry else operation["datapaths"].get(key[0])
                failures["s{}".format(dp.id) if dp else "unknown"] = "barrier reply timed out"
        details = "; ".join("{}: {}".format(name, reason)
                             for name, reason in sorted(failures.items()))
        return RouteInstallError(details or default_reason, operation["id"], failures)

    def _initialize_datapath(self, dp):
        with self._update_lock:
            if self.datapaths.get(dp.id) is not dp:
                return
            operation = self._new_update([dp], "switch_initialization")
            try:
                queues = configure_switch_queues("s{}".format(dp.id), CLASS_CONFIG)
                parser, of = dp.ofproto_parser, dp.ofproto
                miss = parser.OFPFlowMod(
                    datapath=dp, priority=0, match=parser.OFPMatch(),
                    instructions=[parser.OFPInstructionActions(of.OFPIT_APPLY_ACTIONS,
                        [parser.OFPActionOutput(of.OFPP_CONTROLLER,
                                                of.OFPCML_NO_BUFFER)])])
                if self._send_update_message(operation, dp, miss):
                    self.install_routes(dp, self.mode, self.qos_enabled, operation)
                confirmed = self._finish_update(operation)
                if not confirmed:
                    self.route_state = "unknown"
                    self.qos_state_confirmed = False
                    self.log("switch_setup_failed", dpid=dp.id,
                             operation_id=operation["id"],
                             failed_switches=operation["errors"],
                             switch_barrier_confirmed=False)
                    return
                if self.datapaths.get(dp.id) is not dp:
                    self.log("switch_setup_failed", dpid=dp.id,
                             operation_id=operation["id"],
                             reason="datapath disconnected before setup confirmation",
                             switch_barrier_confirmed=False)
                    return
                self.ready_datapaths[dp.id] = dp
                self._refresh_global_state()
                self.log("switch_connected", dpid=dp.id, mode=self.mode,
                         qos_queues=queues["queues"], qos_ports=queues["ports"],
                         switch_barrier_confirmed=True)
            except Exception as exc:
                operation["errors"].setdefault("s{}".format(dp.id), str(exc))
                self._finish_update(operation, timeout=0)
                self.route_state = "unknown"
                self.qos_state_confirmed = False
                self.log("switch_setup_failed", dpid=dp.id,
                         operation_id=operation["id"],
                         failed_switches=operation["errors"],
                         switch_barrier_confirmed=False)

    def install_routes(self, dp, mode, qos_enabled, operation):
        parser, of = dp.ofproto_parser, dp.ofproto
        delete = parser.OFPFlowMod(datapath=dp, cookie=MEDROUTE_COOKIE,
            cookie_mask=MEDROUTE_COOKIE_MASK, table_id=of.OFPTT_ALL,
            command=of.OFPFC_DELETE, out_port=of.OFPP_ANY,
            out_group=of.OFPG_ANY, match=parser.OFPMatch())
        if not self._send_update_message(operation, dp, delete):
            return []
        # Unknown destinations and unmatched traffic are explicitly dropped.
        drop = parser.OFPFlowMod(datapath=dp, cookie=MEDROUTE_COOKIE,
            table_id=0, priority=1, match=parser.OFPMatch(), instructions=[])
        installed = []
        if not self._send_update_message(operation, dp, drop):
            return installed
        for spec in flow_specs(ROUTES[mode], CLASS_CONFIG):
            if spec["dpid"] != dp.id:
                continue
            match = parser.OFPMatch(**spec["match"])
            actions = [parser.OFPActionSetQueue(value) if kind == "set_queue"
                       else parser.OFPActionOutput(value)
                        for kind, value in flow_action_specs(spec, qos_enabled)]
            flow = parser.OFPFlowMod(datapath=dp, cookie=MEDROUTE_COOKIE,
                table_id=0, priority=spec["priority"], match=match,
                instructions=[parser.OFPInstructionActions(of.OFPIT_APPLY_ACTIONS, actions)])
            if not self._send_update_message(operation, dp, flow):
                return installed
            installed.append(spec)
        self._send_barrier(operation, dp)
        return installed

    def _required_datapaths(self):
        datapaths = list(self.datapaths.values())
        if not datapaths:
            raise RouteInstallError("no connected switches are available")
        unready = ["s{}".format(dp.id) for dp in datapaths
                   if self.ready_datapaths.get(dp.id) is not dp]
        if unready:
            raise RouteInstallError("switch setup is not confirmed for: " + ", ".join(unready),
                                    failed_switches={name: "initial setup unconfirmed"
                                                     for name in unready})
        return datapaths

    def _check_update_membership(self, operation):
        required_ids = set(operation["datapaths"])
        current_ids = {id(dp) for dp in self.datapaths.values()}
        if current_ids != required_ids:
            missing = ["s{}".format(dp.id) for identity, dp in operation["datapaths"].items()
                       if identity not in current_ids]
            added = ["s{}".format(dp.id) for dp in self.datapaths.values()
                     if id(dp) not in required_ids]
            for name in missing:
                operation["errors"].setdefault(name, "switch disconnected during update")
            for name in added:
                operation["errors"].setdefault(name, "switch connected during update; not covered")
            return False
        return True

    def set_mode(self, mode, reason="experiment coordinator"):
        if not isinstance(mode, str) or mode not in ROUTES:
            raise ValueError("mode must be one of: " + ", ".join(sorted(ROUTES)))
        started = time.perf_counter()
        with self._update_lock:
            datapaths = self._required_datapaths()
            previous = self.mode
            now = time.monotonic()
            self.route_change_history = [stamp for stamp in self.route_change_history
                if now - stamp < ROUTE_CHANGE_WINDOW_SECONDS]
            if previous != mode and len(self.route_change_history) >= MAX_ROUTE_CHANGES_PER_WINDOW:
                self.log("route_oscillation_guard_triggered", previous=previous, requested=mode,
                         recent_change_count=len(self.route_change_history),
                         window_seconds=ROUTE_CHANGE_WINDOW_SECONDS,
                         update_rejected=True)
                raise RouteInstallError(
                    "route change rejected: more than {} changes in {} seconds".format(
                        MAX_ROUTE_CHANGES_PER_WINDOW, ROUTE_CHANGE_WINDOW_SECONDS),
                    failed_switches={"controller": "route_oscillation_limit"})
            operation = self._new_update(datapaths, "route_mode")
            installed = []
            for dp in datapaths:
                if self.datapaths.get(dp.id) is not dp:
                    self._fail_update(operation, dp, "switch disconnected before programming")
                    continue
                installed.extend(self.install_routes(dp, mode, self.qos_enabled, operation))
            enqueue_ms = (time.perf_counter() - started) * 1000
            confirmed = self._finish_update(operation)
            self._check_update_membership(operation)
            confirmed = confirmed and not operation["errors"]
            if not confirmed:
                self.route_state = "unknown"
                failure = self._operation_failure(operation)
                self.last_route_update = {"operation_id": operation["id"],
                    "selected_route": mode, "confirmed": False,
                    "failed_switches": failure.failed_switches}
                self.log("forwarding_mode_change_failed", previous=previous, mode=mode,
                         reason=reason, operation_id=operation["id"],
                         failed_switches=failure.failed_switches,
                         controller_flow_programming_ms=round(
                             (time.perf_counter() - started) * 1000, 3),
                         flow_programming_enqueue_ms=round(enqueue_ms, 3),
                         flow_mod_count=operation["flow_mod_count"],
                         barrier_count=operation["barrier_count"],
                         barrier_confirmation_latency_ms_by_switch=operation[
                             "barrier_confirmation_latency_ms_by_switch"],
                         switch_barrier_confirmed=False)
                raise failure
            self.mode = mode
            if previous != mode:
                self.route_change_history.append(time.monotonic())
            self.route_state = "confirmed"
            self.route_decision = {"timestamp": time.time(), "selected_route": mode,
                                   "reason": reason, "previous_route": previous}
            self.last_route_update = {"operation_id": operation["id"],
                                      "selected_route": mode, "confirmed": True,
                                      "failed_switches": {}}
            active_dpids = sorted(dp.id for dp in datapaths)
            self.log("forwarding_mode_changed", previous=previous, mode=mode, reason=reason,
                     active_dpids=active_dpids, class_rule_count=len(installed),
                     route_change_count=int(previous != mode),
                     flow_programming_request_count=len(datapaths),
                     submitted_rule_count=len(installed),
                     controller_flow_programming_ms=round(
                         (time.perf_counter() - started) * 1000, 3),
                     flow_programming_enqueue_ms=round(enqueue_ms, 3),
                     flow_mod_count=operation["flow_mod_count"],
                     barrier_count=operation["barrier_count"],
                     barrier_confirmation_latency_ms_by_switch=operation[
                         "barrier_confirmation_latency_ms_by_switch"],
                     switch_barrier_confirmed=True,
                     operation_id=operation["id"],
                     queue_map={name: profile["queue_id"]
                                for name, profile in CLASS_CONFIG["classes"].items()})
            return {"mode": self.mode, "active_dpids": active_dpids,
                    "rules": len(ROUTES[self.mode]), "confirmed": True,
                    "switch_barrier_confirmed": True, "operation_id": operation["id"]}

    def set_qos_enabled(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be boolean")
        started = time.perf_counter()
        with self._update_lock:
            datapaths = self._required_datapaths()
            operation = self._new_update(datapaths, "qos_state")
            installed = []
            for dp in datapaths:
                if self.datapaths.get(dp.id) is not dp:
                    self._fail_update(operation, dp, "switch disconnected before programming")
                    continue
                installed.extend(self.install_routes(dp, self.mode, enabled, operation))
            enqueue_ms = (time.perf_counter() - started) * 1000
            confirmed = self._finish_update(operation)
            self._check_update_membership(operation)
            confirmed = confirmed and not operation["errors"]
            if not confirmed:
                self.route_state = "unknown"
                self.qos_state_confirmed = False
                failure = self._operation_failure(operation)
                self.log("qos_mode_change_failed", enabled=enabled,
                         operation_id=operation["id"], failed_switches=failure.failed_switches,
                         controller_flow_programming_ms=round(
                             (time.perf_counter() - started) * 1000, 3),
                         flow_programming_enqueue_ms=round(enqueue_ms, 3),
                         flow_mod_count=operation["flow_mod_count"],
                         barrier_count=operation["barrier_count"],
                         barrier_confirmation_latency_ms_by_switch=operation[
                             "barrier_confirmation_latency_ms_by_switch"],
                         switch_barrier_confirmed=False)
                raise failure
            self.qos_enabled = enabled
            self.qos_state_confirmed = True
            self.route_state = "confirmed"
            active_dpids = sorted(dp.id for dp in datapaths)
            self.log("qos_mode_changed", enabled=enabled, active_dpids=active_dpids,
                     class_rule_count=len(installed), submitted_rule_count=len(installed),
                     controller_flow_programming_ms=round(
                         (time.perf_counter() - started) * 1000, 3),
                     flow_programming_enqueue_ms=round(enqueue_ms, 3),
                     flow_mod_count=operation["flow_mod_count"],
                     barrier_count=operation["barrier_count"],
                     barrier_confirmation_latency_ms_by_switch=operation[
                         "barrier_confirmation_latency_ms_by_switch"],
                     switch_barrier_confirmed=True, operation_id=operation["id"])
            return {"qos_enabled": enabled, "active_dpids": active_dpids,
                    "confirmed": True, "switch_barrier_confirmed": True,
                    "operation_id": operation["id"]}

    @set_ev_cls(ofp_event.EventOFPBarrierReply, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def barrier_reply(self, ev):
        dp, xid = ev.msg.datapath, ev.msg.xid
        key = (id(dp), xid)
        entry = self._pending_requests.get(key)
        if entry is None or entry["kind"] != "barrier":
            self.log("stale_or_unmatched_barrier_reply", dpid=dp.id, xid=xid)
            return
        operation = entry["operation"]
        self._pending_requests.pop(key, None)
        operation["pending_barriers"].discard(key)
        sent_at = entry.get("sent_at")
        if sent_at is not None:
            operation["barrier_confirmation_latency_ms_by_switch"][
                "s{}".format(dp.id)] = round((time.monotonic() - sent_at) * 1000, 3)
        if self.datapaths.get(dp.id) is not dp:
            self._fail_update(operation, dp, "switch disconnected before barrier reply")
        elif not operation["pending_barriers"]:
            operation["event"].set()

    @set_ev_cls(ofp_event.EventOFPErrorMsg, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def openflow_error(self, ev):
        dp, xid = ev.msg.datapath, ev.msg.xid
        entry = self._pending_requests.get((id(dp), xid))
        if entry is None:
            self.log("unmatched_openflow_error", dpid=dp.id, xid=xid,
                     error_type=ev.msg.type, error_code=ev.msg.code)
            return
        self._pending_requests.pop((id(dp), xid), None)
        self._fail_update(entry["operation"], dp,
                          "OpenFlow error type {} code {} for {} request".format(
                              ev.msg.type, ev.msg.code, entry["kind"]))

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def datapath_state_change(self, ev):
        if ev.state == DEAD_DISPATCHER:
            self._datapath_disconnected(ev.datapath, "switch disconnected")

    def _datapath_disconnected(self, dp, reason):
        if self.datapaths.get(dp.id) is dp:
            self.datapaths.pop(dp.id, None)
        if self.ready_datapaths.get(dp.id) is dp:
            self.ready_datapaths.pop(dp.id, None)
        for operation in list(self._active_updates.values()):
            if operation["datapaths"].get(id(dp)) is dp:
                self._fail_update(operation, dp, reason)
        self._refresh_global_state()
        self.log("switch_disconnected", dpid=dp.id, reason=reason,
                 route_state=self.route_state)

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
            body = {"mode": self.app.mode,
                    "active_dpids": sorted(self.app.ready_datapaths),
                    "connected_dpids": sorted(self.app.datapaths),
                    "route_state": self.app.route_state,
                    "route_installation_confirmed": self.app.route_state == "confirmed",
                    "last_route_update": self.app.last_route_update,
                    "route_decision": self.app.route_decision,
                    "qos_enabled": self.app.qos_enabled}
            return Response(content_type="application/json", body=json.dumps(body).encode("utf-8"))
        try:
            payload = json.loads(req.body.decode("utf-8"))
            result = self.app.set_mode(payload["mode"], payload.get("reason", "coordinator"))
            return Response(content_type="application/json", body=json.dumps(result).encode("utf-8"))
        except RouteInstallError as exc:
            body = {"error": str(exc), "operation_id": exc.operation_id,
                    "failed_switches": exc.failed_switches,
                    "switch_barrier_confirmed": False}
            return Response(status=503, content_type="application/json",
                            body=json.dumps(body).encode("utf-8"))
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
                    "qos_state_confirmed": self.app.qos_state_confirmed,
                    "route_state": self.app.route_state,
                    "active_dpids": sorted(self.app.ready_datapaths),
                    "connected_dpids": sorted(self.app.datapaths)}
            return Response(content_type="application/json", body=json.dumps(body).encode("utf-8"))
        try:
            payload = json.loads(req.body.decode("utf-8"))
            result = self.app.set_qos_enabled(payload["enabled"])
            return Response(content_type="application/json", body=json.dumps(result).encode("utf-8"))
        except RouteInstallError as exc:
            body = {"error": str(exc), "operation_id": exc.operation_id,
                    "failed_switches": exc.failed_switches,
                    "switch_barrier_confirmed": False}
            return Response(status=503, content_type="application/json",
                            body=json.dumps(body).encode("utf-8"))
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
