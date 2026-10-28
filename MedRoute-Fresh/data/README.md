# Healthcare network workload profiles

`healthcare_traffic_profiles.csv` is MedRoute's reproducible **input workload
catalog**, not a patient dataset and not experiment output. It has six
synthetic traffic profiles. The synthetic metadata source loads traffic type,
criticality, protocol, port, rate, packet size, and representative duration
from this CSV; the traffic classifier's explicit UDP-port and criticality
policy is tested against the catalog so the two stay aligned.

All rates, packet sizes, and durations are declared engineering workload
assumptions for exercising network routing. They are not clinical limits or
claims about actual devices. The dedicated Braess test intentionally declares
its own scenario load (2 Mbit/s ECG and five 20 Mbit/s imaging senders) and
records that configuration with each run. The ordinary experiment runner also
records its chosen rates/durations. Neither scenario overwrites these profiles.

The CSV contains no names, diagnoses, device identifiers, or patient records.
Its purpose is to generate repeatable healthcare-traffic-shaped network loads.
Latency, jitter, packet loss, throughput, and utilization are collected from
Mininet/OpenFlow/iperf/ping during execution and belong in experiment evidence,
never in this input catalog.

The synthetic source uses traffic type, rate, packet size, port, criticality,
and duration from the catalog when it creates metadata records. A consumer can
use those fields to shape traffic; the existing Mininet experiment scripts
still set their scenario-specific `iperf3` rates and durations explicitly.
`duration_seconds` does not override an experiment's explicit duration.
`source_role` and `destination_role` are explanatory labels, not real endpoint
addresses.

## CICIoMT2024 characterization

Raw CICIoMT2024 CSVs are preserved under `data/CICIoMT2024/raw/`. Inventory and
bounded samples are generated with:

```bash
python scripts/preprocess_ciciomt.py --sample-size 1000 --seed 20261015
```

This streams all raw CSVs and writes file sizes, headers, row counts, missing
cell counts, and explicit label-column counts to
`data/CICIoMT2024/processed/inventory.json`. It also writes independent,
deterministic reservoir samples for `Benign_train.pcap.csv` and
`Benign_test.pcap.csv`. Only the training sample contributes to
`benign_training_profile.json`; the test sample is held out from profile
derivation.

The runner accepts `--dataset-profile ciciomt-benign-train`. It maps the
training split's median `AVG` feature to an approximate UDP application payload
(`round(AVG) - 28` bytes, bounded to 1..1400) and passes that value to iperf3
with `-l`. It retains the class-specific offered bit rate from the engineering
catalog. This is a dataset-informed synthetic workload parameter, not packet
replay, a device-specific profile, a clinical priority label, or patient data.
The default `generic` profile keeps the existing workload behavior.
