# Results and project status (2026-10-29)

## Software validation

Latest validation on 2026-10-29 passed 83 Python tests and 28 Node tests, including simulation topology API and playground coverage. Software tests do not establish network performance. WSL has Mininet, OVS, and Ryu 4.34.

## Latest two-repetition live pilot

Run [`pilot-20261029T142341Z`](../artifacts/pilot-20261029T142341Z/) completed in WSL2 with workload seed `1526175684`. It contains two complete repetitions for each of five scenarios: baseline without prioritization, prioritization without congestion, emergency surge, heavy background without prioritization, and heavy background with prioritization. Scenario validation passed with no errors. Flow rules were verified; required telemetry was complete; six of six catalog profiles were complete. Failure recovery completed with 3/3 probes received and the recovery route verified. The Stage 6 [`experiment_report.md`](../artifacts/pilot-20261029T142341Z/experiment_report.md), four plots, `manifest.json`, and refreshed `checksums.sha256` are saved in the run directory.

The two shortcut comparisons were one beneficial and one neutral; no harmful shortcut was observed in this run. Optional candidate-evaluation fairness telemetry was unavailable, so `all_telemetry_complete` is false even though `required_telemetry_complete` is true. Repeated Linux HTB quantum warnings appeared during queue setup, but did not stop the runner or invalidate scenario validation. This is one seeded smoke pilot, not an independent-seed study or matched M1-M4 comparison. The run does not establish clinical service guarantees.

## Fresh two-repetition live pilot

Run `artifacts/research-pilot-20261029T080424Z/` completed on WSL2 with Ryu 4.34, Mininet 2.3.0, and Open vSwitch 2.17.12. It contains two repetitions of each of the four existing traffic scenarios (eight scenario repetitions total), plus the candidate-shortcut comparison and link-failure recovery. `scenario_validation_passed` is true with no validation errors; the recovery probe received 3/3 packets and forwarding rules were verified. The manifest has no missing expected files and says the run is not resumable.

The candidate comparison had one neutral decision and one harmful decision. In the neutral repetition, the shortcut was selected. In the harmful repetition, the baseline was selected and prevention verification passed. The aggregate therefore records `harmful_shortcut_prevented`, with one harmful candidate out of two and one prevention verified. This is a two-repeat smoke pilot using deterministic workload generation, not an independent-seed study. It does not support a general performance claim or clinical guarantee.

The first pilot, `artifacts/research-pilot-20261029T075522Z/`, exposed an aggregation defect: its top-level status described only its first candidate comparison. The all-repetitions status aggregation was fixed and exercised in the second run. The final follow-up also changes top-level result labels to report a mixed verdict explicitly and to identify the final repeated route; those label changes are covered by unit tests but have not been rerun live.

## Prior evidence (separate)

Historical evidence in `artifacts/wsl-final-20261023T0015Z/` records four scenarios, three repetitions per scenario, and a harmful shortcut decision under that run's composite cost. Its route-cost values and QoS outcomes apply only to that saved synthetic workload, code revision, and environment. It does not validate the current controller changes.

The analytical result in `artifacts/analytical-review-20261028/` records the configured Wardrop example at demand 4000: no-shortcut equilibrium average cost 65, shortcut equilibrium average cost 80, an increase of 15 (23.08%). This is mathematical-model evidence, separate from live forwarding measurements.

## Evidence still unavailable

Historical and pilot repetitions use deterministic workload generation, not independent random seeds. The current repository still lacks a matched live comparison of shortest path, QoS-only, congestion-aware routing, and CBDR; independent-seed trials; completed ablations; load and live-topology sweeps; validated per-service targets; and complete dashboard views for the structured method results. M3 has a distinct measured-utilization selector in the runner, but its current changes have not been live-verified; M4's profile-level live inputs and decisions also require further verification. The new topology playground is simulation-only and is not part of the Mininet testbed. Resume/checkpoint support is not implemented. Novelty and clinical relevance have not been established.
