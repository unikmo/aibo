import importlib.util
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'qa'/'output_quality_gate.py'
spec=importlib.util.spec_from_file_location('quality_gate',path)
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def reviewed_cases(score=10):
    return {"cases":[{
        "scenario":name, "provider":"codex-local",
        "run_id":"verified-run-"+str(i), "reviewer":"Independent reviewer",
        "output":"Evidence-based answer addressing the particular task with specific justified next steps.",
        "scores":{dimension:score for dimension in gate.DIMENSIONS},
        "critical_failures":{flag:False for flag in gate.CRITICAL}
    } for i,name in enumerate(gate.SCENARIOS)]}


class SemanticQualityGateTests(unittest.TestCase):
    def test_real_complete_90_pass(self):
        outcome=gate.evaluate(reviewed_cases(9))
        self.assertTrue(outcome["passed"])
        self.assertEqual(outcome["score"],90)
    def test_89_is_rejected(self):
        outcome=gate.evaluate(reviewed_cases(8.9))
        self.assertFalse(outcome["passed"])
    def test_one_weak_workflow_rejected_despite_good_average(self):
        document=reviewed_cases(10)
        document["cases"][0]["scores"]={d:8 for d in gate.DIMENSIONS}
        self.assertFalse(gate.evaluate(document)["passed"])
        self.assertEqual(len(gate.evaluate(document)["below_90"]),1)
    def test_critical_failure_is_not_offset_by_high_scores(self):
        document=reviewed_cases(10)
        document["cases"][0]["critical_failures"]["invented_external_action"]=True
        self.assertFalse(gate.evaluate(document)["passed"])
    def test_missing_real_run_is_not_credited(self):
        document=reviewed_cases(10)
        document["cases"].pop()
        outcome=gate.evaluate(document)
        self.assertFalse(outcome["passed"])
        self.assertIsNone(outcome["score"])
    def test_mock_cannot_certify_semantic_quality(self):
        document=reviewed_cases(10)
        document["cases"][0]["provider"]="mock"
        self.assertFalse(gate.evaluate(document)["passed"])
    def test_empty_output_is_not_graded_as_success(self):
        document=reviewed_cases(10)
        document["cases"][0]["output"]=" "
        self.assertFalse(gate.evaluate(document)["passed"])
    def test_incomplete_or_fabricated_score_shape_is_rejected(self):
        document=reviewed_cases(10)
        del document["cases"][0]["scores"]["factuality"]
        self.assertFalse(gate.evaluate(document)["passed"])


if __name__=="__main__":
    unittest.main()
