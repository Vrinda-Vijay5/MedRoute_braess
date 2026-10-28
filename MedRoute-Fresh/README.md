# MedRoute AI: a Braess-paradox-aware SDN framework for prioritized healthcare traffic

## Purpose and scope

MedRoute AI is a deterministic SDN prototype for investigating whether a measured route-cost policy can avoid harmful topology shortcuts in a healthcare-shaped traffic scenario. The project is intentionally not a trained ML model and does not claim clinical deployment or production safety.

The implementation combines:

- Ryu SDN control logic
- OpenFlow 1.3 forwarding and queue actions
- Mininet + Open vSwitch topology emulation
- deterministic class scoring and policy assignment
- QoS-based prioritization for four traffic classes
- explicit baseline/shortcut/recovery route evaluation
- analytical Braess modeling separate from live forwarding evidence
- saved scenario evidence and dashboard inspection

This document reflects the actual repository state and must be read as a status report, not a marketing summary.

## Verified project status

Current implementation status is best described as:

- Implemented and inspected: deterministic controller logic, QoS configuration, topology, analysis helpers, scenario runner, evidence outputs, and tests.
- Verified by saved evidence: harmful-shortcut prevention on the historical WSL run in `artifacts/wsl-final-20261023T0015Z/`.
- Verified by analytical model: Braess paradox example in `artifacts/analytical-review-20261028/`.
- Verified by repository tests: the offline Python suite passed in the current session with 40 tests passing and 0 failures.
- Not claimed as live clinical validation: no hospital, patient, or live-production deployment was conducted.
- Needs verification before reuse: any newer runner or data-path change that has not been exercised against live infrastructure.

## Architecture and implemented components

### 1. SDN topology and route selection

The live network topology is the four-switch diamond used throughout the project:

- `sdn/topology.py` defines the switch topology and the optional S2-S3 shortcut link.
- `sdn/routes.json` defines the baseline route and alternative route sets used by the controller.
- The live experiment uses a controlled link-failure recovery path that temporarily disables the S1-S2 link and re-routes through the recovery path before restoring the normal topology.

All live routing is deterministic. There is no trained traffic model or learned route policy in the current implementation.

### 2. Traffic classification and QoS

The live controller reads class metadata from `sdn/classes.json` and applies policy by precedence:

1. transport port / service port
2. IPv4 DSCP
3. default class fallback

The actual class definitions in the current repository are:

| Traffic class | DSCP | UDP/TCP port | Queue ID | Notes |
|---|---:|---:|---:|---|
| ECG | 46 | 5101 | 1 | highest priority |
| ICU | 34 | 5102 | 2 | high priority |
| WEARABLE | 18 | 5103 | 3 | medium priority |
| BACKGROUND | 0 | 5104 | 4 | default traffic |

The repository also preserves a deterministic criticality formula in `src/criticality.js`:

`100 * (0.6 * latencySensitivity + 0.4 * lossSensitivity)`

This is not a medical diagnosis model. It is a policy score used to order traffic classes, not a patient-clinical classifier.

The queue ordering is intended to match the class priority order. The live route and QoS logic are policy-driven and explicit, not ML-based.

### 3. Route-cost decision logic

The route-cost equation implemented by the live runner is:

`(latency_ms / 20 + jitter_ms / 5 + packet_loss_pct / 1) / 3`

This is a composite demonstration cost, not a clinical metric and not an SLA. It is used to compare a baseline route against the shortcut route or a prevention route.

The implemented decision policy is:

- harmful: shortcut cost exceeds baseline by more than 5%
- beneficial: shortcut cost is more than 5% below baseline
- neutral: cost difference falls within the 5% band
- inconclusive: missing, stale, or incomplete measurements

The implementation records the decision and the route chosen; a harmful-shortcut decision must still be backed by complete follow-up telemetry and verified forwarding evidence before it is treated as a prevention success.

### 4. Controller and evidence system

The project records:

- `controller.jsonl` controller telemetry
- `scenario_results.json` scenario summaries
- `decisions.json` route decisions
- `measurements.json` per-stage measurement records
- `failure_recovery.json` recovery details
- `flows_*.txt` OpenFlow flow dumps
- `plot_*.png` latency, jitter, loss, throughput plots
- `experiment_report.md` generated summary
- `evidence.sqlite` derived evidence database

The evidence system is designed to keep the run reproducible and auditable. Saved histories are under `artifacts/<timestamp>/`.

## CICIoMT2024 integration and provenance

The project intentionally uses CICIoMT2024 only as a source of aggregate, training-derived traffic profiles used to shape synthetic load. It does not replay raw packet captures and does not infer clinical labels from dataset features.

### Current metadata status

The preferred file `data/CICIoMT2024/processed/workload_profiles.json` was not found in the inspected working tree. The repository adapter therefore falls back to `data/CICIoMT2024/processed/benign_training_profile.json` when loading profiles.

The saved evidence bundle records the fallback provenance and explicitly notes that the source profile metadata may be missing or unspecified. This is a documentation/provenance issue, not an indication of a hidden live model.

### Verified dataset facts

The current workload profile file used by the repo contains:

- dataset: `CICIoMT2024`
- training split: `train`
- benign-only aggregate profile design
- `profile_version`: present in the supplied profile as `ciciomt-benign-v1`
- `source_kind`: present in the supplied profile as `benign IoMT traffic characterization`
- SHA-256 of the supplied profile: `a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c`

The project uses two aggregate training profiles:

- `ciciomt-benign-train-typical`
- `ciciomt-benign-train-high`

These are used to create synthetic offered rates and UDP packet sizes. They are not patient measurements or raw packet traces.

### Important limitations

The dataset-derived profiles are intentionally used to parameterize synthetic scenario traffic. The project explicitly does not claim:

- packet-level replay of real traffic
- clinical label inference
- patient physiological monitoring
- medical-grade validation

This project is a networking and routing prototype using healthcare-shaped traffic classes, not a clinical decision system.

## Historical live-experiment evidence

The most important saved live run is:

- `artifacts/wsl-final-20261023T0015Z/`

The summary records:

- `live_experiment`: `harmful_shortcut_prevented`
- `live_prevention_verified`: `true`
- `shortcut_verdict`: `harmful`
- `selected_route`: `baseline`
- `braess_prevention_verified_repetitions`: `2`
- `scenario_validation_passed`: `true`
- `scenario_validation_errors`: `[]`

The run also reports:

- 4 scenarios
- 3 repetitions per scenario
- 12 scenario repetitions
- 6 catalog profiles in the synthetic traffic catalog
- successful recovery check after S1-S2 failure
- 3 packets transmitted, 3 received, 0% packet loss in the recovery probe

Measured route-cost values captured in the summary are:

- baseline: `3.518333333333333`
- shortcut: `4.015`
- prevention route: `3.4676666666666667`

These are dimensionless composite costs under the implemented route-cost equation. They are not milliseconds.

The route-decision reason recorded by the run states that the shortcut cost exceeded the baseline by more than the 5% threshold, and the controller selected `baseline`.

## QoS and congestion evidence from the saved report

The saved summary report at `artifacts/wsl-final-20261023T0015Z/experiment_report.md` records four scenarios with three repetitions each:

1. `baseline_no_prioritization`
2. `class_prioritization_no_congestion`
3. `heavy_background_no_prioritization`
4. `heavy_background_with_prioritization`

For the heavy-background scenario, the report records mean packet loss across the three repetitions:

| Class | Without prioritization | With prioritization |
|---|---:|---:|
| ECG | 17.333% | 0% |
| ICU | 17.000% | 0% |
| WEARABLE | 16.667% | 0% |
| BACKGROUND | 40.667% | 89.000% |

This is a result from the specific saved simulation report and must be interpreted carefully. It shows that in this measured synthetic scenario, priority classes had lower loss while the background class had higher loss under prioritization. It does not generalize to all networks or establish clinical safety.

The report also includes latency, throughput, jitter, and packet-loss means and sample standard deviations. These values were recorded for the specific synthetic workload and cannot be assumed to transfer to a real hospital network.

## Analytical Braess model

The analytical model is stored under:

- `artifacts/analytical-review-20261028/`

The report records:

- demand: `4000`
- baseline equilibrium cost: `65`
- shortcut equilibrium cost: `80`
- change: `23.08%`
- verdict: `harmful`

This is a mathematical Wardrop demonstration of a Braess paradox scenario; it remains separate from any live Mininet forwarding evidence. The analytical review proves the example under the model, not that the live network always fails under the same conditions.

## Current project status and known issues

### Implemented and supported

- deterministic route selection and policy evaluation
- class-based QoS queueing as configured in `sdn/classes.json`
- controlled route failure/recovery checks
- evidence generation and artifact storage under `artifacts/`
- analytical Braess cost model
- offline unit testing for policy and scenario helpers

### Open or needs-verification items

- full live replay / package setup on every machine
- explicit validation of all newer method-policy branches under live Ryu/Mininet conditions
- metadata provenance cleanup when the preferred profile file is absent
- distinction between analytical results and live measured results in every user-facing explanation
- any future ML component would need a dedicated, leakage-safe dataset and separate validation plan; it is not part of the current implementation

## Running the project safely

The repository should be treated as an offline + live hybrid prototype. The workflow is:

1. review code and saved evidence
2. run offline unit checks when appropriate
3. run the live Mininet/Ryu workflow only in a controlled environment
4. inspect saved `summary.json`, `scenario_results.json`, and `controller.jsonl` before making claims

No live Mininet, OVS, or traffic generation should be started without an explicit, environment-ready execution step. This README intentionally avoids claiming revalidation of any step that has not been performed in the current environment.

## Summary

MedRoute AI is a rule-based, deterministic SDN prototype that demonstrates healthcare-style traffic prioritization, route-cost comparison, and harmful-shortcut detection in an analytical and network-emulated environment. The project has a real evidence trail and a separate analytical Braess model, but it is not a clinical system, not a production deployment, and not an ML-based controller.

The strongest implemented claim supported by saved evidence is that the historical WSL run in `artifacts/wsl-final-20261023T0015Z/` records a harmful shortcut being prevented by selecting the baseline route under the project’s measured conditions. The project should be presented as a prototype and research artifact, not as a guaranteed prevention mechanism for all networks.
t is saved as
`failure_recovery.json`; a failed or incomplete recovery check fails the live run.
