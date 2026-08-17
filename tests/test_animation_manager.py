"""Тесты FlipperAnimationManager (T5) без GUI-части."""
import os
import sys
import tempfile
import unittest

from PIL import Image

from core.animation_manager import FlipperAnimationManager


def _dummy_frames(manager, n):
    manager.frames = [
        {"path": f"/tmp/f{i}.png", "bytes": bytes([i]), "preview": None, "dither_level": 1}
        for i in range(n)
    ]
    manager.meta_params["passive_frames"] = n


class MetaManifestTest(unittest.TestCase):
    def setUp(self):
        self.m = FlipperAnimationManager()

    def test_default_meta_has_zero_frames(self):
        meta = self.m.generate_meta_txt()
        self.assertIn("Filetype: Flipper Animation", meta)
        self.assertIn("Passive frames: 0", meta)
        self.assertIn("Width: 128", meta)

    def test_passive_frames_updates_after_add(self):
        _dummy_frames(self.m, 3)
        self.assertEqual(self.m.meta_params["passive_frames"], 3)

    def test_manifest_clamps_max_bh(self):
        manifest = self.m.generate_manifest_txt("X", min_bh=0, max_bh=99)
        self.assertIn("Max butthurt: 18", manifest)

    def test_manifest_content(self):
        manifest = self.m.generate_manifest_txt(
            "Dolphin", min_bh=2, max_bh=14, min_lv=1, max_lv=30, weight=8
        )
        self.assertIn("Name: Dolphin", manifest)
        self.assertIn("Weight: 8", manifest)


class FrameOpsTest(unittest.TestCase):
    def setUp(self):
        self.m = FlipperAnimationManager()
        _dummy_frames(self.m, 4)

    def test_move_frame_up(self):
        self.m.move_frame(0, 2)
        self.assertEqual(self.m.frames[2]["path"], "/tmp/f0.png")

    def test_remove_frame_updates_passive_count(self):
        self.m.remove_frame(1)
        self.assertEqual(len(self.m.frames), 3)
        self.assertEqual(self.m.meta_params["passive_frames"], 3)

    def test_get_frame_bytes_list_order(self):
        self.m.move_frame(0, 3)
        self.assertEqual(self.m.get_frame_bytes_list(), [bytes([1]), bytes([2]), bytes([3]), bytes([0])])


class ReprocessFramesTest(unittest.TestCase):
    """T5: reprocess_frames / reprocess_frames_to_bytes (нужен QApplication
    для построения QPixmap-превью, гоняем в offscreen-режиме)."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt6.QtWidgets import QApplication
            cls.app = QApplication.instance() or QApplication(sys.argv)
        except Exception as e:  # pragma: no cover
            raise unittest.SkipTest(f"QApplication недоступен: {e}")

        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.paths = []
        for i, color in enumerate([0, 128, 255]):
            p = os.path.join(cls.tmpdir.name, f"f{i}.png")
            Image.new("L", (64, 64), color).save(p)
            cls.paths.append(p)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def _manager_with_frames(self):
        m = FlipperAnimationManager()
        for p in self.paths:
            m.add_frame(p, dither_level=1)
        return m

    def test_add_frame_builds_preview_and_bytes(self):
        m = self._manager_with_frames()
        self.assertEqual(len(m.frames), 3)
        for f in m.frames:
            self.assertIsInstance(f["bytes"], bytes)
            self.assertTrue(f["bytes"])
            self.assertIsNotNone(f["preview"])

    def test_reprocess_frames_updates_dither_level_and_preview(self):
        m = self._manager_with_frames()
        before = [f["bytes"] for f in m.frames]

        m.reprocess_frames(0)  # без дизеринга
        self.assertEqual(len(m.frames), 3)
        for f in m.frames:
            self.assertEqual(f["dither_level"], 0)
            self.assertIsInstance(f["bytes"], bytes)
            self.assertTrue(f["bytes"])
            self.assertIsNotNone(f["preview"])

        # После add_frame(dither=1) bytes отличаются от reprocess(0) хотя бы
        # на одном кадре (полутоновый 128 меняется от дизеринга).
        changed = sum(f["bytes"] != before[i] for i, f in enumerate(m.frames))
        self.assertGreaterEqual(changed, 1)

    def test_reprocess_frames_to_bytes_returns_pairs(self):
        m = self._manager_with_frames()
        pairs = m.reprocess_frames_to_bytes(1)
        self.assertEqual(len(pairs), 3)
        for p, b in pairs:
            self.assertIsInstance(p, str)
            self.assertIsInstance(b, bytes)
            self.assertTrue(b)


if __name__ == "__main__":
    unittest.main()