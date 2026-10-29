import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("matched_study", ROOT / "scripts" / "matched_study.py")
study = importlib.util.module_from_spec(spec); spec.loader.exec_module(study)


class MatchedStudyTests(unittest.TestCase):
    def test_each_seed_has_all_methods_and_independent_ablations(self):
        plan = study.study_plan([7, 8])
        self.assertEqual(len(plan), 14)
        for seed in (7, 8):
            rows = [row for row in plan if row["seed"] == seed]
            self.assertEqual({row["method"] for row in rows if row["ablation"] is None}, set(study.METHODS))
            self.assertEqual({row["ablation"] for row in rows if row["ablation"]}, set(study.ABLATIONS))
