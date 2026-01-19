import json
import tempfile
import unittest
from pathlib import Path

from src.asset_registry import AssetRegistry, AssetRegistryError


class TestAssetRegistry(unittest.TestCase):
    def _write_manifest(self, base: Path, payload: dict) -> Path:
        manifest_path = base / "manifest.json"
        manifest_path.write_text(json.dumps(payload))
        return manifest_path

    def test_validate_detects_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            references = Path(tmpdir) / "references"
            references.mkdir()
            manifest = {
                "global_references": ["env/missing.png"],
                "designs": {},
            }
            self._write_manifest(references, manifest)
            registry = AssetRegistry.load(references)
            missing = registry.validate()
            self.assertIn("env/missing.png", missing)

    def test_resolves_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            references = Path(tmpdir) / "references"
            (references / "hoodies").mkdir(parents=True)
            (references / "env").mkdir(parents=True)

            hoodie = references / "hoodies" / "h.png"
            hoodie.write_text("x")
            hoodie_alt = references / "hoodies" / "h2.png"
            hoodie_alt.write_text("x")
            env = references / "env" / "e.png"
            env.write_text("x")

            manifest = {
                "global_references": [{"path": "env/e.png", "role": "ENV_TEST"}],
                "designs": {
                    "hoodie_013": [
                        {"path": "hoodies/h.png", "role": "DESIGN_FRONT"}
                    ],
                    "hoodie_014": [
                        {"path": "hoodies/h2.png", "role": "DESIGN_FRONT"}
                    ],
                },
            }
            self._write_manifest(references, manifest)
            registry = AssetRegistry.load(references)

            self.assertEqual(
                registry.get_design_assets("hoodie_013"),
                [str(hoodie)],
            )
            assets_by_role = registry.get_assets_by_role(
                ["DESIGN_FRONT", "ENV_TEST"],
                design_id="hoodie_013",
            )
            self.assertEqual(assets_by_role["DESIGN_FRONT"], [str(hoodie)])
            self.assertEqual(assets_by_role["ENV_TEST"], [str(env)])

    def test_validate_required_errors_on_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            references = Path(tmpdir) / "references"
            references.mkdir()
            manifest = {
                "global_references": [],
                "designs": {},
            }
            self._write_manifest(references, manifest)
            registry = AssetRegistry.load(references)
            with self.assertRaises(AssetRegistryError):
                registry.validate_required("hoodie_013")

    def test_rejects_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            references = Path(tmpdir) / "references"
            references.mkdir()
            manifest = {
                "global_references": [{"path": "/etc/passwd", "role": "ENV_BAD"}],
                "designs": {},
            }
            self._write_manifest(references, manifest)
            registry = AssetRegistry.load(references)
            with self.assertRaises(AssetRegistryError):
                registry.validate()
