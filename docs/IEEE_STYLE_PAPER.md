# MedRoute: A Deterministic Braess-Aware SDN Demonstration

## Abstract

MedRoute demonstrates a non-ML SDN controller that screens topology changes
against Wardrop equilibrium and measured route cost. A canonical analytical
network predicts a cost increase from 65 to 80 after adding a zero-cost link.
In a WSL2 Mininet experiment, the controller measured a harmful shortcut
(4.191 baseline versus 6.415 shortcut) and restored the baseline route.
Congestion experiments further show deterministic queue protection for
critical classes. These results are prototype evidence, not clinical claims.

## Method

The analytical model uses `c_SA(x)=x/100`, `c_BT(x)=x/100`,
`c_AT=c_SB=45`, and optional `c_AB=0` at demand 4000. Live measurements use
five route probes, iperf3 receiver output, OpenFlow port counters, and three
repetitions per traffic scenario. Costs are
`((latency/20)+(jitter/5)+(loss/1))/3`.

## Results

The final live run verified three repetitions for each normal, prioritized,
heavy-background, and heavy-background-prioritized scenario. Under congestion,
critical traffic had 0% loss with queues enabled while unprioritized critical
traffic had measurable loss. S1-S2 failure recovery preserved connectivity and
verified recovery rules.

## Limitations

The topology is small, traffic is synthetic, and the healthcare catalog has no
patient records. Three repetitions are suitable for a demonstration, not a
clinical or production performance claim. Confidence intervals are approximate
normal intervals.

## Reproducibility

Use the WSL commands in `README.md`; inspect `summary.json`,
`scenario_results.json`, `controller.jsonl`, flow dumps, and
`experiment_report.md`.
