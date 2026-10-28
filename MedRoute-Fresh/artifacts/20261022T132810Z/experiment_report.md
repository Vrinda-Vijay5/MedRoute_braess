# Stage 6 experiment summary

Mean ± sample standard deviation, calculated from saved scenario repetitions. Missing measurements are shown as unavailable.

| Scenario | Class | Latency ms | Throughput Mbps | Loss % | Jitter ms |
|---|---|---|---|---|---|
| baseline_no_prioritization | BACKGROUND | 4.397 ± 0.023 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.143 ± 0.006 ms (n=3) |
| baseline_no_prioritization | ECG | 4.418 ± 0.053 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.173 ± 0.006 ms (n=3) |
| baseline_no_prioritization | ICU | 4.387 ± 0.012 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.183 ± 0.021 ms (n=3) |
| baseline_no_prioritization | WEARABLE | 4.395 ± 0.018 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.157 ± 0.025 ms (n=3) |
| class_prioritization_no_congestion | BACKGROUND | 4.315 ± 0.025 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.117 ± 0.012 ms (n=3) |
| class_prioritization_no_congestion | ECG | 4.345 ± 0.063 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.133 ± 0.042 ms (n=3) |
| class_prioritization_no_congestion | ICU | 4.343 ± 0.015 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.123 ± 0.025 ms (n=3) |
| class_prioritization_no_congestion | WEARABLE | 4.338 ± 0.015 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.123 ± 0.032 ms (n=3) |
| heavy_background_no_prioritization | BACKGROUND | 4.698 ± 0.151 ms (n=3) | 17.845 ± 0.331 Mbps (n=3) | 48.696 ± 0.952% (n=3) | 0.273 ± 0.068 ms (n=3) |
| heavy_background_no_prioritization | ECG | 4.757 ± 0.136 ms (n=3) | 0.512 ± 0.168 Mbps (n=3) | 70.285 ± 9.490% (n=3) | 0.367 ± 0.080 ms (n=3) |
| heavy_background_no_prioritization | ICU | 4.663 ± 0.170 ms (n=3) | 0.559 ± 0.175 Mbps (n=3) | 67.680 ± 9.800% (n=3) | 0.317 ± 0.135 ms (n=3) |
| heavy_background_no_prioritization | WEARABLE | 4.675 ± 0.278 ms (n=3) | 0.492 ± 0.176 Mbps (n=3) | 71.153 ± 9.350% (n=3) | 0.313 ± 0.186 ms (n=3) |
| heavy_background_with_prioritization | BACKGROUND | 30.037 ± 24.936 ms (n=3) | 3.886 ± 0.000 Mbps (n=3) | 83.030 ± 0.013% (n=3) | 46.673 ± 6.270 ms (n=3) |
| heavy_background_with_prioritization | ECG | 4.210 ± 0.013 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.087 ± 0.006 ms (n=3) |
| heavy_background_with_prioritization | ICU | 4.227 ± 0.006 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.093 ± 0.006 ms (n=3) |
| heavy_background_with_prioritization | WEARABLE | 4.235 ± 0.043 ms (n=3) | 1.998 ± 0.000 Mbps (n=3) | 0.000 ± 0.000% (n=3) | 0.103 ± 0.021 ms (n=3) |
