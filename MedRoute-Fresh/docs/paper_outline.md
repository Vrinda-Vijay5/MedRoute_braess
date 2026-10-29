# Journal paper outline (evidence-gated)

1. **Abstract** — placeholder until independent-seed results and comparison methods are complete.
2. **Introduction and gap** — test whether a measured route-cost guard can reject harmful candidate routes in a controlled SDN prototype; do not claim novelty until related work is expanded.
3. **Related work** — Wardrop equilibrium, Braess paradox, QoS-aware SDN routing, healthcare/IoMT network assumptions, multi-constraint path selection.
4. **System model and assumptions** — four-switch diamond, fixed routes, offered loads, cost scales, measurement age, and controller confirmation semantics.
5. **Traffic classes and objectives** — six synthetic profile names mapped to four live queues; all current objectives are assumptions pending domain/standards validation.
6. **CBDR algorithm** — evaluator validation, cost comparison, hard constraints, freshness, fairness safeguard, explicit fallback and reason codes.
7. **Analytical Braess model** — edge functions, demand, Wardrop conditions, beneficial/harmful/neutral load regimes.
8. **Implementation and setup** — Mininet, OVS, Ryu/OpenFlow 1.3, data provenance, versions, and evidence format.
9. **Baselines and ablations** — describe M3's measured bottleneck-utilization selector and M4's CBDR path, but report live comparative results and ablations only when matched evidence bundles exist.
10. **Results/statistics** — placeholder for paired independent run seeds, confidence intervals, effect sizes, and flow-installation outcomes.
11. **Fairness and safety** — background throughput/fairness tradeoffs; no patient-level or clinical safety inference.
12. **Threats to validity** — small topology, synthetic traffic, deterministic current generator, measurements, and external validity.
13. **Limitations** — refer to `docs/limitations.md`.
14. **Conclusion and future work** — restrict conclusions to verified analytical and emulated evidence.

No performance result or novelty claim should be filled in from the illustrative project brief. Use only evidence bundles produced by the current code and methods.
