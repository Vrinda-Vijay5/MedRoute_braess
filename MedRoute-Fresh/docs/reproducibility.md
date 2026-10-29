# Reproducibility and run evidence

## Offline validation

From WSL, at the repository root:

```bash
cd /mnt/c/Users/subiw/MEDROUTE_FINAL_GOD_HELP/MedRoute-Fresh
PYTHONDONTWRITEBYTECODE=1 /home/subiw/ryu-env/bin/python -m unittest discover -s test -v
npm test
```

For a fresh WSL setup, use Python 3.12 and install the tagged `ryu4312`
compatibility release. Upstream Ryu 4.34 is from 2020 and fails to build with
current packaging tools. `ryu4312` installs the compatible controller under
the existing `ryu` Python import namespace, so the MedRoute controller code
does not need import changes. It is a third-party maintained fork, not an
upstream Ryu release.

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv mininet openvswitch-switch iperf3
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --upgrade setuptools wheel
.venv/bin/python -m pip install 'ryu4312 @ git+https://github.com/olibrius/ryu4312.git@v4.35.1'
.venv/bin/python -m pip install matplotlib
git -C .. lfs pull
git -C .. lfs checkout
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s test -p 'test_*.py' -v
node --test
```

If this compatibility fork is unsuitable for your deployment, use a
maintained controller such as OpenStack os-ken and port/test the MedRoute Ryu
application against its API before using it; do not treat the two as
drop-in-verified here.

`data/CICIoMT2024/raw/healthcare_traffic_profiles.csv` is LFS-managed. The
runner now fails explicitly if the checkout still contains its LFS pointer; it
does not invent or overwrite the workload catalog.

## Controlled live pilot

Run only in the configured WSL environment with Mininet, OVS, iperf3, and sudo available. A run requires privileged network setup and writes a new, unique directory under `artifacts/`.

```bash
cd /mnt/c/Users/subiw/MEDROUTE_FINAL_GOD_HELP/MedRoute-Fresh
RUN_ID="pilot-$(date -u +%Y%m%dT%H%M%SZ)"
sudo /home/subiw/ryu-env/bin/python scripts/live_experiment.py \
  --evidence-dir "artifacts/$RUN_ID" --repetitions 2
```

The two repetitions are a smoke pilot, not enough for journal-level inference. Do not reuse a populated `--evidence-dir`; use a new ID. The runner writes a manifest and SHA-256 file list even for many partial failures.

## Matched M1--M4 and ablation study

The existing runner supports one method at a time. Use this orchestrator to run every method and each M4 ablation with the same seed/topology condition. It writes one evidence directory per condition plus an index, and records incomplete conditions instead of manufacturing a comparison.

```bash
sudo /home/subiw/ryu-env/bin/python scripts/matched_study.py \
  --output-dir "artifacts/matched-$(date -u +%Y%m%dT%H%M%SZ)" \
  --seeds 101 202 303 --repetitions 2
```

When using the project-local environment, start discovery and the controller
before a live run:

```bash
sudo .venv/bin/ryu-manager --observe-links sdn/controller.py
```

Use at least two seeds for the script and preferably ten or more independent seeds for inference. Do not report M1--M4 or ablation effects until all paired conditions have complete telemetry, forwarding verification, and saved raw results. This checkout has no newly generated matched-study artifact.

## Dashboard and saved results

```bash
npm run dashboard
```

The dashboard reads saved run directories and queries `http://127.0.0.1:8080/medroute/topology` for observed controller topology. Start Ryu with `--observe-links` to populate dynamic switch/link discovery. Set `MEDROUTE_CONTROLLER_URL` when the controller uses another address. Open `http://127.0.0.1:8765/playground` for the in-memory simulation topology editor. Its graph is independent of Mininet and resets when the server restarts. The simulation graph is never used as a fallback for live state. Dashboard presence does not mean current live telemetry is connected. Inspect `manifest.json`, `summary.json`, `scenario_results.json`, `measurements.json`, and `controller.jsonl`; a partial manifest or unavailable metric is not a pass.

The current runner does not resume incomplete matrices. `manifest.json` records `resumable: false` rather than implying checkpoint support.
