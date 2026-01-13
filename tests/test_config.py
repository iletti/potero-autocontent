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
            config = load_config()
            self.assertTrue(config.run_id)
            self.assertTrue(isinstance(config.output_dir, Path))
            self.assertTrue(isinstance(config.references_dir, Path))
            self.assertTrue(isinstance(config.asset_manifest_path, Path))
        finally:
            os.environ.clear()
            os.environ.update(original)
