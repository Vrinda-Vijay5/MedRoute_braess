# Stage 6 experiment summary

Mean ± sample standard deviation and approximate 95% normal confidence intervals, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 5.490 ± 0.066 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.117 ± 0.006 ms (n=3) |
| baseline_no_prioritization | ECG | 5.478 ± 0.033 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.110 ± 0.010 ms (n=3) |
| baseline_no_prioritization | ICU | 5.457 ± 0.031 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.123 ± 0.006 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 5.458 ± 0.071 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.010 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 5.432 ± 0.048 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.110 ± 0.017 ms (n=3) |
| class_prioritization_no_congestion | ECG | 5.492 ± 0.060 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.117 ± 0.006 ms (n=3) |
| class_prioritization_no_congestion | ICU | 5.493 ± 0.075 ms (n=3) | 0.494 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.127 ± 0.006 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 5.457 ± 0.075 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.117 ± 0.015 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 5.857 ± 0.060 ms (n=3) | 12.833 ± 0.153 Mbps (n=3) | 38.667 ± 0.577% (n=3) | 0.190 ± 0.030 ms (n=3) |
| heavy_background_no_prioritization | ECG | 5.867 ± 0.075 ms (n=3) | 0.371 ± 0.044 Mbps (n=3) | 22.667 ± 8.021% (n=3) | 0.205 ± 0.013 ms (n=3) |
| heavy_background_no_prioritization | ICU | 5.767 ± 0.076 ms (n=3) | 0.390 ± 0.045 Mbps (n=3) | 19.000 ± 7.810% (n=3) | 0.192 ± 0.020 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 5.790 ± 0.048 ms (n=3) | 0.393 ± 0.037 Mbps (n=3) | 19.333 ± 7.506% (n=3) | 0.232 ± 0.026 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 5.918 ± 0.125 ms (n=3) | 2.840 ± 0.017 Mbps (n=3) | 86.000 ± 0.000% (n=3) | 0.115 ± 0.023 ms (n=3) |
| heavy_background_with_prioritization | ECG | 5.523 ± 0.018 ms (n=3) | 0.493 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.117 ± 0.021 ms (n=3) |
| heavy_background_with_prioritization | ICU | 5.537 ± 0.114 ms (n=3) | 0.494 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.010 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 5.497 ± 0.044 ms (n=3) | 0.493 ± 0.001 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.113 ± 0.021 ms (n=3) |

## Workload provenance

Dataset: CICIoMT2024 · profile version ciciomt-benign-v1 · source data/CICIoMT2024/processed/workload_profiles.json · SHA-256 151ed44e4b6f085fff97f56e15448653defcefb912b5663e9c8dbc5213e8ff19.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

