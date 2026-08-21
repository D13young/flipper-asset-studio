"""Тесты для GIF → PNG (кадрирование) — регрессия на баг с уменьшенным превью.

Баг: CropPreviewWidget хранила рамку crop в координатах УМЕНЬШЕННОГО превью
(GIF-превью сжимается до <=640 px), а при экспорте координаты применялись
к ПОЛНОРАЗМЕРНОМУ кадру. Итог: «вырезался только верхний левый угол» исходника.

Фикс: виджету задаётся реальный размер исходника (set_source_size), и рамка
всегда хранится/выдаётся в координатах исходника.
"""

import io
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from PyQt6.QtWidgets import QApplication

from core.image_processor import FlipperImageProcessor
from ui.gif_crop_editor import _pil_to_preview_pixmap
from ui.jpg_crop_editor import CropPreviewWidget


def _make_horiz_bands(size, colors):
    """Картинка с горизонтальными полосами (для контроля вертикальной обрезки)."""
    w, h = size
    img = Image.new("RGBA", (w, h), colors[0])
    band_h = h // len(colors)
    for i, color in enumerate(colors[1:], start=1):
        band = Image.new("RGBA", (w, h), color)
        img.paste(band, (0, i * band_h))
    return img


def _make_gif(frame):
    buf = io.BytesIO()
    frame.save(buf, format="GIF", save_all=True, loop=0)
    buf.seek(0)
    return buf


class TestGifCropSourceSize(unittest.TestCase):
    """Рамка crop должна работать в координатах полноразмерного кадра."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def test_crop_rect_is_in_full_source_coords(self):
        src_w, src_h = 2000, 1500  # заметно больше превью (<=640)
        frame = _make_horiz_bands(
            (src_w, src_h), [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
        )

        preview = _pil_to_preview_pixmap(frame)
        self.assertLess(preview.width(), src_w)
        self.assertLess(preview.height(), src_h)

        w = CropPreviewWidget(empty_hint="")
        w.set_output_size(128, 64)      # ratio = 2.0
        w.set_pixmap(preview, reset_crop=True)
        w.set_source_size(src_w, src_h)  # ключевая часть фикса

        left, top, right, bottom = w.get_crop_rect_in_source()

        # 2000/1500 < 2.0  =>  рамка = 2000x1000 по центру по вертикали
        self.assertEqual((left, top), (0, 250))
        self.assertEqual((right, bottom), (2000, 1250))

    def test_export_crops_center_not_corner(self):
        """Без фикса экспорт резал бы только верхний левый угол (красная полоса)."""
        src_w, src_h = 2000, 1500
        frame = _make_horiz_bands(
            (src_w, src_h), [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
        )

        # Воспроизводим путь GIF-редактора: превью уменьшено, источник задан явно.
        preview = _pil_to_preview_pixmap(frame)
        w = CropPreviewWidget(empty_hint="")
        w.set_output_size(128, 64)
        w.set_pixmap(preview, reset_crop=True)
        w.set_source_size(src_w, src_h)
        crop = w.get_crop_rect_in_source()

        gif_buf = _make_gif(frame)
        with tempfile.TemporaryDirectory() as td:
            gif_path = Path(td) / "test.gif"
            gif_path.write_bytes(gif_buf.getvalue())
            out_dir = Path(td) / "out"
            saved = FlipperImageProcessor.export_gif_frames_custom_crop_to_png(
                input_path=str(gif_path),
                output_dir=str(out_dir),
                output_w=128,
                output_h=64,
                crop_left=crop[0],
                crop_top=crop[1],
                crop_right=crop[2],
                crop_bottom=crop[3],
            )

            with Image.open(saved[0]).convert("RGB") as out:
                top_px = out.getpixel((64, 0))      # верх = верх центральной полосы (красный)
                mid_px = out.getpixel((64, 32))     # середина = зелёный
                bottom_px = out.getpixel((64, 63))  # низ = синий

        self.assertEqual(top_px, (255, 0, 0))
        self.assertEqual(mid_px, (0, 255, 0))
        self.assertEqual(bottom_px, (0, 0, 255))


if __name__ == "__main__":
    unittest.main()