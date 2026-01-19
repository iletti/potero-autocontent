from pathlib import Path
from typing import Dict, List


def select_critic_reference_assets(
    reference_assets: List[str],
    asset_role_map: Dict[str, str],
) -> List[str]:
    if not reference_assets:
        return []
    selected: List[str] = []
    for asset in reference_assets:
        role = asset_role_map.get(asset)
        if role:
            if role.startswith("DESIGN_"):
                selected.append(asset)
            continue
        if "hoodies" in Path(asset).parts:
            selected.append(asset)
    return selected
