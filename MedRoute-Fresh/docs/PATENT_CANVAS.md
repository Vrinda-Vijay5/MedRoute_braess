# MedRoute Patent Canvas

## Problem

A routing change that appears to add capacity can increase user-equilibrium
cost under congestion. Static shortest-path routing does not provide a
network-wide safety check for this decision.

## Proposed system

A deterministic controller pipeline combines: (1) a Wardrop/Braess candidate
screen, (2) fresh paired route telemetry, (3) criticality-aware queue policy,
(4) discovered topology/component health, and (5) verified OpenFlow actuation
with evidence capture.

## Potentially distinctive aspects

1. Gated topology-change actuation requiring both model/measurement evidence and
   forwarding verification.
2. Preservation of a safe route when candidate cost exceeds a configurable
   threshold.
3. Joint recording of class policy, route decision, receiver metrics, link
   counters, and flow-table proof.
4. Recovery-mode route selection after a failed link while preserving class
   queue policy.
5. An auditable sequence linking topology observations, candidate constraints,
   decision explanation, barrier-confirmed rule installation, and recovery
   timing. This remains a candidate differentiator until prior art is reviewed.

## Prior-art and legal status

This is an engineering canvas, not a patentability opinion. Prior-art search,
claim drafting, inventorship, novelty, and jurisdictional review remain future
legal work.

## Prototype evidence

The latest WSL2 smoke pilot is `artifacts/pilot-20261029T142341Z/`. It records
five traffic scenarios with two repetitions each, a seeded shortcut comparison,
flow-rule verification, receiver-side throughput and route probes, and verified
failure recovery. Required telemetry is complete, but optional candidate
fairness telemetry is missing. This is engineering evidence for a prototype;
it does not establish novelty, inventorship, patentability, clinical value, or
production performance.

## Open disclosure work

Before filing, document the actual inventors and contribution dates, search
relevant prior art, identify the implementation details that are new, and have
counsel review claim scope and jurisdiction. Preserve dated source revisions
and experiment manifests as supporting records. Do not treat this canvas as a
claim set or legal opinion.
