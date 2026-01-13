import unittest

from src.agents.editor import Editor
from src.state import SlideBrief


class TestEditorRefine(unittest.TestCase):
    def test_refine_does_not_echo_feedback_text(self):
        editor = Editor()
        brief = SlideBrief(
            index=1,
            shot_type="hero_shot",
            positive_prompt="Base prompt.",
            negative_prompt="",
            reference_assets=[],
        )
        feedback = "Unapproved text 'Reconnaissance' on hoodie and backpack."
        refined = editor.refine_brief(brief, feedback)
        self.assertNotIn("Reconnaissance", refined.positive_prompt)

