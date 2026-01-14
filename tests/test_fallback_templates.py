import unittest

from src.graph import build_fallback_brief


class TestFallbackTemplates(unittest.TestCase):
    def test_fallback_templates_rotate(self):
        brief1 = build_fallback_brief(1, "forest", "v1_1")
        brief2 = build_fallback_brief(2, "forest", "v1_1")
        brief3 = build_fallback_brief(3, "forest", "v1_1")

        self.assertNotEqual(brief1.shot_type, brief2.shot_type)
        self.assertNotEqual(brief2.shot_type, brief3.shot_type)
        self.assertTrue(brief1.positive_prompt)
