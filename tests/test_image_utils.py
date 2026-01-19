import unittest
from pathlib import Path

from src.image_utils import ensure_unique_path, infer_image_extension, read_image_dimensions


class TestImageUtils(unittest.TestCase):
    def test_infer_jpeg(self):
        data = b"\xff\xd8\xff\xe0" + b"0" * 10
        self.assertEqual(infer_image_extension(data, "png"), "jpg")

    def test_infer_png(self):
        data = b"\x89PNG\r\n\x1a\n" + b"0" * 10
        self.assertEqual(infer_image_extension(data, "jpg"), "png")

    def test_infer_webp(self):
        data = b"RIFF" + b"0" * 4 + b"WEBP" + b"0" * 10
        self.assertEqual(infer_image_extension(data, "png"), "webp")

    def test_infer_default(self):
        data = b"notanimage"
        self.assertEqual(infer_image_extension(data, "png"), "png")

    def test_read_dimensions_png(self):
        # Minimal PNG header with IHDR width=32 height=16
        data = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\x0dIHDR"
            b"\x00\x00\x00\x20"
            b"\x00\x00\x00\x10"
            b"\x08\x02\x00\x00\x00"
        )
        tmp = __import__("tempfile").NamedTemporaryFile(delete=False)
        try:
            tmp.write(data)
            tmp.close()
            dims = read_image_dimensions(Path(tmp.name))
            self.assertEqual(dims, (32, 16))
        finally:
            __import__("os").unlink(tmp.name)

    def test_read_dimensions_jpeg(self):
        # Minimal JPEG with SOF0 width=32 height=16
        data = (
            b"\xff\xd8"
            b"\xff\xc0"
            b"\x00\x11"
            b"\x08"
            b"\x00\x10"
            b"\x00\x20"
            b"\x03"
            b"\x01\x11\x00"
            b"\x02\x11\x00"
            b"\x03\x11\x00"
            b"\xff\xd9"
        )
        tmp = __import__("tempfile").NamedTemporaryFile(delete=False)
        try:
            tmp.write(data)
            tmp.close()
            dims = read_image_dimensions(Path(tmp.name))
            self.assertEqual(dims, (32, 16))
        finally:
            __import__("os").unlink(tmp.name)

    def test_ensure_unique_path(self):
        tmpdir = __import__("tempfile").TemporaryDirectory()
        try:
            base = Path(tmpdir.name) / "slide_1.jpg"
            base.write_bytes(b"x")
            next_path = ensure_unique_path(base)
            self.assertNotEqual(next_path, base)
            self.assertEqual(next_path.name, "slide_1_r1.jpg")
        finally:
            tmpdir.cleanup()
