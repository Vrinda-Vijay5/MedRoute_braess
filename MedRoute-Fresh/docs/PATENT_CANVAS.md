# MedRoute Patent Canvas

## Problem

A routing change that appears to add capacity can increase user-equilibrium
cost under congestion. Static shortest-path routing does not provide a
network-wide safety check for this decision.

## Proposed system

A deterministic controller pipeline combines: (1) a Wardrop/Braess candidate
screen, (2) fresh paired route telemetry, (3) criticality-aware queue policy,
and (4) verified OpenFlow actuation with evidence capture.

## Potentially distinctive aspects

1. Gated topology-change actuation requiring both model/measurement evidence and
   forwarding verification.
2. Preservation of a safe route when candidate cost exceeds a configurable
   threshold.
3. Joint recording of class policy, route decision, receiver metrics, link
   counters, and flow-table proof.
4. Recovery-mode route selection after a failed link while preserving class
   queue policy.

## Prior-art and legal status

This is an engineering canvas, not a patentability opinion. Prior-art search,
claim drafting, inventorship, novelty, and jurisdictional review remain future
legal work.

## Enablement evidence

The WSL run in `artifacts/wsl-live-20261022T1858Z/` demonstrates the workflow
with Mininet, Ryu, OpenFlow dumps, receiver-side iperf metrics, and failure
recovery.
