# Stage 6 experiment summary

Mean ± sample standard deviation and approximate 95% normal confidence intervals, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 4.457 ± 0.042 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.133 ± 0.021 ms (n=3) |
| baseline_no_prioritization | ECG | 4.413 ± 0.033 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.133 ± 0.006 ms (n=3) |
| baseline_no_prioritization | ICU | 4.427 ± 0.020 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.143 ± 0.035 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 4.455 ± 0.020 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.140 ± 0.020 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 300/300 | 4.970 ms | 5.120 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ECG | 300/300 | 4.940 ms | 5.130 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 4.920 ms | 5.110 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 4.970 ms | 5.130 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 1.0000 (4/4 classes with complete throughput).

| class_prioritization_no_congestion | BACKGROUND | 4.420 ± 0.017 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.127 ± 0.021 ms (n=3) |
| class_prioritization_no_congestion | ECG | 4.447 ± 0.051 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.123 ± 0.015 ms (n=3) |
| class_prioritization_no_congestion | ICU | 4.452 ± 0.075 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.150 ± 0.026 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 4.422 ± 0.035 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.010 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 300/300 | 4.920 ms | 5.090 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ECG | 300/300 | 4.950 ms | 5.210 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 5.010 ms | 5.170 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 4.900 ms | 5.110 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 1.0000 (4/4 classes with complete throughput).

| heavy_background_no_prioritization | BACKGROUND | 4.388 ± 0.041 ms (n=3) | 21.267 ± 0.058 Mbps (n=3) | 0.073 ± 0.127% (n=3) | 0.097 ± 0.012 ms (n=3) |
| heavy_background_no_prioritization | ECG | 4.373 ± 0.070 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.097 ± 0.006 ms (n=3) |
| heavy_background_no_prioritization | ICU | 4.355 ± 0.048 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.093 ± 0.015 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 4.363 ± 0.073 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.107 ± 0.021 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 300/300 | 4.910 ms | 5.060 ms | 0/300 (0.000%) | met | 99.927% | met | 0.073% | met |
| ECG | 300/300 | 4.930 ms | 5.040 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 4.880 ms | 5.260 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 4.920 ms | 5.150 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 0.2856 (4/4 classes with complete throughput).

| heavy_background_with_prioritization | BACKGROUND | 4.883 ± 0.063 ms (n=3) | 11.200 ± 0.000 Mbps (n=3) | 47.000 ± 0.000% (n=3) | 0.200 ± 0.000 ms (n=3) |
| heavy_background_with_prioritization | ECG | 4.433 ± 0.034 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.097 ± 0.015 ms (n=3) |
| heavy_background_with_prioritization | ICU | 4.430 ± 0.054 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.097 ± 0.031 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 4.428 ± 0.053 ms (n=3) | 0.495 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.087 ± 0.012 ms (n=3) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 275/300 | 42.900 ms | 43.000 ms | 25/300 (8.333%) | missed | 53.000% | missed | 47.000% | missed |
| ECG | 300/300 | 4.980 ms | 5.110 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 300/300 | 4.910 ms | 5.070 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 300/300 | 4.970 ms | 5.100 ms | 0/300 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 0.3187 (4/4 classes with complete throughput).


## Workload provenance

Dataset: CICIoMT2024 · profile version unspecified · source data/CICIoMT2024/processed/benign_training_profile.json · SHA-256 a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

