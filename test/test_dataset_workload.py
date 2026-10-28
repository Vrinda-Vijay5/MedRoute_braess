import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "dataset_workload", ROOT / "scripts" / "dataset_workload.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DatasetWorkloadTests(unittest.TestCase):
    def test_supplied_training_profile_and_catalog_are_traceable(self):
        provenance = MODULE.load_profiles(ROOT)
        catalog = MODULE.load_traffic_catalog(ROOT)
        self.assertEqual(provenance["dataset"], "CICIoMT2024")
        self.assertEqual(catalog["row_count"], 6)
        self.assertTrue(len(catalog["sha256"]) == 64)
        workloads = MODULE.build_scenario_workloads(
            provenance, {"normal": {"heavy_background": False},
                          "heavy": {"heavy_background": True}},
            ("ECG", "ICU", "WEARABLE", "BACKGROUND"), 20)
        self.assertEqual(workloads["normal"]["ECG"]["dataset_profile"],
                         "ciciomt-benign-train-typical")
        self.assertGreater(workloads["heavy"]["BACKGROUND"]["offered_load_mbps"], 20)


if __name__ == "__main__":
    unittest.main()
