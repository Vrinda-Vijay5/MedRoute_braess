import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "experiment_methods", ROOT / "scripts" / "experiment_methods.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

LIVE_SPEC = importlib.util.spec_from_file_location(
    "live_experiment", ROOT / "scripts" / "live_experiment.py")
LIVE = importlib.util.module_from_spec(LIVE_SPEC)
LIVE_SPEC.loader.exec_module(LIVE)


class ExperimentMethodTests(unittest.TestCase):
    def test_available_methods_returns_stable_method_ids(self):
        self.assertEqual(MODULE.available_methods(), ("M1", "M2", "M3"))

    def test_m1_is_static_baseline_without_qos_or_guard(self):
        method = MODULE.get_method("M1")
        self.assertEqual(method.method_id, "M1")
        self.assertEqual(method.name, "shortest_path_baseline")
        self.assertEqual(method.initial_route, "baseline")
        self.assertFalse(method.qos_enabled)
        self.assertFalse(method.candidate_evaluation_enabled)
        self.assertFalse(method.braess_guard_enabled)

    def test_m2_enables_qos_without_candidate_evaluation_or_guard(self):
        method = MODULE.get_method("M2")
        self.assertEqual(method.method_id, "M2")
        self.assertEqual(method.name, "qos_only")
        self.assertEqual(method.initial_route, "baseline")
        self.assertTrue(method.qos_enabled)
        self.assertFalse(method.candidate_evaluation_enabled)
        self.assertFalse(method.braess_guard_enabled)

    def test_m3_enables_qos_candidate_evaluation_and_guard(self):
        method = MODULE.get_method("M3")
        self.assertEqual(method.method_id, "M3")
        self.assertEqual(method.name, "qos_braess_guard")
        self.assertEqual(method.initial_route, "baseline")
        self.assertTrue(method.qos_enabled)
        self.assertTrue(method.candidate_evaluation_enabled)
        self.assertTrue(method.braess_guard_enabled)

    def test_unknown_method_id_raises_clear_value_error(self):
        with self.assertRaisesRegex(ValueError, "unknown experiment method"):
            MODULE.get_method("M4")

    def test_method_policy_is_immutable(self):
        method = MODULE.get_method("M1")
        with self.assertRaises(AttributeError):
            method.qos_enabled = True

    def test_retrieved_policy_cannot_mutate_stored_definition(self):
        method = MODULE.get_method("M1")
        with self.assertRaises(AttributeError):
            method.name = "changed"
        self.assertEqual(MODULE.get_method("M1").name, "shortest_path_baseline")
        self.assertFalse(MODULE.get_method("M1").qos_enabled)



    def test_method_scenario_plan_keeps_policy_fixed(self):
        for method_id, expected_qos in (("M1", False), ("M2", True), ("M3", True)):
            with self.subTest(method=method_id):
                plan = MODULE.build_method_scenario_plan(method_id)
                self.assertEqual(tuple(plan), ("normal_load", "heavy_background"))
                self.assertEqual(plan["normal_load"]["qos_enabled"], expected_qos)
                self.assertEqual(plan["heavy_background"]["qos_enabled"], expected_qos)
                self.assertFalse(plan["normal_load"]["heavy_background"])
                self.assertTrue(plan["heavy_background"]["heavy_background"])

    def test_method_scenario_plan_rejects_unknown_method(self):
        with self.assertRaisesRegex(ValueError, "unknown experiment method"):
            MODULE.build_method_scenario_plan("M4")

    def test_default_runner_plan_preserves_existing_scenario_behavior(self):
        self.assertEqual(LIVE.resolve_method_plan(), LIVE.SCENARIO_PLAN)
        self.assertEqual(list(LIVE.resolve_method_plan().keys()), [
            "baseline_no_prioritization",
            "class_prioritization_no_congestion",
            "heavy_background_no_prioritization",
            "heavy_background_with_prioritization",
        ])

    def test_method_policy_summary_and_plan_are_policy_specific(self):
        summary = LIVE.summarize_method_policy("M1")
        self.assertEqual(summary["selected_method"], "M1")
        self.assertFalse(summary["qos_enabled"])
        self.assertFalse(summary["braess_guard_enabled"])
        plan = LIVE.resolve_method_plan("M2")
        self.assertEqual(plan["normal_load"]["qos_enabled"], True)
        self.assertEqual(plan["heavy_background"]["heavy_background"], True)
        self.assertEqual(plan["heavy_background"]["qos_enabled"], True)

    def test_qos_restore_helper_tracks_requested_policy(self):
        calls = []

        def set_qos(enabled):
            calls.append(enabled)

        self.assertTrue(LIVE.restore_method_qos_state(
            "M2",
            set_qos_fn=set_qos,
            read_qos_fn=lambda: True,
        ))
        self.assertEqual(calls, [True])
        self.assertFalse(LIVE.restore_method_qos_state(
            "M1",
            set_qos_fn=set_qos,
            read_qos_fn=lambda: True,
        ))
        self.assertEqual(calls[-1], False)

    def test_m1_catalog_matrix_summary_is_not_applicable(self):
        matrix_summary, validation_errors = LIVE.catalog_matrix_validation("M1", [])
        self.assertEqual(matrix_summary["status"], "not_applicable")
        self.assertTrue(matrix_summary["skipped"])
        self.assertFalse(matrix_summary["complete"])
        self.assertEqual(validation_errors, [])
        self.assertEqual(LIVE.build_catalog_matrix_summary("M1", [])["status"], "not_applicable")

    def test_m1_skip_does_not_hide_real_failures(self):
        matrix_summary, matrix_errors = LIVE.catalog_matrix_validation("M1", [])
        self.assertEqual(matrix_summary["status"], "not_applicable")
        self.assertEqual(matrix_errors, [])

        base_errors = ["real validation failure"]
        combined_errors = LIVE.combine_validation_errors(base_errors, matrix_errors)
        scenario_validation = not bool(combined_errors)
        self.assertFalse(scenario_validation)
        self.assertEqual(combined_errors, ["real validation failure"])

    def test_m2_runs_catalog_matrix_when_qos_is_enabled(self):
        matrix_summary, validation_errors = LIVE.catalog_matrix_validation("M2", [{"complete": True, "profile": "good"}])
        self.assertFalse(matrix_summary["skipped"])
        self.assertEqual(matrix_summary["profiles"], 1)
        self.assertEqual(validation_errors, [])

        incomplete_summary, incomplete_errors = LIVE.catalog_matrix_validation(
            "M2", [{"complete": False, "profile": "broken"}])
        self.assertFalse(incomplete_summary["skipped"])
        self.assertEqual(incomplete_errors, [
            "catalog profile broken has incomplete live execution or forwarding evidence"
        ])

    def test_m3_catalog_matrix_incomplete_entries_fail_validation(self):
        matrix_summary, validation_errors = LIVE.catalog_matrix_validation(
            "M3", [{"complete": False, "profile": "profile_1"}])
        self.assertFalse(matrix_summary["skipped"])
        self.assertEqual(validation_errors, [
            "catalog profile profile_1 has incomplete live execution or forwarding evidence"
        ])

    def test_braess_validation_is_not_run_for_m1_m2(self):
        for method_id in ("M1", "M2"):
            with self.subTest(method=method_id):
                result = LIVE.braess_validation_result(method_id, [])
                self.assertEqual(result["status"], "not_run")
                self.assertTrue(result["not_applicable"])
                self.assertFalse(result["passed"])

    def test_compute_exit_code_requires_qos_verification_for_method_runs(self):
        self.assertEqual(LIVE.compute_exit_code(True, True, "M1", False), 2)
        self.assertEqual(LIVE.compute_exit_code(True, True, "M2", True), 0)
        self.assertEqual(LIVE.compute_exit_code(True, True, None, None), 0)
        self.assertEqual(LIVE.compute_exit_code(True, False, None, None), 2)

if __name__ == "__main__":
    unittest.main()
