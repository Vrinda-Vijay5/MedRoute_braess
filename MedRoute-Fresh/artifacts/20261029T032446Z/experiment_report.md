# Stage 6 experiment summary

Mean ± sample standard deviation and approximate 95% normal confidence intervals, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 5.623 ± 0.157 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.160 ± 0.036 ms (n=3) |
| baseline_no_prioritization | ECG | 5.652 ± 0.113 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.127 ± 0.025 ms (n=3) |
| baseline_no_prioritization | ICU | 5.637 ± 0.193 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.137 ± 0.045 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 5.632 ± 0.144 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.153 ± 0.015 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 300/300 | 6.270 ms | 6.420 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ECG | 300/300 | 6.270 ms | 6.430 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 6.250 ms | 6.560 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 6.240 ms | 6.470 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 1.0000 (4/4 classes with complete throughput).

| class_prioritization_no_congestion | BACKGROUND | 5.688 ± 0.038 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.147 ± 0.031 ms (n=3) |
| class_prioritization_no_congestion | ECG | 5.682 ± 0.038 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.167 ± 0.015 ms (n=3) |
| class_prioritization_no_congestion | ICU | 5.675 ± 0.039 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.160 ± 0.020 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 5.632 ± 0.081 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.157 ± 0.023 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 300/300 | 6.350 ms | 6.500 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ECG | 300/300 | 6.330 ms | 6.540 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 6.280 ms | 6.500 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 6.290 ms | 6.520 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 1.0000 (4/4 classes with complete throughput).

| heavy_background_no_prioritization | BACKGROUND | 5.462 ± 0.060 ms (n=3) | 21.200 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.020 ms (n=3) |
| heavy_background_no_prioritization | ECG | 5.432 ± 0.018 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.026 ms (n=3) |
| heavy_background_no_prioritization | ICU | 5.497 ± 0.052 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.127 ± 0.006 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 5.428 ± 0.010 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.010 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 300/300 | 6.180 ms | 6.330 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ECG | 300/300 | 6.010 ms | 6.240 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 6.110 ms | 6.290 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 6.040 ms | 6.260 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 0.2857 (4/4 classes with complete throughput).

| heavy_background_with_prioritization | BACKGROUND | 6.037 ± 0.095 ms (n=3) | 11.067 ± 0.115 Mbps (n=3) | 47.667 ± 0.577% (n=3) | 0.203 ± 0.006 ms (n=3) |
| heavy_background_with_prioritization | ECG | 5.660 ± 0.076 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.130 ± 0.017 ms (n=3) |
| heavy_background_with_prioritization | ICU | 5.663 ± 0.087 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.127 ± 0.038 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 5.703 ± 0.058 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.140 ± 0.020 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 280/300 | 44.100 ms | 48.600 ms | 20/300 (6.667%) | missed | 52.333% | missed | 47.667% | missed |
| ECG | 300/300 | 6.410 ms | 7.370 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 6.410 ms | 7.300 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 6.470 ms | 7.940 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 0.3195 (4/4 classes with complete throughput).


## Workload provenance

Dataset: CICIoMT2024 · profile version unspecified · source data/CICIoMT2024/processed/benign_training_profile.json · SHA-256 a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

