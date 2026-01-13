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
                "global_references": ["m05/missing.png"],
                "m05_swatches": [],
                "designs": {},
            }
            self._write_manifest(references, manifest)
            registry = AssetRegistry.load(references)
            missing = registry.validate()
            self.assertIn("m05/missing.png", missing)

    def test_resolves_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            references = Path(tmpdir) / "references"
            (references / "m05").mkdir(parents=True)
            (references / "hoodies").mkdir(parents=True)

            swatch = references / "m05" / "m05.png"
            swatch.write_text("x")
            hoodie = references / "hoodies" / "h.png"
            hoodie.write_text("x")

            manifest = {
                "global_references": [],
                "m05_swatches": ["m05/m05.png"],
                "designs": {"hoodie_013": {"front": "hoodies/h.png"}},
            }
            self._write_manifest(references, manifest)
            registry = AssetRegistry.load(references)

            self.assertEqual(
                registry.get_m05_swatches(),
                [str(swatch)],
            )
            self.assertEqual(
                registry.get_design_assets("hoodie_013"),
                [str(hoodie)],
            )

    def test_validate_required_errors_on_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            references = Path(tmpdir) / "references"
            references.mkdir()
            manifest = {
                "global_references": [],
                "m05_swatches": [],
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
                "global_references": ["/etc/passwd"],
                "m05_swatches": [],
                "designs": {},
            }
            self._write_manifest(references, manifest)
            registry = AssetRegistry.load(references)
            with self.assertRaises(AssetRegistryError):
                registry.validate()
