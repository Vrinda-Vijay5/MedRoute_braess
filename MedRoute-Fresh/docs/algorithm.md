# Candidate evaluation algorithm (CBDR prototype)

## Inputs and cost

The evaluator in `sdn/cbdr.py` takes the current route/topology record, candidate route/topology record, measurement timestamps, completeness flag, metrics, optional traffic class, QoS configuration mode, and optional fairness safeguard. A measurement must include latency, jitter, packet loss, a timestamp, and `complete: true`. Missing, invalid, future-dated, or stale samples produce `INCONCLUSIVE` and retain the last verified route.

The compatible demonstration cost remains:

`C = (latency_ms/20 + jitter_ms/5 + packet_loss_pct/1)/3`

The threshold is configured as 0.05. It is a prototype policy threshold. It is not a clinical limit or confidence bound. Relative change is `(candidate_cost - baseline_cost)/baseline_cost`; zero baseline cost is inconclusive.

## Outcomes and safeguards

1. Validate both measurement records and freshness.
2. Compute the existing normalized cost and relative change.
3. If a traffic class is supplied, evaluate each configured objective. A hard violation rejects a candidate even when weighted cost improves. If the baseline also violates it, return `safe_route_exists: false` and describe baseline retention only as a fallback.
4. In strict mode, missing validation provenance or required measurements fails closed.
5. If configured fairness measurements exist, compare Jain indices and apply the declared maximum drop; otherwise record fairness as unavailable.
6. Classify measured change as beneficial, neutral, harmful, or inconclusive. Neutral policy defaults to retaining baseline in standalone CBDR; the current legacy aggregate runner explicitly retains its prior neutral-to-shortcut behavior for compatibility.
7. Return structured reason codes, source/timestamp/age, baseline/candidate costs, actions, and `route_installation_verified: false`. Controller installation is a separate verification stage.

The evaluator labels a degradation `OBSERVED_CANDIDATE_DEGRADATION`. It sets `classical_braess_paradox` to `not_established_by_measured_route_comparison`. A classical claim requires equilibrium assumptions and a separately validated model, such as the Wardrop example in `src/model.js`.

## Limits

The runner's candidate comparison uses aggregate route probes rather than class-tagged baseline and candidate measurements. It currently supplies no `traffic_class` to the evaluator, so no live per-class hard-constraint claim is made. The six service names in `config/healthcare_qos.json` map to four existing live queue classes and their targets remain unvalidated experimental assumptions.
