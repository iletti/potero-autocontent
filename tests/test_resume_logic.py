import unittest

from src.main import _first_incomplete_index
from src.state import CarouselState, GlobalConstraints, SlideState


class TestResumeLogic(unittest.TestCase):
    def test_first_incomplete_index(self):
        state = CarouselState(
            carousel_id="run_test",
            global_constraints=GlobalConstraints(
                design_id_locked="hoodie",
                environment="forest",
            ),
            slides=[
                SlideState(index=1, status="completed", image_path="a.png"),
                SlideState(index=2, status="completed", image_path="b.png"),
                SlideState(index=3, status="failed", image_path=None),
            ],
        )
        self.assertEqual(_first_incomplete_index(state), 2)

    def test_first_incomplete_none(self):
        state = CarouselState(
            carousel_id="run_test",
            global_constraints=GlobalConstraints(
                design_id_locked="hoodie",
                environment="forest",
            ),
            slides=[
                SlideState(index=1, status="completed", image_path="a.png"),
                SlideState(index=2, status="completed", image_path="b.png"),
            ],
        )
        self.assertIsNone(_first_incomplete_index(state))
