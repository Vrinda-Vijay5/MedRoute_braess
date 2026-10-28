# MedRoute Architecture Canvas

## Purpose

MedRoute is a deterministic, non-ML SDN prototype that screens topology
changes for congestion degradation, classifies synthetic healthcare-shaped
traffic, and enforces selected paths and queues through Ryu/OpenFlow.

## Components

| Layer | Component | Contract |
|---|---|---|
| Input | `healthcare_traffic_profiles.csv` and CICIoMT2024 derived profiles | Reproducible workload metadata; no patient data |
| Policy | `src/criticality.js`, `sdn/classes.json` | Criticality score, class, DSCP, service port, queue |
| Analysis | `src/model.js`, `src/braess_guard.js` | Wardrop equilibrium and candidate screening |
| Coordination | `src/coordinator.js`, `scripts/live_experiment.py` | Fresh paired telemetry and route decision |
| Control | `sdn/controller.py` | Ryu REST API and OpenFlow 1.3 rule installation |
| Data plane | `sdn/topology.py`, OVS/Mininet | Diamond topology, shortcut, recovery route |
| Evidence | `artifacts/<run>/`, `scripts/build_evidence_db.py` | Raw data, logs, flow dumps, SQLite index |
| Presentation | `dashboard/`, Stage 6 plots | Saved evidence visualization |

## Data flow

`catalog/profile -> deterministic class and workload -> Mininet traffic ->
OpenFlow queue/path -> receiver and port telemetry -> guard -> controller
decision -> evidence JSON/SQLite/dashboard`.

## Trust boundaries and limitations

- The dataset is used for aggregate workload parameters, not packet replay.
- Criticality is a synthetic policy input, not a clinical judgment.
- Analytical Wardrop results and live measurements are stored separately.
- A live prevention claim requires complete telemetry, controller recording, and
  matching OpenFlow evidence.
