# Limitations and threats to validity

- This is a synthetic Mininet/OVS prototype, not a hospital deployment or clinical system.
- The analytical four-node Wardrop result and measured Mininet route degradation answer different questions. Neither establishes the other.
- Candidate route probes are aggregate and do not identify six individual services. The live topology has four policy classes/queues; EHR, imaging, and CCTV share BACKGROUND.
- QoS targets are explicit experimental assumptions. No clinical or standards-based validation is provided. `strict` evaluator mode fails closed for classes without a validated hard-constraint profile.
- The live guard cost combines normalized latency, jitter, and loss with fixed reference scales. Its weights and 5% threshold need preregistration and sensitivity analysis.
- Existing scenario repetitions use a deterministic workload generator; they do not provide independent random seeds. Current confidence intervals are descriptive and not a substitute for run-level replication.
- M3's measured-utilization selector is implemented and unit-tested, but its current live changes and a matched live M1-M4 comparison remain unverified. Five ablations, load/capacity sweeps, Mininet topology scaling, experiment resumption, paired tests, and a complete literature novelty review remain unimplemented.
- The dashboard topology playground is a separate in-memory simulation graph. It is not connected to Mininet, OVS, the controller, or live experiment evidence, and resets when the dashboard server restarts.
- The current dataset integration derives aggregate synthetic workload profiles from benign CICIoMT2024 training CSV features. It does not replay packets, use labels, model patient data, or validate healthcare service targets. The custom six-row healthcare catalog is synthetic input, not CICIoMT source data.
- Link utilization is based on available port counters; queue occupancy, controller CPU/memory, and starvation duration are not collected.
- Barrier confirmation means prior OpenFlow requests were processed on each responding switch. It does not prove traffic delivery or clinical service compliance.
- External validity is limited by the small topology, single host pair for route probes, selected flow durations/rates, and the current OVS/Mininet environment.
