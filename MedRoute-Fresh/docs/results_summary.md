# Results and project status (2026-10-29)

## Software validation

The final offline validation passed 69 Python tests and 25 Node tests. The focused CBDR, evidence-manifest, barrier, and live-metric regression set passed 37 tests. Software tests do not establish network performance.

## Fresh two-repetition live pilot

Run `artifacts/research-pilot-20261029T080424Z/` completed on WSL2 with Ryu 4.34, Mininet 2.3.0, and Open vSwitch 2.17.12. It contains two repetitions of each of the four existing traffic scenarios (eight scenario repetitions total), plus the candidate-shortcut comparison and link-failure recovery. `scenario_validation_passed` is true with no validation errors; the recovery probe received 3/3 packets and forwarding rules were verified. The manifest has no missing expected files and says the run is not resumable.

The candidate comparison had one neutral decision and one harmful decision. In the neutral repetition, the shortcut was selected. In the harmful repetition, the baseline was selected and prevention verification passed. The aggregate therefore records `harmful_shortcut_prevented`, with one harmful candidate out of two and one prevention verified. This is a two-repeat smoke pilot using deterministic workload generation, not an independent-seed study. It does not support a general performance claim or clinical guarantee.

The first pilot, `artifacts/research-pilot-20261029T075522Z/`, exposed an aggregation defect: its top-level status described only its first candidate comparison. The all-repetitions status aggregation was fixed and exercised in the second run. The final follow-up also changes top-level result labels to report a mixed verdict explicitly and to identify the final repeated route; those label changes are covered by unit tests but have not been rerun live.

## Prior evidence (separate)

Historical evidence in `artifacts/wsl-final-20261023T0015Z/` records four scenarios, three repetitions per scenario, and a harmful shortcut decision under that run's composite cost. Its route-cost values and QoS outcomes apply only to that saved synthetic workload, code revision, and environment. It does not validate the current controller changes.

The analytical result in `artifacts/analytical-review-20261028/` records the configured Wardrop example at demand 4000: no-shortcut equilibrium average cost 65, shortcut equilibrium average cost 80, an increase of 15 (23.08%). This is mathematical-model evidence, separate from live forwarding measurements.

## Evidence still unavailable

Historical and pilot repetitions use deterministic workload generation, not independent random seeds. The current repo still lacks a complete comparative study of shortest path, QoS-only, a distinct congestion-aware policy, and CBDR; independent-seed trials; candidate-evaluation, QoS, and guard ablations; load and topology sweeps; validated per-service targets; and a dashboard for the new structured policy outputs. M3 and M4 are not represented as complete live methods. Resume/checkpoint support is not implemented. The project's novelty and clinical relevance have not been established by this implementation or pilot.
