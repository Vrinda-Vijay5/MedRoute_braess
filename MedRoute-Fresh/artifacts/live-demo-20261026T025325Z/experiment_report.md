# Stage 6 experiment summary

Mean ± sample standard deviation and approximate 95% normal confidence intervals, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 9.183 ± 0.190 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.147 ± 0.031 ms (n=3) |
| baseline_no_prioritization | ECG | 9.053 ± 0.168 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.160 ± 0.026 ms (n=3) |
| baseline_no_prioritization | ICU | 9.187 ± 0.268 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.167 ± 0.029 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 9.183 ± 0.234 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.170 ± 0.026 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 9.188 ± 0.246 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.183 ± 0.035 ms (n=3) |
| class_prioritization_no_congestion | ECG | 9.187 ± 0.265 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.150 ± 0.010 ms (n=3) |
| class_prioritization_no_congestion | ICU | 9.143 ± 0.240 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.153 ± 0.006 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 9.225 ± 0.128 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.200 ± 0.010 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 9.085 ± 0.225 ms (n=3) | 21.233 ± 0.058 Mbps (n=3) | 0.033 ± 0.058% (n=3) | 0.197 ± 0.040 ms (n=3) |
| heavy_background_no_prioritization | ECG | 9.120 ± 0.090 ms (n=3) | 0.493 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.200 ± 0.044 ms (n=3) |
| heavy_background_no_prioritization | ICU | 9.112 ± 0.240 ms (n=3) | 0.493 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.180 ± 0.035 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 9.027 ± 0.181 ms (n=3) | 0.493 ± 0.002 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.163 ± 0.023 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 9.148 ± 0.176 ms (n=3) | 21.200 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.173 ± 0.065 ms (n=3) |
| heavy_background_with_prioritization | ECG | 9.220 ± 0.122 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.200 ± 0.053 ms (n=3) |
| heavy_background_with_prioritization | ICU | 9.153 ± 0.114 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.193 ± 0.031 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 9.182 ± 0.114 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.180 ± 0.036 ms (n=3) |

## Workload provenance

Dataset: CICIoMT2024 · profile version None · source data/CICIoMT2024/processed/benign_training_profile.json · SHA-256 a8326b59835916ae3b8f1952dceda56cf7945a6a2ec75f5a6ab167f279471c3c.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

