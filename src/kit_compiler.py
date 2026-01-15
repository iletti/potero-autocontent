from typing import List, Optional

from src.asset_registry import AssetRegistry
from src.model_utils import update_model
from src.state import SlideBrief

WEAPON_ROLES = [] # Specifically disabled to avoid Gemini safety blocks, rely on text
PALS_ROLES = [
    "GEAR_PALS_CLOSE",
    "GEAR_BACKPACK_FRONT",
    "GEAR_BACKPACK_BACK",
    "GEAR_STRAPS_CONNECT",
]
PLATE_ROLES = [
    "GEAR_PLATE_CARRIER_FRONT",
    "GEAR_PLATE_CARRIER_BACK",
    "GEAR_POUCHES_DETAIL",
]


def apply_kit_consistency(
    brief: SlideBrief,
    registry: Optional[AssetRegistry],
) -> SlideBrief:
    updated = brief
    kit_anchors = list(brief.kit_anchors or [])
    roles_required = list(brief.reference_roles_required or [])

    prompt_text = (brief.positive_prompt or "").lower()

    weapon_present = "RK95_TP" in kit_anchors or "rifle" in prompt_text
    pals_present = any(anchor in kit_anchors for anchor in ("SAVOTTA_JAAKARI_34", "PALS_WEBBING"))
    plate_present = "RES_TAC_CARRIER" in kit_anchors

    if weapon_present:
        # We handle weapons via text to avoid vision safety blocks
        updated = _append_positive(updated, "Professional-grade tactical rifle; matte finish technical hardware. Hands on rail/sling.")
        # Ensure no accidental role injection
        roles_required = _remove_items(roles_required, ["WEAPON_RK95_LEFT", "WEAPON_RK95_MUZZLE_CLOSE", "WEAPON_RK95_RIGHT"])


    if pals_present:
        updated = _append_positive(updated, "Rugged technical hardware, premium manufacturing quality.")
        if not _roles_available(registry, PALS_ROLES):
            kit_anchors = _remove_items(kit_anchors, ["PALS_WEBBING"])
            roles_required = _remove_items(roles_required, PALS_ROLES)
            updated = _append_positive(updated, "Backpack edge only; PALS webbing not visible.")

    if plate_present:
        updated = _append_positive(updated, "Savotta-style rugged construction, professional load-bearing equipment.")
        if not _roles_available(registry, PLATE_ROLES):
            roles_required = _remove_items(roles_required, PLATE_ROLES)
            updated = _append_positive(updated, "Plate carrier partially out of frame.")

    if brief.env_preset == "taiga_winter_kaamos":
        updated = _append_negative(updated, "no warm light, no golden hour, no sunlight")
        updated = _append_positive(updated, "Harsh on-axis camera flash lighting.")

    if brief.risk_profile == "high":
        updated = _append_positive(updated, "Neck-down crop only. No face visible.")

    return update_model(
        updated,
        {
            "kit_anchors": kit_anchors,
            "reference_roles_required": roles_required,
        },
    )


def _roles_available(registry: Optional[AssetRegistry], roles: List[str]) -> bool:
    if registry is None:
        return False
    assets = registry.get_assets_by_role(roles)
    for role in roles:
        if not assets.get(role):
            return False
    return True


def _append_positive(brief: SlideBrief, text: str) -> SlideBrief:
    return _append_prompt(brief, "positive_prompt", text)


def _append_negative(brief: SlideBrief, text: str) -> SlideBrief:
    return _append_prompt(brief, "negative_prompt", text)


def _append_prompt(brief: SlideBrief, field: str, text: str) -> SlideBrief:
    current = getattr(brief, field) or ""
    if text.lower() in current.lower():
        return brief
    if current:
        current = f"{current}\n{text}".strip()
    else:
        current = text
    return update_model(brief, {field: current})


def _remove_items(items: List[str], remove: List[str]) -> List[str]:
    remove_set = {item for item in remove if item}
    return [item for item in items if item not in remove_set]
