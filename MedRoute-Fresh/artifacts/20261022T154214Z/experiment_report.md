# Stage 6 experiment summary

Mean ± sample standard deviation, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 3.318 ± 0.038 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.080 ± 0.020 ms (n=3) |
| baseline_no_prioritization | ECG | 3.307 ± 0.028 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.080 ± 0.017 ms (n=3) |
| baseline_no_prioritization | ICU | 3.305 ± 0.010 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.077 ± 0.006 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 3.312 ± 0.016 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.073 ± 0.015 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 3.302 ± 0.048 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.110 ± 0.010 ms (n=3) |
| class_prioritization_no_congestion | ECG | 3.297 ± 0.051 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.110 ± 0.010 ms (n=3) |
| class_prioritization_no_congestion | ICU | 3.310 ± 0.074 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.123 ± 0.015 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 3.320 ± 0.052 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.127 ± 0.015 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 3.338 ± 0.025 ms (n=3) | 21.412 ± 0.033 Mbps (n=3) | 0.309 ± 0.148% (n=3) | 0.127 ± 0.012 ms (n=3) |
| heavy_background_no_prioritization | ECG | 3.338 ± 0.046 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.110 ± 0.030 ms (n=3) |
| heavy_background_no_prioritization | ICU | 3.325 ± 0.018 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.087 ± 0.015 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 3.335 ± 0.030 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.097 ± 0.015 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 3.638 ± 0.051 ms (n=3) | 14.084 ± 0.140 Mbps (n=3) | 33.304 ± 0.635% (n=3) | 0.190 ± 0.010 ms (n=3) |
| heavy_background_with_prioritization | ECG | 3.425 ± 0.046 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.117 ± 0.035 ms (n=3) |
| heavy_background_with_prioritization | ICU | 3.402 ± 0.046 ms (n=3) | 0.500 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.120 ± 0.035 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 3.373 ± 0.021 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.133 ± 0.021 ms (n=3) |

## Workload provenance

Dataset: CICIoMT2024 · profile version ciciomt-benign-v1 · source data/CICIoMT2024/processed/workload_profiles.json · SHA-256 151ed44e4b6f085fff97f56e15448653defcefb912b5663e9c8dbc5213e8ff19.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

