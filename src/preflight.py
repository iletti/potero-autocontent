from dataclasses import dataclass
from typing import List

from src.model_utils import update_model
from src.state import SlideBrief

STYLE_TIGHTEN_DELTA = (
    "Increase on-axis flash intensity and harsh shadowing. "
    "Add high ISO grain and subtle color noise. "
    "Enforce Nordic palette: desaturated blues/greens, no warm tones. "
    "Candid imperfections; avoid influencer warcore cues."
)


@dataclass(frozen=True)
class PreflightResult:
    status: str
    reasons: List[str]
    constraints: str


def apply_brand_drift_preflight(
    brief: SlideBrief,
    theme: str,
) -> tuple[SlideBrief, PreflightResult]:
    result = run_brand_drift_preflight(brief, theme)
    if result.status != "rewrite_required":
        return brief, result

    updated = _append_constraints(brief, result.constraints)
    return updated, result


def apply_style_tighten(brief: SlideBrief) -> SlideBrief:
    return update_model(
        brief,
        {"positive_prompt": _append_if_missing(brief.positive_prompt, STYLE_TIGHTEN_DELTA)},
    )


def run_brand_drift_preflight(
    brief: SlideBrief,
    theme: str,
) -> PreflightResult:
    text = _normalize_text(" ".join([brief.positive_prompt, brief.negative_prompt]))
    theme_text = _normalize_text(theme)

    reasons: List[str] = []

    banned_vibes = [
        "cinematic",
        "golden hour",
        "hero shot",
        "tactical influencer",
        "operator",
        "high fashion",
        "epic",
        "movie poster",
    ]
    us_kit = [
        "ar-15",
        "m4",
        "multicam",
        "seal",
        "navy seal",
        "delta",
    ]
    risky_text = [
        "logo",
        "brand",
        "patch text",
        "readable text",
        "watermark",
    ]
    warm_light = [
        "warm",
        "sunset",
        "golden",
    ]

    reasons.extend(_match_tokens(text, banned_vibes, "banned_vibe"))
    reasons.extend(_match_tokens(text, us_kit, "us_kit"))
    reasons.extend(_match_tokens(text, risky_text, "risky_text"))

    winter_theme = any(token in theme_text for token in ("winter", "kaamos", "snow"))
    if winter_theme:
        reasons.extend(_match_tokens(text, warm_light, "warm_light"))

    if not reasons:
        return PreflightResult(status="ok", reasons=[], constraints="")

    constraints = (
        "Documentary snapshot, candid, understated. "
        "No cinematic lighting, no golden hour, no hero poses. "
        "No US kit (AR-15/M4/Multicam/SEAL). "
        "No readable text, logos, or patch lettering. "
        "If winter/kaamos, keep cool color temperature and avoid warm light."
    )
    return PreflightResult(
        status="rewrite_required",
        reasons=reasons,
        constraints=constraints,
    )


def _append_constraints(brief: SlideBrief, constraints: str) -> SlideBrief:
    if not constraints:
        return brief
    positive = _append_if_missing(brief.positive_prompt, constraints)
    negative = _append_if_missing(
        brief.negative_prompt,
        "no cinematic lighting, no golden hour, no hero poses",
    )
    return update_model(
        brief,
        {
            "positive_prompt": positive,
            "negative_prompt": negative,
        },
    )


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


def _match_tokens(text: str, tokens: List[str], label: str) -> List[str]:
    matches = []
    for token in tokens:
        if token in text:
            matches.append(f"{label}:{token}")
    return matches
