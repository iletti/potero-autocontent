from pathlib import Path
from typing import Dict, List
import json


def load_golden_packs(assets_dir: Path, version: str = "v1") -> Dict[str, List[str]]:
    path = assets_dir / "potero" / f"golden_reference_packs_{version}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    env_presets = data.get("env_presets")
    if not isinstance(env_presets, dict):
        return {}
    packs: Dict[str, List[str]] = {}
    for key, value in env_presets.items():
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            packs[key] = value
    return packs
