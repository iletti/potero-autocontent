import unittest

from src.agents.critic import Critic


class TestCriticGrading(unittest.TestCase):
    def test_grade_result_thresholds(self):
        critic = Critic(warn_threshold=85, fail_threshold=70)
        self.assertEqual(critic._grade_result(True, 90), "pass")
        self.assertEqual(critic._grade_result(True, 80), "warn")
        self.assertEqual(critic._grade_result(True, 60), "fail")

    def test_grade_result_pass_false(self):
        critic = Critic()
        self.assertEqual(critic._grade_result(False, 100), "fail")

    def test_fail_fast_on_violations(self):
        critic = Critic()
        result = {"pass": True, "qa_score": 90, "feedback": "", "violations": ["face"]}
        updated = critic._apply_fail_fast(result)
        self.assertFalse(updated["pass"])
        self.assertLessEqual(updated["qa_score"], 10)

    def test_fail_fast_on_embroidery_color_mismatch(self):
        critic = Critic()
        result = {
            "pass": True,
            "qa_score": 90,
            "feedback": "Embroidery color mismatch on the left chest.",
            "violations": [],
            "repair_mode": "none",
            "repair_targets": [],
            "repair_instructions": "",
        }
        updated = critic._apply_fail_fast(result)
        self.assertFalse(updated["pass"])
        self.assertEqual(updated["repair_mode"], "edit")
        self.assertIn("embroidery color", updated["repair_targets"])
