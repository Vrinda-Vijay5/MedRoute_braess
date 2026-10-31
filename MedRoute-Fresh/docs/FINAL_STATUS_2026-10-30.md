# MedRoute finalization status — 2026-10-30

## Verified outcome

MedRoute is a deterministic SDN research/demo prototype. The saved evidence and
offline implementation are demonstrable, but this checkout does not contain a
completed matched live M1–M4 study, independent-seed study, or complete live
ablation matrix.

## Dashboard verification

The documented server command is `npm run dashboard` from the project root. On
PowerShell with script execution disabled, use `npm.cmd run dashboard`; the
earlier malformed-path failure came from an external quoted invocation, not
from `package.json` or `scripts/dashboard_server.js`.

Verified routes:

| Route | Result |
|---|---|
| `/` | 200; dashboard rendered in the browser |
| `/api/runs` | 200; 65 saved runs were listed |
| `/api/run/pilot-20261029T142341Z` | 200; summary, measurements, scenarios, profile matrix, and files loaded |
| `/api/live/topology` | 503 when no controller is reachable; no simulation fallback is used |
| `/artifact/pilot-20261029T142341Z/experiment_report.md` | 200; artifact served |

The dashboard dynamically loads the selected run. The experiment table in
`dashboard/index.html` is populated from saved `scenario_results.json`; it is
not hard-coded. A narrow server fix now enriches missing run timestamps from
`manifest.json` and supplies the separate saved analytical model when a live
run has no local `analytical.json`. The analytical result remains explicitly
separate from live measurements.

## Evidence index

| Run | Scenarios | Repetitions | Telemetry | Flows | Recovery | Braess result | Prevention |
|---|---:|---:|---|---|---|---|---|
| `pilot-20261029T142341Z` | 5 | 2 each; 2 paired shortcut decisions | Required complete; optional fairness missing | Verified | Verified, 3/3 probes | One beneficial, one neutral; no harmful shortcut observed | Not triggered |
| `research-pilot-20261029T080424Z` | 4 | 2 each; 2 paired decisions | Complete in saved run | Verified | Verified, 3/3 probes | Mixed historical pilot; harmful decision present | Harmful shortcut prevented |
| `wsl-final-20261023T0015Z` | 4 | 3 each; 3 decisions | Complete | Verified | Verified | Harmful | Verified |
| `wsl-profile-matrix-20261023T0130Z` | 4 | 3 each; 3 decisions | Complete | Verified | Verified | Neutral | Not triggered; two prevention-count records are not a harmful-prevention claim |

Historical prevention evidence and the latest pilot are separate experiments and
must not be pooled into one success rate.

## M1–M4 implementation audit

| Method | Actual implementation | Current status |
|---|---|---|
| M1 | Baseline route, QoS disabled, candidate/Braess evaluation disabled | Implemented prototype baseline; no matched live result |
| M2 | Baseline route with the four configured QoS classes; candidate evaluation disabled | Implemented prototype QoS-only method; no matched live result |
| M3 | Measures baseline, alternate, and shortcut route conditions, selects minimum measured bottleneck-utilization route, and does not invoke CBDR | Real congestion-selection branch exists and is unit-tested; live matched verification is absent |
| M4 | Runs class-aware baseline/candidate profile measurements, fairness and network-cost checks, criticality policy, CBDR evaluation, flow verification, and explicit ablations | Real CBDR prototype path exists; no completed paired M1–M4 comparison |

The metadata helper describes M3 using the same QoS/scenario-plan fields as M2;
that is a documentation/metadata limitation, not evidence that the M3 runtime
branch is absent. No method was renamed or rewritten during finalization.

## Existing ablations

The runner exposes M4 ablations for `disable_braess_detection`,
`disable_priority_handling`, and `disable_link_change_evaluation`. The code
contains separate control paths, but this checkout has no completed paired live
ablation artifact. Therefore no ablation effect or statistical significance is
claimed.

## Analytical versus live result

The analytical Wardrop example records average cost 65 without the shortcut and
80 with it at demand 4000. The live pilot instead observed one beneficial and
one neutral shortcut comparison. The analytical result predicts a canonical
model behavior; it does not prove that every live workload produces a harmful
shortcut.

## Failure and recovery

Saved runs inject failure of `s1-eth2 ↔ s2-eth1`, select the recovery route,
verify installed flows, and preserve connectivity. The saved recovery probe in
the latest pilot received 3/3 packets. The latest pilot records completion but
does not provide a separately reported detection/recovery duration suitable for
a timing claim.

## Demonstration commands

From `C:\Users\subiw\MEDROUTE_FINAL_GOD_HELP\MedRoute-Fresh`:

```powershell
npm.cmd run dashboard
npm.cmd test
```

Open:

```text
http://127.0.0.1:8765/?run=pilot-20261029T142341Z
http://127.0.0.1:8765/?run=wsl-final-20261023T0015Z
http://127.0.0.1:8765/playground
```

The WSL-only live commands remain documented in `docs/reproducibility.md`.
WSL was not runnable in this audit because the host returned
`Wsl/Service/CreateInstance/E_ACCESSDENIED`; no new live experiment was started.

## Final demonstration sequence

1. Start the dashboard and open the latest pilot URL. Show the executive cards,
   saved run selector, scenario table, plots, six-profile matrix, flow links,
   recovery result, QoS metrics, and dataset provenance.
2. Open `/playground`; explain that its graph is in-memory simulation only and
   never changes Mininet.
3. Select `wsl-final-20261023T0015Z`; show the historical harmful shortcut,
   baseline selection, forwarding proof, and recovery artifact.
4. Select `research-pilot-20261029T080424Z`; explain that this separate pilot
   contains harmful prevention evidence.
5. Return to `pilot-20261029T142341Z`; explain that its two shortcut decisions
   were beneficial and neutral, so prevention was not triggered.
6. Show the analytical 65-to-80 model and state that it is separate from live
   measurements.
7. Show the M1–M4 table and explicitly say that matched live results are not
   available in this checkout.
8. Run `npm.cmd test` and show the passing Node test output. Present the saved
   Python result as historical documentation unless the WSL Python suite is
   rerun successfully in the demonstration environment.
9. Show `manifest.json`, `checksums.sha256`, `summary.json`,
   `scenario_results.json`, `controller.jsonl`, flow dumps, plots, and the
   per-run SQLite database.
10. Close with the limitations: synthetic workload, fixed emulated topology,
    small repeated samples, no clinical validation, no production deployment,
    no independent-seed inference, and no proven patent novelty.
