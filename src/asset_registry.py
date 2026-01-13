from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class AssetRegistryError(Exception):
    pass


@dataclass(frozen=True)
class AssetRegistry:
    references_dir: Path
    manifest_path: Path
    manifest: Dict[str, Any]

    @classmethod
    def load(
        cls,
        references_dir: Path,
        manifest_path: Optional[Path] = None,
    ) -> "AssetRegistry":
        if not references_dir.exists():
            raise AssetRegistryError(
                f"References directory not found: {references_dir}"
            )
        resolved_manifest = manifest_path or references_dir / "manifest.json"
        if not resolved_manifest.exists():
            raise AssetRegistryError(
                f"Manifest not found: {resolved_manifest}"
            )
        try:
            manifest = json.loads(resolved_manifest.read_text())
        except json.JSONDecodeError as exc:
            raise AssetRegistryError(
                f"Manifest JSON invalid: {resolved_manifest}"
            ) from exc
        if not isinstance(manifest, dict):
            raise AssetRegistryError("Manifest must be a JSON object.")
        return cls(
            references_dir=references_dir,
            manifest_path=resolved_manifest,
            manifest=manifest,
        )

    def validate(self) -> List[str]:
        missing: List[str] = []
        for raw_path in self._collect_paths():
            rel_path = self._ensure_relative(raw_path)
            absolute = self.references_dir / rel_path
            if not absolute.exists():
                missing.append(str(rel_path))
        return missing

    def validate_required(self, design_id: str) -> List[str]:
        required: List[str] = []
        required.extend(self._extract_paths(self.manifest.get("m05_swatches", [])))
        designs = self.manifest.get("designs", {})
        if isinstance(designs, dict):
            design_entry = designs.get(design_id) or {}
            required.extend(self._extract_paths(design_entry))

        if not required:
            raise AssetRegistryError(
                "Manifest must include m05_swatches and design assets."
            )

        missing: List[str] = []
        for raw_path in required:
            rel_path = self._ensure_relative(raw_path)
            absolute = self.references_dir / rel_path
            if not absolute.exists():
                missing.append(str(rel_path))
        return missing

    def asset_count(self) -> int:
        return len(self._collect_paths())

    def get_global_assets(self) -> List[str]:
        return self._resolve_list(
            self._extract_paths(self.manifest.get("global_references", []))
        )

    def get_m05_swatches(self) -> List[str]:
        return self._resolve_list(
            self._extract_paths(self.manifest.get("m05_swatches", []))
        )

    def get_design_assets(self, design_id: str) -> List[str]:
        designs = self.manifest.get("designs", {})
        if not isinstance(designs, dict):
            raise AssetRegistryError("Manifest designs must be an object.")
        entry = designs.get(design_id)
        if entry is None:
            return []
        return self._resolve_list(self._extract_paths(entry))

    def _collect_paths(self) -> List[str]:
        paths: List[str] = []
        paths.extend(
            self._extract_paths(self.manifest.get("global_references", []))
        )
        paths.extend(
            self._extract_paths(self.manifest.get("m05_swatches", []))
        )
        designs = self.manifest.get("designs", {})
        if isinstance(designs, dict):
            for entry in designs.values():
                paths.extend(self._extract_paths(entry))
        return paths

    def _resolve_list(self, paths: List[str]) -> List[str]:
        resolved: List[str] = []
        for raw_path in paths:
            rel_path = self._ensure_relative(raw_path)
            resolved.append(str(self.references_dir / rel_path))
        return resolved

    def _extract_paths(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            if not all(isinstance(item, str) for item in value):
                raise AssetRegistryError(
                    "Manifest list entries must be strings."
                )
            return value
        if isinstance(value, dict):
            if not all(isinstance(item, str) for item in value.values()):
                raise AssetRegistryError(
                    "Manifest dict entries must be strings."
                )
            return list(value.values())
        raise AssetRegistryError("Manifest entries must be string, list, or dict.")

    def _ensure_relative(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute() or ".." in path.parts:
            raise AssetRegistryError(
                f"Manifest path must be relative: {path_str}"
            )
        return path
