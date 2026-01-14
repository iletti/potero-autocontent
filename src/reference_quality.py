from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Image = None


@dataclass(frozen=True)
class ReferenceScore:
    path: str
    score: float
    reasons: List[str]
    width: Optional[int]
    height: Optional[int]
    size_bytes: int


def score_references(paths: List[str]) -> Dict[str, ReferenceScore]:
    scores: Dict[str, ReferenceScore] = {}
    for path in paths:
        scores[path] = _score_reference(Path(path))
    return scores


def _score_reference(path: Path) -> ReferenceScore:
    reasons: List[str] = []
    score = 10.0

    if not path.exists():
        return ReferenceScore(
            path=str(path),
            score=0.0,
            reasons=["missing"],
            width=None,
            height=None,
            size_bytes=0,
        )

    size_bytes = path.stat().st_size
    if size_bytes < 150_000:
        score -= 3.0
        reasons.append("low_filesize")
    elif size_bytes < 300_000:
        score -= 1.5
        reasons.append("medium_filesize")

    width = None
    height = None
    if Image is not None:
        try:
            with Image.open(path) as img:
                width, height = img.size
        except Exception:
            reasons.append("unreadable_image")
            score -= 3.0
    if width and height:
        if min(width, height) < 512:
            score -= 4.0
            reasons.append("very_low_resolution")
        elif min(width, height) < 1024:
            score -= 2.0
            reasons.append("low_resolution")

    ext = path.suffix.lower().strip(".")
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        score -= 1.0
        reasons.append("unexpected_format")

    score = max(0.0, min(10.0, score))
    return ReferenceScore(
        path=str(path),
        score=score,
        reasons=reasons,
        width=width,
        height=height,
        size_bytes=size_bytes,
    )
