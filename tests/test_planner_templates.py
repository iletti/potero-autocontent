import logging
import unittest

from src.agents.planner import Planner, TEMPLATE_SHOTS
from src.state import CarouselState, GlobalConstraints, SlideState


class TemplatePlanner(Planner):
    def __init__(self, planner_mode: str = "template"):
        from pathlib import Path
        self.model_name = "stub"
        self.model = None
        self.registry = None
        self.logger = logging.getLogger(__name__)
        self.planner_mode = planner_mode
        self.potero_shader_version = "v1_2"
        self.potero_image_aspect = "4:5"
        self.potero_image_size = "2K"
        self.potero_allow_warn_pass = False
        self.potero_pass_threshold = 7.5
        self.potero_warn_threshold = 6.0
        self.potero_enable_edit_mode = True
        self.potero_max_refs_per_call = 10
        self.potero_max_refs_hard = 14
        self.potero_assets_dir = Path(__file__).resolve().parents[1] / "assets"


class TestPlannerTemplates(unittest.TestCase):
    def _build_state(self, theme: str) -> CarouselState:
        return CarouselState(
            carousel_id=f"run_{theme}_test",
            global_constraints=GlobalConstraints(
                design_id_locked="hoodie_013_ranger_green",
                environment=theme,
            ),
            slides=[SlideState(index=i) for i in range(1, 6)],
        )

    def test_template_briefs_have_five_slides(self):
        planner = TemplatePlanner()
        state = self._build_state("winter_ambush")
        briefs = planner.generate_briefs(state)
        self.assertEqual(len(briefs), 5)
        self.assertEqual([b.index for b in briefs], [1, 2, 3, 4, 5])

    def test_template_briefs_use_fixed_shot_types(self):
        planner = TemplatePlanner()
        state = self._build_state("winter_ambush")
        briefs = planner.generate_briefs(state)
        self.assertEqual([b.shot_type for b in briefs], TEMPLATE_SHOTS)

    def test_default_template_used_for_unknown_theme(self):
        planner = TemplatePlanner()
        state = self._build_state("unknown_theme")
        briefs = planner.generate_briefs(state)
        self.assertEqual(len(briefs), 5)
        self.assertEqual([b.shot_type for b in briefs], TEMPLATE_SHOTS)

    def test_front_shot_embroidery_is_left_chest_only(self):
        planner = TemplatePlanner()
        state = self._build_state("winter_ambush")
        briefs = planner.generate_briefs(state)
        front_brief = briefs[1]
        prompt = front_brief.positive_prompt.lower()
        self.assertIn("left chest", prompt)
        self.assertIn("potero standard", prompt)

    def test_back_shots_forbid_text_on_back(self):
        planner = TemplatePlanner()
        state = self._build_state("winter_ambush")
        briefs = planner.generate_briefs(state)
        for idx in (0, 2, 3, 4):
            prompt = briefs[idx].positive_prompt.lower()
            self.assertIn("back view", prompt)
            self.assertIn("back design matches reference", prompt)

    def test_non_front_shots_avoid_front_chest(self):
        planner = TemplatePlanner()
        state = self._build_state("winter_ambush")
        briefs = planner.generate_briefs(state)
        for idx in (0, 2, 4):
            negative = briefs[idx].negative_prompt.lower()
            self.assertIn("front chest", negative)

    def test_gear_detail_defaults_to_front_design(self):
        planner = TemplatePlanner()
        state = self._build_state("cqb_raid")
        briefs = planner.generate_briefs(state)
        gear_brief = briefs[3]
        self.assertIn("DESIGN_FRONT", gear_brief.reference_roles_required)
        self.assertIn("color must match the reference", gear_brief.positive_prompt.lower())

    def test_composition_guidance_has_no_text_mentions(self):
        planner = TemplatePlanner()
        state = self._build_state("winter_ambush")
        briefs = planner.generate_briefs(state)
        for brief in briefs:
            if not brief.composition_guidance:
                continue
            guidance = brief.composition_guidance.lower()
            self.assertNotIn("text", guidance)
            self.assertNotIn("typography", guidance)
            self.assertNotIn("logo", guidance)
