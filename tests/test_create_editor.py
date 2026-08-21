"""Тесты для пиксельного редактора Create (ui/create_editor.py).

Проверяем алгоритмы кисти, фигур и onion skin без GUI-взаимодействия
(используется offscreen QApplication).
"""

import sys
import unittest

from PyQt6.QtWidgets import QApplication

from ui.create_editor import PixelCanvas


class TestPixelCanvasAlgorithms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        self.canvas = PixelCanvas(32, 32, cell=4)

    def test_brush_size_area(self):
        self.canvas.set_brush_size(3)
        self.canvas._stamp_brush(5, 5, 1)
        self.assertEqual(self.canvas.pixels[5][5], 1)
        self.assertEqual(self.canvas.pixels[4][4], 1)
        self.assertEqual(self.canvas.pixels[6][6], 1)
        # не должен выходить за пределы
        self.canvas._stamp_brush(0, 0, 1)
        self.assertEqual(self.canvas.pixels[0][0], 1)

    def test_brush_size_changed_signal(self):
        received = []
        self.canvas.brush_size_changed.connect(received.append)
        self.canvas.set_brush_size(4)
        self.assertEqual(received, [4])
        self.assertEqual(self.canvas.brush_size, 4)
        # повторная установка того же значения не эмитит
        self.canvas.set_brush_size(4)
        self.assertEqual(received, [4])

    def test_line_cells(self):
        cells = PixelCanvas._line_cells(1, 1, 5, 4)
        self.assertIn((1, 1), cells)
        self.assertIn((5, 4), cells)
        self.assertGreaterEqual(len(cells), 5)
        # диагональ 0..3 должна покрывать все точки
        diag = PixelCanvas._line_cells(0, 0, 3, 3)
        self.assertEqual(len(diag), 4)

    def test_rect_outline_and_fill(self):
        rect = self.canvas._rect_cells(2, 2, 6, 4, fill=False)
        self.assertEqual(len(rect), 2 * 5 + 2 * 1)  # верх/низ по 5 + бока по 1
        self.assertIn((2, 2), rect)
        self.assertIn((6, 4), rect)
        self.assertIn((2, 3), rect)
        self.assertNotIn((3, 3), rect)
        rect_f = self.canvas._rect_cells(2, 2, 6, 4, fill=True)
        self.assertEqual(len(rect_f), 5 * 3)
        self.assertIn((3, 3), rect_f)

    def test_square_rect(self):
        xa, ya, xb, yb = self.canvas._square_rect(2, 2, 7, 4)
        self.assertEqual(abs(xb - xa), 5)
        self.assertEqual(abs(yb - ya), 5)
        self.assertEqual((xa, ya), (2, 2))
        self.assertEqual((xb, yb), (7, 7))

    def test_ellipse_cells(self):
        circ = self.canvas._ellipse_cells(2, 2, 8, 8, fill=False)
        self.assertTrue(circ, "ellipse outline must not be empty")
        circ_f = self.canvas._ellipse_cells(2, 2, 8, 8, fill=True)
        self.assertIn((5, 5), circ_f)  # центр залит
        # вырожденный эллипс (0x0) даёт один пиксель
        degen = self.canvas._ellipse_cells(5, 5, 5, 5, fill=False)
        self.assertEqual(degen, [(5, 5)])
        # заливка не «теряет» макушку: верх/низ повторяют контур (см. отдельный тест)
        outline = self.canvas._ellipse_cells(4, 4, 20, 20, fill=False)
        fill_set = set(self.canvas._ellipse_cells(4, 4, 20, 20, fill=True))
        self.assertEqual(set(outline) - fill_set, set(),
                         "Контур круга не должен выходить за пределы заливки")

    def test_ellipse_outline_complete(self):
        """Контур не должен терять дуги сверху/снизу/слева/справа."""
        circ = self.canvas._ellipse_cells(10, 10, 50, 40, fill=False)
        xs = [p[0] for p in circ]
        ys = [p[1] for p in circ]
        midx = (min(xs) + max(xs)) // 2
        midy = (min(ys) + max(ys)) // 2
        self.assertIn((midx, min(ys)), circ)  # верхняя дуга
        self.assertIn((midx, max(ys)), circ)  # нижняя дуга
        self.assertIn((min(xs), midy), circ)  # левая дуга
        self.assertIn((max(xs), midy), circ)  # правая дуга

    def test_ellipse_flat_degenerates_to_line(self):
        hline = self.canvas._ellipse_cells(2, 5, 10, 5, fill=False)
        self.assertEqual(sorted(hline), [(x, 5) for x in range(2, 11)])
        vline = self.canvas._ellipse_cells(5, 2, 5, 10, fill=False)
        self.assertEqual(sorted(vline), [(5, y) for y in range(2, 11)])

    def test_batch_emits_once_and_syncs_frames(self):
        """Фигура применяется одним пакетом, кадр синхронизируется мгновенно."""
        from ui.create_editor import CreateEditorWidget

        w = CreateEditorWidget()
        canvas = w.canvas
        canvas.set_tool(canvas.TOOL_CIRCLE)
        canvas.set_fill_shapes(True)
        batches = []
        canvas.pixels_batch_changed.connect(lambda ch: batches.append(ch))
        canvas._shape_anchor = (10, 10)
        canvas._shape_cur = (40, 30)
        canvas._apply_shape()
        self.assertEqual(len(batches), 1)  # ровно один пакет
        self.assertGreater(len(batches[0]), 100)
        # кадр в редакторе совпал с холстом
        self.assertEqual(w.frames_pixels[0][20][25], canvas.pixels[20][25])
        self.assertEqual(w.frames_pixels[0][20][25], 1)  # (25,20) внутри круга

    def test_pencil_stroke_batches(self):
        """Штрих карандаша обновляет кадр одним пакетом, без драки сигналов."""
        from ui.create_editor import CreateEditorWidget

        w = CreateEditorWidget()
        canvas = w.canvas
        canvas.set_brush_size(4)
        batches = []
        canvas.pixels_batch_changed.connect(batches.append)
        canvas.begin_batch()
        canvas._paint_stroke(5, 5, 60, 40, 1)
        canvas.end_batch()
        self.assertEqual(len(batches), 1)
        self.assertGreaterEqual(len(batches[0]), 30)
        self.assertEqual(w.frames_pixels[0][5][5], 1)

    def test_triangle_cells(self):
        tri = self.canvas._triangle_cells(2, 8, 8, 8, fill=False)
        self.assertIn((2, 8), tri)
        self.assertIn((8, 8), tri)
        ax = (2 + 8) // 2
        ay = 8 - max(6, 1)
        self.assertIn((ax, ay), tri)
        tri_f = self.canvas._triangle_cells(2, 8, 8, 8, fill=True)
        self.assertGreaterEqual(len(tri_f), len(tri))

    def test_paint_stroke_continuous(self):
        self.canvas.set_brush_size(1)
        self.canvas._paint_stroke(3, 3, 20, 10, 1)
        self.assertEqual(self.canvas.pixels[3][3], 1)   # (x=3, y=3)
        self.assertEqual(self.canvas.pixels[10][20], 1)  # (x=20, y=10)
        painted = sum(sum(row) for row in self.canvas.pixels)
        self.assertGreaterEqual(painted, 18)  # длинная линия покрывает много клеток

    def test_apply_shape_one_action(self):
        self.canvas.set_tool(self.canvas.TOOL_RECT)
        self.canvas.set_fill_shapes(True)
        self.canvas._shape_anchor = (4, 4)
        self.canvas._shape_cur = (8, 8)
        finished = []
        self.canvas.painting_finished.connect(lambda: finished.append(1))
        self.canvas._apply_shape()
        self.assertEqual(self.canvas.pixels[4][4], 1)
        self.assertEqual(self.canvas.pixels[8][8], 1)
        self.assertEqual(self.canvas.pixels[6][6], 1)
        self.assertEqual(self.canvas.pixels[10][10], 0)
        self.assertEqual(finished, [1])

    def test_set_overlay(self):
        overlay = [[1 if x % 2 else 0 for x in range(32)] for _ in range(32)]
        self.canvas.set_overlay(overlay, True)
        self.assertTrue(self.canvas._show_overlay)
        self.assertIs(self.canvas._overlay_pixels, overlay)
        self.canvas.set_overlay(None, False)
        self.assertIsNone(self.canvas._overlay_pixels)
        self.assertFalse(self.canvas._show_overlay)

    def test_set_tool_validation(self):
        self.canvas.set_tool("bogus")
        self.assertEqual(self.canvas.tool, self.canvas.TOOL_PENCIL)
        received = []
        self.canvas.tool_changed.connect(received.append)
        self.canvas.set_tool(self.canvas.TOOL_CIRCLE)
        self.assertEqual(self.canvas.tool, self.canvas.TOOL_CIRCLE)
        self.assertEqual(received, [self.canvas.TOOL_CIRCLE])


    def test_ellipse_fill_matches_outline_apex(self):
        """Залитый круг: верх/низ повторяют контур (не схлопываются в точку)."""
        outline = self.canvas._ellipse_cells(4, 4, 20, 20, fill=False)
        fill = self.canvas._ellipse_cells(4, 4, 20, 20, fill=True)
        fill_set = set(fill)
        self.assertEqual(set(outline) - fill_set, set())
        top = sorted(x for x, y in outline if y == 4)
        bot = sorted(x for x, y in outline if y == 20)
        self.assertGreaterEqual(len(top), 3, "контур: макушка должна быть плоской")
        self.assertEqual(set(top), set(x for x, y in fill if y == 4),
                         "верхняя дуга заливки совпадает с контуром")
        self.assertEqual(set(bot), set(x for x, y in fill if y == 20),
                         "нижняя дуга заливки совпадает с контуром")

    def test_round_brush_excludes_corners(self):
        """Круглая кисть убирает углы, оставляя края и «плечи»."""
        self.canvas.set_brush_size(5)
        self.canvas.set_round_brush(True)
        self.canvas._stamp_brush(10, 10, 1)
        px = self.canvas.pixels
        self.assertEqual(px[10][10], 1)  # центр
        self.assertEqual(px[10][12], 1)  # правое ребро
        self.assertEqual(px[10][8], 1)   # левое ребро
        self.assertEqual(px[8][10], 1)   # верх
        for dy in (-2, 2):
            for dx in (-2, 2):
                self.assertEqual(px[10 + dy][10 + dx], 0, "углы круглой кисти пусты")

    def test_round_brush_fallback_square_for_small(self):
        """До диаметра 2 круглая кисть не отличается от квадратной."""
        self.canvas.set_brush_size(2)
        self.canvas.set_round_brush(True)
        self.canvas._stamp_brush(5, 5, 1)
        self.assertEqual(self.canvas.pixels[6][6], 1)

    def test_flood_fill_region(self):
        """«Ведро» заливает связную область, не выходя за «стены»."""
        self.canvas.pixels[5][5] = 1
        self.canvas.pixels[5][6] = 1
        self.canvas.pixels[6][5] = 1
        self.canvas.pixels[7][7] = 1  # изолированная клетка — не трогаем
        self.canvas._flood_fill(5, 4, 1)
        self.assertTrue(all(self.canvas.pixels[5][x] for x in range(5, 7)))
        self.assertEqual(self.canvas.pixels[7][7], 1)

    def test_flood_fill_noop_if_same(self):
        """Если цвет совпадает с целевым — изменений нет."""
        before = [row[:] for row in self.canvas.pixels]
        self.canvas._flood_fill(3, 3, 0)
        self.assertEqual(self.canvas.pixels, before)

    def test_flood_fill_erase_island(self):
        """value=0 (правая кнопка) стирает связный островок."""
        self.canvas.pixels[4][4] = 1
        self.canvas.pixels[4][5] = 1
        self.canvas.pixels[4][3] = 1
        self.canvas.pixels[9][9] = 1  # отдельный островок — сохраняется
        self.canvas._flood_fill(4, 4, 0)
        for x in (3, 4, 5):
            self.assertEqual(self.canvas.pixels[4][x], 0)
        self.assertEqual(self.canvas.pixels[9][9], 1)

    def test_round_brush_setter_and_bucket_tool_validation(self):
        self.canvas.set_round_brush(True)
        self.assertTrue(self.canvas.round_brush)
        received = []
        self.canvas.tool_changed.connect(received.append)
        self.canvas.set_tool(self.canvas.TOOL_BUCKET)
        self.assertEqual(self.canvas.tool, self.canvas.TOOL_BUCKET)
        self.assertEqual(received, [self.canvas.TOOL_BUCKET])
if __name__ == "__main__":
    unittest.main()
