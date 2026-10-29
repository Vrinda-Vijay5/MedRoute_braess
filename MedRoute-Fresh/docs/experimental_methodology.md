# Experimental methodology and current coverage

## Existing live workflow

The current Mininet runner uses a four-switch diamond, six hosts, a 100 Mbit/s link configuration, an optional S2–S3 link, and four live classes. It collects baseline/candidate route probes, simultaneous UDP traffic scenarios, OVS flow dumps, port counters, and controlled primary-link failure recovery. It supports configurable repetitions, currently deterministic workloads. Repeating a deterministic workload is not an independent random-seed study.

The saved historical WSL bundle is evidence from its dated code and environment. It is not new validation of the current controller changes. New runs must use a fresh evidence directory; the runner now refuses to start into a non-empty output directory.

## Method comparison status

| Method | Current implementation | Research-comparison status |
|---|---|---|
| M1 shortest path | Static baseline route with QoS disabled | Available as a prototype baseline; not generalized shortest-path recomputation |
| M2 QoS aware | Baseline route with current four queue classes | Available as a prototype policy |
| M3 congestion aware without Braess guard | No distinct congestion-based route selector | Unavailable; must not be substituted with M2 or the guard |
| M4 CBDR | Aggregate candidate-cost guard and standalone class evaluator | Partial prototype; not a completed live class-aware method because candidate measurements are not per-class and hard constraints are not validated |

Current scenarios cover normal load, mixed-priority/background congestion, candidate route comparison, and primary-link recovery. The runner does not yet implement emergency surge, stale-telemetry live scenario, load/capacity sweep, topology scaling, five controlled ablations, execution-order randomization, or checkpoint/resume.

## Metrics and statistics

Available metrics include RTT summaries, jitter, loss, throughput, configured deadline misses, Jain throughput fairness, route update/barrier telemetry, flow programming counts, recovery probe outcomes, and link utilization where counters are complete. Fairness is currently calculated over configured class throughput means; those classes can have different workloads and are not inherently comparable. Queue occupancy, starvation duration, controller CPU/memory, run-level independent-seed intervals, and paired hypothesis tests are not currently available.

Stage 6 confidence intervals now use a two-sided Student-t critical value through 30 degrees of freedom and a normal approximation above that. They summarize the recorded scenario repetitions; because current workloads are deterministic, these intervals must not be presented as independent-seed uncertainty or statistical evidence about general networks.

For a journal study, compare shortest path, QoS-only, congestion-aware without CBDR, and CBDR under paired workload seeds. Add candidate-evaluation, QoS, Braess-guard, hard-constraint, and fairness ablations. Run pilots first, predefine exclusions, randomize method order, and gather at least ten independent run-level seeds per condition when runtime permits. Report confidence intervals at the run level; packets within one run are not independent replicates.
