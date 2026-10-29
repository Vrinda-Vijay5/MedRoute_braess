"""Definitions for the explicit MedRoute routing comparison methods."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple


@dataclass(frozen=True)
class ExperimentMethod:
    """Immutable routing-method policy used by experiment orchestration."""

    method_id: str
    name: str
    initial_route: str
    qos_enabled: bool
    candidate_evaluation_enabled: bool
    braess_guard_enabled: bool
    available: bool
    unavailable_reason: str


_METHODS: Mapping[str, ExperimentMethod] = MappingProxyType({
    "M1": ExperimentMethod(
        method_id="M1",
        name="shortest_path_baseline",
        initial_route="baseline",
        qos_enabled=False,
        candidate_evaluation_enabled=False,
        braess_guard_enabled=False,
        available=True,
        unavailable_reason="",
    ),
    "M2": ExperimentMethod(
        method_id="M2",
        name="qos_only",
        initial_route="baseline",
        qos_enabled=True,
        candidate_evaluation_enabled=False,
        braess_guard_enabled=False,
        available=True,
        unavailable_reason="",
    ),
    "M3": ExperimentMethod(
        method_id="M3",
        name="measured_path_congestion_aware_without_braess_guard",
        initial_route="baseline",
        qos_enabled=True,
        candidate_evaluation_enabled=False,
        braess_guard_enabled=False,
        available=True,
        unavailable_reason="",
    ),
    "M4": ExperimentMethod(
        method_id="M4",
        name="criticality_aware_braess_detection_routing",
        initial_route="baseline",
        qos_enabled=True,
        candidate_evaluation_enabled=True,
        braess_guard_enabled=True,
        available=True,
        unavailable_reason="",
    ),
})


def available_methods() -> Tuple[str, ...]:
    """Return only methods faithfully supported by the live runner."""

    return tuple(method_id for method_id, method in _METHODS.items() if method.available)


def defined_methods() -> Tuple[str, ...]:
    """Return the full requested research catalogue, including unavailable methods."""

    return tuple(_METHODS)


def get_method(method_id: str) -> ExperimentMethod:
    """Return an immutable method policy.

    Raises:
        ValueError: If ``method_id`` is not one of the supported method IDs.
    """

    try:
        return _METHODS[method_id]
    except (KeyError, TypeError) as exc:
        supported = ", ".join(available_methods())
        raise ValueError(
            "unknown experiment method {!r}; expected one of: {}".format(
                method_id, supported
            )
        ) from exc


def build_method_scenario_plan(method_id: str):
    """Return matched scenarios while holding the selected method controls fixed."""
    method = get_method(method_id)
    if not method.available:
        raise ValueError("{} is unavailable: {}".format(method_id, method.unavailable_reason))
    return {
        "normal_load": {
            "qos_enabled": method.qos_enabled,
            "heavy_background": False,
            "bottleneck": False,
        },
        "emergency_surge": {
            "qos_enabled": method.qos_enabled,
            "heavy_background": False,
            "emergency_surge": True,
            "bottleneck": True,
        },
        "mixed_priority_congestion": {
            "qos_enabled": method.qos_enabled,
            "heavy_background": True,
            "bottleneck": True,
        },
    }


__all__ = ["ExperimentMethod", "available_methods", "defined_methods", "get_method", "build_method_scenario_plan"]
