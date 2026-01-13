import tempfile
import unittest
from pathlib import Path

from src.run_storage import RunStorage
from src.model_utils import model_dump


try:
    from src.state import CarouselState, GlobalConstraints, SlideBrief, SlideState
except Exception:  # pragma: no cover - optional dependency for CI
    CarouselState = None
    GlobalConstraints = None
    SlideBrief = None
    SlideState = None


@unittest.skipIf(CarouselState is None, "pydantic not available")
class TestRunStorage(unittest.TestCase):
    def test_save_and_load_state_and_briefs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            storage = RunStorage.create(base_dir, "run_001")

            state = CarouselState(
                carousel_id="run_001",
                global_constraints=GlobalConstraints(
                    design_id_locked="hoodie",
                    environment="forest",
                ),
                slides=[SlideState(index=1), SlideState(index=2)],
            )
            briefs = [
                SlideBrief(
                    index=1,
                    shot_type="hero",
                    positive_prompt="p1",
                    negative_prompt="n1",
                    reference_assets=[],
                ),
                SlideBrief(
                    index=2,
                    shot_type="detail",
                    positive_prompt="p2",
                    negative_prompt="n2",
                    reference_assets=[],
                ),
            ]

            storage.save_state(state)
            storage.save_briefs(briefs)

            loaded_state = storage.load_state()
            loaded_briefs = storage.load_briefs()

            self.assertIsNotNone(loaded_state)
            self.assertIsNotNone(loaded_briefs)
            self.assertEqual(model_dump(loaded_state), model_dump(state))
            self.assertEqual(
                [model_dump(b) for b in loaded_briefs],
                [model_dump(b) for b in briefs],
            )
