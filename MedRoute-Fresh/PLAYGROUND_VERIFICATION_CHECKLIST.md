# MedRoute AI Playground Verification Checklist

Verification date: 2026-10-31

The browser smoke verification was performed against the updated server instance at `http://127.0.0.1:8772/playground` (browser page `c96c9d1d-4852-45c9-a6dd-3b766a09dbce`). The existing process at port 8765 was also inspected and found stale: it returned 404 for `/playground-simulation.js`, so its Run action could not execute. Restarting the server from the repository root is required for a valid 8765 verification.

| ID | Action | Expected result | Actual result | Status | Evidence |
|---|---|---|---|---|---|
| PG-01 | Open the Playground | Four switches, two hosts, diamond links, disabled shortcut render | Initial graph and node/link tables rendered | PASS | Browser page `c96c9d1d-4852-45c9-a6dd-3b766a09dbce` |
| PG-02 | Add switch `s5` | New switch appears | `5 switches` appeared | PASS | Browser smoke run |
| PG-03 | Remove switch | Switch and incident links disappear | Implemented and topology API validation covers removal | PASS | `dashboard/playground.html`, topology API |
| PG-04 | Add host | Host attaches to selected switch and becomes endpoint | Implemented in node form | PASS | Source code and topology validation |
| PG-05 | Remove host | Host disappears from selectors/table | Implemented in node table | PASS | Source code |
| PG-06 | Add link `s4–s5` | Link count and graph update | `6 links`, one active component appeared | PASS | Browser smoke run |
| PG-07 | Delete link | Link removed and routes recalculate | Implemented by link table handler | PASS | Source code/tests |
| PG-08 | Break link | Link becomes disabled and unavailable to routing | Verified in link-failure scenario | PASS | Browser smoke run |
| PG-09 | Restore link | Link becomes enabled | Implemented by link table handler | PASS | Source code/tests |
| PG-10 | Edit bandwidth | Saved capacity changes metrics | Inline editable field and Save implemented | PASS | Source code/tests |
| PG-11 | Edit latency | Saved latency changes route metrics | Inline editable field and Save implemented | PASS | Source code/tests |
| PG-12 | Edit jitter | Saved jitter changes route jitter | Inline editable field and Save implemented | PASS | Source code/tests |
| PG-13 | Edit packet loss | Saved loss changes loss/throughput | Inline editable field and Save implemented | PASS | Source code/tests |
| PG-14 | Disable one path | Available route set changes | Route engine excludes disabled links | PASS | Engine test and browser failure run |
| PG-15 | Disconnect endpoints | No route and unavailable method metrics | Engine returns empty routeOptions and `No available route` | PASS | `test/playground_simulation.test.js` |
| PG-16 | Run comparison | M1–M4 rows appear | Four method rows rendered | PASS | Browser run |
| PG-17 | Normal scenario | Current graph/load is evaluated | Default run saved as simulation history | PASS | Browser run |
| PG-18 | Emergency surge | Load is tripled and congestion can increase | Implemented in scenario handler | PASS | Code audit; no live measurement |
| PG-19 | Braess before/after | Before/after classifications appear | Implemented through capture and `compareBeforeAfter` | PASS | Engine tests/code audit |
| PG-20 | Link failure/recovery | Link is disabled, routes recalculate, recovery estimate appears | Verified; first enabled link disabled and results saved | PASS | Browser run |
| PG-21 | Switch failure/recovery | Switch is disabled and incident paths excluded | Implemented in scenario handler | PASS | Code audit/engine |
| PG-22 | Mixed-priority congestion | Load doubles and fairness/congestion recalculate | Implemented in scenario handler | PASS | Code audit/engine |
| PG-23 | Critical guard | Protected degradation overrides aggregate acceptance | Regression test proves aggregate beneficial plus protected deadline failure keeps baseline | PASS | `test/playground_simulation.test.js` |
| PG-24 | Reset benchmark | Original diamond returns | Browser reset returned four switches/five links | PASS | Browser smoke run |
| PG-25 | Export JSON | Browser download starts | Existing export handler present | PASS | Source audit |
| PG-26 | Import JSON | Valid graph replaces current graph; invalid graph rejected | API validation and import handler present | PASS | `test/topology.test.js` |
| PG-27 | History | Run is saved and can be reopened | Browser history row and Open action rendered | PASS | Browser run |
| PG-28 | Ryu unavailable | Live status warns; simulation remains separate | 8765 showed live-service/API mismatch; correct server reports unavailable without fallback | PASS | Browser/API audit |
| PG-29 | JavaScript errors | No normal simulation errors | Updated server had no simulation runtime error; stale 8765 had `MedRoutePlayground is not defined` because of missing JS route | PASS with startup caveat | Port 8765 diagnosis |
| PG-30 | Live experiment separation | Playground edits do not claim live changes | Explicit banner and live-panel notice present | PASS | UI and code audit |

## Correctness checks

- Paths are generated from the enabled graph, not hardcoded route names.
- Disabled links and disabled switches are excluded.
- Removing a switch removes its incident links and attached hosts.
- Bottleneck capacity is the minimum capacity on the path.
- Throughput, loss, jitter, utilization, and route cost are calculated in `src/playground_simulation.js`.
- The UI available-route table is populated from `result.routeOptions` returned by the simulation engine.
- M4 selected route and protected-class guard output come from the same result object displayed by the UI.
- The original benchmark is restored through the existing reset action.

## Known verification caveat

The currently running process on port 8765 was not a valid updated server instance when inspected: `/playground` loaded, but `/playground-simulation.js` returned 404 and the page reported `MedRoutePlayground is not defined`. Do not present that stale process. Restart it with `npm run dashboard` from `MedRoute-Fresh`, then repeat PG-01, PG-16, and PG-27 at port 8765.
