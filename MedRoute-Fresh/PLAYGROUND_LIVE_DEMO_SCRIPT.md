# MedRoute AI Playground 5–7 Minute Demonstration Script

This is a simulation demonstration. Say that explicitly before showing metrics.

## 0:00–0:45 — Start and orient the evaluator

Run:

```powershell
cd C:\Users\subiw\MEDROUTE_FINAL_GOD_HELP\MedRoute-Fresh
npm run dashboard
```

Open `http://127.0.0.1:8765/playground`.

Say: “This page is the interactive MedRoute simulation Playground. The metrics are deterministic estimates from the editable graph. They are not live Mininet or Ryu measurements. The separate live panel is intentionally isolated.”

Point out the four switches, two hosts, enabled diamond links, and disabled `s2–s3` shortcut.

## 0:45–1:30 — Run the four methods

Keep `h1` as source, `h2` as destination, profile `ECG`, and load `10 Mbps`. Click **Run M1–M4 comparison**.

Say: “All four methods receive the same current topology, endpoints, profile, and offered load. M1 is shortest-path, M2 is QoS-aware, M3 is congestion-aware, and M4 evaluates a candidate with the CBDR and critical-class guard logic.”

Show the method table and the **Available route comparison** table. Explain that rows marked selected are used by one or more methods and alternatives remain visible.

## 1:30–2:15 — Show healthcare profiles and metrics

Open the traffic-profile dropdown and show ECG, ICU, TELEMEDICINE, EHR, IMAGING, and CCTV. Return to ECG.

Point to latency, p95/p99, loss, jitter, throughput, fairness, deadline violation, recovery, and overhead.

Say: “These values are calculated from link capacity, latency, jitter, packet loss, offered load, and the selected profile. Route cost follows the displayed project formula, not a random score.”

## 2:15–3:00 — Break a link and show actual graph recalculation

Click **Break** on the `s1–s2` link. The link becomes dashed/disabled. Click **Run M1–M4 comparison**.

Say: “This is a graph mutation, not a label change. The disabled edge is excluded from path search, so the available route set and selected path change.”

Click **Restore** on the same link and confirm the route set returns.

## 3:00–3:45 — Braess before/after

Click **Reset benchmark**. Click **Capture current topology as before**. Click **Restore** on the disabled `s2–s3` shortcut. Select **Braess shortcut before/after** and click **Run M1–M4 comparison**.

Say: “The simulator compares the original and changed graph under identical conditions. A new link is not assumed to help; the result can be beneficial, neutral, harmful, or inconclusive.”

Show the before/after verdicts and M4 reason. Do not call it a classical Braess paradox unless the calculated result is harmful.

## 3:45–4:30 — Change congestion and link quality

In a link row, reduce capacity, increase latency or jitter, or set packet loss to a nonzero value, then click that row’s **Save**. Increase the Load Mbps value and click **Run M1–M4 comparison**.

Say: “The bottleneck and link properties now change the calculated throughput, utilization, congestion, loss, jitter, and route cost. This is the reasoned effect of the graph parameters, not fabricated data.”

## 4:30–5:15 — Critical-class guard

Use a topology where a lower aggregate-cost candidate has latency above a protected deadline, then run M4. The result reason should contain `CRITICAL_CLASS_DEGRADATION` and identify `EMERGENCY_ALARM` or `CRITICAL_PHYSIOLOGICAL_TELEMETRY`.

Say: “M4 does not allow an aggregate improvement to conceal protected critical-class harm. The aggregate evaluation remains visible, but the final decision retains the baseline when a protected class is harmful or violates a hard constraint.”

## 5:15–6:00 — Reset and show history

Click **Reset benchmark**, run once more, then open the **Experiment history** entry.

Say: “The reset returns the simulator to the original benchmark. Each run is saved in the dashboard process history and can be reopened. This history is simulation history, not the persistent live evidence directory.”

## 6:00–6:45 — Live fallback and limitations

Point to the live panel and live Ryu topology status.

Say: “If Ryu is unavailable, the live panel reports unavailable and does not substitute the simulation graph. To run a real experiment, Mininet, OVS, Ryu, and the live runner must be prepared separately. Playground edits never modify the live topology.”

If the live panel is unavailable, continue with the simulation and state: “The live service is unavailable, but that does not invalidate this simulation demonstration because the two paths are intentionally separate.”

## Pre-demo safety checks

- Verify the server is the fresh process by opening `/playground-simulation.js` and confirming JavaScript is returned.
- Reset the topology before starting.
- Use the simulation-only wording for every Playground metric.
- Keep a copy of the original project terminal available.
- Do not claim clinical validation, production deployment, or live Mininet changes from this page.
