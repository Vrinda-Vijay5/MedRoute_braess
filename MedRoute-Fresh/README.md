# Braess-Paradox-Aware, Criticality-Constrained Routing in Software-Defined Networks for Life-Critical Healthcare Traffic

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
- Current offline validation on 2026-10-29: Python passed 83/83 after the manifest-runtime fix and Node passed 28/28. Live pilot `artifacts/pilot-20261029T142341Z/` completed five scenarios × two repetitions with validation passing, all flow rules verified, all required telemetry complete, successful 3/3 failure-recovery probes, and six complete profile records. Its two shortcut decisions were one beneficial and one neutral; no harmful shortcut was observed. Optional candidate-evaluation fairness telemetry is unavailable, so all telemetry is not marked complete. Stage 6 tables/plots and the refreshed checksums are saved with the run. This is a single-seed smoke pilot, not a matched M1-M4 study. The earlier pilot `artifacts/research-pilot-20261029T080424Z/` remains separate historical evidence. `data/CICIoMT2024/raw/healthcare_traffic_profiles.csv` is a six-row synthetic healthcare workload catalog, not a raw CICIoMT packet trace.
- Not claimed as live clinical validation: no hospital, patient, or live-production deployment was conducted.
- Needs verification before reuse: any newer runner or data-path change that has not been exercised against live infrastructure.

## Implementation and evidence progress

| Area | Current status | What is actually supported |
|---|---|---|
| M1 shortest-path baseline | Implemented offline | Baseline route with QoS, candidate evaluation, and Braess guard disabled. |
| M2 QoS-aware routing | Implemented offline | Baseline route with QoS enabled and candidate evaluation disabled. |
| M3 congestion-aware routing | Implemented in the live runner; current changes not live-verified | Measures baseline, alternate, and shortcut conditions and selects the lowest measured bottleneck-utilization score without the CBDR guard. |
| M4 CBDR routing | Runner path implemented; current live verification pending | Evaluates named catalog profiles and measured network cost with configured constraints and fairness checks; live inputs and current changes still require validation. |
| Candidate telemetry and barriers | Implemented; historical live evidence exists | Freshness/completeness checks, controller decision recording, flow verification, and barrier-confirmed installation are represented. |
| Queue occupancy | Implemented with explicit unavailable state | Uses `tc` class backlog counters; missing counters remain incomplete rather than fabricated. |
| Seeded workloads | Implemented | `--seed` is recorded and deterministically perturbs synthetic offered rates. |
| Ablation controls | Implemented in runner CLI | M4 supports disabling Braess detection, priority handling, or candidate-link evaluation; matched live ablation results are pending. |
| Four-method matched study | Pending | No saved matrix comparing M1–M4 under identical seeds, topology, workload, and repetitions has been verified. |
| Topology playground | Simulation-only, implemented | Dashboard graph editing, node/link removal, JSON import/export, topology validation, link toggles, and disconnected-route handling use a separate in-memory graph; this does not configure Mininet. |
| Clinical or production validation | Not implemented / not claimed | The project is a networking prototype, not a medical validation study. |

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

### 3a. Research metrics and scenario coverage

The live scenario summary now derives per-class p95/p99 RTT, deadline-miss rate,
packet-loss objective status, and Jain throughput fairness from the saved raw
probe and receiver measurements. These are emitted with sample counts in
`scenario_results.json` and included in the generated report. A missing target
or missing measurement is reported as unavailable, never as a pass. Controller
route-change telemetry records actual mode changes, per-switch flow-programming
requests, submitted rule counts, and controller-side programming-call time in
`controller.jsonl`. Route and QoS update calls now wait cooperatively for all
required OpenFlow barrier replies with a bounded timeout. Their wall time
includes the barrier wait; it is not a per-switch acknowledgement latency.

`sdn/classes.json` now names the prototype traffic mappings and provides
explicit delay, loss, and reliability targets. They are policy assumptions for
experiment wiring only; the file labels them as requiring validation against
the selected application's requirements and applicable standards. They are
not clinical service guarantees. The current class mapping remains four
classes, so video/EHR/imaging/backup are grouped rather than independently
validated.

The current runner contains normal-load, emergency-surge, mixed-priority
congestion, shortcut-evaluation, and primary-link failure-recovery paths. It
also exposes M1 shortest-path, M2 QoS-only, M3 congestion-aware, and M4 CBDR
method paths, plus M4 ablation controls. The repository has not yet produced a
matched live M1-M4 multi-topology/multi-seed study or completed live ablation
matrix, so those remain pending and are not inferred from historical artifacts.
The intended comparison reports deadline misses, p95/p99, recovery time and
loss, route changes, controller overhead, Jain fairness, queue occupancy where
`tc` exposes it, and uncertainty across independent seeds. The illustrative
table from the project brief is not used as data. Use `--repetitions N` and
`--seed N` with `scripts/live_experiment.py`; both values are saved in the run
configuration. Repetitions without different seeds are not independent
replications.

`config/healthcare_qos.json` adds six named healthcare workload profiles mapped
onto the existing four live policy classes. Its service targets are explicitly
unvalidated experimental assumptions. `sdn/cbdr.py` returns structured
beneficial/neutral/harmful/inconclusive/constraint-violation decisions, reason
codes, freshness and completeness details, and a separate controller action.
The live candidate probes are aggregate; they do not support per-class
constraint claims. Neutral policy in the standalone evaluator retains baseline;
the legacy runner preserves its prior neutral-route behavior.

The method catalogue exposes four distinct runner paths. M1 uses the baseline
route without QoS or candidate evaluation. M2 uses the baseline route with QoS.
M3 measures baseline, alternate, and shortcut route conditions and selects from
their congestion scores without CBDR. M4 measures each catalog profile before
and after the shortcut, evaluates the CBDR objective, hard-constraint status,
fairness, and network cost, then verifies the selected route. These paths are
implemented and unit-tested, but the complete live comparison remains
unverified. See `docs/experimental_methodology.md`.

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
- `profile_version`: not defined in the supplied profile; runtime fallback is `unspecified`
- `source_kind`: not defined in the supplied profile; runtime fallback is `training-derived aggregate profile`
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
- per-class tail RTT, configurable deadline/loss objective checks, and Jain throughput fairness in scenario statistics
- controller route-update and install-time telemetry
- class-based QoS queueing as configured in `sdn/classes.json`
- controlled route failure/recovery checks
- evidence generation and artifact storage under `artifacts/`
- analytical Braess cost model
- offline unit testing for policy and scenario helpers
- modular candidate-route evaluation with explicit telemetry and constraint status
- six-profile versioned QoS mapping to the current four queue classes
- per-run manifests and SHA-256 lists for new live runs

### Open or needs-verification items

- full live replay / package setup on every machine
- explicit validation of all newer method-policy branches under live Ryu/Mininet conditions
- matched live validation for M1-M4, ablations, multi-seed sweeps, and resume support
- metadata provenance cleanup when the preferred profile file is absent
- distinction between analytical results and live measured results in every user-facing explanation
- any future ML component would need a dedicated, leakage-safe dataset and separate validation plan; it is not part of the current implementation

## Running the project safely

The repository should be treated as an offline + live hybrid prototype. The workflow is:

1. review code and saved evidence
2. run offline unit checks when appropriate
3. run the live Mininet/Ryu workflow only in a controlled environment
4. inspect saved `summary.json`, `scenario_results.json`, and `controller.jsonl` before making claims

Use the controlled pilot command in `docs/reproducibility.md` only in the configured WSL environment. This README does not claim a live run for code changes unless a new run directory contains complete measurements and forwarding evidence.

Start the evidence dashboard from the repository root with `npm run dashboard`, then open `http://127.0.0.1:8765`. The simulation-only topology editor is at `http://127.0.0.1:8765/playground`; its in-memory graph does not change Mininet or persist after the dashboard server stops. Run the Node checks with `npm test`. In the configured WSL environment, run Python checks with `PYTHONDONTWRITEBYTECODE=1 /home/subiw/ryu-env/bin/python -m unittest discover -s test -v`.

## Summary

MedRoute AI is a rule-based, deterministic SDN prototype that demonstrates healthcare-style traffic prioritization, route-cost comparison, and harmful-shortcut detection in an analytical and network-emulated environment. The project has a real evidence trail and a separate analytical Braess model, but it is not a clinical system, not a production deployment, and not an ML-based controller.

The current two-repetition WSL2 pilot records one harmful candidate being prevented by selecting the baseline route, alongside one neutral comparison where the shortcut was accepted. These outcomes apply only to the saved synthetic workload and setup. The project should be presented as a prototype and research artifact, not as a guaranteed prevention mechanism for all networks.
