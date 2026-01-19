import json
import logging
from pathlib import Path
from typing import Any, List, Optional

from src.asset_registry import AssetRegistry
from src.asset_registry import AssetRegistry
from src.model_utils import model_dump, update_model
from src.model_utils import model_dump, update_model
from src.budget import can_consume, consume
from src.state import (
    CarouselState,
    SlideBrief,
    GlobalConstraints,
    SlideState,
    RunBudget,
)
from src.interaction_logger import InteractionLogger


POTERO_SHADER_V1_2 = (
    "Raw lo-fi documentary flash photo (on-axis flash, hard shadows, hotspot falloff). "
    "Cold blue ambient, desaturated greens, crushed blacks. "
    "Heavy 35mm grain with subtle dust/scratches (SA-kuva), not clean digital. "
    "Center-weighted framing, 24-28mm feel, f/8-ish depth, no cinematic bokeh. "
    "Anonymity/OPSEC: no face/eyes/skin identifiers; hood/helmet/balaclava OK. "
    "Symbols worn, not shouted: no extra text/logos beyond approved hoodie design."
)
IDENTITY_LOCKS = (
    "Hoodie must exactly match the provided reference images (front/back as required). "
    "Gear must be solid Ranger Green/Grey only, matte Cordura and real hardware. "
    "Material contrast matters: cordura/nylon/polymer should reflect differently. "
    "Nordic utilitarian kit cues; Finnish reservist realism; no US SF cosplay."
)
POTERO_NEGATIVE_V1_2 = (
    "bad anatomy, extra fingers, watermark, signature, username, "
    "unapproved text, typography, slogans, numbers, "
    "unapproved logos, patches on gear, chest rig logos, "
    "flag, name tape, face, eyes, skin, bright colors, sunny, "
    "studio lighting, softbox, rim light, HDR, glossy commercial look, "
    "cinematic teal-orange grading, bokeh, 3d render, cgi, "
    "decorative snowfall overlay, bokeh snow particles, glitter, sparkles, "
    "floating dust particles, fake film overlay snow, "
    "US special forces vibe, multicam, Crye logos, American flag patches."
)


class PlannerError(Exception):
    pass

TEMPLATE_SHOTS = [
    "anchor_shot",
    "close_up_texture",
    "tactical_action",
    "gear_detail",
    "final_brand_shot",
]

POSE_LIBRARY = {
    "transition": "standing still, shoulders relaxed, waiting posture, back turned",
    "mobilization": "packing gear, tying boot laces, checking straps, dynamic movement",
    "field_wait": "sitting on pack, eating, adjusting glove, cleaning gear, resting",
    "artifact_detail": "macro tight crop on chest/back area only, no head in frame",
    "domestic_front": "flat lay on floor or gear pile, water can, coffee mug, static",
}

INTENT_BY_SHOT = {
    "anchor_shot": "transition",
    "close_up_texture": "artifact_detail",
    "tactical_action": "mobilization",
    "gear_detail": "field_wait",
    "final_brand_shot": "domestic_front",
}

RISK_BY_SHOT = {
    "anchor_shot": "medium",
    "close_up_texture": "low",
    "tactical_action": "medium",
    "gear_detail": "medium",
    "final_brand_shot": "low",
}

ENV_PRESET_BY_TOKEN = {
    "kaamos": "taiga_winter_kaamos",
    "winter": "taiga_winter_kaamos",
    "snow": "taiga_winter_kaamos",
    "cqb": "cqb_osb",
    "osb": "cqb_osb",
    "industrial": "industrial_hall",
    "hall": "industrial_hall",
    "shelter": "shelter_brutalist",
    "bunker": "shelter_brutalist",
}

ENV_ROLE_BY_PRESET = {
    "taiga_winter_kaamos": "ENV_TAIGA_WINTER_KAAMOS",
    "taiga_summer": "ENV_TAIGA_SUMMER_NIGHT",
    "cqb_osb": "ENV_CQB_OSB",
    "industrial_hall": "ENV_INDUSTRIAL_HALL",
    "shelter_brutalist": "ENV_SHELTER",
}

THEME_TEMPLATES = {
    "winter_ambush": [
        {
            "shot_type": "anchor_shot",
            "positive_prompt": (
                "Back view of Finnish reservist wearing the reference hoodie "
                "and a high-cut ballistic helmet with comms; "
                "standing still, shoulders relaxed, face fully obscured "
                "by hood and angle, harsh flash, back design matches reference"
            ),
            "composition_guidance": "Leave the upper-left quadrant empty.",
        },
        {
            "shot_type": "close_up_texture",
            "positive_prompt": (
                "Front chest detail of the reference hoodie with the small "
                "'POTERO STANDARD' embroidery visible on the left chest only "
                "and matching the reference in size, color, and placement; high "
                "ISO grain, harsh flash; premium technical gear (Pouches, PALS webbing) "
                "may appear in background only. "
                "Crop: Neck-down only. No face."
            ),
            "composition_guidance": "Keep the top band clean.",
        },
        {
            "shot_type": "tactical_action",
            "positive_prompt": (
                "Back view, packing premium Ranger Green gear, tying boot laces or checking "
                "rugged Savotta-style straps, candid movement, face not visible, low angle, "
                "back of hoodie visible, back design matches reference"
            ),
            "composition_guidance": "Leave the right third as negative space.",
        },
        {
            "shot_type": "gear_detail",
            "positive_prompt": (
                "Back view while gloved hands adjust professional-grade comms headset on a "
                "ballistic helmet, fingers natural, no face visible, harsh flash, "
                "back of hoodie visible, back design matches reference"
            ),
            "composition_guidance": "Leave the top-left quadrant empty.",
        },
        {
            "shot_type": "final_brand_shot",
            "positive_prompt": (
                "Static flat lay of the reference hoodie on snowy ground, "
                "back side up and fully visible, solid color fabric, "
                "Ranger Green gear nearby, desaturated greens, back design matches reference"
            ),
            "composition_guidance": "Leave the upper-right quadrant empty.",
        },
    ],
    "cqb_raid": [
        {
            "shot_type": "anchor_shot",
            "positive_prompt": (
                "Back view of Finnish reservist in a dimly lit OSB shooting house; "
                "wearing the reference hoodie and a high-cut ballistic helmet; "
                "standing still, facing a textured wall, face fully obscured, "
                "harsh on-axis flash, back design matches reference"
            ),
            "composition_guidance": "Leave the upper-left quadrant empty.",
        },
        {
            "shot_type": "close_up_texture",
            "positive_prompt": (
                "Front chest detail of the reference hoodie in a low-light indoor setting; "
                "small 'POTERO STANDARD' embroidery visible on the left chest; "
                "high ISO grain, harsh flash; tactical belt and IFAK visible in background. "
                "Crop: Neck-down only. No face."
            ),
            "composition_guidance": "Keep the top band clean.",
        },
        {
            "shot_type": "tactical_action",
            "positive_prompt": (
                "Dynamic movement in a CQB environment; Finnish reservist checking "
                "a tactical battle belt, wearing the reference hoodie, "
                "Ranger Green gear, harsh strobe-like lighting, motion blur in hands, "
                "back of hoodie visible, back design matches reference"
            ),
            "composition_guidance": "Leave the right third as negative space.",
        },
        {
            "shot_type": "gear_detail",
            "positive_prompt": (
                "Tight macro of a Ranger Green IFAK pouch and tourniquet on a battle belt; "
                "hands mid-adjustment, wearing the reference hoodie, "
                "industrial indoor background, heavy shadows, high contrast."
            ),
            "composition_guidance": "Leave the top-left quadrant empty.",
        },
        {
            "shot_type": "final_brand_shot",
            "positive_prompt": (
                "Flat lay of the reference hoodie on an industrial concrete floor; "
                "back side up, surrounded by spent brass casings and a tactical belt; "
                "utilitarian messy aesthetic, harsh top-down flash."
            ),
            "composition_guidance": "Leave the upper-right quadrant empty.",
        },
    ],
    "brutalist_shelter": [
        {
            "shot_type": "anchor_shot",
            "positive_prompt": (
                "Back view of Finnish reservist in a cold, brutalist concrete civil defense shelter; "
                "wearing the reference hoodie; standing against a massive ribbed concrete wall; "
                "harsh on-axis flash, crushing shadows, back design matches reference"
            ),
            "composition_guidance": "Leave the upper-left quadrant empty.",
        },
        {
            "shot_type": "close_up_texture",
            "positive_prompt": (
                "Front chest detail of the reference hoodie; 'POTERO STANDARD' embroidery "
                "crisp against the Ranger Green fabric; background is a blurred "
                "brutalist concrete pillar; harsh flash, high ISO noise. "
                "Crop: Neck-down only. No face."
            ),
            "composition_guidance": "Keep the top band clean.",
        },
        {
            "shot_type": "tactical_action",
            "positive_prompt": (
                "Back view, Finnish reservist checking tactical straps while sitting on a "
                "concrete ledge; brutalist architecture in background, heavy shadows, "
                "utilitarian feel, back of hoodie visible, back design matches reference"
            ),
            "composition_guidance": "Leave the right third as negative space.",
        },
        {
            "shot_type": "gear_detail",
            "positive_prompt": (
                "Macro focus on technical gear details (Cordura, hardware) against a "
                "raw concrete background; hands mid-adjustment, wearing the reference hoodie, "
                "low light, intense highlights from flash."
            ),
            "composition_guidance": "Leave the top-left quadrant empty.",
        },
        {
            "shot_type": "final_brand_shot",
            "positive_prompt": (
                "Flat lay of the reference hoodie on a cold concrete floor of a "
                "brutalist shelter; back side up, surrounded by a rustic metal cup "
                "and tactical belt; high contrast, harsh top-down lighting."
            ),
            "composition_guidance": "Leave the upper-right quadrant empty.",
        },
    ],
}

class Planner:
    def __init__(
        self,
        model_name: str = "gemini-3-flash-preview",
        registry: Optional[AssetRegistry] = None,
        planner_mode: str = "template",
        potero_shader_version: str = "v1_1",
        potero_image_aspect: str = "4:5",
        potero_image_size: str = "2K",
        potero_allow_warn_pass: bool = False,
        potero_pass_threshold: float = 7.5,
        potero_warn_threshold: float = 6.0,
        potero_enable_edit_mode: bool = True,
        potero_max_refs_per_call: int = 10,
        potero_max_refs_hard: int = 14,
        potero_anchor_candidates: int = 3,
        potero_assets_dir: Optional[Path] = None,
        client: Optional[Any] = None,
        interaction_logger: Optional[InteractionLogger] = None,
    ):
        self.model_name = model_name
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        self.interaction_logger = interaction_logger
        self.planner_mode = planner_mode
        self.potero_shader_version = potero_shader_version
        self.potero_image_aspect = potero_image_aspect
        self.potero_image_size = potero_image_size
        self.potero_allow_warn_pass = potero_allow_warn_pass
        self.potero_pass_threshold = potero_pass_threshold
        self.potero_warn_threshold = potero_warn_threshold
        self.potero_enable_edit_mode = potero_enable_edit_mode
        self.potero_max_refs_per_call = potero_max_refs_per_call
        self.potero_max_refs_hard = potero_max_refs_hard
        self.potero_anchor_candidates = potero_anchor_candidates
        if potero_assets_dir is None:
            potero_assets_dir = Path(__file__).resolve().parents[2] / "assets"
        self.potero_assets_dir = potero_assets_dir
        self.client = client

    def plan_carousel(
        self,
        theme_id: str,
        design_id: str,
        budget: Optional["RunBudget"] = None,
    ) -> CarouselState:
        """
        Parses a theme into a concrete execution plan with 5 slide briefs.
        """
        global_constraints = GlobalConstraints(
            design_id_locked=design_id,
            environment=theme_id, # Simplified for now
            aspect_ratio="4:5",
            potero_shader_version=self.potero_shader_version,
            image_aspect=self.potero_image_aspect,
            image_size=self.potero_image_size,
            allow_warn_pass=self.potero_allow_warn_pass,
            potero_pass_threshold=self.potero_pass_threshold,
            potero_warn_threshold=self.potero_warn_threshold,
            enable_edit_mode=self.potero_enable_edit_mode,
            max_refs_per_call=self.potero_max_refs_per_call,
            max_refs_hard=self.potero_max_refs_hard,
            anchor_candidates=self.potero_anchor_candidates,
        )
        
        slides = [SlideState(index=i) for i in range(1, 6)]
        
        state = CarouselState(
            carousel_id=f"run_{theme_id}_{design_id}",
            global_constraints=global_constraints,
            slides=slides
        )
        if budget:
            state.budget = budget
        
        return state

    def generate_briefs(self, state: CarouselState) -> List[SlideBrief]:
        reference_assets = self._resolve_reference_assets(
            state.global_constraints.design_id_locked
        )
        briefs = self._build_template_briefs(state, reference_assets)

        if self.planner_mode == "template":
            return briefs

        if self.planner_mode != "template+llm":
            self.logger.warning(
                "planner_mode_unrecognized",
                extra={"planner_mode": self.planner_mode},
            )
            return briefs

        if not can_consume(state.budget, "planner"):
            self.logger.warning("planner_budget_exceeded")
            return briefs
        consume(state.budget, "planner")

        try:
            refined = self._refine_briefs_with_llm(briefs, state)
            refined = self._merge_briefs(briefs, refined)
            refined = self._enforce_invariants(refined, reference_assets)
            return self._normalize_indices(refined)
        except Exception as exc:
            self.logger.warning(
                "planner_refinement_failed",
                extra={"error": str(exc)},
            )
            return briefs

    def _build_template_briefs(
        self,
        state: CarouselState,
        reference_assets: List[str],
    ) -> List[SlideBrief]:
        theme = state.global_constraints.environment
        template = THEME_TEMPLATES.get(theme)
        if not template:
            template = self._default_template(theme)
        briefs: List[SlideBrief] = []
        for idx, entry in enumerate(template, start=1):
            shot_type = entry.get("shot_type", TEMPLATE_SHOTS[idx - 1])
            brief = SlideBrief(
                index=idx,
                shot_type=shot_type,
                positive_prompt=entry.get("positive_prompt", ""),
                negative_prompt="unapproved text, face, watermark",
                reference_assets=reference_assets,
                composition_guidance=entry.get("composition_guidance"),
                potero_shader_version=self.potero_shader_version,
            )
            briefs.append(self._apply_metadata(state, brief))
        return self._enforce_invariants(briefs, reference_assets)

    def _default_template(self, theme: str) -> List[dict]:
        return [
            {
                "shot_type": TEMPLATE_SHOTS[0],
                "positive_prompt": (
                    f"Back view anchor shot in {theme}, Finnish reservist wearing "
                    "the reference hoodie, standing still, shoulders relaxed, face fully obscured, harsh flash, "
                    "back design matches reference"
                ),
                "composition_guidance": "Leave the top-left quadrant empty.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[1],
                "positive_prompt": (
                    f"Front chest detail in {theme}, reference hoodie "
                    "embroidery small on the left chest only and matching "
                    "size/placement; high ISO. Crop: Neck-down only. No face."
                ),
                "composition_guidance": "Keep the top band clean.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[2],
                "positive_prompt": (
                    f"Back view tactical movement in {theme}, packing gear or checking straps, "
                    "no face visible, back of hoodie visible, back design matches reference"
                ),
                "composition_guidance": "Leave the right third as negative space.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[3],
                "positive_prompt": (
                    f"Back view gear detail in {theme}, sitting on pack or resting, "
                    "harsh flash, back of hoodie visible, back design matches reference"
                ),
                "composition_guidance": "Leave the top-left quadrant empty.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[4],
                "positive_prompt": (
                    f"Final product-focused shot in {theme}, flat lay of reference hoodie "
                    "on ground with back side up, back design matches reference"
                ),
                "composition_guidance": "Leave the upper-right quadrant empty.",
            },
        ]

    def _apply_metadata(
        self,
        state: CarouselState,
        brief: SlideBrief,
    ) -> SlideBrief:
        env_preset = brief.env_preset or self._infer_env_preset(
            state.global_constraints.environment
        )
        intent = brief.intent or INTENT_BY_SHOT.get(
            brief.shot_type, "field_wait"
        )
        lighting_signature = brief.lighting_signature or self._infer_lighting(
            env_preset
        )
        risk_profile = brief.risk_profile or RISK_BY_SHOT.get(
            brief.shot_type, "medium"
        )
        kit_anchors = brief.kit_anchors or self._infer_kit_anchors(
            brief.positive_prompt
        )
        required_roles = brief.reference_roles_required or self._infer_roles(
            env_preset, kit_anchors, brief
        )
        brief = update_model(
            brief,
            {
                "intent": intent,
                "continuum_cue": brief.continuum_cue,
                "kit_anchors": kit_anchors,
                "env_preset": env_preset,
                "lighting_signature": lighting_signature,
                "risk_profile": risk_profile,
                "reference_roles_required": required_roles,
                "image_aspect": state.global_constraints.image_aspect,
                "image_size": state.global_constraints.image_size,
            },
        )
        brief = self._apply_front_back_rules(brief)
        return self._apply_potero_tunings(brief)

    def _apply_potero_tunings(self, brief: SlideBrief) -> SlideBrief:
        positive = brief.positive_prompt or ""
        negative = brief.negative_prompt or ""

        if brief.shot_type == "anchor_shot":
            positive = _append_if_missing(
                positive,
                "Background stays dark; deep shadows behind subject.",
            )
            # Anchor consistency: No torso gear on Slide 1 to prevent drift.
            positive = _append_if_missing(
                positive,
                "No plate carrier or chest rig; hoodie fully visible on torso.",
            )
            negative = _append_if_missing(
                negative,
                "plate carrier, chest rig, tactical vest, torso armor",
            )

        if brief.shot_type == "close_up_texture":
            positive = _append_if_missing(
                positive,
                "Embroidery threads are crisp and raised; stitching is real, not printed.",
            )
            positive = _append_if_missing(
                positive,
                "Letters are perfectly straight; color matches the reference exactly (e.g., black threads stay black).",
            )
            negative = _append_if_missing(
                negative,
                "crooked text, warped typography",
            )

        if brief.intent == "mobilization":
            positive = _append_if_missing(
                positive,
                "Wear tactical gloves; no bare hands.",
            )
            positive = _append_if_missing(
                positive,
                "Hands natural; no extra fingers or melted knuckles.",
            )
            positive = _append_if_missing(
                positive,
                "Gear looks used, not pristine.",
            )
            negative = _append_if_missing(
                negative,
                "bare hands",
            )

        if brief.shot_type == "gear_detail":
            positive = _append_if_missing(
                positive,
                "Candid mid-adjustment, not a posed hero stance.",
            )
            positive = _append_if_missing(
                positive,
                "Slight motion blur in hands only (flash freeze with tiny blur).",
            )

        if brief.shot_type == "final_brand_shot":
            positive = _append_if_missing(
                positive,
                "Utilitarian, not styled; small mess, scuffs, pine needles.",
            )
            negative = _append_if_missing(
                negative,
                "perfectly arranged flatlay, instagram styled, clean studio flatlay",
            )

        return update_model(
            brief,
            {
                "positive_prompt": positive,
                "negative_prompt": negative,
            },
        )

    def _infer_env_preset(self, theme: str) -> str:
        lowered = (theme or "").lower()
        for token, preset in ENV_PRESET_BY_TOKEN.items():
            if token in lowered:
                return preset
        return "taiga_summer"

    def _infer_lighting(self, env_preset: str) -> str:
        if env_preset == "taiga_winter_kaamos":
            return "lofi_flash_on_axis_kaamos"
        return "lofi_flash_on_axis"

    def _infer_kit_anchors(self, prompt: str) -> List[str]:
        lowered = (prompt or "").lower()
        anchors = []
        if "rifle" in lowered or "weapon" in lowered:
            anchors.append("RK95_TP")
        if "backpack" in lowered or "pack" in lowered:
            anchors.append("SAVOTTA_JAAKARI_34")
            anchors.append("PALS_WEBBING")
        if "plate carrier" in lowered or "carrier" in lowered or "rig" in lowered:
            anchors.append("RES_TAC_CARRIER")
        if "pouch" in lowered:
            anchors.append("TACTICAL_BELT_POUCH")
        if "headset" in lowered or "comms" in lowered:
            anchors.append("COMTAC_HEADSET")
        if "helmet" in lowered:
            anchors.append("PGD_HIGH_CUT")
        if "glove" in lowered:
            anchors.append("MECHANIX_GLOVES")
        if "boot" in lowered:
            anchors.append("BLACK_COMBAT_BOOTS")
        return _unique_list(anchors)

    def _infer_roles(
        self,
        env_preset: str,
        kit_anchors: List[str],
        brief: SlideBrief,
    ) -> List[str]:
        roles: List[str] = []
        prompt = brief.positive_prompt or ""
        is_front = self._is_front_shot(brief)
        is_back = self._is_back_shot(brief)

        def _front_back(front_role: str, back_role: str) -> List[str]:
            if is_front:
                return [front_role]
            if is_back:
                return [back_role]
            return [front_role]
        env_role = ENV_ROLE_BY_PRESET.get(env_preset)
        if env_role:
            # Safety Compliance: Environment references also trigger blocks.
            # Rely on text description.
            pass
            # roles.append(env_role)
        if "RK95_TP" in kit_anchors or "rifle" in (prompt or "").lower():
            # Safety Compliance: Weapon reference images trigger model blocks.
            # Rely on text prompt (RK95_TP anchor) only.
            pass 
            # roles.extend(["WEAPON_RK95_LEFT", "WEAPON_RK95_MUZZLE_CLOSE"])
        if "SAVOTTA_JAAKARI_34" in kit_anchors or "PALS_WEBBING" in kit_anchors:
            roles.extend(
                _front_back("GEAR_BACKPACK_FRONT", "GEAR_BACKPACK_BACK")
            )
            roles.extend(["GEAR_PALS_CLOSE", "GEAR_STRAPS_CONNECT"])
        if "RES_TAC_CARRIER" in kit_anchors:
            roles.extend(
                _front_back("GEAR_PLATE_CARRIER_FRONT", "GEAR_PLATE_CARRIER_BACK")
            )
            roles.append("GEAR_POUCHES_DETAIL")
        if "TACTICAL_BELT_POUCH" in kit_anchors:
            roles.extend(
                _front_back("GEAR_BATTLE_BELT_FRONT", "GEAR_BATTLE_BELT_BACK")
            )
            roles.append("GEAR_BELT_DUMP_POUCH")
        if "COMTAC_HEADSET" in kit_anchors:
            roles.append("GEAR_HEADSET_COMTAC")
        if "PGD_HIGH_CUT" in kit_anchors:
            roles.append("GEAR_HELMET_HIGH_CUT")
        roles.extend(self._infer_design_roles(brief))
        return _unique_list(roles)

    def _infer_design_roles(self, brief: SlideBrief) -> List[str]:
        if self._is_front_shot(brief):
            return ["DESIGN_FRONT"]
        if self._is_back_shot(brief):
            return ["DESIGN_BACK"]
        if brief.shot_type == "gear_detail":
            return ["DESIGN_FRONT"]
        return ["DESIGN_SIDE"]

    def _apply_front_back_rules(self, brief: SlideBrief) -> SlideBrief:
        prompt = brief.positive_prompt or ""
        negative = brief.negative_prompt or ""
        is_front = self._is_front_shot(brief)
        is_back = self._is_back_shot(brief)
        has_design_front = "DESIGN_FRONT" in (brief.reference_roles_required or [])
        if is_front or has_design_front:
            # Only mention the specific embroidery for front shots
            prompt = _append_if_missing(
                prompt,
                "Show the 'POTERO STANDARD' embroidery on the left chest, matching the reference."
            )
        else:
            if is_back:
                prompt = _append_if_missing(
                    prompt,
                    "Back view only. Back design matches reference."
                )
            prompt = _append_if_missing(
                prompt,
                "Avoid front chest view; no front embroidery visible.",
            )
            negative = _append_if_missing(
                negative,
                "front chest, chest embroidery, chest text",
            )
        if brief.shot_type == "gear_detail" and not (is_front or has_design_front):
            prompt = _append_if_missing(
                prompt,
                "Frame gear and hands; keep hoodie chest out of frame.",
            )
            negative = _append_if_missing(
                negative,
                "front logo",
            )
        return update_model(
            brief,
            {"positive_prompt": prompt, "negative_prompt": negative},
        )

    def _is_front_shot(self, brief: SlideBrief) -> bool:
        text = _normalize_text(f"{brief.shot_type} {brief.positive_prompt}")
        markers = [
            "front view",
            "front-facing",
            "front facing",
            "front chest",
            "chest detail",
            "left chest",
            "front of the hoodie",
        ]
        return any(marker in text for marker in markers)

    def _is_back_shot(self, brief: SlideBrief) -> bool:
        text = _normalize_text(f"{brief.shot_type} {brief.positive_prompt}")
        markers = [
            "back view",
            "back-facing",
            "back facing",
            "back side",
            "back design",
            "back of the hoodie",
            "back side up",
        ]
        return any(marker in text for marker in markers)
    def _refine_briefs_with_llm(
        self,
        briefs: List[SlideBrief],
        state: CarouselState,
    ) -> List[SlideBrief]:
        if not self.client:
            raise PlannerError("GenAI client not configured for refinement.")
        payload = [model_dump(brief) for brief in briefs]
        prompt = f"""
You are refining a fixed carousel plan. Do not change indices or shot_type.
Only improve positive_prompt and composition_guidance. Keep negative_prompt as-is.
Theme: {state.global_constraints.environment}
Design ID: {state.global_constraints.design_id_locked}

Return strict JSON list with the same length and fields.
Input:
{json.dumps(payload)}
""".strip()
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        text = getattr(response, "text", None) or str(response)

        if self.interaction_logger:
            self.interaction_logger.log(
                agent="Planner",
                step="refine_briefs",
                model=self.model_name,
                prompt=prompt,
                response=text,
                metadata={"brief_count": len(briefs)}
            )

        refined = self._parse_briefs_json(text, expected_count=len(briefs))
        return refined

    def _merge_briefs(
        self,
        base: List[SlideBrief],
        refined: List[SlideBrief],
    ) -> List[SlideBrief]:
        if len(base) != len(refined):
            raise PlannerError("Refined briefs length mismatch.")
        merged: List[SlideBrief] = []
        for base_brief, refined_brief in zip(base, refined):
            updates = {
                "positive_prompt": refined_brief.positive_prompt
                or base_brief.positive_prompt,
                "composition_guidance": refined_brief.composition_guidance
                or base_brief.composition_guidance,
                "negative_prompt": base_brief.negative_prompt,
                "shot_type": base_brief.shot_type,
                "index": base_brief.index,
            }
            merged.append(update_model(base_brief, updates))
        return merged

    def _parse_briefs_json(
        self,
        raw_text: str,
        expected_count: int,
    ) -> List[SlideBrief]:
        data = _extract_json(raw_text)
        if isinstance(data, dict):
            data = data.get("slides") or data.get("briefs")
        if not isinstance(data, list):
            raise PlannerError("Planner output must be a JSON list.")
        briefs = [self._parse_brief(item) for item in data]
        if len(briefs) != expected_count:
            raise PlannerError(
                f"Expected {expected_count} briefs, got {len(briefs)}."
            )
        return briefs

    def _parse_brief(self, payload: Any) -> SlideBrief:
        if not isinstance(payload, dict):
            raise PlannerError("Each brief must be a JSON object.")
        return _parse_slide_brief(payload)

    def _enforce_invariants(
        self,
        briefs: List[SlideBrief],
        reference_assets: List[str],
    ) -> List[SlideBrief]:
        enriched: List[SlideBrief] = []
        for brief in briefs:
            # Explicitly construct the prompt using internal blocks.
            positive_parts = [
                POTERO_SHADER_V1_2,
                IDENTITY_LOCKS,
                brief.positive_prompt,
            ]
            positive = "\n".join(
                part for part in positive_parts if part
            ).strip()
            
            # Append metadata to prompt (formerly done by compiler)
            meta_parts = []
            if brief.continuum_cue:
                meta_parts.append(f"Continuum cue: {brief.continuum_cue}.")
            if brief.env_preset:
                meta_parts.append(f"Environment preset: {brief.env_preset}.")
            if brief.lighting_signature:
                meta_parts.append(f"Lighting signature: {brief.lighting_signature}.")
            if brief.kit_anchors:
                anchors = ", ".join(brief.kit_anchors)
                meta_parts.append(f"Kit anchors: {anchors}.")
            
            # Enforce pose library if intent matches
            pose_instruction = POSE_LIBRARY.get(brief.intent)
            if pose_instruction:
                meta_parts.append(f"Pose guidance: {pose_instruction}.")
            
            if meta_parts:
                positive += "\n" + "\n".join(meta_parts)

            negative = f"{brief.negative_prompt}, {POTERO_NEGATIVE_V1_2}".strip()
            
            # Create updated brief
            # note: reference_assets will be refined later in graph, but we set initial here
            enriched.append(
                update_model(
                    brief,
                    {
                        "positive_prompt": positive,
                        "negative_prompt": negative,
                        "reference_assets": reference_assets,
                        "potero_shader_version": self.potero_shader_version,
                    },
                )
            )
        return enriched

    def _normalize_indices(self, briefs: List[SlideBrief]) -> List[SlideBrief]:
        normalized: List[SlideBrief] = []
        for idx, brief in enumerate(briefs, start=1):
            if brief.index == idx:
                normalized.append(brief)
                continue
            normalized.append(update_model(brief, {"index": idx}))
        return normalized

    def _fallback_briefs(
        self,
        state: CarouselState,
        reference_assets: List[str],
    ) -> List[SlideBrief]:
        briefs: List[SlideBrief] = []
        for slide in state.slides:
            brief = SlideBrief(
                index=slide.index,
                shot_type="placeholder",
                positive_prompt=(
                    f"{POTERO_SHADER_V1_2} {IDENTITY_LOCKS} "
                    f"Placeholder prompt for slide {slide.index} of theme "
                    f"{state.global_constraints.environment}"
                ),
                negative_prompt=(
                    f"unapproved text, face, watermark, {POTERO_NEGATIVE_V1_2}"
                ),
                reference_assets=reference_assets,
                composition_guidance="Leave top-left quadrant empty for text.",
                potero_shader_version=self.potero_shader_version,
            )
            briefs.append(self._apply_metadata(state, brief))
        return briefs

    def _resolve_reference_assets(self, design_id: str) -> List[str]:
        if not self.registry:
            return []
        assets: List[str] = []
        assets.extend(self.registry.get_global_assets())
        assets.extend(self.registry.get_design_assets(design_id))
        return _unique_paths(assets)


def _unique_paths(paths: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def _unique_list(values: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _append_if_missing(text: str, snippet: str) -> str:
    if not snippet:
        return text
    normalized = _normalize_text(text)
    if _normalize_text(snippet) in normalized:
        return text
    if not text:
        return snippet
    return f"{text}\n{snippet}".strip()


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def _extract_json(raw_text: str) -> Any:
    text = raw_text.strip()
    if not text:
        raise PlannerError("Planner returned empty response.")
    if text[0] in "[{":
        return json.loads(text)
    start = min(
        [idx for idx in (text.find("["), text.find("{")) if idx != -1],
        default=-1,
    )
    end = max(text.rfind("]"), text.rfind("}"))
    if start == -1 or end == -1 or end <= start:
        raise PlannerError("Unable to locate JSON in planner output.")
    return json.loads(text[start : end + 1])


def _parse_slide_brief(payload: dict) -> SlideBrief:
    if hasattr(SlideBrief, "model_validate"):
        return SlideBrief.model_validate(payload)
    return SlideBrief.parse_obj(payload)
