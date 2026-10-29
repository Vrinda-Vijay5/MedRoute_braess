"""Measured candidate-route evaluation for the MedRoute CBDR prototype.

Observed performance degradation is deliberately distinguished from a formal
Braess paradox, which requires an equilibrium model and assumptions.
"""
import json
import math
from pathlib import Path


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "healthcare_qos.json"
METRIC_RANGES = {
    "latency_ms": (0, math.inf),
    "jitter_ms": (0, math.inf),
    "packet_loss_pct": (0, 100),
    "reliability_pct": (0, 100),
    "throughput_mbps": (0, math.inf),
}


class ConfigurationError(ValueError):
    pass


def load_config(path=DEFAULT_CONFIG):
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("cannot load healthcare QoS configuration: {}".format(exc)) from exc
    validate_config(config)
    return config


def validate_config(config):
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ConfigurationError("schema_version 1 configuration is required")
    if config.get("configuration_mode") not in ("experimental", "strict"):
        raise ConfigurationError("configuration_mode must be experimental or strict")
    threshold = config.get("candidate_degradation_threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold < 0:
        raise ConfigurationError("candidate_degradation_threshold must be finite and non-negative")
    classes = config.get("classes")
    if not isinstance(classes, dict) or not classes:
        raise ConfigurationError("classes must be a non-empty object")
    priorities = []
    for name, profile in classes.items():
        if not isinstance(profile, dict) or not isinstance(profile.get("objectives"), dict):
            raise ConfigurationError("{} must include an objectives object".format(name))
        priority = profile.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 1:
            raise ConfigurationError("{} has invalid priority".format(name))
        priorities.append(priority)
        score = profile.get("criticality_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
            raise ConfigurationError("{} has invalid criticality_score".format(name))
        objectives = profile["objectives"]
        if not isinstance(objectives.get("hard_constraint"), bool) or not isinstance(objectives.get("validated"), bool):
            raise ConfigurationError("{} must declare hard_constraint and validated".format(name))
        for metric in ("max_latency_ms", "max_jitter_ms", "max_packet_loss_pct", "min_throughput_mbps", "min_reliability_pct"):
            value = objectives.get(metric)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                raise ConfigurationError("{}.{} must be null or a finite non-negative number".format(name, metric))
    if len(priorities) != len(set(priorities)):
        raise ConfigurationError("class priorities must be unique")


def _valid_metrics(record, now, max_age_seconds):
    if not isinstance(record, dict):
        return None, "missing_measurement"
    stamp = record.get("timestamp")
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
        return None, "missing_or_invalid_timestamp"
    age = now - stamp
    if age < 0 or age > max_age_seconds:
        return None, "stale_or_future_measurement"
    metrics = record.get("metrics")
    if not isinstance(metrics, dict) or record.get("complete") is not True:
        return None, "incomplete_measurement"
    normalized = {}
    for name, (minimum, maximum) in METRIC_RANGES.items():
        value = metrics.get(name)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
            return None, "invalid_{}_measurement".format(name)
        normalized[name] = float(value)
    if not all(key in normalized for key in ("latency_ms", "jitter_ms", "packet_loss_pct")):
        return None, "missing_cost_metric"
    normalized["cost"] = (normalized["latency_ms"] / 20.0 + normalized["jitter_ms"] / 5.0 + normalized["packet_loss_pct"]) / 3.0
    return {"metrics": normalized, "timestamp": stamp, "age_seconds": age,
            "source": record.get("source", "measured")}, None


def _objective_violations(profile, metrics):
    objectives = profile["objectives"]
    checks = (("max_latency_ms", "latency_ms", "gt"),
              ("max_jitter_ms", "jitter_ms", "gt"),
              ("max_packet_loss_pct", "packet_loss_pct", "gt"),
              ("min_throughput_mbps", "throughput_mbps", "lt"),
              ("min_reliability_pct", "reliability_pct", "lt"))
    results = []
    missing = []
    for target_name, metric_name, comparison in checks:
        target = objectives.get(target_name)
        if target is None:
            continue
        if metric_name not in metrics:
            missing.append(metric_name)
            continue
        violated = metrics[metric_name] > target if comparison == "gt" else metrics[metric_name] < target
        results.append({"metric": metric_name, "target": target, "observed": metrics[metric_name],
                        "violated": violated})
    return results, missing


def evaluate_candidate(*, current, candidate, traffic_class=None, config=None,
                       now=None, max_age_seconds=30, constraint_mode=None,
                       neutral_policy=None, fairness_policy=None):
    """Evaluate a measured route/topology pair and return an auditable decision.

    Each measurement has ``timestamp``, ``complete``, ``source``, and ``metrics``.
    Supported sources are recorded as supplied; this function never fabricates
    measurements. ``strict`` mode requires validated hard objectives.
    """
    config = load_config() if config is None else config
    validate_config(config)
    now = __import__("time").time() if now is None else now
    mode = constraint_mode or config["configuration_mode"]
    if mode not in ("experimental", "strict"):
        raise ConfigurationError("constraint_mode must be experimental or strict")
    threshold = config["candidate_degradation_threshold"]
    policy = neutral_policy or config.get("neutral_policy", "retain_baseline")
    if policy not in ("retain_baseline", "accept_candidate"):
        raise ConfigurationError("neutral_policy must be retain_baseline or accept_candidate")
    if fairness_policy is not None:
        max_drop = fairness_policy.get("max_drop") if isinstance(fairness_policy, dict) else None
        if (isinstance(max_drop, bool) or not isinstance(max_drop, (int, float)) or
                not math.isfinite(max_drop) or not 0 <= max_drop <= 1):
            raise ConfigurationError("fairness_policy.max_drop must be between 0 and 1")

    result = {
        "current_topology": current.get("topology") if isinstance(current, dict) else None,
        "current_route": current.get("route") if isinstance(current, dict) else None,
        "candidate_topology": candidate.get("topology") if isinstance(candidate, dict) else None,
        "candidate_route": candidate.get("route") if isinstance(candidate, dict) else None,
        "traffic_class": traffic_class,
        "criticality_score": None,
        "measurement_source": {"current": None, "candidate": None},
        "measurement_timestamps": {"current": None, "candidate": None},
        "measurement_ages_seconds": {"current": None, "candidate": None},
        "baseline_cost": None, "candidate_cost": None, "relative_change": None,
        "constraint_violations": [], "missing_constraints": [],
        "fairness": {"status": "unavailable"},
        "classification": "inconclusive", "decision": "retain_baseline",
        "reason_code": None, "explanation": None,
        "classical_braess_paradox": "not_established_by_measured_route_comparison",
        "controller_action": "retain_last_verified_route",
        "route_installation_verified": False,
    }
    current_valid, current_error = _valid_metrics(current, now, max_age_seconds)
    candidate_valid, candidate_error = _valid_metrics(candidate, now, max_age_seconds)
    for label, value in (("current", current_valid), ("candidate", candidate_valid)):
        if value:
            result["measurement_source"][label] = value["source"]
            result["measurement_timestamps"][label] = value["timestamp"]
            result["measurement_ages_seconds"][label] = value["age_seconds"]
    if current_error or candidate_error:
        error = current_error or candidate_error
        result["reason_code"] = "TELEMETRY_" + error.upper()
        result["explanation"] = "Candidate evaluation is inconclusive because {} telemetry is {}.".format(
            "current" if current_error else "candidate", error.replace("_", " "))
        return result

    base = current_valid["metrics"]
    proposed = candidate_valid["metrics"]
    result["baseline_cost"], result["candidate_cost"] = base["cost"], proposed["cost"]
    result["relative_change"] = ((proposed["cost"] - base["cost"]) / base["cost"]
                                 if base["cost"] > 0 else None)
    profile = config["classes"].get(traffic_class) if traffic_class else None
    if traffic_class and profile is None:
        result["reason_code"] = "UNKNOWN_TRAFFIC_CLASS"
        result["explanation"] = "Traffic class is not present in the versioned QoS configuration."
        return result
    if profile:
        result["criticality_score"] = profile.get("criticality_score")
        candidate_checks, candidate_missing = _objective_violations(profile, proposed)
        baseline_checks, baseline_missing = _objective_violations(profile, base)
        hard = profile["objectives"].get("hard_constraint") is True
        validated = profile["objectives"].get("validated") is True
        result["objective_checks"] = candidate_checks
        result["missing_constraints"] = candidate_missing
        result["baseline_objective_checks"] = baseline_checks
        if hard and any(check["violated"] for check in candidate_checks) and (mode != "strict" or validated):
            result["constraint_violations"] = [check for check in candidate_checks if check["violated"]]
        if mode == "strict" and (not hard or not validated):
            result["classification"] = "inconclusive"
            result["reason_code"] = "STRICT_CONSTRAINT_NOT_VALIDATED"
            result["explanation"] = "Strict mode fails closed because this class has no validated hard-constraint profile."
            return result
        if mode == "strict" and hard and candidate_missing:
            result["classification"] = "inconclusive"
            result["reason_code"] = "STRICT_CONSTRAINT_MEASUREMENT_MISSING"
            result["explanation"] = "Strict mode fails closed because a required constraint measurement is unavailable."
            return result
    if result["constraint_violations"]:
        result["classification"] = "constraint_violation"
        result["decision"] = "reject_candidate"
        result["reason_code"] = "HARD_CONSTRAINT_VIOLATION"
        result["explanation"] = "The candidate violates a configured hard service constraint; the weighted cost cannot override it."
        result["controller_action"] = "retain_baseline_fallback_not_guaranteed_safe"
        baseline_violation = bool(profile and any(item["violated"] for item in baseline_checks))
        result["safe_route_exists"] = not baseline_violation
        return result

    if fairness_policy:
        base_fairness = current.get("jain_fairness") if isinstance(current, dict) else None
        candidate_fairness = candidate.get("jain_fairness") if isinstance(candidate, dict) else None
        max_drop = fairness_policy.get("max_drop")
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1
               for value in (base_fairness, candidate_fairness)):
            drop = base_fairness - candidate_fairness
            result["fairness"] = {"status": "measured", "metric": "Jain fairness index",
                                  "baseline": base_fairness, "candidate": candidate_fairness,
                                  "drop": drop, "max_drop": max_drop}
            if isinstance(max_drop, (int, float)) and drop > max_drop:
                result["classification"] = "constraint_violation"
                result["decision"] = "reject_candidate"
                result["reason_code"] = "FAIRNESS_GUARDRAIL_VIOLATION"
                result["explanation"] = "Candidate fairness degradation exceeds the configured safeguard."
                return result
        else:
            result["fairness"] = {"status": "unavailable", "reason": "missing_or_invalid_fairness_measurement"}

    if base["cost"] == 0:
        result["reason_code"] = "ZERO_BASELINE_COST"
        result["explanation"] = "Relative degradation is undefined for a zero baseline cost."
        return result
    relative = result["relative_change"]
    if relative > threshold:
        classification, reason = "harmful", "OBSERVED_CANDIDATE_DEGRADATION"
        decision = "reject_candidate"
        explanation = "Measured candidate cost is more than the configured degradation threshold above baseline."
    elif relative < -threshold:
        classification, reason = "beneficial", "OBSERVED_CANDIDATE_IMPROVEMENT"
        decision = "accept_candidate"
        explanation = "Measured candidate cost is more than the configured threshold below baseline."
    else:
        classification, reason = "neutral", "OBSERVED_CHANGE_WITHIN_NEUTRAL_BAND"
        decision = "accept_candidate" if policy == "accept_candidate" else "retain_baseline"
        explanation = "Measured change is within the configured neutral band; policy is {}.".format(policy)
    result.update({"classification": classification, "decision": decision,
                   "reason_code": reason, "explanation": explanation,
                   "controller_action": "request_candidate_route" if decision == "accept_candidate"
                       else "retain_last_verified_route",
                   "safe_route_exists": True})
    return result


def _jain(values):
    denominator = len(values) * sum(value * value for value in values)
    return (sum(values) ** 2 / denominator) if values and denominator > 0 else None


def evaluate_class_aware_candidate(*, current_by_class, candidate_by_class,
                                   current_network_cost_pct,
                                   candidate_network_cost_pct, config=None,
                                   current_fairness=None, candidate_fairness=None,
                                   now=None, max_age_seconds=120):
    """Evaluate a topology change across measured named healthcare profiles.

    The aggregate objective normalizes per-profile delay/jitter and loss, gives
    higher-criticality profiles larger weights, counts configured hard-target
    violations, and includes maximum observed link utilization. A hard
    violation cannot be traded for a lower weighted score. Targets are only
    as authoritative as their provenance in the input configuration.
    """
    config = load_config() if config is None else config
    validate_config(config)
    now = __import__("time").time() if now is None else now
    weights = config.get("objective_weights", {})
    required_weights = ("critical_delay_jitter", "critical_packet_loss",
                        "qos_violations", "network_congestion")
    if (any(not isinstance(weights.get(key), (int, float)) or
            isinstance(weights.get(key), bool) or not math.isfinite(weights[key]) or
            weights[key] < 0 for key in required_weights) or
            not math.isclose(sum(weights[key] for key in required_weights), 1.0,
                             rel_tol=1e-9, abs_tol=1e-9)):
        raise ConfigurationError("objective_weights must be non-negative and sum to one")
    output = {"algorithm": "CBDR", "classification": "inconclusive",
              "decision": "retain_baseline", "reason_code": None,
              "explanation": None, "current_objective": None,
              "candidate_objective": None, "relative_change": None,
              "current_network_cost_pct": current_network_cost_pct,
              "candidate_network_cost_pct": candidate_network_cost_pct,
              "class_evaluations": {}, "baseline_hard_violations": [],
              "candidate_hard_violations": [], "safe_route_exists": None,
              "fairness": {"status": "unavailable"},
              "route_installation_verified": False}
    names = list(config["classes"])
    missing = [name for name in names if name not in current_by_class or
               name not in candidate_by_class]
    if missing:
        output.update(reason_code="MISSING_CLASS_MEASUREMENTS",
                      explanation="Candidate evaluation lacks complete current/candidate records for: " +
                      ", ".join(missing))
        return output
    costs = {"current": 0.0, "candidate": 0.0}
    violation_weights = {"current": 0.0, "candidate": 0.0}
    criticality_total = sum(config["classes"][name]["criticality_score"] for name in names)
    if criticality_total <= 0:
        raise ConfigurationError("class criticality scores must have a positive total")
    for name in names:
        profile = config["classes"][name]
        before = current_by_class[name]
        after = candidate_by_class[name]
        pair = evaluate_candidate(current=before, candidate=after,
            traffic_class=name, config=config, now=now,
            max_age_seconds=max_age_seconds, constraint_mode="experimental",
            neutral_policy="retain_baseline")
        output["class_evaluations"][name] = pair
        if pair["classification"] == "inconclusive":
            output.update(reason_code="INCOMPLETE_CLASS_TELEMETRY",
                explanation="CBDR retains the baseline because class {} cannot be evaluated: {}".format(
                    name, pair.get("reason_code")))
            return output
        normalized_weight = profile["criticality_score"] / criticality_total
        for side, record, metric_name in (("current", before, "current"),
                                          ("candidate", after, "candidate")):
            metrics = record["metrics"]
            objectives = profile["objectives"]
            delay_ref = objectives.get("max_latency_ms") or config.get("objective_references", {}).get("latency_ms", 250)
            jitter_ref = objectives.get("max_jitter_ms") or config.get("objective_references", {}).get("jitter_ms", 25)
            loss_ref = objectives.get("max_packet_loss_pct") or config.get("objective_references", {}).get("packet_loss_pct", 1)
            delay_jitter = .5 * (metrics["latency_ms"] / delay_ref +
                                 metrics["jitter_ms"] / jitter_ref)
            loss = metrics["packet_loss_pct"] / loss_ref
            checks = pair.get("objective_checks", []) if side == "candidate" else pair.get("baseline_objective_checks", [])
            hard_count = sum(bool(check["violated"]) for check in checks
                             if objectives.get("hard_constraint") is True)
            costs[side] += normalized_weight * (
                weights["critical_delay_jitter"] * delay_jitter +
                weights["critical_packet_loss"] * loss)
            violation_weights[side] += normalized_weight * hard_count
            if hard_count:
                key = "candidate_hard_violations" if side == "candidate" else "baseline_hard_violations"
                output[key].append({"traffic_class": name, "count": hard_count})
    for side, value in (("current", current_network_cost_pct),
                        ("candidate", candidate_network_cost_pct)):
        if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                not math.isfinite(value) or value < 0):
            output.update(reason_code="INVALID_NETWORK_COST",
                          explanation="CBDR requires measured non-negative path/network utilization.")
            return output
        costs[side] += weights["network_congestion"] * value / 100.0
        costs[side] += weights["qos_violations"] * violation_weights[side]
    base, proposed = costs["current"], costs["candidate"]
    relative = (proposed - base) / base if base > 0 else None
    output["current_objective"], output["candidate_objective"] = base, proposed
    output["relative_change"] = relative
    output["safe_route_exists"] = not output["baseline_hard_violations"] and not output["candidate_hard_violations"]
    if current_fairness is not None and candidate_fairness is not None:
        fairness = {"status": "measured", "current": current_fairness,
                    "candidate": candidate_fairness,
                    "drop": current_fairness - candidate_fairness,
                    "max_drop": config.get("fairness_max_drop", 0.1)}
        output["fairness"] = fairness
        if fairness["drop"] > fairness["max_drop"]:
            output.update(classification="constraint_violation", decision="reject_candidate",
                reason_code="FAIRNESS_GUARDRAIL_VIOLATION",
                explanation="Candidate normalized-delivery fairness degradation exceeds the configured safeguard.")
            return output
    if output["candidate_hard_violations"]:
        baseline_count = sum(row["count"] for row in output["baseline_hard_violations"])
        candidate_count = sum(row["count"] for row in output["candidate_hard_violations"])
        if output["baseline_hard_violations"] and candidate_count < baseline_count and proposed < base:
            output.update(classification="constraint_violation", decision="accept_candidate",
                reason_code="INFEASIBLE_BOTH_ROUTES_CANDIDATE_REDUCES_VIOLATIONS",
                explanation="Neither route meets all configured targets; the candidate reduces violations and weighted cost.")
        else:
            output.update(classification="constraint_violation", decision="reject_candidate",
                reason_code="HARD_CONSTRAINT_VIOLATION",
                explanation="The candidate introduces or does not reduce hard QoS violations; retain baseline.")
        output["safe_route_exists"] = False
        return output
    if base <= 0 or relative is None:
        output.update(reason_code="ZERO_BASELINE_OBJECTIVE",
                      explanation="Relative candidate cost is undefined for a zero baseline objective.")
        return output
    threshold = config["candidate_degradation_threshold"]
    if relative > threshold:
        output.update(classification="harmful", decision="reject_candidate",
                      reason_code="WEIGHTED_CBDR_OBJECTIVE_DEGRADATION",
                      explanation="The criticality-weighted delay/loss/violation/congestion objective worsened beyond threshold.")
    elif relative < -threshold:
        output.update(classification="beneficial", decision="accept_candidate",
                      reason_code="WEIGHTED_CBDR_OBJECTIVE_IMPROVEMENT",
                      explanation="The criticality-weighted objective improved beyond threshold.")
    else:
        output.update(classification="neutral", decision="retain_baseline",
                      reason_code="WEIGHTED_CBDR_OBJECTIVE_WITHIN_THRESHOLD",
                      explanation="The objective change is within the neutral band; retain baseline.")
    return output


__all__ = ["ConfigurationError", "load_config", "validate_config", "evaluate_candidate",
           "evaluate_class_aware_candidate"]
