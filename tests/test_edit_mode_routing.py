import unittest

from src.state import CarouselState, GlobalConstraints, SlideBrief, SlideState
from src.graph import create_graph, GraphState, LANGGRAPH_AVAILABLE


class DummyPlanner:
    def __init__(self):
        self.registry = None
        self.potero_assets_dir = None

    def generate_briefs(self, state):
        return [
            SlideBrief(
                index=1,
                shot_type="hero",
                positive_prompt="p",
                negative_prompt="n",
                reference_assets=[],
            )
        ]


class DummyArtist:
    def generate_image(self, brief, anchor_image_path=None):
        return "dummy.png"


class DummyCritic:
    def validate_image(self, image_path, reference_assets=None):
        if image_path == "edited.png":
            return {
                "pass": True,
                "qa_score": 90,
                "qa_status": "pass",
                "feedback": "ok",
                "opsec_pass": True,
                "potero_score": 8.0,
                "repair_mode": None,
                "repair_instructions": "",
                "repair_targets": [],
            }
        return {
            "pass": False,
            "qa_score": 0,
            "qa_status": "fail",
            "feedback": "repair",
            "opsec_pass": True,
            "potero_score": 5.0,
            "repair_mode": "edit",
            "repair_instructions": "fix pals",
            "repair_targets": ["pals_grid"],
        }


class DummyEditor:
    def uses_llm(self):
        return False

    def refine_with_mode(self, brief, critic_payload):
        return brief

    def refine_brief(self, brief, feedback, reference_assets=None, allow_llm=True):
        return brief


class DummyArtistEdit:
    def edit_image(self, brief, image_path, instructions):
        return "edited.png"


class TestEditModeRouting(unittest.TestCase):
    def test_edit_path_triggered(self):
        if not LANGGRAPH_AVAILABLE:
            self.skipTest("langgraph not available")
        state = CarouselState(
            carousel_id="run",
            global_constraints=GlobalConstraints(
                design_id_locked="hoodie",
                environment="forest",
                enable_edit_mode=True,
                anchor_candidates=1,
            ),
            slides=[SlideState(index=1, image_path="dummy.png")],
        )

        workflow = create_graph(
            planner=DummyPlanner(),
            artist=DummyArtist(),
            critic=DummyCritic(),
            editor=DummyEditor(),
            artist_edit=DummyArtistEdit(),
        )
        app = workflow.compile()
        initial_state = GraphState(
            carousel_state=state,
            briefs=[
                SlideBrief(
                    index=1,
                    shot_type="hero",
                    positive_prompt="p",
                    negative_prompt="n",
                    reference_assets=[],
                )
            ],
            retry_count=0,
            critic_passed=False,
            critic_feedback=None,
            skip_validation=False,
        )

        app.invoke(initial_state, {"recursion_limit": 5})
        self.assertEqual(state.slides[0].image_path, "edited.png")
