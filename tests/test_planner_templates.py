import logging
import unittest

from src.agents.planner import Planner, TEMPLATE_SHOTS
from src.state import CarouselState, GlobalConstraints, SlideState


class TemplatePlanner(Planner):
    def __init__(self, planner_mode: str = "template"):
        self.model_name = "stub"
        self.model = None
        self.registry = None
        self.logger = logging.getLogger(__name__)
        self.planner_mode = planner_mode


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
