"""Тесты icon_builder (T7): статичная и анимированная иконки."""
import struct
import tempfile
import unittest
from pathlib import Path

from core.icon_builder import FlipperIconBuilder


class IconBuilderTest(unittest.TestCase):
    def test_static_icon_fallback_writes_bmx(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            fl = FlipperIconBuilder.export_icon(
                [b"\xff" * 1024],       # 1 кадр 128x64
                128, 64, 1,
                out / "Icons" / "Passport",
                compress=True,
                file_basename="passport_128x64",
            )
            self.assertTrue(fl.exists())
            self.assertEqual(fl.name, "passport_128x64.bmx")
            # .bmx: width/height заголовок <II
            data = fl.read_bytes()
            w, h = struct.unpack("<II", data[0:8])
            self.assertEqual((w, h), (128, 64))

    def test_animated_icon_creates_meta_and_frames(self):
        with tempfile.TemporaryDirectory() as td:
            out = FlipperIconBuilder.export_icon(
                [b"\x01" * 1024, b"\x02" * 1024],
                128, 64, 2,
                Path(td) / "folder",
                compress=True,
            )
            self.assertTrue((out / "meta").exists())
            self.assertTrue((out / "frame_00.bmx").exists())
            self.assertTrue((out / "frame_01.bmx").exists())
            meta = (out / "meta").read_bytes()
            w, h, fps, count = struct.unpack("<HHBB", meta)
            self.assertEqual((w, h, fps, count), (128, 64, 2, 2))

    def test_binary_meta_pack(self):
        self.assertEqual(
            FlipperIconBuilder.create_binary_meta(46, 49, 1, 2),
            struct.pack("<HHBB", 46, 49, 1, 2),
        )


if __name__ == "__main__":
    unittest.main()