import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evidence_manifest import write_manifest


class EvidenceManifestTests(unittest.TestCase):
    def test_manifest_hashes_files_and_lists_missing_stages(self):
        with tempfile.TemporaryDirectory(prefix="medroute-manifest-") as temp:
            run = Path(temp) / "run-abc"
            run.mkdir()
            (run / "summary.json").write_text(json.dumps({"live_experiment": "inconclusive"}))
            (run / "raw.json").write_text('{"sample": 1}\n')
            manifest = write_manifest(run, started_at="2026-01-01T00:00:00+00:00")
            self.assertEqual(manifest["run_id"], "run-abc")
            self.assertEqual(manifest["status"], "partial")
            self.assertIn("scenario_results.json", manifest["missing_expected_files"])
            raw = next(item for item in manifest["files"] if item["path"] == "raw.json")
            self.assertEqual(raw["sha256"], hashlib.sha256((run / "raw.json").read_bytes()).hexdigest())
            checksums = (run / "checksums.sha256").read_text()
            self.assertIn("raw.json", checksums)
            self.assertFalse(manifest["resumable"])

    def test_failed_run_is_marked_failed_and_historical_run_is_not_required(self):
        with tempfile.TemporaryDirectory(prefix="medroute-manifest-failed-") as temp:
            run = Path(temp) / "run-failed"
            run.mkdir()
            (run / "error.txt").write_text("intentional test fixture")
            manifest = write_manifest(run)
            self.assertEqual(manifest["status"], "failed")


if __name__ == "__main__":
    unittest.main()
