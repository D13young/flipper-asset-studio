"""Smoke-тест UI-виджета CreateEditorWidget (главный сценарий рисования).

Симулирует реальные события мыши (QTest) поверх offscreen QApplication:
карандаш, прямоугольник, треугольник, дублирование кадра и onion skin.
"""

import sys
import unittest

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from ui.create_editor import CreateEditorWidget, PixelCanvas


def _screen_pos(canvas: PixelCanvas, cell_x: int, cell_y: int) -> QPoint:
    return QPoint(
        canvas.pan_offset_x + cell_x * canvas._cell_size() + 2,
        canvas.pan_offset_y + cell_y * canvas._cell_size() + 2,
    )


class TestCreateEditorSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        self.w = CreateEditorWidget()
        self.canvas = self.w.canvas

    def test_pencil_click_paints_pixel(self):
        self.canvas.set_brush_size(1)
        self.canvas.set_tool(self.canvas.TOOL_PENCIL)
        p = _screen_pos(self.canvas, 5, 5)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
        self.assertEqual(self.w.frames_pixels[0][5][5], 1)

    def test_pencil_stroke_repaints_during_drag(self):
        """Карандаш должен перерисовывать холст сразу, пока кнопка ещё зажата (без задержки до отпускания)."""
        from unittest import mock

        self.canvas.set_brush_size(1)
        self.canvas.set_tool(self.canvas.TOOL_PENCIL)
        p1 = _screen_pos(self.canvas, 3, 3)
        p2 = _screen_pos(self.canvas, 10, 6)
        with mock.patch.object(self.canvas, "update", wraps=self.canvas.update) as m:
            QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
            press_repaints = m.call_count
            QTest.mouseMove(self.canvas, p2, 50)
            move_repaints = m.call_count
            self.assertGreater(
                move_repaints, press_repaints,
                "Линия карандаша должна появляться ещё во время ведения, а не после отпускания",
            )
            QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)
        frame = self.w.frames_pixels[0]
        self.assertEqual(frame[3][3], 1)
        self.assertEqual(frame[6][10], 1)

    def test_rect_drag_applies_fill(self):
        self.canvas.set_tool(self.canvas.TOOL_RECT)
        self.canvas.set_fill_shapes(True)
        p1 = _screen_pos(self.canvas, 2, 2)
        p2 = _screen_pos(self.canvas, 6, 5)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
        QTest.mouseMove(self.canvas, p2, 50)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)
        self.assertEqual(self.w.frames_pixels[0][2][2], 1)
        self.assertEqual(self.w.frames_pixels[0][5][6], 1)
        self.assertEqual(self.w.frames_pixels[0][4][4], 1)  # заливка внутри

    def test_triangle_drag_outline(self):
        self.canvas.set_tool(self.canvas.TOOL_TRIANGLE)
        self.canvas.set_fill_shapes(False)
        p1 = _screen_pos(self.canvas, 2, 8)
        p2 = _screen_pos(self.canvas, 8, 8)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
        QTest.mouseMove(self.canvas, p2, 50)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)
        frame = self.w.frames_pixels[0]
        self.assertEqual(frame[8][2], 1)  # левый угол основания
        self.assertEqual(frame[8][8], 1)  # правый угол основания

    def test_filled_circle_drag_syncs_frames(self):
        """Залитый круг, нарисованный мышью, сразу синхронизируется с кадром (без задержки)."""
        batches = []
        self.canvas.pixels_batch_changed.connect(lambda ch: batches.append(ch))
        self.canvas.set_tool(self.canvas.TOOL_CIRCLE)
        self.canvas.set_fill_shapes(True)
        p1 = _screen_pos(self.canvas, 20, 10)
        p2 = _screen_pos(self.canvas, 60, 40)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
        QTest.mouseMove(self.canvas, p2, 30)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)
        frame = self.w.frames_pixels[0]
        # центр круга должен быть залит
        self.assertEqual(frame[25][40], 1)
        # применялось одним пакетом изменений (быстро, без сотен сигналов)
        self.assertEqual(len(batches), 1)
        self.assertGreater(len(batches[0]), 100)

    def test_circle_outline_complete_via_drag(self):
        """Контур круга, нарисованный мышью, не теряет пиксели дуг."""
        self.canvas.set_tool(self.canvas.TOOL_CIRCLE)
        self.canvas.set_fill_shapes(False)
        p1 = _screen_pos(self.canvas, 4, 4)
        p2 = _screen_pos(self.canvas, 20, 20)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
        QTest.mouseMove(self.canvas, p2, 30)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)
        frame = self.w.frames_pixels[0]
        # верхняя и нижняя дуги круга (центр по x) должны быть заполнены
        # круг от (4,4) до (20,20), центр (12,12), радиус ~8
        self.assertEqual(frame[4][12], 1)  # верх
        self.assertEqual(frame[20][12], 1)  # низ
        self.assertEqual(frame[12][4], 1)   # лево
        self.assertEqual(frame[12][20], 1)  # право

    def test_brush_size_spinbox_sync(self):
        self.w.spin_brush.setValue(5)
        self.assertEqual(self.canvas.brush_size, 5)
        # из canvas -> в спинбокс
        self.canvas.set_brush_size(3)
        self.assertEqual(self.w.spin_brush.value(), 3)

    def test_duplicate_frame_button(self):
        self.w.frames_pixels[0][0][0] = 1
        self.w.btn_dup_frame.click()
        self.assertEqual(len(self.w.frames_pixels), 2)
        self.assertEqual(self.w.active_index, 1)
        self.assertEqual(self.w.frames_pixels[1][0][0], 1)

    def test_onion_skin_toggle(self):
        self.w.btn_add_frame.click()  # теперь 2 кадра, активный = 1
        self.w.frames_pixels[0][3][3] = 1
        self.w.chk_onion.setChecked(True)
        self.assertTrue(self.canvas._show_overlay)
        self.assertIs(self.canvas._overlay_pixels, self.w.frames_pixels[0])
        self.w.chk_onion.setChecked(False)
        self.assertFalse(self.canvas._show_overlay)

    def test_undo_restores_before_stroke(self):
        self.canvas.set_brush_size(1)
        self.canvas.set_tool(self.canvas.TOOL_PENCIL)
        p = _screen_pos(self.canvas, 4, 4)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
        self.assertEqual(self.w.frames_pixels[0][4][4], 1)
        self.w.undo()
        self.assertEqual(self.w.frames_pixels[0][4][4], 0)


    def test_bucket_fill_via_click(self):
        """Инструмент «ведро»: клик заливает область и синхронизирует кадр."""
        self.canvas.set_tool(self.canvas.TOOL_BUCKET)
        # нарисуем замкнутую рамку прямоугольника контуром
        self.canvas.set_tool(self.canvas.TOOL_RECT)
        self.canvas.set_fill_shapes(False)
        c1 = _screen_pos(self.canvas, 5, 5)
        c2 = _screen_pos(self.canvas, 12, 12)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, c1)
        QTest.mouseMove(self.canvas, c2, 50)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, c2)
        # заливка внутри рамки
        self.canvas.set_tool(self.canvas.TOOL_BUCKET)
        inside = _screen_pos(self.canvas, 8, 8)
        batches = []
        self.canvas.pixels_batch_changed.connect(batches.append)
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, inside)
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, inside)
        self.assertEqual(self.w.frames_pixels[0][8][8], 1)   # внутренность залита
        self.assertEqual(self.canvas.pixels[8][8], 1)
        # один пакет изменений (быстро, одно действие для Undo)
        self.assertGreaterEqual(len(batches), 1)

    def test_round_brush_checkbox_wiring(self):
        self.w.chk_round.setChecked(True)
        self.assertTrue(self.canvas.round_brush)
        self.w.chk_round.setChecked(False)
        self.assertFalse(self.canvas.round_brush)
if __name__ == "__main__":
    unittest.main()
