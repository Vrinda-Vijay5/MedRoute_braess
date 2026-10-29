# Reproducibility and run evidence

## Offline validation

From WSL, at the repository root:

```bash
cd /mnt/c/Users/subiw/MEDROUTE_FINAL_GOD_HELP/MedRoute-Fresh
PYTHONPATH=test /home/subiw/.venvs/medroute-ryu/bin/python -m unittest discover -s test -v
npm test
```

## Controlled live pilot

Run only in the configured WSL environment with Mininet, OVS, iperf3, and sudo available. A run requires privileged network setup and writes a new, unique directory under `artifacts/`.

```bash
cd /mnt/c/Users/subiw/MEDROUTE_FINAL_GOD_HELP/MedRoute-Fresh
RUN_ID="pilot-$(date -u +%Y%m%dT%H%M%SZ)"
sudo /home/subiw/.venvs/medroute-ryu/bin/python scripts/live_experiment.py \
  --evidence-dir "artifacts/$RUN_ID" --repetitions 2
```

The two repetitions are a smoke pilot, not enough for journal-level inference. Do not reuse a populated `--evidence-dir`; use a new ID. The runner writes a manifest and SHA-256 file list even for many partial failures.

## Dashboard and saved results

```bash
npm run dashboard
```

The dashboard reads saved run directories. Its presence does not mean current live telemetry is connected. Inspect `manifest.json`, `summary.json`, `scenario_results.json`, `measurements.json`, and `controller.jsonl`; a partial manifest or unavailable metric is not a pass.

The current runner does not resume incomplete matrices. `manifest.json` records `resumable: false` rather than implying checkpoint support.
