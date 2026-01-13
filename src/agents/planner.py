import json
import logging
from typing import Any, List, Optional

from src.asset_registry import AssetRegistry
from src.model_utils import model_dump, update_model
from src.budget import can_consume, consume
from src.state import (
    CarouselState,
    SlideBrief,
    GlobalConstraints,
    SlideState,
    RunBudget,
)

GLOBAL_STYLE_BLOCK = (
    "Photorealistic raw photo, Finnish Reservist aesthetic, M05 camouflage on "
    "gear only, grainy, high ISO, crushed blacks, desaturated greens/blues, "
    "M05 camo slightly washed out and less saturated for realism. "
    "Shot on 35mm film, harsh on-camera flash. Documentary style, not cinematic."
)
DESIGN_INVARIANTS = (
    "Hoodie must exactly match the provided reference images in color, fabric, "
    "embroidery, print, size, and placement. Never apply M05 or any other camo "
    "to the hoodie fabric; M05 appears only on gear or background elements. "
    "Match the Finnish M05 swatch reference exactly for any camo on gear or trousers. "
    "Only allowed text/logo is the approved 'POTERO STANDARD' embroidery copied "
    "exactly from the reference images; no other text or graphics anywhere. "
    "If you cannot match the embroidery exactly, omit all text/logos entirely."
    "Prioritize showing the back of the hoodie in most shots; front view should "
    "be a minority of the carousel (about 20% front, 80% back). For back-view "
    "shots, the front embroidery does not need to be visible; the back design "
    "must match references and be at least partially visible. Partial occlusion "
    "by gear is acceptable if the back design remains verifiable. Ensure at "
    "least one front-facing shot where the chest embroidery is clearly visible "
    "and matches the reference."
)
NEGATIVE_CONSTRAINTS = (
    "bad anatomy, extra fingers, watermark, signature, username, "
    "unapproved text, text, letters, words, typography, slogans, numbers, "
    "unapproved logos, logos on gear, patches on gear, chest rig logos, "
    "flag, patch, name tape, face, eyes, "
    "skin, bright colors, sunny, studio lighting, bokeh, 3d render, cgi. "
    "Only allowed text/logo is the approved 'POTERO STANDARD' embroidery that "
    "matches hoodie reference images."
)


class PlannerError(Exception):
    pass

TEMPLATE_SHOTS = [
    "hero_shot",
    "close_up_texture",
    "tactical_action",
    "gear_detail",
    "final_brand_shot",
]

THEME_TEMPLATES = {
    "winter_ambush": [
        {
            "shot_type": "hero_shot",
            "positive_prompt": (
                "Back view of Finnish reservist wearing the reference hoodie "
                "crouched in a snowy pine stand, rifle low, face fully obscured "
                "by hood and angle, harsh flash, M05 gear visible, back design "
                "matches reference and may be partially occluded by gear"
            ),
            "composition_guidance": "Leave upper-left quadrant empty for typography.",
        },
        {
            "shot_type": "close_up_texture",
            "positive_prompt": (
                "Front chest detail of the reference hoodie with the "
                "'POTERO STANDARD' embroidery clearly visible and matching the "
                "reference in size, color, and placement; high ISO grain, harsh "
                "flash; M05 gear may appear in background only"
            ),
            "composition_guidance": "Keep top band clean for overlay text.",
        },
        {
            "shot_type": "tactical_action",
            "positive_prompt": (
                "Back view of candid movement through foggy forest, boots in snow, "
                "face not visible, low angle, back of hoodie visible, back design "
                "matches reference"
            ),
            "composition_guidance": "Leave right third negative space.",
        },
        {
            "shot_type": "gear_detail",
            "positive_prompt": (
                "Back view while gloved hands adjust comms headset, fingers "
                "natural, no face visible, harsh flash, back of hoodie visible, "
                "back design matches reference"
            ),
            "composition_guidance": "Leave top-left empty for typography.",
        },
        {
            "shot_type": "final_brand_shot",
            "positive_prompt": (
                "Static hero of the reference hoodie laid on snowy ground, "
                "back side up and fully visible, solid color fabric, "
                "M05 gear nearby, desaturated greens, back design matches reference"
            ),
            "composition_guidance": "Leave upper-right empty for overlay text.",
        },
    ],
}

class Planner:
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        registry: Optional[AssetRegistry] = None,
        planner_mode: str = "template",
        client: Optional[Any] = None,
    ):
        self.model_name = model_name
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        self.planner_mode = planner_mode
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
            aspect_ratio="4:5"
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
            briefs.append(
                SlideBrief(
                    index=idx,
                    shot_type=entry.get("shot_type", TEMPLATE_SHOTS[idx - 1]),
                    positive_prompt=entry.get("positive_prompt", ""),
                    negative_prompt="unapproved text, face, watermark",
                    reference_assets=reference_assets,
                    composition_guidance=entry.get("composition_guidance"),
                )
            )
        return self._enforce_invariants(briefs, reference_assets)

    def _default_template(self, theme: str) -> List[dict]:
        return [
            {
                "shot_type": TEMPLATE_SHOTS[0],
                "positive_prompt": (
                    f"Back view hero shot in {theme}, Finnish reservist wearing "
                    "the reference hoodie, face fully obscured, harsh flash, "
                    "back design matches reference"
                ),
                "composition_guidance": "Leave top-left empty for typography.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[1],
                "positive_prompt": (
                    f"Front chest detail in {theme}, reference hoodie embroidery "
                    "clearly visible and matching size/placement; high ISO"
                ),
                "composition_guidance": "Keep top band clean for overlay text.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[2],
                "positive_prompt": (
                    f"Back view tactical movement in {theme}, candid angle, "
                    "no face visible, back of hoodie visible, back design matches reference"
                ),
                "composition_guidance": "Leave right third negative space.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[3],
                "positive_prompt": (
                    f"Back view gear detail in {theme}, hands on equipment, "
                    "harsh flash, back of hoodie visible, back design matches reference"
                ),
                "composition_guidance": "Leave top-left empty for typography.",
            },
            {
                "shot_type": TEMPLATE_SHOTS[4],
                "positive_prompt": (
                    f"Final product-focused shot in {theme}, reference hoodie "
                    "on ground with back side up, back design matches reference"
                ),
                "composition_guidance": "Leave upper-right empty for overlay text.",
            },
        ]

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
            positive = (
                f"{GLOBAL_STYLE_BLOCK} {DESIGN_INVARIANTS} "
                f"{brief.positive_prompt}"
            ).strip()
            negative = f"{brief.negative_prompt}, {NEGATIVE_CONSTRAINTS}".strip()
            enriched.append(
                update_model(
                    brief,
                    {
                        "positive_prompt": positive,
                        "negative_prompt": negative,
                        "reference_assets": reference_assets,
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
            briefs.append(
                SlideBrief(
                    index=slide.index,
                    shot_type="placeholder",
                    positive_prompt=(
                        f"{GLOBAL_STYLE_BLOCK} Placeholder prompt for slide "
                        f"{slide.index} of theme "
                        f"{state.global_constraints.environment}"
                    ),
                    negative_prompt=(
                        f"unapproved text, face, watermark, {NEGATIVE_CONSTRAINTS}"
                    ),
                    reference_assets=reference_assets,
                    composition_guidance="Leave top-left quadrant empty for text.",
                )
            )
        return briefs

    def _resolve_reference_assets(self, design_id: str) -> List[str]:
        if not self.registry:
            return []
        assets: List[str] = []
        assets.extend(self.registry.get_global_assets())
        assets.extend(self.registry.get_m05_swatches())
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
