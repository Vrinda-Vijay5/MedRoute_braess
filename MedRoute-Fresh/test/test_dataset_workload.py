import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "dataset_workload", ROOT / "scripts" / "dataset_workload.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DatasetWorkloadTests(unittest.TestCase):
    def test_supplied_training_profile_and_catalog_are_traceable(self):
        provenance = MODULE.load_profiles(ROOT)
        try:
            catalog = MODULE.load_traffic_catalog(ROOT)
        except ValueError as exc:
            if "Git LFS pointer" in str(exc):
                self.skipTest("Git LFS catalog object is unavailable in this checkout")
            raise
        self.assertEqual(provenance["dataset"], "CICIoMT2024")
        self.assertEqual(provenance["profile_version"], "unspecified")
        self.assertEqual(provenance["source_kind"], "training-derived aggregate profile")
        self.assertEqual(catalog["row_count"], 6)
        self.assertTrue(len(catalog["sha256"]) == 64)
        workloads = MODULE.build_scenario_workloads(
            provenance, {"normal": {"heavy_background": False},
                          "heavy": {"heavy_background": True}},
            ("ECG", "ICU", "WEARABLE", "BACKGROUND"), 20)
        self.assertEqual(workloads["normal"]["ECG"]["dataset_profile"],
                         "ciciomt-benign-train-typical")
        self.assertGreater(workloads["heavy"]["BACKGROUND"]["offered_load_mbps"], 20)

    def test_profile_metadata_falls_back_to_safe_values_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            payload = {
                "dataset": "CICIoMT2024",
                "profiles": {
                    "ciciomt-benign-train-typical": {
                        "split": "train",
                        "offered_rate_bps": 500_000,
                        "packet_size_bytes": 83,
                    },
                    "ciciomt-benign-train-high": {
                        "split": "train",
                        "offered_rate_bps": 700_000,
                        "packet_size_bytes": 109,
                    },
                },
                "train_source_files": ["Benign_train.pcap.csv"],
                "test_source_files_excluded_from_workload_derivation": ["Benign_test.pcap.csv"],
            }
            profile_path = root / "data" / "CICIoMT2024" / "processed"
            profile_path.mkdir(parents=True)
            (profile_path / "workload_profiles.json").write_text(json.dumps(payload), encoding="utf-8")
            provenance = MODULE.load_profiles(root)
            self.assertEqual(provenance["profile_version"], "unspecified")
            self.assertEqual(provenance["source_kind"], "training-derived aggregate profile")

    def test_lfs_pointer_is_reported_as_missing_input_not_a_schema_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            catalog = root / "data" / "CICIoMT2024" / "raw"
            catalog.mkdir(parents=True)
            (catalog / "healthcare_traffic_profiles.csv").write_text(
                "version https://git-lfs.github.com/spec/v1\noid sha256:abc\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Git LFS pointer"):
                MODULE.load_traffic_catalog(root)


if __name__ == "__main__":
    unittest.main()
