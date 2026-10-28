# Stage 6 experiment summary

Mean ± sample standard deviation and approximate 95% normal confidence intervals, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 4.322 ± 0.008 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.090 ± 0.017 ms (n=3) |
| baseline_no_prioritization | ECG | 4.330 ± 0.036 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.097 ± 0.006 ms (n=3) |
| baseline_no_prioritization | ICU | 4.340 ± 0.026 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.093 ± 0.021 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 4.332 ± 0.028 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.090 ± 0.020 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 4.382 ± 0.141 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.113 ± 0.040 ms (n=3) |
| class_prioritization_no_congestion | ECG | 4.363 ± 0.093 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.100 ± 0.017 ms (n=3) |
| class_prioritization_no_congestion | ICU | 4.367 ± 0.127 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.090 ± 0.017 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 4.380 ± 0.124 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.127 ± 0.029 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 4.588 ± 0.128 ms (n=3) | 9.233 ± 1.373 Mbps (n=3) | 45.667 ± 11.846% (n=3) | 0.173 ± 0.045 ms (n=3) |
| heavy_background_no_prioritization | ECG | 4.678 ± 0.138 ms (n=3) | 0.406 ± 0.034 Mbps (n=3) | 17.000 ± 7.000% (n=3) | 0.170 ± 0.030 ms (n=3) |
| heavy_background_no_prioritization | ICU | 4.622 ± 0.115 ms (n=3) | 0.407 ± 0.035 Mbps (n=3) | 16.667 ± 7.371% (n=3) | 0.173 ± 0.031 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 4.645 ± 0.104 ms (n=3) | 0.399 ± 0.049 Mbps (n=3) | 17.667 ± 8.327% (n=3) | 0.178 ± 0.038 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 4.577 ± 0.020 ms (n=3) | 1.933 ± 0.256 Mbps (n=3) | 84.000 ± 6.245% (n=3) | 0.147 ± 0.041 ms (n=3) |
| heavy_background_with_prioritization | ECG | 4.495 ± 0.040 ms (n=3) | 0.490 ± 0.006 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.177 ± 0.059 ms (n=3) |
| heavy_background_with_prioritization | ICU | 4.487 ± 0.019 ms (n=3) | 0.493 ± 0.003 Mbps (n=3) | 0.067 ± 0.115% (n=3) | 0.150 ± 0.036 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 4.450 ± 0.057 ms (n=3) | 0.491 ± 0.002 Mbps (n=3) | 0.050 ± 0.087% (n=3) | 0.143 ± 0.050 ms (n=3) |

## Workload provenance

Dataset: CICIoMT2024 · profile version None · source data/CICIoMT2024/processed/benign_training_profile.json · SHA-256 a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

