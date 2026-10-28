# Stage 6 experiment summary

Mean ± sample standard deviation, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 5.542 ± 0.180 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.240 ± 0.080 ms (n=3) |
| baseline_no_prioritization | ECG | 5.573 ± 0.172 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.260 ± 0.085 ms (n=3) |
| baseline_no_prioritization | ICU | 5.575 ± 0.204 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.240 ± 0.053 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 5.620 ± 0.213 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.237 ± 0.093 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 5.452 ± 0.146 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.207 ± 0.126 ms (n=3) |
| class_prioritization_no_congestion | ECG | 5.468 ± 0.146 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.203 ± 0.120 ms (n=3) |
| class_prioritization_no_congestion | ICU | 5.452 ± 0.191 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.187 ± 0.115 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 5.432 ± 0.189 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.190 ± 0.092 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 5.442 ± 0.163 ms (n=3) | 21.404 ± 0.112 Mbps (n=3) | 0.302 ± 0.523% (n=3) | 0.137 ± 0.064 ms (n=3) |
| heavy_background_no_prioritization | ECG | 5.433 ± 0.178 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.140 ± 0.053 ms (n=3) |
| heavy_background_no_prioritization | ICU | 5.447 ± 0.199 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.157 ± 0.081 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 5.457 ± 0.217 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.143 ± 0.061 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 6.055 ± 0.009 ms (n=3) | 14.173 ± 0.271 Mbps (n=3) | 32.171 ± 0.134% (n=3) | 0.267 ± 0.059 ms (n=3) |
| heavy_background_with_prioritization | ECG | 5.558 ± 0.053 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.187 ± 0.042 ms (n=3) |
| heavy_background_with_prioritization | ICU | 5.575 ± 0.056 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.187 ± 0.050 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 5.608 ± 0.068 ms (n=3) | 0.499 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.207 ± 0.108 ms (n=3) |

## Workload provenance

Dataset: CICIoMT2024 · profile version ciciomt-benign-v1 · source data/CICIoMT2024/processed/workload_profiles.json · SHA-256 151ed44e4b6f085fff97f56e15448653defcefb912b5663e9c8dbc5213e8ff19.
Training-derived aggregate profiles shape synthetic offered rates and UDP packet sizes; the experiment does not replay raw packets or infer healthcare labels.

