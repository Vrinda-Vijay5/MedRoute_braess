# MedRoute AI — Complete Project Explanation & Implementation Review Guide

> **Status:** Deterministic SDN research/demo prototype with retained Mininet/OpenFlow evidence.  
> **Important:** The current reviewed implementation does **not** contain a trained machine-learning model and is **not** a clinically validated or production medical system.

## 1. Project at a glance

**MedRoute AI** is a deterministic Software-Defined Networking (SDN) framework that combines healthcare-shaped traffic priorities, measured network telemetry, and a Braess-Paradox-aware route guard. It evaluates whether a candidate shortcut should be used, then enforces the selected route through OpenFlow forwarding rules and QoS queues in a Mininet/Open vSwitch test network.

The central idea is: **do not accept a new or apparently shorter route automatically**. Compare measured route costs, apply a documented policy, and verify the forwarding state installed by the controller.

### One-sentence explanation

> MedRoute is a deterministic SDN routing framework that uses traffic priorities, measured network telemetry, and a Braess-aware safety guard to decide whether a candidate route should be used, while enforcing the decision through OpenFlow rules and QoS queues in Mininet.

### Main contribution

- Measured route comparison and a deterministic Braess-aware guard.
- Traffic classification and class-based QoS.
- Ryu/OpenFlow route installation and verification.
- Controlled congestion and link-failure/recovery experiments.
- Retained raw evidence and a read-only dashboard for review.

These are prototype-level demonstrations, not claims of clinical suitability or universal optimal routing.

## 2. Problem statement and motivation

Healthcare networks may carry traffic with different urgency and tolerance for delay or loss. ECG-like monitoring traffic may need stronger priority than CCTV/background traffic.

A conventional shortest-path choice can be locally attractive yet worsen overall user-equilibrium cost. The **Braess Paradox** is the network phenomenon in which adding a link can increase equilibrium travel cost.

MedRoute explores two questions:

1. Can a measured candidate route be classified as harmful, beneficial, neutral, or inconclusive?
2. Can the selected route and traffic-priority policy be enforced and checked in the SDN data plane?

The healthcare context motivates the traffic classes. The current workload is synthetic and does not establish clinical safety.

| Traffic type | Intended priority | Intended behavior |
|---|---|---|
| ECG-like monitoring | Very high | Strong protection from background load |
| ICU-like monitoring | High | Preferential treatment over background traffic |
| Wearable-like data | Medium | Normal priority |
| CCTV/background | Low | Lower-priority traffic that can tolerate more delay/loss |

These are demonstration policies, not clinical service-level agreements (SLAs).

## 3. What “AI” means in the current project

Although the project name includes “AI,” the reviewed implementation uses **deterministic logic**, not machine learning.

Current decision mechanisms include:
- A canonical analytical Braess/Wardrop model.
- A fixed criticality-scoring formula.
- Threshold-based route-cost comparisons.
- Telemetry validity and freshness checks.
- Queue and forwarding policies.

There is no trained model, model-training pipeline, inference endpoint, or verified ML evaluation in the current implementation. Do not claim otherwise during a review.

## 4. Architecture

```text
Synthetic healthcare-shaped workload / profile metadata
                         |
                         v
            Criticality / traffic classification
                         |
                         v
             Mininet + Open vSwitch topology
                         |
                         v
                 Ryu OpenFlow controller
                         |
             +-----------+-----------+
             |                       |
             v                       v
      Route measurements        QoS/queue policy
      latency/jitter/loss       class and DSCP rules
             |                       |
             v                       |
       Route-cost calculation        |
             |                       |
             v                       |
       Braess-aware guard             |
             |                       |
             +-----------+-----------+
                         |
                         v
              Selected route / mode
                         |
                         v
            OpenFlow rules + set_queue
                         |
                         v
             Traffic, counters, recovery
                         |
                         v
             Saved evidence + dashboard
```

### Logical layers

1. **Workload/profile layer:** Supplies synthetic traffic-profile metadata and traffic rates.
2. **Classification layer:** Maps traffic to deterministic classes.
3. **Network layer:** Mininet hosts, four Open vSwitch switches, shaped links, and alternative paths.
4. **Control layer:** Ryu controller programs OpenFlow rules and route modes.
5. **Decision/measurement layer:** Collects route telemetry and applies the route-cost guard.
6. **Evidence layer:** Stores run outputs, flow dumps, measurements, summaries, and a read-only dashboard.

## 5. Workload profiles and criticality

The project uses six synthetic healthcare-shaped profiles:

- ECG
- ICU
- TELEMEDICINE
- EHR
- IMAGING
- CCTV

These profiles are synthetic metadata used to exercise routing policy. They are not real patient readings or clinical diagnoses. CICIoMT2024-derived aggregate features may shape synthetic workload rates and packet sizes; the project does not claim raw packet replay or clinical labels.

### Deterministic criticality score

```text
score = 100 × (
    0.6 × latency_sensitivity
  + 0.4 × loss_sensitivity
)
```

| Score | Class |
|---:|---|
| 90–100 | ECG |
| 70–89.99 | ICU |
| 40–69.99 | WEARABLE |
| 0–39.99 | BACKGROUND |

This is policy classification, not medical inference.

### Catalog-to-forwarding-class mapping

| Synthetic profile | MedRoute class | Queue |
|---|---|---:|
| ECG | ECG | 1 |
| ICU | ECG | 1 |
| TELEMEDICINE | ICU | 2 |
| EHR | ICU | 2 |
| IMAGING | WEARABLE | 3 |
| CCTV | BACKGROUND | 4 |

The catalog profile mapping and forwarding-class policy are separate stages. Explain them as configured policy, not learned behavior. Actual enforcement depends on installed rules and queue configuration.

### Forwarding classes, queues, and DSCP

| Class | Queue ID | DSCP | Purpose |
|---|---:|---:|---|
| ECG | 1 | 46 | Highest-priority class |
| ICU | 2 | 34 | High-priority class |
| WEARABLE | 3 | 18 | Medium-priority class |
| BACKGROUND | 4 | 0 | Lowest-priority class |

## 6. Network topology and routes

The test topology is a four-switch diamond implemented with Mininet and Open vSwitch, using OpenFlow 1.3. Links can be shaped with TCLink and QoS queues with Linux HTB.

Conceptual topology:

```text
                  S2
                /    \
H1 ---- S1 ----        ---- S4 ---- H2
                \    /
                  S3
```

Documented logical route examples:

```text
Baseline:  H1 → S1 → S2 → S4 → H2
Shortcut:  H1 → S1 → S2 → S3 → S4 → H2
Recovery:  H1 → S1 → S3 → S2 → S4 → H2
```

- S2–S3 is described as the optional shortcut.
- S1–S2 is used as the controlled failure link in the recorded recovery demonstration.
- The recovery test demonstrates a specific failure case, not every possible link/switch failure.

Confirm exact link arrangement and route sequences against the current topology/controller code before making code-level claims.

## 7. SDN controller and OpenFlow enforcement

The Ryu controller translates a selected route mode and class policy into OpenFlow forwarding rules.

Documented responsibilities:
1. Accepting switch connections.
2. Installing forwarding rules.
3. Installing class-based matches.
4. Applying `set_queue` actions where QoS is enabled.
5. Switching between baseline, shortcut, and recovery route modes.
6. Cleaning up MedRoute-owned rules using cookies.
7. Recording decisions and telemetry.
8. Exposing HTTP API endpoints for policy/measurement operations.

Documented API routes:

```text
GET/POST /medroute/mode
GET/POST /medroute/metrics
GET/POST /medroute/decision
GET/POST /medroute/qos
POST     /medroute/classify
```

Verify exact methods and payloads in the current controller source before using these APIs in a live review. Avoid unverified POST requests during the demo.

A forwarding rule may match IPv4 source/destination, TCP/UDP service port, and DSCP, then apply `set_queue(queue_id)` and output to a selected switch port.

### Inspect saved/live flow evidence

When the corresponding Mininet/OVS experiment is active:

```bash
ovs-ofctl -O OpenFlow13 dump-flows s1
ovs-ofctl -O OpenFlow13 dump-flows s2
ovs-ofctl -O OpenFlow13 dump-flows s3
ovs-ofctl -O OpenFlow13 dump-flows s4
```

Saved flow dumps can be inspected without starting a live network. Evidence is stronger when flow entries and traffic counters are checked, rather than relying only on controller logs.

## 8. Analytical Braess/Wardrop model

Relevant files identified in project notes:
- `model.js`
- `braess_guard.js`
- `braess_experiment.js`

Canonical analytical parameters:

```text
Demand = 4000
Variable-edge cost = flow / 100
Fixed edge cost = 45
Shortcut cost = 0
```

### Without shortcut

```text
Flow per outer path = 2000
Cost = 2000 / 100 + 45 = 65
```

### With shortcut

```text
Variable-edge contribution = 4000 / 100 = 40
Total equilibrium cost = 40 + 40 = 80
```

| Configuration | Equilibrium cost |
|---|---:|
| Without shortcut | 65 |
| With shortcut | 80 |
| Absolute increase | 15 |
| Relative increase | 23.08% |

The model checks Wardrop equilibrium conditions: all used paths have equal cost, and no unused path is cheaper. This analytical example is distinct from measured Mininet route costs.

Demo command from project notes:

```bash
npm run braess -- artifacts/analytical-validation
```

Check the script's CLI handling if the output path matters. Do not assume this command starts or measures a live Mininet network.

## 9. Measured route-cost guard

The primary measured route cost is:

```text
cost = (
    latency_ms / 20
  + jitter_ms / 5
  + packet_loss_pct / 1
) / 3
```

The normalization constants are demonstration reference values, not clinical SLAs. The primary formula uses latency, jitter, and packet loss. Throughput and OpenFlow utilization are retained for congestion/scenario analysis but are not direct terms in this composite cost.

### Measurement definitions

- **Latency:** Median successful ping round-trip time.
- **Jitter:** Median absolute difference between adjacent successful RTT samples.
- **Probe packet loss:** Percentage of failed route probes.
- **Receiver UDP loss:** Reported separately from route-probe loss.
- **Throughput:** Receiver-side `iperf3` throughput.
- **Link utilization:** Directional OpenFlow port-counter deltas divided by the measurement interval and configured link capacity.

Probe loss and UDP receiver loss are not interchangeable.

### Threshold policy

```text
candidate_cost > baseline_cost × 1.05
    => harmful; retain baseline

candidate_cost < baseline_cost × 0.95
    => beneficial; select shortcut

otherwise
    => neutral; current policy selects shortcut
```

The system does not reject every shortcut. Neutral candidates are allowed under the current documented policy.

### Fail-safe behavior

If inputs are missing, invalid, incomplete, stale, future-dated, or otherwise unusable, the intended policy is an inconclusive decision with baseline retained. Confirm exact validation behavior against the current guard/coordinator implementation and tests before describing edge cases as verified.

### Follow-up measurement

After a harmful shortcut is rejected, the experiment measures the selected route again. This is a new observation and may vary under load. The documented verification rule requires complete follow-up telemetry and verified baseline forwarding; the new follow-up cost is reported separately rather than required to equal the earlier baseline measurement.

## 10. Experiment matrix and collected evidence

The described live experiment is implemented in `live_experiment.py`. Documented scenario families:

| Scenario | QoS | Heavy background traffic |
|---|---:|---:|
| `baseline_no_prioritization` | Disabled | No |
| `class_prioritization_no_congestion` | Enabled | No |
| `heavy_background_no_prioritization` | Disabled | Yes |
| `heavy_background_with_prioritization` | Enabled | Yes |

The documented runner uses three repetitions per scenario and traffic classes including ECG, ICU, WEARABLE, and BACKGROUND. The six-profile matrix adds ECG, ICU, TELEMEDICINE, EHR, IMAGING, and CCTV.

Traffic is generated using `iperf3` UDP with DSCP marking. Evidence may include:
- Latency and jitter
- Probe packet loss
- Receiver throughput and UDP loss
- OpenFlow traffic counters
- Queue IDs
- Link utilization
- Route decisions
- Flow-rule verification
- Controller event records

The profile-matrix run is reported as six out of six profiles complete in the dashboard. The 48 scenario measurement rows (4 scenario families × 3 repetitions × 4 forwarding classes) apply to the described matrix; inspect the selected run's JSON/SQLite artifacts if asked to independently verify the exact count.

### Statistical limitation

Three repetitions per scenario support a controlled demonstration but not broad statistical generalization. Do not claim production-grade confidence intervals or universal performance improvement unless the selected artifacts actually support them.

## 11. Link-failure and recovery experiment

The recorded resilience demonstration disables S1–S2. The expected recovery route is:

```text
H1 → S1 → S3 → S2 → S4 → H2
```

The retained evidence is described as checking:
- Connectivity from H1 to H2 after failure
- Recovery forwarding rules
- Route recording
- Link restoration
- Restoration of the normal route

The notes report three packets received and 0% packet loss in the recovery check. Treat these as the recorded check's results, not as a guarantee under all loads or failure types.

**Scope:** One controlled primary-link failure/recovery case is demonstrated. Full multi-link, switch-failure, and exhaustive resilience testing is not complete.

## 12. Evidence layout and traceability

Runs are stored under:

```text
artifacts/<run-id>/
```

Main run identified in the project context:

```text
artifacts/wsl-final-20261023T0015Z
```

Six-profile matrix run:

```text
artifacts/wsl-profile-matrix-20261023T0130Z
```

The dashboard API was verified during review setup: `GET /api/runs` returned HTTP 200 and listed both run IDs.

Useful files may include:

```text
summary.json
scenario_results.json
profile_matrix.json
config.json
measurements.json
decisions.json
controller.jsonl
evidence.sqlite
flows_baseline.txt
flows_shortcut.txt
flows_prevention.txt
flows_failure_recovery.txt
ryu.stdout.log
plot_*.png
experiment_report.md
```

Not every run contains every file; inspect the selected run directory before claiming a particular artifact exists.

### Evidence traceability

```text
Dashboard
   ↓
Saved run summary / scenario results
   ↓
Controller records and measurements
   ↓
OpenFlow flow dumps and traffic counters
```

The SQLite database is a per-run evidence index. It does not, by itself, prove every measurement is correct; raw logs and flow dumps provide additional traceability.

### Git/reproducibility limitation

The current project directory was audited as not being a Git checkout. Therefore, the reviewed evidence is not tied to an immutable Git commit/branch in that directory. Mention this if asked about versioned reproducibility; do not claim commit-level provenance.

## 13. Dashboard

The dashboard is a **read-only saved-evidence viewer**. It lists saved runs, displays summaries/decisions and recovery/profile status where available, and links to raw artifacts.

It does **not**:
- Control Ryu or Mininet.
- Change routes or QoS.
- Provide a verified live telemetry stream.
- Turn saved results into a production guarantee.

### URLs

```text
Main harmful-shortcut run:
http://127.0.0.1:8765/?run=wsl-final-20261023T0015Z

Six-profile matrix:
http://127.0.0.1:8765/?run=wsl-profile-matrix-20261023T0130Z
```

Start from the project root:

```bash
npm run dashboard
```

The reviewed dashboard required modern Node.js syntax. Node.js `v12.22.9` failed to parse `??` in `scripts/dashboard_server.js`; the user upgraded and verified Node.js `v22.23.4` and npm `10.9.9`.

The screenshots showed:
- Main run: harmful decision, baseline selected, live prevention verified, recovery verified, profile matrix 6/6.
- Matrix run: neutral decision, shortcut selected, prevention not triggered, recovery verified, profile matrix 6/6.

“Prevention not triggered” is expected for a neutral candidate under the current policy; it does not mean harmful prevention failed.

## 14. Implementation review: file responsibilities

The following responsibilities are based on project notes. Confirm paths and exact symbols in the current checkout before quoting implementation details in a code-level review.

| File/module | Described responsibility |
|---|---|
| `model.js` | Analytical equilibrium, route costs, Wardrop validation, configuration comparison, Braess detection |
| `braess_guard.js` | Analytical and/or measured Braess decision helpers |
| `guard.js` | Measured route-cost thresholds and safe fallback |
| `coordinator.js` | Sample-count, timestamp, freshness, RTT summary, guard coordination |
| `topology.py` | Mininet topology and links |
| `controller.py` / `medroute_controller.py` | Ryu/OpenFlow route installation, class rules, QoS and telemetry APIs; exact filename depends on current module layout |
| `qos.py` | OVS/HTB queue configuration |
| `classes.json` | Class, service-port and DSCP policy |
| `live_experiment.py` | Live Mininet orchestration and evidence generation |
| `dataset_workload.py` | Synthetic workload shaping from profile/dataset-derived aggregate features |
| `build_evidence_db.py` | Per-run SQLite evidence index |
| `dashboard_server.js` | Node HTTP server for dashboard and artifact/API routes |
| `index.html` | Dashboard UI |

## 15. Safe review and validation commands

Run from the project root:

```bash
cd /mnt/c/Users/subiw/MEDROUTE_FINAL_GOD_HELP/MedRoute-Fresh
```

Runtime versions:

```bash
node --version
npm --version
python --version
```

Activate the Python environment before Python tests:

```bash
source ~/.venvs/medroute-ryu/bin/activate
```

Previously observed test results:
- Node tests: 24 passed, 0 failed.
- Python tests: 22 passed.
- Python AST syntax check: 12 files passed.

Rerun regression tests:

```bash
npm test
python -m unittest discover -s test -p 'test_*.py' -v
```

Dashboard health check, while `npm run dashboard` is running in another terminal:

```bash
curl -sS -i --max-time 5 http://127.0.0.1:8765/api/runs
```

A successful check previously returned `HTTP/1.1 200 OK` and listed the saved run IDs.

Read saved evidence without rerunning experiments:

```bash
python - <<'PY'
import json
from pathlib import Path

run = Path("artifacts/wsl-final-20261023T0015Z")
for name in ("summary.json", "scenario_results.json"):
    path = run / name
    print(f"\n--- {path} ---")
    if path.exists():
        print(json.dumps(json.loads(path.read_text()), indent=2)[:12000])
    else:
        print("Not present in this run.")
PY
```

Do not start Ryu/Mininet merely to show saved evidence. Live runs can change network state and take time; do not rerun the demo/matrix during a short review unless you intend a fresh experiment and have checked the environment.

## 16. Implemented versus incomplete

### Implemented and verified historically
- Canonical analytical Braess model.
- Wardrop-equilibrium checks.
- Deterministic measured route-cost guard.
- Baseline/shortcut/recovery route modes.
- Ryu/OpenFlow 1.3 controller.
- Mininet/Open vSwitch test topology.
- Class-based QoS queue actions.
- Congestion and traffic-class scenarios.
- OpenFlow forwarding verification.
- One controlled link-failure/recovery demonstration.
- Six-profile synthetic traffic matrix.
- Saved raw artifacts and SQLite evidence index.
- Read-only evidence dashboard.
- Node and Python unit-test suites.

### Not implemented or not fully verified
- Trained ML model or online learning.
- End-to-end patient-reading ingestion, freshness state machine, and automatic patient-criticality route binding.
- Real medical-device integration or clinical validation.
- Production deployment or clinical SLAs.
- Universal optimal routing or prevention of every possible Braess paradox.
- Exhaustive multi-link/switch resilience matrix.
- Verified live-streaming dashboard telemetry.
- Commit-level Git traceability for the reviewed directory.
- Broad statistical generalization from three repetitions per scenario.

## 17. Reviewer questions and answers

**Why call it MedRoute AI if it has no ML?**  
The current reviewed scope prioritizes a deterministic SDN prototype with measurable forwarding evidence. It uses analytical and policy-based logic, not a trained ML model. ML is future work and is not claimed as implemented.

**Does the project use real healthcare records?**  
No. It uses synthetic healthcare-shaped profiles and dataset-derived aggregate workload characteristics. It does not claim real patient records, clinical labels, or raw packet replay.

**Does it always reject the shortcut?**  
No. A candidate more than 5% worse than baseline is harmful and baseline is retained. A sufficiently better candidate is allowed. A neutral candidate follows the current policy and selects the shortcut. Invalid telemetry should fail safe to baseline.

**Why is prevention “not triggered” in one run?**  
Prevention applies to harmful candidates. The matrix screenshot shows a neutral candidate, for which the current policy selects the shortcut, so prevention is not triggered.

**How do you prove a route was enforced?**  
The experiment retains controller records, OpenFlow flow dumps, and traffic-counter checks. These provide evidence that selected forwarding rules were installed and exercised in the test network.

**What is the difference between analytical and live results?**  
The analytical model computes the canonical equilibrium example with costs 65 and 80. The live experiment measures a shaped Mininet network using latency, jitter, and packet loss. They illustrate related concepts but are different models and must not be presented as the same measurement.

**Does throughput affect route selection?**  
Throughput is recorded for scenario/congestion analysis. It is not a direct term in the current composite route-cost formula, which uses latency, jitter, and packet loss.

**What happens if measurements are stale or missing?**  
The intended policy is an inconclusive result and baseline retained. Cite the current implementation/tests for exact validation details.

**Is the dashboard live?**  
It is a read-only viewer over saved run artifacts. It does not control the controller or network and is not a verified live telemetry stream.

**Is the project statistically conclusive?**  
No. Three repetitions per scenario support a controlled prototype demonstration, not broad production-grade statistical conclusions.

**What is the main contribution?**  
Combining a measured Braess-aware route guard with class-based traffic prioritization, OpenFlow route enforcement, and retained evidence connecting decisions to forwarding behavior.

**What are the next steps?**
1. Implement and validate patient-reading ingestion and freshness.
2. Add ML only with a defensible dataset, training/evaluation protocol, and comparison baseline.
3. Expand link/switch failure testing.
4. Increase repetitions and report uncertainty honestly.
5. Add immutable run metadata and Git commit provenance.
6. Improve automated consistency checks across SQLite, JSON, controller logs, and flow dumps.
7. Validate with realistic workloads before any clinical/production claims.

## 18. Seven-minute demo script

### Minute 0–1: Motivation
> “MedRoute explores safe route selection for prioritized healthcare-shaped traffic. Adding a shortcut can worsen equilibrium cost, so the network should measure the candidate route rather than accept it automatically.”

### Minute 1–2: Analytical model
> “The canonical model gives a cost of 65 without the shortcut and 80 with it, a 23.08% increase. This is the mathematical Braess example, separate from our live Mininet measurements.”

### Minute 2–3: Dashboard
> “This saved run measured a harmful shortcut. The guard selected the baseline, and the dashboard reports prevention verified using retained controller and forwarding evidence.”

### Minute 3–4: Decision policy
> “A candidate more than 5% worse is rejected. A beneficial candidate is accepted, and neutral candidates follow the documented shortcut policy. Invalid telemetry should not authorize a route change.”

### Minute 4–5: OpenFlow/QoS
> “The controller translates the decision into forwarding rules and queue actions. We retain flow dumps and traffic counters to check the data-plane behavior.”

### Minute 5–6: Profiles and congestion
> “These six synthetic profiles map to four forwarding classes. The scenario matrix compares prioritized and non-prioritized traffic with and without heavy background load.”

### Minute 6–7: Recovery and limitations
> “We demonstrated recovery for a controlled S1–S2 link failure. This is a deterministic prototype, not a clinical system. ML, patient integration, broader resilience testing, and clinical validation remain future work.”

## 19. Closing statement

> MedRoute demonstrates that a topology change should not be accepted solely because it appears to provide a shorter route. The prototype evaluates measured network effects, applies deterministic traffic-priority policies, verifies OpenFlow forwarding, and retains evidence for review. The current implementation is a deterministic SDN demonstration with Mininet/OpenFlow evidence; it does not claim machine learning, real clinical traffic, or production deployment.
