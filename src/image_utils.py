from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Image = None


def infer_image_extension(image_bytes: bytes, default: str = "png") -> str:
    if not image_bytes:
        return default
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "webp"
    return default


def read_image_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    if Image is not None:
        try:
            with Image.open(path) as img:
                width, height = img.size
                if width and height:
                    return width, height
        except Exception:
            pass
    try:
        data = path.read_bytes()
    except Exception:
        return None

    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        if width > 0 and height > 0:
            return width, height

    if data.startswith(b"\xff\xd8"):
        idx = 2
        length = len(data)
        while idx < length:
            if data[idx] != 0xFF:
                idx += 1
                continue
            while idx < length and data[idx] == 0xFF:
                idx += 1
            if idx >= length:
                break
            marker = data[idx]
            idx += 1
            if marker in (0xD8, 0xD9):
                continue
            if idx + 1 >= length:
                break
            seg_len = int.from_bytes(data[idx:idx + 2], "big")
            if seg_len < 2:
                break
            seg_start = idx + 2
            seg_end = seg_start + seg_len - 2
            if marker in {
                0xC0, 0xC1, 0xC2, 0xC3,
                0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB,
                0xCD, 0xCE, 0xCF,
            }:
                if seg_start + 7 <= length:
                    height = int.from_bytes(data[seg_start + 1:seg_start + 3], "big")
                    width = int.from_bytes(data[seg_start + 3:seg_start + 5], "big")
                    if width > 0 and height > 0:
                        return width, height
                break
            idx = seg_end

    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        offset = 12
        length = len(data)
        while offset + 8 <= length:
            chunk_type = data[offset:offset + 4]
            chunk_size = int.from_bytes(data[offset + 4:offset + 8], "little")
            chunk_data_start = offset + 8
            if chunk_type == b"VP8X" and chunk_data_start + 10 <= length:
                width_minus_one = int.from_bytes(
                    data[chunk_data_start + 4:chunk_data_start + 7],
                    "little",
                )
                height_minus_one = int.from_bytes(
                    data[chunk_data_start + 7:chunk_data_start + 10],
                    "little",
                )
                return width_minus_one + 1, height_minus_one + 1
            offset = chunk_data_start + chunk_size
            if chunk_size % 2 == 1:
                offset += 1
    return None


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_r{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
