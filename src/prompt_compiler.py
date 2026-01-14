from pathlib import Path
from typing import List, Optional

from src.model_utils import update_model
from src.state import SlideBrief

POTERO_DIR = "potero"
SHADER_TEMPLATE = "potero_shader_{version}.txt"
NEGATIVE_TEMPLATE = "potero_negative_{version}.txt"

LOCKED_SHADER_START = "<<POTERO_SHADER:{version}>>"
LOCKED_SHADER_END = "<</POTERO_SHADER>>"
LOCKED_NEGATIVE_START = "<<POTERO_NEGATIVE:{version}>>"
LOCKED_NEGATIVE_END = "<</POTERO_NEGATIVE>>"


class PromptCompilerError(Exception):
    pass


def compile_brief(
    brief: SlideBrief,
    assets_dir: Path,
    shader_version: Optional[str] = None,
) -> SlideBrief:
    version = (shader_version or brief.potero_shader_version or "v1_1").strip()
    potero_dir = assets_dir / POTERO_DIR
    shader = _load_text(potero_dir / SHADER_TEMPLATE.format(version=version))
    negative = _load_text(potero_dir / NEGATIVE_TEMPLATE.format(version=version))

    positive_prompt = _compile_positive(brief, shader, version)
    negative_prompt = _compile_negative(brief, negative, version)

    return update_model(
        brief,
        {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "potero_shader_version": version,
        },
    )


def _compile_positive(brief: SlideBrief, shader: str, version: str) -> str:
    slide_specific = _strip_locked_blocks(brief.positive_prompt or "")
    parts: List[str] = [
        _locked_block(LOCKED_SHADER_START, LOCKED_SHADER_END, shader, version),
    ]
    if slide_specific:
        parts.append(slide_specific)
    if brief.intent:
        parts.append(f"Intent: {brief.intent}.")
    if brief.continuum_cue:
        parts.append(f"Continuum cue: {brief.continuum_cue}.")
    if brief.env_preset:
        parts.append(f"Environment preset: {brief.env_preset}.")
    if brief.lighting_signature:
        parts.append(f"Lighting signature: {brief.lighting_signature}.")
    if brief.kit_anchors:
        anchors = ", ".join(brief.kit_anchors)
        parts.append(f"Kit anchors: {anchors}.")
    if brief.risk_profile:
        parts.append(f"Risk profile: {brief.risk_profile}.")
    return "\n".join(part for part in parts if part).strip()


def _compile_negative(brief: SlideBrief, negative: str, version: str) -> str:
    slide_specific = _strip_locked_blocks(brief.negative_prompt or "")
    parts: List[str] = [
        _locked_block(LOCKED_NEGATIVE_START, LOCKED_NEGATIVE_END, negative, version),
    ]
    if slide_specific:
        parts.append(slide_specific)
    return "\n".join(part for part in parts if part).strip()


def _locked_block(start_token: str, end_token: str, text: str, version: str) -> str:
    start = start_token.format(version=version)
    end = end_token.format(version=version)
    return f"{start}\n{text.strip()}\n{end}".strip()


def _strip_locked_blocks(text: str) -> str:
    cleaned = text
    for start, end in (
        ("<<POTERO_SHADER:", LOCKED_SHADER_END),
        ("<<POTERO_NEGATIVE:", LOCKED_NEGATIVE_END),
    ):
        cleaned = _strip_block(cleaned, start, end)
    return cleaned.strip()


def _strip_block(text: str, start_token: str, end_token: str) -> str:
    current = text
    while True:
        start_idx = current.find(start_token)
        if start_idx == -1:
            break
        end_idx = current.find(end_token, start_idx)
        if end_idx == -1:
            break
        current = current[:start_idx] + current[end_idx + len(end_token) :]
    return current


def _load_text(path: Path) -> str:
    if not path.exists():
        raise PromptCompilerError(f"Missing prompt asset: {path}")
    return path.read_text().strip()
