import base64
import io
import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

try:
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency
    types = None

from src.state import SlideBrief
from src.upload_cache import UploadCache

class Artist:
    def __init__(
        self,
        model_name: str = "gemini-3-pro-image-preview",
        output_dir: Union[Path, str] = "output",
        upload_cache: Optional[UploadCache] = None,
        client: Optional[Any] = None,
        fallbacks: Optional[List[str]] = None,
    ):
        self.primary_model = model_name
        self.fallbacks = fallbacks or ["imagen-3.0-generate-001", "gemini-1.5-flash"]
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        self.client = client
        if upload_cache is not None:
            self.upload_cache = upload_cache
        elif client is not None:
            self.upload_cache = UploadCache(client=client)
        else:
            self.upload_cache = None

    def generate_image(
        self,
        brief: SlideBrief,
        anchor_image_path: Optional[str] = None,
    ) -> str:
        """
        Generates a 4:5 image based on the brief with model fallback.
        """
        if not self.client:
            raise ValueError("GenAI client not configured for artist.")
        models_to_try = [self.primary_model] + self.fallbacks
        prompt = self._build_prompt(brief)
        image_parts = self._load_reference_images(
            brief.reference_assets, anchor_image_path
        )
        aspect_ratio = brief.image_aspect
        image_size = brief.image_size

        for model in models_to_try:
            try:
                self.logger.info(
                    "artist_generation_attempt",
                    extra={"model": model, "slide_index": brief.index},
                )
                if self._is_imagen_model(model):
                    images_config = self._build_images_config()
                    if images_config:
                        response = self.client.models.generate_images(
                            model=model,
                            prompt=prompt,
                            config=images_config,
                        )
                    else:
                        response = self.client.models.generate_images(
                            model=model,
                            prompt=prompt,
                        )
                    image_bytes, file_ext = self._extract_imagen_bytes(response)
                else:
                    generation_config = self._build_generation_config(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                    )
                    if generation_config:
                        response = self.client.models.generate_content(
                            model=model,
                            contents=[prompt, *image_parts],
                            config=generation_config,
                        )
                    else:
                        response = self.client.models.generate_content(
                            model=model,
                            contents=[prompt, *image_parts],
                        )
                    image_bytes, file_ext = self._extract_image_bytes(response)
                if not image_bytes:
                    self.logger.warning(
                        "artist_no_image_returned",
                        extra={"model": model, "slide_index": brief.index},
                    )
                    continue

                filename = f"slide_{brief.index}.{file_ext}"
                output_path = self.output_dir / filename
                output_path.write_bytes(image_bytes)
                return str(output_path)
            except Exception as e:
                self.logger.warning(
                    "artist_generation_failed",
                    extra={"model": model, "error": str(e)},
                )
        
        raise Exception("All image generation models failed.")

    def generate_candidates(
        self,
        brief: SlideBrief,
        anchor_image_path: Optional[str],
        count: int,
    ) -> List[str]:
        candidates: List[str] = []
        for _ in range(max(1, count)):
            candidates.append(self.generate_image(brief, anchor_image_path))
        return candidates

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
                    size=image_size or "2K",
                ),
            )
        return types.GenerateContentConfig(
            response_modalities=["IMAGE"]
        )

    def _build_images_config(self) -> Optional[Any]:
        if types is None or not hasattr(types, "GenerateImagesConfig"):
            return None
        return types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/png",
        )

    def _build_prompt(self, brief: SlideBrief) -> str:
        composition = brief.composition_guidance or ""
        return (
            f"{brief.positive_prompt}\n"
            f"Negative prompt: {brief.negative_prompt}\n"
            f"Composition guidance: {composition}\n"
            "Reference images are attached. Follow them as strict ground truth.\n"
            "Preserve all the details from the original images, especially "
            "hoodie color, embroidery, and print placement/scale.\n"
            "Do not add any text or graphics unless it is the exact "
            "'POTERO STANDARD' embroidery copied from the references; "
            "if you cannot match it exactly, omit all text/logos."
        ).strip()

    def _load_reference_images(
        self,
        reference_assets: List[str],
        anchor_image_path: Optional[str],
    ) -> List[Any]:
        if self.upload_cache is None:
            self.logger.warning("upload_cache_unavailable")
            return []
        assets: List[str] = []
        if anchor_image_path:
            assets.append(anchor_image_path)
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
        image_bytes = self._extract_from_candidates(response)
        if image_bytes:
            return image_bytes, "png"

        parts = getattr(response, "parts", None)
        if parts:
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data:
                    data = getattr(inline_data, "data", None)
                    if data:
                        return self._decode_data(data), "png"
        return None, "png"

    def _extract_from_candidates(self, response: Any) -> Optional[bytes]:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None
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
                    return self._decode_data(data)
        return None

    def _extract_imagen_bytes(self, response: Any) -> Tuple[Optional[bytes], str]:
        images = getattr(response, "generated_images", None)
        if not images:
            return None, "png"
        first = images[0]
        image = getattr(first, "image", None)
        if image is None:
            return None, "png"
        if isinstance(image, bytes):
            return image, "png"
        if hasattr(image, "tobytes"):
            return image.tobytes(), "png"
        if hasattr(image, "save"):
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue(), "png"
        return None, "png"

    def _decode_data(self, data: Any) -> Optional[bytes]:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return base64.b64decode(data)
        return None

    def _is_imagen_model(self, model: str) -> bool:
        if not model:
            return False
        normalized = model
        if normalized.startswith("models/"):
            normalized = normalized[len("models/"):]
        return normalized.startswith("imagen-")
