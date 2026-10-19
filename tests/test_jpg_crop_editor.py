"""Тесты JPG Crop: в списке Output Size присутствуют размеры пресетов Icons."""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from core.icon_builder import ICON_PRESETS
from core.image_processor import FlipperImageProcessor


class TestJpgCropSizeCombo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        from ui.jpg_crop_editor import JpegCropEditorWidget
        self.w = JpegCropEditorWidget()

    def tearDown(self):
        self.w.deleteLater()

    def _combo_items(self):
        return [(self.w.size_combo.itemText(i), self.w.size_combo.itemData(i))
                for i in range(self.w.size_combo.count())]

    def test_standard_sizes_still_present(self):
        items = dict(self._combo_items())
        for w, h in FlipperImageProcessor.VALID_ICON_SIZES:
            self.assertIn((w, h), items.values(), f"Нет стандартного размера {w}x{h}")

    def test_icon_preset_sizes_present(self):
        items = dict(self._combo_items())
        expected = set()
        for files in ICON_PRESETS.values():
            expected.update(files.values())
        for w, h in expected:
            self.assertIn((w, h), items.values(), f"Нет размера иконки {w}x{h}")
        # Конкретно новые размеры из вкладки Icons
        for size in {(91, 55), (51, 64), (97, 61), (123, 52), (46, 49), (128, 64)}:
            self.assertIn(size, items.values())

    def test_no_duplicates_and_sorted(self):
        items = self._combo_items()
        sizes = [data for _, data in items]
        self.assertEqual(len(sizes), len(set(sizes)), "Размеры не должны дублироваться")
        self.assertEqual(sizes, sorted(sizes, key=lambda p: (p[0], p[1])))

    def test_preset_sizes_have_icons_tooltip(self):
        # (46, 49) и (128, 64) есть и в стандартных, и в Icons — тултип обязателен
        for w, h in {(91, 55), (51, 64), (123, 52), (46, 49), (128, 64)}:
            idx = self.w.size_combo.findText(f"{w}x{h}")
            self.assertGreaterEqual(idx, 0)
            tip = self.w.size_combo.itemData(idx, Qt.ItemDataRole.ToolTipRole)
            self.assertIsInstance(tip, str)
            self.assertTrue(tip.startswith("Icons: "), f"{w}x{h}: тултип {tip!r}")


if __name__ == "__main__":
    unittest.main()
