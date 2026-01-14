import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.upload_cache import UploadCache
class CriticError(Exception):
    pass

class Critic:
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        warn_threshold: int = 85,
        fail_threshold: int = 70,
        potero_pass_threshold: float = 7.5,
        potero_warn_threshold: float = 6.0,
        allow_warn_pass: bool = False,
        upload_cache: Optional[UploadCache] = None,
        client: Optional[Any] = None,
    ):
        self.model_name = model_name
        self.warn_threshold = warn_threshold
        self.fail_threshold = fail_threshold
        self.potero_pass_threshold = potero_pass_threshold
        self.potero_warn_threshold = potero_warn_threshold
        self.allow_warn_pass = allow_warn_pass
        self.logger = logging.getLogger(__name__)
        self.client = client
        self.upload_cache = upload_cache

    def validate_image(
        self,
        image_path: str,
        reference_assets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Validates the generated image against the Potero "Kill List".
        """
        vqa_checklist = [
            "Is a face or identifiable tattoo visible?",
            (
                "Is there any readable text or logo that is NOT the approved "
                "'POTERO STANDARD' embroidery on the hoodie front?"
            ),
            "Are there exactly 5 fingers on each hand? Are they holding gear correctly?",
            "Is any camo pattern on gear or trousers NOT Finnish M05?",
            (
                "Is there any camo pattern applied to the hoodie fabric itself?"
            ),
            (
                "Is the hoodie front-facing (chest visible) or back-facing?"
            ),
            (
                "If the hoodie is front-facing, is the 'POTERO STANDARD' "
                "embroidery present and matching the reference size, color, and placement?"
            ),
            (
                "If the hoodie is back-facing, does the back design match the "
                "reference exactly and remain at least partially visible "
                "(partial occlusion by gear is acceptable)?"
            ),
            "Is the lighting flat or glossy (not harsh with crushed blacks)?",
        ]
        
        self.logger.info("critic_analyzing_image", extra={"image_path": image_path})

        try:
            if not self.client:
                raise CriticError("GenAI client not configured for critic.")
            image_part = self._load_image(image_path)
            reference_parts = self._load_reference_assets(reference_assets)
            prompt = self._build_prompt(vqa_checklist)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, image_part, *reference_parts],
            )
            text = getattr(response, "text", None) or str(response)
            result = self._parse_result(text)
            result = self._apply_fail_fast(result)
            result = self._apply_thresholds(result)
            qa_status = self._grade_result(
                result.get("pass"),
                result.get("qa_score"),
            )
            result["qa_status"] = qa_status
            self.logger.info(
                "critic_result",
                extra={
                    "passed": result.get("pass"),
                    "qa_score": result.get("qa_score"),
                    "qa_status": qa_status,
                },
            )
            return result
        except Exception as exc:
            error_text = str(exc)
            fatal = _is_model_not_found(error_text)
            self.logger.error(
                "critic_validation_failed",
                extra={"error": error_text, "fatal": fatal},
            )
            return {
                "pass": False,
                "qa_score": 0,
                "qa_status": "fail",
                "feedback": f"Critic failure: {error_text}",
                "fatal": fatal,
            }

    def _load_image(self, image_path: str) -> Any:
        path = Path(image_path)
        if not path.exists():
            raise CriticError(f"Image not found: {image_path}")
        if not self.upload_cache:
            raise CriticError("Upload cache not configured for critic.")
        return self.upload_cache.upload(path)

    def _build_prompt(self, checklist: List[str]) -> str:
        questions = "\n".join(f"- {item}" for item in checklist)
        return f"""
You are the Critic Agent for Potero Carousel Factory.
Analyze the generated image and compare it to the reference images.
The first image is the generated output. Any additional images are references
(hoodie product shots and/or M05 swatches). Use them as strict ground truth.
The only allowed readable text/logo is the approved "POTERO STANDARD" embroidery
that matches the hoodie references in size, color, and placement.
Only require the front embroidery when the hoodie is front-facing. If the
hoodie is back-facing, the front embroidery may be absent and should NOT be
treated as a violation. Back design must match references; partial occlusion
by gear is acceptable if the design remains verifiable. If the back design is
not visible enough to verify, mark "back_design_not_visible".
If you are not fully confident the embroidery matches the references exactly,
set pass=false and include "hoodie_mismatch" in violations.

Checklist:
{questions}

If any checklist item is a violation, set opsec_pass=false or add to violations.
Return strict JSON only in this format (arrays can be empty):
{{
  "pass": true,
  "opsec_pass": true,
  "opsec_violations": [],
  "potero_score": 0-10,
  "potero_breakdown": {{
    "lighting": 0-3,
    "texture": 0-3,
    "authenticity": 0-3,
    "narrative": 0-1,
    "anti_warcore": 0-1,
    "composition_imperfect": 0-1
  }},
  "potero_fail_reasons": [],
  "qa_score": 0-100,
  "violations": [
    "face",
    "tattoo",
    "flag",
    "unapproved_text",
    "logo_mismatch",
    "hoodie_mismatch",
    "front_logo_missing",
    "front_logo_incorrect",
    "back_design_mismatch",
    "back_design_not_visible",
    "camo_mismatch",
    "camo_on_hoodie",
    "anatomy",
    "lighting"
  ],
  "feedback": "short reason",
  "repair_mode": "edit or regen",
  "repair_targets": [],
  "repair_instructions": "single paragraph",
  "confidence": 0-1
}}
""".strip()

    def _parse_result(self, raw_text: str) -> Dict[str, Any]:
        data = _extract_json(raw_text)
        if not isinstance(data, dict):
            raise CriticError("Critic output must be a JSON object.")
        passed = _coerce_bool(data.get("pass"))
        qa_score = _coerce_int(data.get("qa_score"))
        feedback = data.get("feedback", "")
        violations = _coerce_list(data.get("violations"))

        opsec_pass = _coerce_bool(data.get("opsec_pass"))
        opsec_violations = _coerce_list(data.get("opsec_violations"))
        potero_score = _coerce_float(data.get("potero_score"))
        potero_breakdown = data.get("potero_breakdown")
        if not isinstance(potero_breakdown, dict):
            potero_breakdown = {}
        potero_fail_reasons = _coerce_list(data.get("potero_fail_reasons"))
        repair_mode = data.get("repair_mode")
        repair_targets = _coerce_list(data.get("repair_targets"))
        repair_instructions = data.get("repair_instructions", "")
        confidence = _coerce_float(data.get("confidence"))
        fatal = _coerce_bool(data.get("fatal")) or False

        if qa_score is not None:
            qa_score = max(0, min(100, qa_score))

        return {
            "pass": passed,
            "qa_score": qa_score,
            "feedback": str(feedback),
            "violations": violations,
            "opsec_pass": opsec_pass,
            "opsec_violations": opsec_violations,
            "potero_score": potero_score,
            "potero_breakdown": potero_breakdown,
            "potero_fail_reasons": potero_fail_reasons,
            "repair_mode": repair_mode,
            "repair_targets": repair_targets,
            "repair_instructions": str(repair_instructions),
            "confidence": confidence,
            "fatal": fatal,
        }

    def _grade_result(self, passed: Any, qa_score: Any) -> str:
        if passed is False:
            return "fail"
        if not isinstance(qa_score, int):
            return "warn"
        if qa_score < self.fail_threshold:
            return "fail"
        if qa_score < self.warn_threshold:
            return "warn"
        return "pass"

    def _apply_fail_fast(self, result: Dict[str, Any]) -> Dict[str, Any]:
        violations = result.get("violations") or []
        opsec_violations = result.get("opsec_violations") or []
        combined = list(violations) + list(opsec_violations)
        hard_fail = {
            "face",
            "tattoo",
            "flag",
            "unapproved_text",
            "logo_mismatch",
            "hoodie_mismatch",
            "front_logo_missing",
            "front_logo_incorrect",
            "back_design_mismatch",
            "back_design_not_visible",
            "camo_mismatch",
            "camo_on_hoodie",
        }
        if any(str(v).lower() in hard_fail for v in combined):
            result["pass"] = False
            if result.get("qa_score") is not None:
                result["qa_score"] = min(result.get("qa_score", 0), 10)
            result["opsec_pass"] = False
            if not result.get("feedback"):
                result["feedback"] = "Hard fail: OPSEC violation."
        return result

    def _apply_thresholds(self, result: Dict[str, Any]) -> Dict[str, Any]:
        opsec_pass = result.get("opsec_pass")
        opsec_violations = result.get("opsec_violations") or []
        if opsec_pass is None:
            opsec_pass = len(opsec_violations) == 0
        if opsec_violations:
            opsec_pass = False

        potero_score = result.get("potero_score")
        qa_score = result.get("qa_score")
        if potero_score is None and isinstance(qa_score, int):
            potero_score = qa_score / 10.0
        if potero_score is not None and qa_score is None:
            qa_score = int(max(0.0, min(10.0, potero_score)) * 10)

        passed = result.get("pass")
        if opsec_pass is False:
            passed = False
        elif potero_score is not None:
            if potero_score >= self.potero_pass_threshold:
                passed = True
            elif potero_score >= self.potero_warn_threshold:
                passed = self.allow_warn_pass
            else:
                passed = False

        result["opsec_pass"] = opsec_pass
        result["potero_score"] = potero_score
        result["qa_score"] = qa_score
        result["pass"] = bool(passed) if passed is not None else False
        return result

    def _load_reference_assets(
        self,
        reference_assets: Optional[List[str]],
    ) -> List[Any]:
        if not reference_assets:
            return []
        if not self.upload_cache:
            raise CriticError("Upload cache not configured for critic.")
        parts: List[Any] = []
        for asset in reference_assets:
            path = Path(asset)
            if not path.exists():
                self.logger.warning(
                    "reference_asset_missing",
                    extra={"asset": str(path)},
                )
                continue
            parts.append(self.upload_cache.upload(path))
        return parts


def _extract_json(raw_text: str) -> Any:
    text = raw_text.strip()
    if not text:
        raise CriticError("Critic returned empty response.")
    if text[0] in "[{":
        return json.loads(text)
    start = min(
        [idx for idx in (text.find("["), text.find("{")) if idx != -1],
        default=-1,
    )
    end = max(text.rfind("]"), text.rfind("}"))
    if start == -1 or end == -1 or end <= start:
        raise CriticError("Unable to locate JSON in critic output.")
    return json.loads(text[start : end + 1])


def _is_model_not_found(error_text: str) -> bool:
    lowered = error_text.lower()
    return "models/" in lowered and "not found" in lowered


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "pass"}
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return []
