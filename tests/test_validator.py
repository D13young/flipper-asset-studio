"""Тесты валидатора (T6)."""
import struct
import tempfile
import unittest
from pathlib import Path

from core.validator import FlipperAssetPackValidator, ValidationLevel


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        self.v = FlipperAssetPackValidator()

    def test_missing_path_is_error(self):
        results = self.v.validate_pack(Path("/nonexistent/pack"))
        self.assertTrue(any(r.level == ValidationLevel.ERROR for r in results))

    def test_empty_dir_has_warning(self):
        with tempfile.TemporaryDirectory() as td:
            results = self.v.validate_pack(Path(td))
        self.assertTrue(any(r.level == ValidationLevel.WARNING for r in results),
                        "не найденные обязательные папки должны давать WARNING")

    def test_valid_animated_icon(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            icon = root / "Icons" / "Passport"
            icon.mkdir(parents=True)
            (icon / "meta").write_bytes(struct.pack("<HHBB", 46, 49, 1, 1))
            results = self.v.validate_pack(root)
        self.assertTrue(any(r.level == ValidationLevel.SUCCESS and "Анимированная иконка" in r.message for r in results))

    def test_bad_icon_meta_size_is_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            icon = root / "Icons" / "Passport"
            icon.mkdir(parents=True)
            (icon / "meta").write_bytes(b"\x00" * 10)  # не 6 байт
            results = self.v.validate_pack(root)
        self.assertTrue(any("должен быть 6 байт" in r.message and r.level == ValidationLevel.ERROR for r in results))

    def test_animation_missing_manifest_warns(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            anim = root / "Anims"
            (anim / "anim1").mkdir(parents=True)
            (anim / "anim1" / "meta.txt").write_text("Filetype: Flipper Animation\n")
            (anim / "anim1" / "frame_0.bm").write_bytes(b"\x00" * 8)
            results = self.v.validate_pack(root)
        self.assertTrue(any("Отсутствует manifest.txt" in r.message for r in results))

    def test_summary_keys(self):
        self.v.validate_pack(Path("/nonexistent"))
        summary = self.v.get_summary()
        self.assertEqual(set(summary), {"info", "warning", "error", "success"})


if __name__ == "__main__":
    unittest.main()