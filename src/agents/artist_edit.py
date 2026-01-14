import base64
import io
import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple

try:
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency
    types = None

from src.state import SlideBrief
from src.state import SlideBrief
from src.upload_cache import UploadCache
from src.interaction_logger import InteractionLogger


class ArtistEdit:
    def __init__(
        self,
        model_name: str = "gemini-3-pro-image-preview",
        output_dir: Optional[Path] = None,
        upload_cache: Optional[UploadCache] = None,
        client: Optional[Any] = None,
        interaction_logger: Optional[InteractionLogger] = None,
    ):
        self.model_name = model_name
        self.output_dir = Path(output_dir) if output_dir else Path("output")
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.interaction_logger = interaction_logger
        if upload_cache is not None:
            self.upload_cache = upload_cache
        elif client is not None:
            self.upload_cache = UploadCache(client=client)
        else:
            self.upload_cache = None

    def edit_image(
        self,
        brief: SlideBrief,
        image_path: str,
        instructions: str,
    ) -> str:
        if not self.client:
            raise ValueError("GenAI client not configured for artist edit.")
        if not instructions:
            raise ValueError("Missing edit instructions.")

        prompt = self._build_prompt(brief, instructions)
        image_parts = self._load_reference_images(
            brief.reference_assets,
            image_path,
        )
        generation_config = self._build_generation_config(
            aspect_ratio=brief.image_aspect,
            image_size=brief.image_size,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, *image_parts],
                config=generation_config,
            )
        except Exception as e:
            if self.interaction_logger:
                self.interaction_logger.log(
                    agent="ArtistEdit",
                    step="edit_image_failed",
                    model=self.model_name,
                    prompt=prompt,
                    response=f"Exception: {str(e)}",
                    metadata={"instructions": instructions}
                )
            raise e

        image_bytes, file_ext = self._extract_image_bytes(response)
        if not image_bytes:
            # Try to extract text to see if it was a refusal
            text_response = "No text returned"
            try:
                text_response = getattr(response, "text", "") or str(response)
            except Exception:
                pass
            
            self.logger.warning(
                "artist_edit_no_image",
                extra={
                    "model": self.model_name,
                    "response_preview": text_response[:500]
                }
            )

            if self.interaction_logger:
                self.interaction_logger.log(
                    agent="ArtistEdit",
                    step="edit_image_failed",
                    model=self.model_name,
                    prompt=prompt,
                    response=f"Failed (No Image): {text_response[:1000]}",
                    metadata={"instructions": instructions}
                )

            raise ValueError(f"No image returned from edit call. Response: {text_response[:200]}")

        filename = f"slide_{brief.index}_edit.{file_ext}"
        output_path = self.output_dir / filename
        output_path.write_bytes(image_bytes)

        if self.interaction_logger:
            self.interaction_logger.log(
                agent="ArtistEdit",
                step="edit_image",
                model=self.model_name,
                prompt=prompt,
                response=f"Success: {filename} ({len(image_bytes)} bytes)",
                metadata={"instructions": instructions}
            )

        return str(output_path)

    def _build_prompt(self, brief: SlideBrief, instructions: str) -> str:
        composition = brief.composition_guidance or ""
        
        preservation_instruction = ""
        if "logo" in instructions.lower() or "embroidery" in instructions.lower():
            preservation_instruction = (
                "CRITICAL: You are fixing the BRANDING/LOGO. "
                "Use the provided FRONT VIEW reference image as the absolute ground truth for the logo "
                "size, position, and color. "
                "Preserve the original image's pose, lighting, background, and fold patterns exactly. "
                "Only overlay/correct the logo pixels."
            )
            
        return (
            "Edit the image based on the instructions. Keep the original composition.\n"
            f"Instructions: {instructions}\n"
            f"{preservation_instruction}\n"
            f"Positive prompt: {brief.positive_prompt}\n"
            f"Negative prompt: {brief.negative_prompt}\n"
            f"Composition guidance: {composition}\n"
            "Reference images are attached. Match their details precisely."
        ).strip()

    def _build_generation_config(
        self,
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None,
    ) -> Optional[Any]:
        if types is None or not hasattr(types, "GenerateContentConfig"):
            return None
        if hasattr(types, "ImageConfig"):
            return types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio or "4:5",
                    image_size=image_size or "2K",
                ),
            )
        return types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        )

    def _load_reference_images(
        self,
        reference_assets: List[str],
        image_path: str,
    ) -> List[Any]:
        if self.upload_cache is None:
            self.logger.warning("upload_cache_unavailable")
            return []
        assets: List[str] = [image_path]
        assets.extend(reference_assets or [])

        parts: List[Any] = []
        for asset in assets:
            path = Path(asset)
            if not path.exists():
                self.logger.warning(
                    "reference_asset_missing",
                    extra={"asset": str(path)},
                )
                continue
            parts.append(self.upload_cache.upload(path))
        return parts

    def _extract_image_bytes(self, response: Any) -> Tuple[Optional[bytes], str]:
        candidates = getattr(response, "candidates", None)
        if candidates:
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None)
                if not parts:
                    continue
                for part in parts:
                    inline_data = getattr(part, "inline_data", None)
                    if not inline_data:
                        continue
                    data = getattr(inline_data, "data", None)
                    if data:
                        return self._decode_data(data), "png"
        return None, "png"

    def _decode_data(self, data: Any) -> Optional[bytes]:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return base64.b64decode(data)
        return None
