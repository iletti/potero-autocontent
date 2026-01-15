import tempfile
import unittest
from pathlib import Path

from src.asset_registry import AssetRegistry
from src.reference_selector import select_reference_assets
from src.state import SlideBrief


class TestReferenceSelector(unittest.TestCase):
    def test_selects_with_caps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            refs = Path(tmpdir) / "references"
            refs.mkdir()
            (refs / "env").mkdir()
            (refs / "hoodies").mkdir()
            (refs / "env" / "e.png").write_text("x")
            (refs / "hoodies" / "h.png").write_text("x")

            manifest = {
                "global_references": [
                    {"path": "env/e.png", "role": "ENV_TAIGA_SUMMER_NIGHT"}
                ],
                "designs": {
                    "hoodie": [{"path": "hoodies/h.png", "role": "DESIGN_FRONT"}]
                },
            }
            (refs / "manifest.json").write_text(__import__("json").dumps(manifest))
            registry = AssetRegistry.load(refs)

            brief = SlideBrief(
                index=1,
                shot_type="hero",
                positive_prompt="",
                negative_prompt="",
                reference_assets=[],
                reference_roles_required=["ENV_TAIGA_SUMMER_NIGHT", "DESIGN_FRONT"],
            )
            selected, _, _ = select_reference_assets(
                brief,
                registry,
                max_refs=1,
                hard_cap=2,
                assets_dir=Path(tmpdir),
            )
            self.assertLessEqual(len(selected), 1)
