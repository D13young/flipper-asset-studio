"""Регрессионный тест РЕНДЕРА превью (QImage/QPixmap, offscreen).

Покрывает исправление: превью 46x49 через bytes_to_preview больше не даёт
«вертикальные полосы» / сдвиг строк (явный bytesPerLine в QImage).

Требуется QGuiApplication; при недоступности дисплея тест пропускается.
"""
import os
import sys
import unittest

import numpy as np
from PIL import Image

# GUI-тесты гоняем в offscreen-режиме, чтобы не зависеть от дисплея.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage

from core.image_processor import FlipperImageProcessor as IP


def _qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class PreviewRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.app = _qapp()
        except Exception as e:  # pragma: no cover
            raise unittest.SkipTest(f"QApplication недоступен: {e}")

    def _render(self, w, h, seed):
        rng = np.random.default_rng(seed)
        arr = (rng.random((h, w)) > 0.5).astype(np.uint8)  # white=1
        fb = IP.pack_to_flipper_bytes(
            Image.fromarray((arr * 255).astype(np.uint8), mode="L"),
            output_w=w, output_h=h,
        )
        pm = IP.bytes_to_preview(fb, width=w, height=h, scale=1)
        qi = pm.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
        buf = qi.bits()
        buf.setsize(qi.height() * qi.bytesPerLine())
        got = np.frombuffer(buf, dtype=np.uint8).reshape(qi.height(), qi.bytesPerLine())[:, :w]
        return pm, (got > 127).astype(np.uint8), arr

    def test_render_46x49_pixel_exact(self):
        pm, got, arr = self._render(46, 49, 1)
        self.assertEqual((pm.width(), pm.height()), (46, 49))
        self.assertEqual(int((got != arr).sum()), 0,
                         "превью 46x49 не должно давать полос/сдвига строк")

    def test_render_128x64_pixel_exact(self):
        pm, got, arr = self._render(128, 64, 2)
        self.assertEqual((pm.width(), pm.height()), (128, 64))
        self.assertEqual(int((got != arr).sum()), 0)


if __name__ == "__main__":
    unittest.main()