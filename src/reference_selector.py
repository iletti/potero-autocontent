from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.asset_registry import AssetRegistry
from src.golden_packs import load_golden_packs
from src.reference_quality import score_references
from src.state import SlideBrief


def select_reference_assets(
    brief: SlideBrief,
    registry: AssetRegistry,
    max_refs: int,
    hard_cap: int,
    anchor_path: Optional[str] = None,
    assets_dir: Optional[Path] = None,
) -> tuple[List[str], Dict[str, List[str]], Dict[str, float]]:
    roles = _normalize_roles(brief.reference_roles_required)
    if assets_dir and brief.env_preset:
        roles = _extend_with_golden_roles(roles, assets_dir, brief.env_preset)
    if not roles:
        return [], {}, {}

    selected: List[str] = []
    used = set()

    role_assets = registry.get_assets_by_role(roles)
    scored_assets, scores = _score_assets(role_assets)

    env_roles = [r for r in roles if r.startswith("ENV_")]
    m05_roles = [r for r in roles if r.startswith("TEXTURE_M05")]

    _append_role_assets(scored_assets, env_roles, selected, used, limit=1)
    _append_role_assets(scored_assets, m05_roles, selected, used, limit=1)

    for role in roles:
        if role in env_roles or role in m05_roles:
            continue
        _append_role_assets(scored_assets, [role], selected, used, limit=2)

    if anchor_path:
        selected.insert(0, anchor_path)

    if len(selected) > hard_cap:
        selected = selected[:hard_cap]
    if len(selected) > max_refs:
        selected = selected[:max_refs]

    role_map = role_assets
    return selected, role_map, scores


def _normalize_roles(roles: Iterable[str]) -> List[str]:
    return [role.strip() for role in roles if role and role.strip()]


def _append_role_assets(
    role_assets: Dict[str, List[str]],
    roles: List[str],
    selected: List[str],
    used: set,
    limit: int,
) -> None:
    for role in roles:
        assets = role_assets.get(role) or []
        added = 0
        for asset in assets:
            if asset in used:
                continue
            selected.append(asset)
            used.add(asset)
            added += 1
            if added >= limit:
                break


def _extend_with_golden_roles(
    roles: List[str],
    assets_dir: Path,
    env_preset: str,
) -> List[str]:
    packs = load_golden_packs(assets_dir)
    extras = packs.get(env_preset) or []
    return _normalize_roles(list(roles) + list(extras))


def _score_assets(
    role_assets: Dict[str, List[str]],
) -> tuple[Dict[str, List[str]], Dict[str, float]]:
    scored: Dict[str, List[str]] = {}
    scores: Dict[str, float] = {}
    for role, assets in role_assets.items():
        role_scores = score_references(list(assets))
        scores.update({path: entry.score for path, entry in role_scores.items()})
        ranked = sorted(
            assets,
            key=lambda path: scores.get(path, 0.0),
            reverse=True,
        )
        scored[role] = ranked
    return scored, scores
