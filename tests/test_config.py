import os
import unittest
from pathlib import Path

from src.config import load_config


class TestConfig(unittest.TestCase):
    def test_load_config_defaults(self):
        original = dict(os.environ)
        try:
            os.environ.pop("POTERO_RUN_ID", None)
            os.environ.pop("POTERO_ASSETS_DIR", None)
            os.environ.pop("POTERO_OUTPUT_DIR", None)
            os.environ.pop("POTERO_REFERENCES_DIR", None)
            os.environ.pop("POTERO_ASSET_MANIFEST", None)
            os.environ.pop("POTERO_PLANNER_MODEL", None)
            os.environ.pop("POTERO_CRITIC_MODEL", None)
            os.environ.pop("POTERO_EDITOR_MODEL", None)
            config = load_config()
            self.assertTrue(config.run_id)
            self.assertTrue(isinstance(config.output_dir, Path))
            self.assertTrue(isinstance(config.references_dir, Path))
            self.assertTrue(isinstance(config.asset_manifest_path, Path))
            self.assertEqual(config.planner_model, "gemini-3-flash-preview")
            self.assertEqual(config.critic_model, "gemini-3-flash-preview")
            self.assertEqual(config.editor_model, "gemini-3-flash-preview")
        finally:
            os.environ.clear()
            os.environ.update(original)
