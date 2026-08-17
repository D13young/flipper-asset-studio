"""Тесты FlipperAnimationManager (T5) без GUI-части."""
import unittest

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


if __name__ == "__main__":
    unittest.main()