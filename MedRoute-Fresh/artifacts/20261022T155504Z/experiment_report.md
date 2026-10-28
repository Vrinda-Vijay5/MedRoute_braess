# Stage 6 experiment summary

Mean ± sample standard deviation, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 4.463 ± 0.062 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.170 ± 0.040 ms (n=3) |
| baseline_no_prioritization | ECG | 4.452 ± 0.045 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.157 ± 0.015 ms (n=3) |
| baseline_no_prioritization | ICU | 4.482 ± 0.078 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.167 ± 0.012 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 4.463 ± 0.061 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.180 ± 0.036 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 4.488 ± 0.146 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.030 ms (n=3) |
| class_prioritization_no_congestion | ECG | 4.485 ± 0.148 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.150 ± 0.030 ms (n=3) |
| class_prioritization_no_congestion | ICU | 4.432 ± 0.096 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.133 ± 0.021 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 4.445 ± 0.123 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.147 ± 0.064 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 4.897 ± 0.101 ms (n=3) | 13.179 ± 0.270 Mbps (n=3) | 36.933 ± 0.174% (n=3) | 0.333 ± 0.104 ms (n=3) |
| heavy_background_no_prioritization | ECG | 4.952 ± 0.203 ms (n=3) | 0.315 ± 0.002 Mbps (n=3) | 36.011 ± 0.350% (n=3) | 0.313 ± 0.100 ms (n=3) |
| heavy_background_no_prioritization | ICU | 4.952 ± 0.189 ms (n=3) | 0.313 ± 0.013 Mbps (n=3) | 35.701 ± 1.795% (n=3) | 0.330 ± 0.113 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 4.883 ± 0.136 ms (n=3) | 0.313 ± 0.007 Mbps (n=3) | 34.005 ± 1.476% (n=3) | 0.277 ± 0.107 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 4.870 ± 0.050 ms (n=3) | 2.880 ± 0.007 Mbps (n=3) | 85.568 ± 0.029% (n=3) | 0.238 ± 0.035 ms (n=3) |
| heavy_background_with_prioritization | ECG | 4.502 ± 0.008 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.147 ± 0.032 ms (n=3) |
| heavy_background_with_prioritization | ICU | 4.485 ± 0.041 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.163 ± 0.042 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 4.492 ± 0.036 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.157 ± 0.042 ms (n=3) |

## Workload provenance

Dataset: CICIoMT2024 · profile version ciciomt-benign-v1 · source data/CICIoMT2024/processed/workload_profiles.json · SHA-256 151ed44e4b6f085fff97f56e15448653defcefb912b5663e9c8dbc5213e8ff19.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

