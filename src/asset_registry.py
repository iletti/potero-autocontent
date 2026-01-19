from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class AssetRegistryError(Exception):
    pass


@dataclass(frozen=True)
class AssetRecord:
    path: str
    role: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            object.__setattr__(self, "tags", [])


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
        for record in self._collect_records():
            rel_path = self._ensure_relative(record.path)
            absolute = self.references_dir / rel_path
            if not absolute.exists():
                missing.append(str(rel_path))
        return missing

    def validate_required(self, design_id: str) -> List[str]:
        required: List[str] = []
        designs = self.manifest.get("designs", {})
        if isinstance(designs, dict):
            design_entry = designs.get(design_id) or {}
            required.extend(self._extract_paths(design_entry))

        if not required:
            raise AssetRegistryError(
                "Manifest must include design assets for the selected design."
            )

        missing: List[str] = []
        for raw_path in required:
            rel_path = self._ensure_relative(raw_path)
            absolute = self.references_dir / rel_path
            if not absolute.exists():
                missing.append(str(rel_path))
        return missing

    def asset_count(self) -> int:
        return len(self._collect_records())

    def get_global_assets(self) -> List[str]:
        return self._resolve_list(
            self._extract_paths(self.manifest.get("global_references", []))
        )

    def get_design_assets(self, design_id: str) -> List[str]:
        designs = self.manifest.get("designs", {})
        if not isinstance(designs, dict):
            raise AssetRegistryError("Manifest designs must be an object.")
        entry = designs.get(design_id)
        if entry is None:
            return []
        return self._resolve_list(self._extract_paths(entry))

    def get_assets_by_role(
        self,
        roles: List[str],
        design_id: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        if not roles:
            return {}
        requested = {role for role in roles if role}
        if not requested:
            return {}
        matches = {role: [] for role in requested}
        for record in self._collect_records_for_design(design_id):
            if record.role in requested:
                rel_path = self._ensure_relative(record.path)
                matches[record.role].append(
                    str(self.references_dir / rel_path)
                )
        return matches

    def _collect_records(self) -> List[AssetRecord]:
        records: List[AssetRecord] = []
        records.extend(
            self._extract_records(self.manifest.get("global_references", []))
        )
        designs = self.manifest.get("designs", {})
        if isinstance(designs, dict):
            for entry in designs.values():
                records.extend(self._extract_records(entry))
        return records

    def _collect_records_for_design(
        self,
        design_id: Optional[str],
    ) -> List[AssetRecord]:
        records: List[AssetRecord] = []
        records.extend(
            self._extract_records(self.manifest.get("global_references", []))
        )
        designs = self.manifest.get("designs", {})
        if not isinstance(designs, dict):
            return records
        if design_id:
            entry = designs.get(design_id)
            if entry is not None:
                records.extend(self._extract_records(entry))
            return records
        for entry in designs.values():
            records.extend(self._extract_records(entry))
        return records

    def _resolve_list(self, paths: List[str]) -> List[str]:
        resolved: List[str] = []
        for raw_path in paths:
            rel_path = self._ensure_relative(raw_path)
            resolved.append(str(self.references_dir / rel_path))
        return resolved

    def _extract_paths(self, value: Any) -> List[str]:
        return [record.path for record in self._extract_records(value)]

    def _extract_records(self, value: Any) -> List[AssetRecord]:
        if value is None:
            return []
        if isinstance(value, str):
            return [AssetRecord(path=value)]
        if isinstance(value, list):
            records: List[AssetRecord] = []
            for item in value:
                records.extend(self._extract_records(item))
            return records
        if isinstance(value, dict):
            if "path" in value:
                path = value.get("path")
                if not isinstance(path, str):
                    raise AssetRegistryError(
                        "Manifest asset path must be a string."
                    )
                role = value.get("role")
                if role is not None and not isinstance(role, str):
                    raise AssetRegistryError(
                        "Manifest asset role must be a string."
                    )
                tags = value.get("tags") or []
                if not isinstance(tags, list) or not all(
                    isinstance(tag, str) for tag in tags
                ):
                    raise AssetRegistryError(
                        "Manifest asset tags must be a list of strings."
                    )
                return [AssetRecord(path=path, role=role, tags=tags)]
            if not all(isinstance(item, str) for item in value.values()):
                raise AssetRegistryError(
                    "Manifest dict entries must be strings."
                )
            return [AssetRecord(path=item) for item in value.values()]
        raise AssetRegistryError(
            "Manifest entries must be string, list, or dict."
        )

    def _ensure_relative(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute() or ".." in path.parts:
            raise AssetRegistryError(
                f"Manifest path must be relative: {path_str}"
            )
        return path
