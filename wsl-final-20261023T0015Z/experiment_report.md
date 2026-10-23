# Stage 6 experiment summary

Mean ± sample standard deviation and approximate 95% normal confidence intervals, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 4.318 ± 0.028 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.080 ± 0.000 ms (n=3) |
| baseline_no_prioritization | ECG | 4.372 ± 0.016 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.067 ± 0.006 ms (n=3) |
| baseline_no_prioritization | ICU | 4.345 ± 0.057 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.087 ± 0.012 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 4.333 ± 0.035 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.063 ± 0.006 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 4.347 ± 0.090 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.070 ± 0.020 ms (n=3) |
| class_prioritization_no_congestion | ECG | 4.322 ± 0.064 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.077 ± 0.006 ms (n=3) |
| class_prioritization_no_congestion | ICU | 4.332 ± 0.037 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.083 ± 0.015 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 4.322 ± 0.055 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.083 ± 0.012 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 4.667 ± 0.032 ms (n=3) | 8.563 ± 0.402 Mbps (n=3) | 40.667 ± 4.041% (n=3) | 0.153 ± 0.015 ms (n=3) |
| heavy_background_no_prioritization | ECG | 4.675 ± 0.033 ms (n=3) | 0.396 ± 0.012 Mbps (n=3) | 17.333 ± 2.517% (n=3) | 0.157 ± 0.012 ms (n=3) |
| heavy_background_no_prioritization | ICU | 4.673 ± 0.055 ms (n=3) | 0.405 ± 0.017 Mbps (n=3) | 17.000 ± 3.606% (n=3) | 0.145 ± 0.035 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 4.615 ± 0.015 ms (n=3) | 0.404 ± 0.015 Mbps (n=3) | 16.667 ± 3.055% (n=3) | 0.153 ± 0.038 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 4.632 ± 0.038 ms (n=3) | 2.220 ± 0.026 Mbps (n=3) | 89.000 ± 0.000% (n=3) | 0.118 ± 0.029 ms (n=3) |
| heavy_background_with_prioritization | ECG | 4.447 ± 0.090 ms (n=3) | 0.492 ± 0.003 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.087 ± 0.012 ms (n=3) |
| heavy_background_with_prioritization | ICU | 4.397 ± 0.020 ms (n=3) | 0.493 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.103 ± 0.015 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 4.455 ± 0.033 ms (n=3) | 0.493 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.117 ± 0.015 ms (n=3) |

## Workload provenance

Dataset: CICIoMT2024 · profile version None · source data/CICIoMT2024/processed/benign_training_profile.json · SHA-256 a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

