# Stage 6 experiment summary

Mean ± sample standard deviation and approximate 95% normal confidence intervals using Student-t critical values through 30 degrees of freedom and a normal approximation above that; calculated from saved run-level repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 5.450 ± 0.028 ms (n=2) | 0.455 ± 0.001 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.085 ± 0.021 ms (n=2) |
| baseline_no_prioritization | ECG | 5.518 ± 0.074 ms (n=2) | 0.456 ± 0.000 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.095 ± 0.021 ms (n=2) |
| baseline_no_prioritization | ICU | 5.450 ± 0.014 ms (n=2) | 0.523 ± 0.000 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.075 ± 0.007 ms (n=2) |
| baseline_no_prioritization | WEARABLE | 5.475 ± 0.021 ms (n=2) | 0.501 ± 0.000 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.085 ± 0.035 ms (n=2) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 200/200 | 6.020 ms | 6.210 ms | Unavailable/200 (Unavailable) | Unavailable | 100.000% | Unavailable | 0.000% | Unavailable |
| ECG | 200/200 | 6.160 ms | 6.500 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 200/200 | 6.190 ms | 6.600 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 200/200 | 6.000 ms | 6.430 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 0.9963 (4/4 classes with complete throughput).

| class_prioritization_no_congestion | BACKGROUND | 5.525 ± 0.000 ms (n=2) | 0.542 ± 0.001 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.085 ± 0.007 ms (n=2) |
| class_prioritization_no_congestion | ECG | 5.503 ± 0.032 ms (n=2) | 0.512 ± 0.000 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.105 ± 0.049 ms (n=2) |
| class_prioritization_no_congestion | ICU | 5.547 ± 0.110 ms (n=2) | 0.470 ± 0.001 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.100 ± 0.014 ms (n=2) |
| class_prioritization_no_congestion | WEARABLE | 5.513 ± 0.032 ms (n=2) | 0.512 ± 0.001 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.110 ± 0.028 ms (n=2) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 200/200 | 5.780 ms | 6.050 ms | Unavailable/200 (Unavailable) | Unavailable | 100.000% | Unavailable | 0.000% | Unavailable |
| ECG | 200/200 | 5.880 ms | 6.290 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 200/200 | 5.880 ms | 6.020 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 200/200 | 5.850 ms | 6.050 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 0.9975 (4/4 classes with complete throughput).

| emergency_surge | BACKGROUND | 5.705 ± 0.042 ms (n=2) | 0.497 ± 0.003 Mbps (n=2) | 0.220 ± 0.311% (n=2) | 0.165 ± 0.021 ms (n=2) |
| emergency_surge | ECG | 5.742 ± 0.018 ms (n=2) | 13.650 ± 0.778 Mbps (n=2) | 1.190 ± 0.721% (n=2) | 0.165 ± 0.007 ms (n=2) |
| emergency_surge | ICU | 5.688 ± 0.053 ms (n=2) | 13.250 ± 1.485 Mbps (n=2) | 1.750 ± 0.778% (n=2) | 0.145 ± 0.007 ms (n=2) |
| emergency_surge | WEARABLE | 5.700 ± 0.035 ms (n=2) | 0.493 ± 0.001 Mbps (n=2) | 0.044 ± 0.062% (n=2) | 0.145 ± 0.021 ms (n=2) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 200/200 | 16.300 ms | 35.500 ms | Unavailable/200 (Unavailable) | Unavailable | 99.780% | Unavailable | 0.220% | Unavailable |
| ECG | 200/200 | 12.100 ms | 33.500 ms | 0/200 (0.000%) | met | 98.810% | missed | 1.190% | met |
| ICU | 200/200 | 10.200 ms | 33.700 ms | 0/200 (0.000%) | met | 98.250% | missed | 1.750% | met |
| WEARABLE | 200/200 | 11.500 ms | 30.900 ms | 0/200 (0.000%) | met | 99.956% | missed | 0.044% | met |

Jain throughput fairness index: 0.5366 (4/4 classes with complete throughput).

| heavy_background_no_prioritization | BACKGROUND | 5.638 ± 0.025 ms (n=2) | 18.750 ± 1.202 Mbps (n=2) | 1.600 ± 0.000% (n=2) | 0.140 ± 0.014 ms (n=2) |
| heavy_background_no_prioritization | ECG | 5.662 ± 0.088 ms (n=2) | 0.484 ± 0.000 Mbps (n=2) | 0.055 ± 0.078% (n=2) | 0.130 ± 0.014 ms (n=2) |
| heavy_background_no_prioritization | ICU | 5.633 ± 0.011 ms (n=2) | 0.514 ± 0.001 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.150 ± 0.071 ms (n=2) |
| heavy_background_no_prioritization | WEARABLE | 5.640 ± 0.071 ms (n=2) | 0.479 ± 0.000 Mbps (n=2) | 0.034 ± 0.016% (n=2) | 0.140 ± 0.057 ms (n=2) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 200/200 | 9.760 ms | 26.400 ms | Unavailable/200 (Unavailable) | Unavailable | 98.400% | Unavailable | 1.600% | Unavailable |
| ECG | 200/200 | 9.190 ms | 28.800 ms | 0/200 (0.000%) | met | 99.945% | met | 0.055% | met |
| ICU | 200/200 | 8.780 ms | 36.600 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 200/200 | 11.400 ms | 25.800 ms | 0/200 (0.000%) | met | 99.966% | missed | 0.034% | met |

Jain throughput fairness index: 0.2903 (4/4 classes with complete throughput).

| heavy_background_with_prioritization | BACKGROUND | 5.755 ± 0.028 ms (n=2) | 10.250 ± 0.071 Mbps (n=2) | 44.000 ± 1.414% (n=2) | 0.137 ± 0.011 ms (n=2) |
| heavy_background_with_prioritization | ECG | 5.607 ± 0.025 ms (n=2) | 0.511 ± 0.001 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.125 ± 0.007 ms (n=2) |
| heavy_background_with_prioritization | ICU | 5.640 ± 0.057 ms (n=2) | 0.481 ± 0.002 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.100 ± 0.014 ms (n=2) |
| heavy_background_with_prioritization | WEARABLE | 5.680 ± 0.021 ms (n=2) | 0.456 ± 0.001 Mbps (n=2) | 0.000 ± 0.000% (n=2) | 0.115 ± 0.007 ms (n=2) |

### Tail latency and configured service objectives

Tail statistics use nearest-rank per-packet ICMP RTT probes, not application payload latency. Receiver delivery is derived from measured UDP receiver loss. Objective values are prototype policy assumptions, not medical standards or service guarantees.

| Class | RTT probes | p95 RTT | p99 RTT | Deadline misses | Delay target | Delivery | Reliability target | Mean loss | Loss target |
|---|---:|---:|---:|---:|---|---:|---|---:|---|
| BACKGROUND | 186/200 | 63.600 ms | 78.000 ms | Unavailable/200 (Unavailable) | Unavailable | 56.000% | Unavailable | 44.000% | Unavailable |
| ECG | 200/200 | 10.600 ms | 22.400 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |
| ICU | 200/200 | 9.760 ms | 15.900 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |
| WEARABLE | 200/200 | 8.670 ms | 21.700 ms | 0/200 (0.000%) | met | 100.000% | met | 0.000% | met |

Jain throughput fairness index: 0.3235 (4/4 classes with complete throughput).


## Workload provenance

Dataset: CICIoMT2024 · profile version unspecified · source data/CICIoMT2024/processed/benign_training_profile.json · SHA-256 a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

