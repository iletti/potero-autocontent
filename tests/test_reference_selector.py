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
            (refs / "m05").mkdir()
            (refs / "env" / "e.png").write_text("x")
            (refs / "m05" / "m.png").write_text("x")

            manifest = {
                "global_references": [],
                "m05_swatches": [{"path": "m05/m.png", "role": "TEXTURE_M05_WOODLAND"}],
                "designs": {},
            }
            (refs / "manifest.json").write_text(__import__("json").dumps(manifest))
            registry = AssetRegistry.load(refs)

            brief = SlideBrief(
                index=1,
                shot_type="hero",
                positive_prompt="",
                negative_prompt="",
                reference_assets=[],
                reference_roles_required=["ENV_TAIGA_SUMMER_NIGHT", "TEXTURE_M05_WOODLAND"],
            )
            selected, _, _ = select_reference_assets(
                brief,
                registry,
                max_refs=1,
                hard_cap=2,
                assets_dir=Path(tmpdir),
            )
            self.assertLessEqual(len(selected), 1)
