# MedRoute-Fresh

MedRoute demonstrates deterministic healthcare traffic classes, OpenFlow and OVS queue enforcement, and a measured route decision on a four-switch Mininet network. It also includes an independent analytical Braess example. The analytical calculation is not live-network evidence. The project does not use AI/ML. The experiment reads the prepared, training-derived workload profiles at `data/CICIoMT2024/processed/workload_profiles.json`; it does not modify the dataset or replay raw records or packets.

## Design

- `sdn/topology.py` creates a four-switch diamond with stable DPIDs 1–4 and the optional S2–S3 shortcut. `sdn/routes.json` defines the baseline and shortcut forwarding paths.
- `sdn/classes.json` drives Ryu classification. TCP/UDP service ports and DSCP values map ECG, ICU, WEARABLE, and BACKGROUND traffic to distinct queues. Port matches take precedence over DSCP. Unknown traffic on an allowed route uses BACKGROUND; unmatched destinations are dropped.
- `sdn/qos.py` attaches Linux HTB QoS and queues to OVS ports. The controller installs class matches, `set_queue`, and output actions. Cookie-based cleanup owns the MedRoute forwarding entries.
- `src/criticality.js` is the single deterministic class score: `100 × (0.6 × latency sensitivity + 0.4 × loss sensitivity)`. Queue order follows the resulting class ranking.
- `scripts/dataset_workload.py` validates and reads only CICIoMT2024's derived training profiles. `scripts/live_experiment.py` uses their synthetic offered rates and UDP packet sizes in the four traffic scenarios, and records source checksum, profile selection, and any intentional congestion scaling. Route evaluation and service-class labels remain MedRoute policy choices.
- `scripts/live_experiment.py` gathers route probes, per-class latency/jitter/loss/throughput, and OpenFlow port-counter link utilization. It runs four required traffic scenarios three times each and records Braess decisions and their evidence.
- `scripts/live_experiment.py` also runs a controlled primary-link failure check: it disables S1-S2, selects the recovery path S1-S3-S2-S4, verifies connectivity and OpenFlow forwarding, then restores the normal topology before continuing.
- `scripts/generate_stage6.py` calculates per-class means and sample standard deviations from saved scenario measurements, then writes four matplotlib charts and `experiment_report.md` into that run directory.
- The existing read-only Node dashboard serves topology, class/queue policy, saved live measurements, route decisions, scenario summaries, charts, and linked evidence. Missing data is displayed as unavailable.

Traffic classes use reserved service ports ECG 5101, ICU 5102, WEARABLE 5103, and BACKGROUND 5104 (TCP and UDP). DSCP values are 46, 34, 18, and 0 respectively. Queue IDs are 1–4. These are demonstration assignments and should not conflict with other services on the test network.

| Class | Queue | Minimum rate | Maximum rate |
|---|---:|---:|---:|
| ECG | 1 | 20 Mbps | 50 Mbps |
| ICU | 2 | 30 Mbps | 80 Mbps |
| WEARABLE | 3 | 10 Mbps | 50 Mbps |
| BACKGROUND | 4 | 5 Mbps | 20 Mbps |

## Run the experiment in WSL

`scripts/run_demo.sh` is the single documented end-to-end entry point. Run it from the project directory in the prepared WSL Ryu environment:

```bash
cd /mnt/c/Users/VICTUS/Downloads/MedRoute-Fresh
source ~/.pyenv/versions/medroute-ryu/bin/activate
sudo env "PATH=$HOME/.pyenv/versions/medroute-ryu/bin:$PATH" bash scripts/run_demo.sh
```

The environment needs Node.js, Python with Ryu and Mininet, Open vSwitch, `iperf3`, `ping`, `tc`, `flock`, root privileges, and matplotlib. The launcher runs analytical and unit checks, allocates a new timestamped evidence directory, prevents overlapping experiment launches with a process lock, runs live validation when prerequisites are present, and generates Stage 6 artifacts from a validated live run. A failed mandatory check returns a nonzero exit status. It cleans up the Mininet network and Ryu process it starts; it does not run broad `mn -c` cleanup.

On WSL installations where Node is exposed only as the Windows executable,
run the live Python coordinator directly as root while preserving the Ryu
virtual environment:

```bash
cd /mnt/c/Users/subiw/MEDROUTE_FINAL_GOD_HELP/MedRoute-Fresh
export PATH="$HOME/.venvs/medroute-ryu/bin:$PATH"
RUN="artifacts/wsl-live-$(date -u +%Y%m%dT%H%M%SZ)"
sudo env PATH="$PATH" MEDROUTE_LOG="$PWD/$RUN/controller.jsonl" \
  python3 scripts/live_experiment.py --evidence-dir "$PWD/$RUN"
python3 scripts/generate_stage6.py "$RUN"
```

This direct command is equivalent to the live portion of the launcher and is
useful when `node` is available only through `node.exe` on the Windows PATH.

For a saved run, charts and the report can also be regenerated without rerunning Mininet:

```bash
python3 scripts/generate_stage6.py artifacts/20261022T132810Z
npm run dashboard
```

Replace the artifact directory with the run you want to inspect. The dashboard prints its local URL, normally <http://127.0.0.1:8765>.
The dashboard is a single review view: it defaults to the authoritative
harmful-shortcut run when present, shows the route/recovery/congestion evidence,
and automatically attaches the latest six-profile matrix. The run selector and
raw artifact links remain available for audit.

To run only the analytical/unit checks and omit the live failure demonstration when
debugging a constrained environment, pass `--skip-failure-recovery` to
`scripts/live_experiment.py`. The normal launcher keeps recovery enabled.

## Checks

```bash
npm test
python3 -m unittest discover -s test -p 'test_*.py'
```

The analytical experiment is independently reproducible without Ryu or Mininet:

```bash
npm run braess -- artifacts/analytical-review
```

It writes `config.json`, `raw-result.json`, and `report.md` under the requested
evidence directory. The reusable Wardrop API is in `src/model.js`:
`validateWardrop`, `compareConfigurations`, and `detectBraess`. The
`src/braess_guard.js` module rejects a topology change when the analytical
equilibrium or complete measured costs identify degradation. This screening
does not claim that a live SDN network has prevented a paradox; that claim
requires the Mininet run and its OpenFlow dump evidence.

Patient criticality is deterministic and non-ML. `classifyPatientTraffic` maps
scores to ECG (90--100), ICU (70--89.99), WEARABLE (40--69.99), or BACKGROUND
(below 40), and the Ryu controller exposes the same policy at
`POST /medroute/classify`. Transport-port and DSCP classification take
precedence over a score, matching the installed flow rules. A successful
classification response contains `traffic_class`, `queue_id`, and the
classifier used.

The single live workflow is `scripts/run_demo.sh` in the documented WSL
environment. It records configuration, workload provenance, controller JSONL
logs, raw measurements, OpenFlow verification, failure-recovery evidence,
summary statistics, plots, and a report under a timestamped `artifacts/`
directory. On Windows or without Ryu/Open vSwitch/Mininet/root privileges the
workflow deliberately reports the live stage as blocked; analytical and unit
results remain valid but must not be presented as live forwarding results.

The tests cover class scoring and ordering, packet classification and queue actions, missing/stale metrics, harmful/beneficial/neutral route decisions, scenario evidence validation, and plot/report generation. Unit tests and analytical checks do not verify a live Ryu/Mininet network; use the WSL experiment and inspect its saved flow and controller evidence for that.

## Decision and metric definitions

The route cost is `((latency_ms / 20) + (jitter_ms / 5) + (packet_loss_pct / 1)) / 3`. These reference values define a demonstration policy; they are not clinical SLAs. A shortcut cost more than 5% above baseline is harmful and selects baseline. A cost more than 5% below is beneficial and selects shortcut. Within the 5% band it is neutral and selects shortcut. Missing, stale, or incomplete inputs produce an inconclusive decision. Harmful-shortcut prevention is verified from complete follow-up telemetry, a recorded controller decision, and OpenFlow dumps confirming the baseline route; the follow-up cost is reported separately because it is a new measurement and can vary under load.

Latency is median successful ICMP RTT. Jitter is median absolute difference between adjacent successful probes. Packet loss is the measured lost-probe percentage for route checks or the iperf UDP loss percentage for per-class scenarios. Per-class throughput is received iperf throughput. Link utilization uses directional OpenFlow port-counter deltas over the measurement interval. The experiment preserves missing observations rather than substituting values.

The independent analytical example uses demand 4000 and edge costs `c_SA(x)=x/100`, `c_BT(x)=x/100`, `c_AT(x)=45`, `c_SB(x)=45`, and optional `c_AB(x)=0`. Its Wardrop equilibrium cost increases from 65 without the shortcut to 80 with it (23.08%). This verifies the mathematical example only; the live network must be judged from its own measurements.

## Measured WSL run

The final WSL2 run `artifacts/wsl-final-20261023T0015Z/` passed the live
workflow after the dataset fallback and criticality trace changes. It completed
three repetitions of each of the four traffic scenarios, verified all class
queues and OpenFlow forwarding rules, verified recovery after disabling S1-S2,
and recorded a harmful shortcut comparison in which the controller selected
the baseline route. Its `summary.json` records
`live_experiment: harmful_shortcut_prevented`,
`live_prevention_verified: true`, and
`scenario_validation_passed: true`. The run also contains
`criticality_trace.json`, `evidence.sqlite`, Stage 6 plots, and
`experiment_report.md`. Known HTB quantum/qdisc messages are cleanup warnings;
the required validation checks passed.

The final run records the supplied CICIoMT2024 training-profile SHA-256
`a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c` and the
six-row synthetic healthcare traffic catalog. The catalog shapes deterministic
synthetic traffic only; it is not clinical data and raw packets are not
replayed.

The expanded run `artifacts/wsl-profile-matrix-20261023T0130Z/` independently
executed all six catalog profiles (ECG, ICU, TELEMEDICINE, EHR, IMAGING, and
CCTV). Each profile produced complete receiver telemetry and verified
OpenFlow/queue forwarding. The catalog's synthetic criticality values map to
the four existing policy classes; they are not clinical labels. This expanded
run's Braess comparison was neutral under the 5% measured threshold, so it is
profile-matrix evidence and not an additional harmful-shortcut prevention
claim. The earlier `wsl-final-20261023T0015Z` run remains the live harmful
shortcut evidence.

The following values are means +/- sample standard deviations across the three saved repetitions. These are the two congested scenarios:

| Scenario | Class | Latency (ms) | Jitter (ms) | Loss (%) | Throughput (Mbps) |
|---|---|---:|---:|---:|---:|
| Heavy background, no prioritization | ECG | 5.433 +/- 0.178 | 0.140 +/- 0.053 | 0.000 +/- 0.000 | 0.499 +/- 0.000 |
| Heavy background, no prioritization | ICU | 5.447 +/- 0.199 | 0.157 +/- 0.081 | 0.000 +/- 0.000 | 0.499 +/- 0.000 |
| Heavy background, no prioritization | WEARABLE | 5.457 +/- 0.217 | 0.143 +/- 0.061 | 0.000 +/- 0.000 | 0.499 +/- 0.000 |
| Heavy background, no prioritization | BACKGROUND | 5.442 +/- 0.163 | 0.137 +/- 0.064 | 0.302 +/- 0.523 | 21.404 +/- 0.112 |
| Heavy background, with prioritization | ECG | 5.558 +/- 0.053 | 0.187 +/- 0.042 | 0.000 +/- 0.000 | 0.499 +/- 0.000 |
| Heavy background, with prioritization | ICU | 5.575 +/- 0.056 | 0.187 +/- 0.050 | 0.000 +/- 0.000 | 0.499 +/- 0.000 |
| Heavy background, with prioritization | WEARABLE | 5.608 +/- 0.068 | 0.207 +/- 0.108 | 0.000 +/- 0.000 | 0.499 +/- 0.000 |
| Heavy background, with prioritization | BACKGROUND | 6.055 +/- 0.009 | 0.267 +/- 0.059 | 32.171 +/- 0.134 | 14.173 +/- 0.271 |

In this run, prioritization reduced BACKGROUND throughput and increased its loss. Critical classes had zero measured loss and equal throughput in both congested conditions, with similar latency and jitter. The run verifies dataset-driven workload generation, queue/flow execution, and scenario measurement, but it does **not** demonstrate that prioritization improved critical-class service over the no-prioritization condition. Do not present it as proof of that claim.

The saved run `artifacts/20261022T151004Z` measured a harmful first shortcut comparison (baseline cost 3.183, shortcut cost 3.567) and selected the baseline route; its OpenFlow flow evidence reports route selection verified. A second repetition was also harmful and selected baseline. The previous runner nevertheless marked the first prevention check failed because its separate follow-up cost was 4.950, above the baseline cost by more than 5%. The prevention check now follows the route-restoration requirement: complete follow-up telemetry and verified baseline forwarding are required, while the separate follow-up cost stays visible. Re-run the experiment after this code change before treating this updated verification rule as live-validated. The older `artifacts/20261022T150138Z` run measured one neutral and two beneficial comparisons, so it did not demonstrate harmful-shortcut prevention.

## Evidence and limitations

Each run is stored under `artifacts/<UTC timestamp>/`. Read `summary.json` for status. Live evidence includes `config.json`, `dataset_workload.json`, `measurements.json`, `scenario_results.json`, `decisions.json`, `controller.jsonl`, OpenFlow flow dumps, logs, four `plot_*.png` files, and `experiment_report.md`. Profile-matrix runs additionally include `profile_matrix.json`. Analytical and live results remain separate.

The per-class scenario workload is synthetic: rates and UDP packet sizes are derived from CICIoMT2024's benign training aggregate profiles. The derived profile file documents that Rate units are unspecified; its relative rate score is normalized to a synthetic engineering load. All classes use the training median profile in ordinary scenarios. In congestion scenarios, BACKGROUND uses the training p75 profile as its base; its offered rate is derived from the configured bottleneck capacity plus the nominal profile rates of the other classes, so total offered demand exceeds capacity. This scenario scaling is not a dataset measurement. The dataset has no healthcare priority labels, so it does not determine class identity, priority, route, or cost. Raw packet replay is not performed, CICIoMT2024's test source is excluded from profile derivation, and the experiment does not alter `data/`. The live workload is also limited to this topology, host pair, and shaping setup. WSL, kernel, OVS, and scheduling differences can change measurements.

The saved run above is dataset-profiled live evidence. Its directory contains `dataset_workload.json`, `config.json`, scenario repetition files, summary, controller records, OpenFlow dumps, plots, and report. A new run with recovery enabled additionally contains `failure_recovery.json`. The dashboard can select either run. CICIoMT2024 shapes synthetic experiment traffic only; it does not directly control Ryu.

## Recovery demonstration

The recovery route is an explicit failover path, not a claim of automatic topology
discovery. During the live check, the experiment brings down the S1-S2 link, enables
the S2-S3 shortcut, installs the `recovery` route (S1-S3-S2-S4), and verifies that
H1 can still reach H2. It then restores S1-S2, disables the shortcut, and continues
with the normal baseline/shortcut comparison. The result is saved as
`failure_recovery.json`; a failed or incomplete recovery check fails the live run.
