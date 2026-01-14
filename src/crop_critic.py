from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.state import SlideBrief


@dataclass(frozen=True)
class CropTarget:
    name: str
    hint: str


@dataclass(frozen=True)
class CropCriticResult:
    failed: bool
    violations: List[str]
    repair_targets: List[str]
    repair_instructions: str


DEFAULT_TARGETS = [
    CropTarget("weapon_muzzle", "rifle muzzle, front barrel, flash hider"),
    CropTarget("weapon_receiver", "receiver/stock area"),
    CropTarget("pals_grid", "PALS webbing grid"),
    CropTarget("strap_connection", "shoulder strap connection/buckle"),
    CropTarget("m05_fabric", "M05 fabric close texture"),
]


def run_crop_critic(
    critic: Any,
    brief: SlideBrief,
    image_path: str,
    max_checks: int,
    consume_fn: Optional[Callable[[], bool]] = None,
) -> CropCriticResult:
    failures: List[str] = []
    repair_targets: List[str] = []

    targets = _select_targets(brief)
    targets = targets[:max_checks]
    for target in targets:
        if consume_fn and not consume_fn():
            break
        result = critic.validate_image(
            image_path,
            reference_assets=brief.reference_assets,
        )
        if not result.get("pass"):
            failures.append(f"crop_fail:{target.name}")
            repair_targets.append(target.name)

    failed = len(failures) > 0
    instructions = ""
    if failed:
        instructions = (
            "Address local defects in the specified regions. "
            "Match the reference assets for weapon geometry, PALS grid straightness, "
            "strap connections, and M05 texture fidelity."
        )

    return CropCriticResult(
        failed=failed,
        violations=failures,
        repair_targets=repair_targets,
        repair_instructions=instructions,
    )


def apply_crop_results(result: CropCriticResult, critic_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not result.failed:
        return critic_payload
    violations = list(critic_payload.get("violations") or []) + result.violations
    repair_targets = list(critic_payload.get("repair_targets") or []) + result.repair_targets
    return {
        **critic_payload,
        "violations": violations,
        "repair_mode": "edit",
        "repair_targets": repair_targets,
        "repair_instructions": result.repair_instructions,
    }


def _select_targets(brief: SlideBrief) -> List[CropTarget]:
    anchors = set(brief.kit_anchors or [])
    prompt = (brief.positive_prompt or "").lower()
    targets: List[CropTarget] = []
    if "RK95_TP" in anchors or "rifle" in prompt:
        targets.extend(DEFAULT_TARGETS[:2])
    if "PALS_WEBBING" in anchors or "SAVOTTA_JAAKARI_34" in anchors:
        targets.append(DEFAULT_TARGETS[2])
        targets.append(DEFAULT_TARGETS[3])
    targets.append(DEFAULT_TARGETS[4])
    return targets or DEFAULT_TARGETS
