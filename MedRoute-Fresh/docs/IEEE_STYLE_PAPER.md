# Braess-Paradox-Aware, Criticality-Constrained Routing in Software-Defined Networks for Healthcare Traffic

## Abstract

MedRoute is a deterministic software-defined networking prototype that combines
topology-change screening, measured route costs, criticality-aware queue policy,
and forwarding-rule verification. Its analytical benchmark predicts an increase
in Wardrop equilibrium average cost from 65 to 80 when a zero-cost shortcut is
added at demand 4000. A recent WSL2 live pilot completed two repetitions of five
traffic scenarios and link-failure recovery. The pilot found one beneficial and
one neutral shortcut comparison; it did not observe a harmful shortcut. This
small seeded pilot is feasibility evidence only, not a comparative study,
clinical result, or production guarantee.

## Method

The analytical benchmark uses `c_SA(x)=x/100`, `c_BT(x)=x/100`,
`c_AT=c_SB=45`, and optional `c_AB=0` at demand 4000. The live pilot used
Mininet 2.3.0, Open vSwitch 2.17.12, and Ryu 4.34 in WSL2. Five scenarios were
run twice each: baseline without prioritization, prioritization without
congestion, emergency surge, heavy background without prioritization, and heavy
background with prioritization. The run used one workload seed and included
receiver-side iperf3 measurements, route probes, OpenFlow counter/flow evidence,
and failure-recovery probes. The composite route cost is
`((latency/20)+(jitter/5)+(loss/1))/3`.

## Results

The run in `artifacts/pilot-20261029T142341Z/` passed scenario validation and
verified flow rules. Required telemetry was complete, all six catalog profiles
were complete, and recovery forwarding was verified with 3/3 probes received.
The two shortcut decisions were one beneficial and one neutral. Optional
candidate-evaluation fairness telemetry was unavailable, so the manifest does
not mark all telemetry complete. Repeated HTB quantum warnings did not stop the
run. See the saved `experiment_report.md` and plots for measured summaries.

## Limitations

This is a small synthetic-network demonstration in a fixed Mininet testbed. The
pilot has two repetitions from one deterministic workload seed and no matched
M1-M4 comparison, independent-seed trials, completed ablations, or validated
per-service targets. The topology playground is simulation-only. These results
do not establish clinical relevance, patent novelty, or service guarantees.

## Reproducibility

Use the WSL commands in `README.md`; inspect the run's `manifest.json`,
`checksums.sha256`, `summary.json`, `scenario_results.json`, controller logs,
flow dumps, and `experiment_report.md`. Historical evidence in other run
directories is separate and should not be pooled with this pilot.
