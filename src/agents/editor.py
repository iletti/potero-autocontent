import logging
from pathlib import Path
from typing import Any, List, Optional

from src.model_utils import update_model
from src.state import SlideBrief
from src.upload_cache import UploadCache

class Editor:
    def __init__(
        self,
        model_name: str = "gemini-3-pro-preview",
        mode: str = "rules",
        client: Optional[Any] = None,
        upload_cache: Optional[UploadCache] = None,
    ):
        self.model_name = model_name
        self.mode = (mode or "rules").strip().lower()
        self.client = client
        self.upload_cache = upload_cache
        self.logger = logging.getLogger(__name__)

    def uses_llm(self) -> bool:
        return self.mode == "llm"

    def refine_brief(
        self,
        brief: SlideBrief,
        feedback: str,
        reference_assets: Optional[List[str]] = None,
        allow_llm: bool = True,
    ) -> SlideBrief:
        """
        Analyzes the Critic's failure reason and modifies the prompt.
        """
        self.logger.info(
            "editor_refining_prompt",
            extra={"feedback": feedback},
        )
        if not feedback:
            return brief
        constraints = self._build_constraints(feedback)
        if not constraints:
            return brief
        base_prompt = self._strip_constraints(brief.positive_prompt)

        if allow_llm and self.uses_llm() and self.client:
            refined = self._refine_with_llm(
                base_prompt=base_prompt,
                constraints=constraints,
                negative_prompt=brief.negative_prompt,
                composition_guidance=brief.composition_guidance,
                reference_assets=reference_assets or brief.reference_assets,
            )
            if refined:
                return update_model(brief, {"positive_prompt": refined})

        refined_prompt = self._merge_prompt(base_prompt, constraints)
        return update_model(brief, {"positive_prompt": refined_prompt})

    def _strip_constraints(self, prompt: str) -> str:
        marker = "\nConstraints:"
        if marker in prompt:
            return prompt.split(marker, 1)[0].strip()
        return prompt.strip()

    def _merge_prompt(self, base_prompt: str, constraints: str) -> str:
        return f"{base_prompt}\nConstraints: {constraints}".strip()

    def _build_constraints(self, feedback: str) -> str:
        feedback_lower = feedback.lower()
        constraints = [
            (
                "No text or logos anywhere except the approved 'POTERO STANDARD' "
                "embroidery on the hoodie chest; if it cannot match the references "
                "exactly, omit all text/logos."
            )
        ]
        if "backpack" in feedback_lower or "gear" in feedback_lower or "patch" in feedback_lower:
            constraints.append("Remove all patches and text from gear and backpack.")
        if "back design" in feedback_lower and "obscured" in feedback_lower:
            constraints.append(
                "Keep the hoodie back design at least partially visible; avoid full occlusion by gear."
            )
        if "size" in feedback_lower or "larger" in feedback_lower or "oversized" in feedback_lower:
            constraints.append(
                "Embroidery must be small chest-sized and match reference scale."
            )
        if "missing" in feedback_lower and "embroidery" in feedback_lower:
            constraints.append(
                "If the hoodie embroidery is present, it must match the reference size and placement."
            )
        if "unapproved" in feedback_lower or "graphics" in feedback_lower or "text" in feedback_lower:
            constraints.append("Remove all unapproved text and graphics.")
        return " ".join(constraints).strip()

    def _refine_with_llm(
        self,
        base_prompt: str,
        constraints: str,
        negative_prompt: str,
        composition_guidance: Optional[str],
        reference_assets: List[str],
    ) -> Optional[str]:
        if not self.client:
            return None
        try:
            reference_parts = self._load_reference_assets(reference_assets)
            prompt = (
                "Refine the image prompt without changing the intent. "
                "Preserve the hoodie and M05 constraints and do not add new text "
                "or graphics. Return ONLY the refined positive prompt text.\n"
                f"Base prompt: {base_prompt}\n"
                f"Constraints: {constraints}\n"
                f"Negative prompt: {negative_prompt}\n"
                f"Composition guidance: {composition_guidance or ''}\n"
            ).strip()
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, *reference_parts],
            )
            text = getattr(response, "text", None) or str(response)
            return text.strip()
        except Exception as exc:
            self.logger.warning(
                "editor_llm_refine_failed",
                extra={"error": str(exc)},
            )
            return None

    def _load_reference_assets(self, reference_assets: List[str]) -> List[Any]:
        if not reference_assets or not self.upload_cache:
            return []
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
