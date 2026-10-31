# MedRoute AI Playground Operation Guide

## Scope

The Playground is a deterministic, in-memory network simulator. Its metrics are simulated estimates calculated from the editable graph. They are not Mininet, Open vSwitch, Ryu, OpenFlow, or clinical measurements. The separate live panel can launch the existing Mininet/Ryu matched study, but Playground graph edits are never applied to that live topology.

## 1. Start and open the Playground

From the repository root:

```powershell
cd C:\Users\subiw\MEDROUTE_FINAL_GOD_HELP\MedRoute-Fresh
npm run dashboard
```

Open:

```text
http://127.0.0.1:8765/playground
```

If the page shows `MedRoutePlayground is not defined`, or the browser console reports `GET /playground-simulation.js 404`, an older dashboard process is occupying port 8765. Stop that old process and run `npm run dashboard` again from the repository root. A correct server must return JavaScript for:

```text
http://127.0.0.1:8765/playground-simulation.js
```

The first page section is the separate **LIVE EXPERIMENT — matched M1–M4 study** panel. It uses the existing fixed Mininet/Ryu workflow and does not use Playground edits.

The main Playground starts with four switches (`s1`–`s4`), two hosts (`h1` attached to `s1`, `h2` attached to `s4`), four enabled diamond links, and one disabled shortcut link (`s2`–`s3`).

## 2. Experiment controls

Select source and destination hosts, a healthcare profile, and offered load, then click **Run M1–M4 comparison**. The run recalculates all methods from the current topology and saves the result in in-memory simulation history.

Traffic profiles are deterministic simulator inputs:

| Profile | Criticality | Demand | Deadline |
|---|---:|---:|---:|
| ECG | 100 | 2 Mbps | 50 ms |
| ICU | 90 | 4 Mbps | 75 ms |
| TELEMEDICINE | 75 | 8 Mbps | 100 ms |
| EHR | 60 | 1 Mbps | 150 ms |
| IMAGING | 55 | 12 Mbps | 200 ms |
| CCTV | 10 | 6 Mbps | 300 ms |

Scenario behavior:

- **Normal healthcare traffic**: runs the current graph and entered load.
- **Emergency traffic surge**: multiplies the entered load by 3 before the comparison.
- **Braess shortcut before/after**: use **Capture current topology as before**, change or enable a link, then run. The result includes before/after cost classifications for M1–M4.
- **Link failure and recovery**: disables the first currently enabled link, recalculates routes, and records simulated recovery time.
- **Switch failure and recovery**: disables the first currently enabled switch and removes its usable incident paths.
- **Mixed-priority congestion and fairness**: multiplies the entered load by 2 and recalculates congestion, throughput, fairness, and QoS results.
- **Link restoration**: enables all links and clears disabled switches, then recalculates.

The failure and restoration scenarios change the simulation topology state. Use **Reset benchmark** to return to the original diamond.

## 3. Topology editing

Every successful edit calls the topology API, validates the whole graph, updates the SVG and tables, refreshes host selectors, and changes the graph used by the next run.

### Add a switch

In **Add switch or host**, choose **Switch**, enter a unique ID such as `s5`, and click **Add**. The switch appears in the graph and node table. It has no route until a link connects it.

### Remove a switch

Click **Remove** on a switch row. The switch, all incident links, and hosts attached to it are removed. Routes are recalculated from the remaining graph.

### Add or remove a host

Choose **Host**, enter a unique host ID, select an attachment switch, and click **Add**. Remove a host with its row's **Remove** button. Hosts are valid source and destination endpoints; switches are the routing graph nodes.

### Add a link

Choose two different existing switches, enter capacity and link properties, and click **Add link**. Duplicate links and self-links are rejected by topology validation.

### Break, restore, or delete a link

In the link table:

- **Break** changes an enabled link to disabled.
- **Restore** changes a disabled link to enabled.
- **Delete** removes the link entirely.

Disabled links remain visible as dashed links but are excluded from route calculation.

### Edit link properties

Each link row contains editable fields. Change capacity, latency, jitter, or packet loss and click that row's **Save** button. The server validates the values and stores them in the current topology.

- Capacity must be positive Mbps.
- Latency must be non-negative milliseconds.
- Jitter must be non-negative milliseconds.
- Packet loss must be between 0 and 100 percent.

### Reset

Click **Reset benchmark** to restore the original four-switch diamond, including its disabled `s2`–`s3` shortcut. This is also the safest recovery after a failure scenario.

## 4. Route selection and comparison

Click **Run M1–M4 comparison** after editing the graph. The method table shows the selected path for each method. The **Available route comparison** table shows every currently reachable simple path, its status, methods using it, metrics, and decision reason.

- **M1**: shortest-path baseline, ordered by hop count and then link latency.
- **M2**: QoS-aware score that weights latency and packet loss by traffic criticality.
- **M3**: congestion-aware selection using utilization plus latency.
- **M4**: CBDR-style candidate evaluation. It starts from the M1 baseline, evaluates an M3 candidate, applies the 5% aggregate threshold, and then applies the protected critical-class guard.

The route table marks paths as **selected** or **alternative**. If no path exists, the method table reports `N/A` route and metrics with reason `No available route`.

## 5. Metrics and formulas

All values in this section are simulated estimates.

- **Average latency (ms)**: sum of link latency values, with deterministic sample jitter applied for the displayed average.
- **p95/p99 latency (ms)**: nearest-rank percentiles of 20 deterministic samples.
- **Jitter (ms)**: square root of the sum of squared link jitter values plus a utilization term `abs(utilization - 0.5) * 2`.
- **Packet loss (%)**: combines independent link delivery probabilities and overload loss. Link delivery is the product of `(1 - packetLossPct / 100)`. Overload begins when offered load exceeds the bottleneck capacity.
- **Throughput (Mbps)**: `min(offered_load, bottleneck_capacity) * link_delivery`.
- **Bottleneck capacity (Mbps)**: minimum capacity on the path.
- **Utilization (%)**: `offered_load / bottleneck_capacity * 100`.
- **Congestion**: `normal` below 80% utilization, `elevated` from 80% through 100%, and `congested` above 100%.
- **Hop count**: number of links on the selected path.
- **Route cost**: `(averageLatencyMs / 20 + jitterMs / 5 + packetLossPct / 1) / 3`.
- **QoS violations**: count indicator equal to 1 when any deterministic latency sample exceeds the selected profile deadline, otherwise 0.
- **Deadline violation (%)**: the percentage of the 20 deterministic latency samples above the profile deadline.
- **Non-critical throughput**: selected throughput multiplied by `1 - criticality / 200`.
- **Fairness index**: when throughput is available, `min(1, (1 + criticality / 100) / 2)`; otherwise unavailable.
- **Route changes**: 1 when the selected method route differs from its baseline object, otherwise 0.
- **Recovery (ms)**: simulated value `10 + number_of_route_nodes * 2` only when the failure flag is active; otherwise `N/A`.
- **Controller overhead (ms)**: simulator estimate: M1/M2 `1`, M3 `1 + candidate_count`, M4 `2 + candidate_count`.

Topology changes affect these values through path latency, bottleneck capacity, link loss, link jitter, overload, and route availability. No random samples are used.

## 6. Braess before/after demonstration

1. Click **Reset benchmark**.
2. Select the desired source, destination, profile, and load.
3. Click **Capture current topology as before**.
4. Click **Restore** for the disabled `s2`–`s3` link, or add another link.
5. Click **Run M1–M4 comparison** with scenario **Braess shortcut before/after**.
6. Read the before/after verdict for each method: beneficial, neutral, harmful, or inconclusive.
7. Read the M4 reason and protected-class guard output.

Adding a link is not automatically beneficial. The result depends on the current latency, capacity, loss, jitter, offered load, and profile. The Playground reports the calculated result; it does not force a paradox.

## 7. Critical-class safety guard

M4 protects `EMERGENCY_ALARM` and `CRITICAL_PHYSIOLOGICAL_TELEMETRY`. It preserves the aggregate CBDR calculation but separately evaluates those classes. A candidate is rejected if a protected class is classified harmful or violates the simulator's hard constraint check. The result reason begins with `CRITICAL_CLASS_DEGRADATION` when this guard rejects the candidate.

To demonstrate it, use a topology with a direct high-latency baseline and a lower-latency candidate whose latency exceeds a protected class deadline. The aggregate route cost can improve while the protected class fails its deadline. M4 then keeps the baseline and displays the class name and degradation/constraint reason.

## 8. Import, export, and history

- **Export JSON** downloads the current simulation topology.
- Paste valid topology JSON into the **Topology JSON** box and click **Import JSON** to validate and replace the current graph.
- **Capture current topology as before** stores a client-side before snapshot for the Braess comparison.
- **Clear before** removes that snapshot.
- Every successful run is posted to `/api/simulation/history` and appears under **Experiment history**.
- Click a history row's **Open** button to reopen its saved metrics in the result display.

History is held in the dashboard server process and is not a replacement for the persistent live experiment evidence directories.

## 9. Live Ryu and Mininet separation

The live topology status polls `/api/live/topology`. If Ryu is unavailable, it reports an unavailable/warning state and does not substitute the simulation graph.

The live panel's **Run LIVE M1–M4 experiment** action launches the existing matched study with a supported live topology profile, seeds, repetitions, and optional ablations. Those results are actual live experiment evidence only when the Mininet/Ryu run completes and its telemetry/flow checks pass.

The Playground's add/remove/break/edit actions never change Mininet or OVS. Do not describe Playground values as live measurements.

## 10. Recommended operator sequence

For a short review: start the server, open `/playground`, explain the simulation-only banner, run the default comparison, show the available route table, capture a before state, restore the shortcut and rerun the Braess scenario, break a link and rerun failure recovery, edit a link's capacity/loss, then reset the benchmark. Use the separate live panel only when Mininet/Ryu is already prepared and a real live study is intended.
