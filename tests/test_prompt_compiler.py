import tempfile
import unittest
from pathlib import Path

from src.prompt_compiler import compile_brief
from src.state import SlideBrief


class TestPromptCompiler(unittest.TestCase):
    def test_compiler_injects_locked_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assets = Path(tmpdir) / "assets" / "potero"
            assets.mkdir(parents=True)
            (assets / "potero_shader_v1_1.txt").write_text("shader")
            (assets / "potero_negative_v1_1.txt").write_text("negative")

            brief = SlideBrief(
                index=1,
                shot_type="hero",
                positive_prompt="scene",
                negative_prompt="avoid",
                reference_assets=[],
            )
            compiled = compile_brief(brief, assets_dir=Path(tmpdir) / "assets")

            self.assertIn("<<POTERO_SHADER:v1_1>>", compiled.positive_prompt)
            self.assertIn("shader", compiled.positive_prompt)
            self.assertIn("<<POTERO_NEGATIVE:v1_1>>", compiled.negative_prompt)
            self.assertIn("negative", compiled.negative_prompt)
