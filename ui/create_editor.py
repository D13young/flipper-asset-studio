from __future__ import annotations

import copy
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QImage, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QSizePolicy,
    QSplitter,
)

from ui.i18n import tr, trf

class PixelCanvas(QWidget):
    pixel_changed = pyqtSignal(int, int, int)
    pixels_batch_changed = pyqtSignal(list)
    painting_finished = pyqtSignal()
    painting_started = pyqtSignal()
    brush_size_changed = pyqtSignal(int)
    tool_changed = pyqtSignal(str)

    # Инструменты рисования
    TOOL_PENCIL = "pencil"
    TOOL_LINE = "line"
    TOOL_RECT = "rect"
    TOOL_SQUARE = "square"
    TOOL_CIRCLE = "circle"
    TOOL_TRIANGLE = "triangle"
    TOOL_BUCKET = "bucket"

    def __init__(self, width_px: int = 128, height_px: int = 64, cell: int = 5, parent: QWidget | None = None):
        super().__init__(parent)
        self.cell = int(cell)
        self.width_px = int(width_px)
        self.height_px = int(height_px)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.pixels: list[list[int]] = [[0 for _ in range(self.width_px)] for _ in range(self.height_px)]

        # zoom in [min_zoom..max_zoom]
        self.zoom_level = 1
        self.min_zoom = 1
        self.max_zoom = 6

        # pan в screen-пикселях (int) для стабильного рендера
        self.pan_offset_x: int = 0
        self.pan_offset_y: int = 0

        self._panning = False
        self._pan_last_pos = None

        self._hover_x: int | None = None
        self._hover_y: int | None = None

        self._painting = False
        self._paint_mode = 1

        self._is_space_held = False  # панорамирование через пробел

        # Кисть и инструменты
        self.brush_size: int = 1
        self.tool: str = self.TOOL_PENCIL
        self.fill_shapes: bool = False
        # Круглая форма кисти (true) вместо квадратной
        self.round_brush: bool = False

        # Перетаскивание фигуры / непрерывный штрих
        self._shape_anchor: tuple[int, int] | None = None
        self._shape_cur: tuple[int, int] | None = None
        self._last_painted: tuple[int, int] | None = None
        # Пакетное накопление изменений (одно обновление кадра за действие)
        self._batch_changes: list[tuple[int, int, int]] | None = None

        # Onion skin: полупрозрачный предыдущий кадр под текущим
        self._overlay_pixels: list[list[int]] | None = None
        self._show_overlay: bool = False

        self._apply_geometry_limits()

    def _apply_geometry_limits(self):
        self.updateGeometry()
        self.setMinimumSize(self.width_px * self.cell, self.height_px * self.cell)

    def set_canvas_size(self, width_px: int, height_px: int):
        width_px = int(width_px)
        height_px = int(height_px)
        if width_px <= 0 or height_px <= 0:
            return

        self.width_px = width_px
        self.height_px = height_px
        self.pixels = [[0 for _ in range(self.width_px)] for _ in range(self.height_px)]
        self._clamp_pan_offset()
        self.update()

    def set_pixels(self, pixels: list[list[int]]):
        if len(pixels) != self.height_px:
            raise ValueError("Invalid height")
        for y in range(self.height_px):
            if len(pixels[y]) != self.width_px:
                raise ValueError("Invalid width")

        self.pixels = [[1 if pixels[y][x] else 0 for x in range(self.width_px)] for y in range(self.height_px)]
        self.update()

    def _cell_size(self) -> int:
        return max(1, self.cell * self.zoom_level)

    def _clamp_pan_offset(self):
        """Не дает утащить холст полностью за пределы видимой области."""
        cell_px = self._cell_size()
        w_total = self.width_px * cell_px
        h_total = self.height_px * cell_px

        if w_total < self.width():
            self.pan_offset_x = (self.width() - w_total) // 2
        else:
            self.pan_offset_x = max(self.width() - w_total, min(0, self.pan_offset_x))

        if h_total < self.height():
            self.pan_offset_y = (self.height() - h_total) // 2
        else:
            self.pan_offset_y = max(self.height() - h_total, min(0, self.pan_offset_y))

    def _draw_checkerboard(self, painter: QPainter, cell_px: int):
        painter.setPen(Qt.PenStyle.NoPen)
        color1 = QColor(30, 30, 30)
        color2 = QColor(45, 45, 45)

        x0 = self.pan_offset_x
        y0 = self.pan_offset_y

        start_x = max(0, (-x0) // cell_px)
        start_y = max(0, (-y0) // cell_px)
        end_x = min(self.width_px, (self.width() - x0 + cell_px - 1) // cell_px)
        end_y = min(self.height_px, (self.height() - y0 + cell_px - 1) // cell_px)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                painter.setBrush(color1 if (x + y) % 2 == 0 else color2)
                painter.drawRect(x0 + x * cell_px, y0 + y * cell_px, cell_px, cell_px)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        cell_px = self._cell_size()
        w_total = self.width_px * cell_px
        h_total = self.height_px * cell_px

        # 1) фон
        self._draw_checkerboard(painter, cell_px)

        # 2) culling видимой области
        start_x = max(0, (-self.pan_offset_x) // cell_px)
        start_y = max(0, (-self.pan_offset_y) // cell_px)
        end_x = min(self.width_px, (self.width() - self.pan_offset_x + cell_px - 1) // cell_px)
        end_y = min(self.height_px, (self.height() - self.pan_offset_y + cell_px - 1) // cell_px)

        # 2b) onion skin: полупрозрачный предыдущий кадр (не экспортируется)
        if self._show_overlay and self._overlay_pixels is not None:
            ghost_color = QColor(90, 200, 130, 90)
            for y in range(start_y, end_y):
                row = self._overlay_pixels[y]
                for x in range(start_x, end_x):
                    if row[x]:
                        px = self.pan_offset_x + x * cell_px
                        py = self.pan_offset_y + y * cell_px
                        painter.fillRect(px, py, cell_px, cell_px, ghost_color)

        # 3) пиксели
        on_color = QColor(230, 230, 230)
        for y in range(start_y, end_y):
            row = self.pixels[y]
            for x in range(start_x, end_x):
                if row[x]:
                    px = self.pan_offset_x + x * cell_px
                    py = self.pan_offset_y + y * cell_px
                    painter.fillRect(px, py, cell_px, cell_px, on_color)

        # 4) hover подсветка
        if self._hover_x is not None and self._hover_y is not None:
            if start_x <= self._hover_x < end_x and start_y <= self._hover_y < end_y:
                hx = self.pan_offset_x + self._hover_x * cell_px
                hy = self.pan_offset_y + self._hover_y * cell_px
                painter.setPen(QColor(137, 180, 250))
                painter.drawRect(hx, hy, cell_px - 1, cell_px - 1)

        # 4b) превью-курсор кисти (показывает реальный размер)
        if (not self._painting) and self.tool == self.TOOL_PENCIL and self._hover_x is not None and self._hover_y is not None:
            if start_x <= self._hover_x < end_x and start_y <= self._hover_y < end_y:
                n = self.brush_size
                canvas_x0 = self.pan_offset_x
                canvas_y0 = self.pan_offset_y
                canvas_x1 = canvas_x0 + self.width_px * cell_px
                canvas_y1 = canvas_y0 + self.height_px * cell_px
                bx0 = max(canvas_x0, min(canvas_x1, canvas_x0 + (self._hover_x - (n - 1) // 2) * cell_px))
                by0 = max(canvas_y0, min(canvas_y1, canvas_y0 + (self._hover_y - (n - 1) // 2) * cell_px))
                bx1 = max(canvas_x0, min(canvas_x1, canvas_x0 + (self._hover_x - (n - 1) // 2 + n) * cell_px))
                by1 = max(canvas_y0, min(canvas_y1, canvas_y0 + (self._hover_y - (n - 1) // 2 + n) * cell_px))
                if bx1 > bx0 and by1 > by0:
                    painter.setPen(QColor(137, 180, 250))
                    if self.round_brush:
                        painter.drawEllipse(bx0, by0, bx1 - bx0, by1 - by0)
                    else:
                        painter.drawRect(bx0, by0, bx1 - bx0 - 1, by1 - by0 - 1)

        # 4c) предпросмотр фигуры (rubber band) при перетаскивании
        if self._painting and self.tool not in (self.TOOL_PENCIL, self.TOOL_BUCKET) and self._shape_anchor is not None and self._shape_cur is not None:
            x0, y0 = self._shape_anchor
            x1, y1 = self._shape_cur
            # живая полупрозрачная заливка (для очень больших фигур — только контур, чтобы не тормозить drag)
            if self.fill_shapes:
                area = abs(x1 - x0 + 1) * abs(y1 - y0 + 1)
                if area <= 8000:
                    fill_color = QColor(0, 200, 255, 60)
                    for cx, cy in self._shape_cells(self.tool, x0, y0, x1, y1, fill=True):
                        if start_x <= cx < end_x and start_y <= cy < end_y:
                            painter.fillRect(self.pan_offset_x + cx * cell_px, self.pan_offset_y + cy * cell_px, cell_px, cell_px, fill_color)
            preview_color = QColor(0, 200, 255)
            for cx, cy in self._shape_cells(self.tool, x0, y0, x1, y1, fill=False):
                if start_x <= cx < end_x and start_y <= cy < end_y:
                    painter.fillRect(self.pan_offset_x + cx * cell_px, self.pan_offset_y + cy * cell_px, cell_px, cell_px, preview_color)

        # 5) сетка в видимой области
        painter.setPen(QColor(40, 40, 40))
        x0 = self.pan_offset_x
        y0 = self.pan_offset_y

        for x in range(start_x, end_x + 1):
            gx = x0 + x * cell_px
            painter.drawLine(gx, y0 + start_y * cell_px, gx, y0 + end_y * cell_px)

        for y in range(start_y, end_y + 1):
            gy = y0 + y * cell_px
            painter.drawLine(x0 + start_x * cell_px, gy, x0 + end_x * cell_px, gy)

        # 6) граница холста
        painter.setPen(QColor(100, 100, 100))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(x0, y0, w_total, h_total)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._is_space_held = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._is_space_held = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def _pos_to_cell(self, pos_x: int, pos_y: int):
        cell_px = self._cell_size()
        x = (pos_x - self.pan_offset_x) // cell_px
        y = (pos_y - self.pan_offset_y) // cell_px
        if x < 0 or y < 0 or x >= self.width_px or y >= self.height_px:
            return None
        return int(x), int(y)

    def _set_pixel(self, x: int, y: int, value: int):
        """Устанавливает пиксель. В режиме пакета изменения копятся и эмитятся разом."""
        if 0 <= x < self.width_px and 0 <= y < self.height_px:
            v = 1 if value else 0
            if self.pixels[y][x] != v:
                self.pixels[y][x] = v
                if self._batch_changes is not None:
                    self._batch_changes.append((x, y, v))
                else:
                    self.pixel_changed.emit(x, y, v)

    def begin_batch(self):
        """Начинает пакет изменений: пиксели меняются без побочных сигналов."""
        self._batch_changes = []

    def end_batch(self):
        """Завершает пакет и эмитит pixels_batch_changed один раз."""
        changes = self._batch_changes
        self._batch_changes = None
        if changes:
            self.pixels_batch_changed.emit(changes)

    def _stamp_brush(self, x: int, y: int, value: int):
        """Закрашивает область brush_size×brush_size с центром в точке.

        При включённой круглой кисти (self.round_brush) штамп — круглый:
        клетки, попадающие внутрь круга радиуса size/2 от центра клетки.
        """
        n = self.brush_size
        x0 = x - (n - 1) // 2
        y0 = y - (n - 1) // 2
        if not self.round_brush or n <= 2:
            for yy in range(y0, y0 + n):
                for xx in range(x0, x0 + n):
                    self._set_pixel(xx, yy, value)
            return
        cxp = x + 0.5
        cyp = y + 0.5
        r2 = (n / 2.0) ** 2
        for yy in range(y0, y0 + n):
            for xx in range(x0, x0 + n):
                dx = (xx + 0.5) - cxp
                dy = (yy + 0.5) - cyp
                if dx * dx + dy * dy <= r2:
                    self._set_pixel(xx, yy, value)

    def _flood_fill(self, x0: int, y0: int, value: int):
        """Заливка области («ведро»/flood fill) по 4-связности.

        Заливает связную область того же цвета, что и стартовая клетка,
        цветом value. Если стартовая клетка уже нужного цвета — нет-оп.
        Вызывается внутри begin_batch()/end_batch() (одно действие Undo).
        """
        if x0 < 0 or y0 < 0 or x0 >= self.width_px or y0 >= self.height_px:
            return
        target = self.pixels[y0][x0]
        if target == value:
            return
        w, h = self.width_px, self.height_px
        stack: list[tuple[int, int]] = [(x0, y0)]
        while stack:
            x, y = stack.pop()
            if not (0 <= x < w and 0 <= y < h):
                continue
            if self.pixels[y][x] != target:
                continue
            self._set_pixel(x, y, value)
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))

    @staticmethod
    def _line_cells(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
        """Ячейки отрезка по алгоритму Брезенхэма."""
        cells: list[tuple[int, int]] = []
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            cells.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return cells

    def _rect_cells(self, x0: int, y0: int, x1: int, y1: int, fill: bool) -> list[tuple[int, int]]:
        xa, xb = (x0, x1) if x0 <= x1 else (x1, x0)
        ya, yb = (y0, y1) if y0 <= y1 else (y1, y0)
        cells: list[tuple[int, int]] = []
        if fill:
            for y in range(ya, yb + 1):
                for x in range(xa, xb + 1):
                    cells.append((x, y))
        else:
            for x in range(xa, xb + 1):
                cells.append((x, ya))
                cells.append((x, yb))
            for y in range(ya + 1, yb):
                cells.append((xa, y))
                cells.append((xb, y))
        return cells

    def _square_rect(self, x0: int, y0: int, x1: int, y1: int) -> tuple[int, int, int, int]:
        """Приводит прямоугольник к квадрату по направлению перетаскивания."""
        sx = 1 if x1 >= x0 else -1
        sy = 1 if y1 >= y0 else -1
        size = max(abs(x1 - x0), abs(y1 - y0), 1)
        return x0, y0, x0 + sx * size, y0 + sy * size

    def _ellipse_cells(self, x0: int, y0: int, x1: int, y1: int, fill: bool) -> list[tuple[int, int]]:
        """Эллипс/круг, вписанный в прямоугольник перетаскивания.

        Контур строится двумя проходами (границы по строкам и по столбцам),
        чтобы дуги сверху/снизу не теряли пиксели.

        Заливка ограничивается ЭТИМ ЖЕ контуром по строкам: верхний/нижний
        ряд залитого круга повторяет дуги превью (а не «схлопывается» в точку).
        Вырожденные эллипсы — линия.
        """
        xa, xb = (x0, x1) if x0 <= x1 else (x1, x0)
        ya, yb = (y0, y1) if y0 <= y1 else (y1, y0)
        cx = (xa + xb) / 2.0
        cy = (ya + yb) / 2.0
        rx = (xb - xa) / 2.0
        ry = (yb - ya) / 2.0
        cells: list[tuple[int, int]] = []

        if rx < 0.5 and ry < 0.5:
            cells.append((int(round(cx)), int(round(cy))))
            return cells
        if rx < 0.5:  # вырожденный по ширине → вертикальная линия
            for y in range(ya, yb + 1):
                cells.append((int(round(cx)), y))
            return cells
        if ry < 0.5:  # вырожденный по высоте → горизонтальная линия
            for x in range(xa, xb + 1):
                cells.append((x, int(round(cy))))
            return cells

        # Контур: лево/право по строкам + верх/низ по столбцам (без дублей)
        outline: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for y in range(ya, yb + 1):
            t = min(1.0, max(-1.0, (y - cy) / ry))
            span = rx * (1.0 - t * t) ** 0.5
            for x in (int(round(cx - span)), int(round(cx + span))):
                p = (x, y)
                if p not in seen:
                    seen.add(p)
                    outline.append(p)
        for x in range(xa, xb + 1):
            t = min(1.0, max(-1.0, (x - cx) / rx))
            span = ry * (1.0 - t * t) ** 0.5
            for y in (int(round(cy - span)), int(round(cy + span))):
                p = (x, y)
                if p not in seen:
                    seen.add(p)
                    outline.append(p)

        if not fill:
            return outline

        # Заливка ограничивается контуром по СТРОКАМ: верх/низ повторяют дуги
        # превью, а не «схлопываются» в одну точку на крайних рядах.
        row_lo: dict[int, int] = {}
        row_hi: dict[int, int] = {}
        for (x, y) in outline:
            prev = row_lo.get(y)
            if prev is None or x < prev:
                row_lo[y] = x
            prev = row_hi.get(y)
            if prev is None or x > prev:
                row_hi[y] = x
        for y in range(ya, yb + 1):
            xl = row_lo.get(y)
            if xl is None:
                continue
            xr = row_hi[y]
            for x in range(xl, xr + 1):
                cells.append((x, y))
        return cells

    def _fill_polygon_cells(self, pts: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Scanline-заливка многоугольника."""
        cells: list[tuple[int, int]] = []
        ys = [p[1] for p in pts]
        min_y, max_y = min(ys), max(ys)
        for y in range(min_y, max_y + 1):
            xs: list[float] = []
            for i in range(len(pts)):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                if y1 == y2:
                    continue
                if (y1 <= y < y2) or (y2 <= y < y1):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
            if not xs:
                continue
            xs.sort()
            xl = int(round(xs[0]))
            xr = int(round(xs[-1]))
            for x in range(xl, xr + 1):
                cells.append((x, y))
        return cells

    def _triangle_cells(self, x0: int, y0: int, x1: int, y1: int, fill: bool) -> list[tuple[int, int]]:
        """Равнобедренный треугольник: основание = перетаскивание, вершина по центру сверху."""
        ax = (x0 + x1) // 2
        ay = min(y0, y1) - max(abs(x1 - x0), 1)
        pts = [(x0, y0), (x1, y1), (ax, ay)]
        if fill:
            return self._fill_polygon_cells(pts)
        cells: list[tuple[int, int]] = []
        for i in range(3):
            cells.extend(self._line_cells(pts[i][0], pts[i][1], pts[(i + 1) % 3][0], pts[(i + 1) % 3][1]))
        return cells

    def _shape_cells(self, tool: str, x0: int, y0: int, x1: int, y1: int, fill: bool) -> list[tuple[int, int]]:
        if tool == self.TOOL_LINE:
            return self._line_cells(x0, y0, x1, y1)
        if tool == self.TOOL_RECT:
            return self._rect_cells(x0, y0, x1, y1, fill)
        if tool == self.TOOL_SQUARE:
            xa, ya, xb, yb = self._square_rect(x0, y0, x1, y1)
            return self._rect_cells(xa, ya, xb, yb, fill)
        if tool == self.TOOL_CIRCLE:
            return self._ellipse_cells(x0, y0, x1, y1, fill)
        if tool == self.TOOL_TRIANGLE:
            return self._triangle_cells(x0, y0, x1, y1, fill)
        return []

    def _paint_stroke(self, x0: int, y0: int, x1: int, y1: int, value: int):
        """Непрерывный штрих: кисть «протаскивается» по отрезку Брезенхэма."""
        for cx, cy in self._line_cells(x0, y0, x1, y1):
            self._stamp_brush(cx, cy, value)

    def _apply_shape(self):
        """Запечатывает нарисованную фигуру в пиксели кадра (одно действие для Undo)."""
        if self._shape_anchor is None or self._shape_cur is None:
            return
        x0, y0 = self._shape_anchor
        x1, y1 = self._shape_cur
        self.begin_batch()
        for cx, cy in self._shape_cells(self.tool, x0, y0, x1, y1, self.fill_shapes):
            self._set_pixel(cx, cy, self._paint_mode)
        self.end_batch()
        self.update()
        self.painting_finished.emit()

    # ── Настройка инструментов (вызывается из родительского виджета) ──
    def set_brush_size(self, size: int):
        size = max(1, min(int(size), 16))
        if size == self.brush_size:
            return
        self.brush_size = size
        self.brush_size_changed.emit(size)
        self.update()

    def set_tool(self, tool: str):
        if tool not in (self.TOOL_PENCIL, self.TOOL_LINE, self.TOOL_RECT,
                        self.TOOL_SQUARE, self.TOOL_CIRCLE, self.TOOL_TRIANGLE,
                        self.TOOL_BUCKET):
            return
        if tool == self.tool:
            return
        self.tool = tool
        self._shape_anchor = None
        self._shape_cur = None
        self.tool_changed.emit(tool)
        self.update()

    def set_fill_shapes(self, fill: bool):
        self.fill_shapes = bool(fill)
        self.update()

    def set_round_brush(self, round_brush: bool):
        """Включает/выключает круглую форму кисти (вместо квадратной)."""
        self.round_brush = bool(round_brush)
        self.update()

    def set_overlay(self, pixels: list[list[int]] | None, visible: bool = True):
        """Устанавливает полупрозрачный «призрак» предыдущего кадра (onion skin)."""
        self._overlay_pixels = pixels
        self._show_overlay = bool(visible)
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Space:
            self._is_space_held = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        if key == Qt.Key.Key_BracketLeft:
            self.set_brush_size(self.brush_size - 1)
            event.accept()
            return
        if key == Qt.Key.Key_BracketRight:
            self.set_brush_size(self.brush_size + 1)
            event.accept()
            return
        tool_by_key = {
            Qt.Key.Key_B: self.TOOL_PENCIL,
            Qt.Key.Key_L: self.TOOL_LINE,
            Qt.Key.Key_R: self.TOOL_RECT,
            Qt.Key.Key_Q: self.TOOL_SQUARE,
            Qt.Key.Key_C: self.TOOL_CIRCLE,
            Qt.Key.Key_T: self.TOOL_TRIANGLE,
            Qt.Key.Key_F: self.TOOL_BUCKET,
        }
        if key in tool_by_key:
            self.set_tool(tool_by_key[key])
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._is_space_held = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        is_pan = event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self._is_space_held)
        
        if is_pan:
            self._panning = True
            self._pan_last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return

        p = event.position()
        cell = self._pos_to_cell(int(p.x()), int(p.y()))
        if cell is None:
            return

        self._painting = True
        self._paint_mode = 1 if event.button() == Qt.MouseButton.LeftButton else 0

        x, y = cell
        self._shape_anchor = (x, y)
        self._shape_cur = (x, y)
        self._last_painted = (x, y)
        self.painting_started.emit()

        if self.tool == self.TOOL_PENCIL:
            self.begin_batch()
            self._stamp_brush(x, y, self._paint_mode)
            self.end_batch()
        elif self.tool == self.TOOL_BUCKET:
            self.begin_batch()
            self._flood_fill(x, y, self._paint_mode)
            self.end_batch()
            self.painting_finished.emit()
        self.update()

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_last_pos is not None:
            dx = int(event.position().x()) - int(self._pan_last_pos.x())
            dy = int(event.position().y()) - int(self._pan_last_pos.y())
            self.pan_offset_x += dx
            self.pan_offset_y += dy
            self._pan_last_pos = event.position()
            self._clamp_pan_offset()
            self.update()
            return

        if self._painting:
            p = event.position()
            cell = self._pos_to_cell(int(p.x()), int(p.y()))
            if cell is None:
                return
            x, y = cell
            if self.tool == self.TOOL_PENCIL:
                last = self._last_painted or (x, y)
                if last != (x, y):
                    self.begin_batch()
                    self._paint_stroke(last[0], last[1], x, y, self._paint_mode)
                    self.end_batch()
                    self._last_painted = (x, y)
                    self.update()  # репейнт холста сразу, пока карандаш ещё нажат
            else:
                self._shape_cur = (x, y)
                self.update()
            return

        p = event.position()
        cell = self._pos_to_cell(int(p.x()), int(p.y()))
        if cell is None:
            if self._hover_x is not None or self._hover_y is not None:
                self._hover_x, self._hover_y = None, None
                self.update()
            return

        x, y = cell
        if self._hover_x != x or self._hover_y != y:
            self._hover_x, self._hover_y = x, y
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self._is_space_held):
            self._panning = False
            self._pan_last_pos = None
            self.setCursor(Qt.CursorShape.ClosedHandCursor if self._is_space_held else Qt.CursorShape.ArrowCursor)
            return
        
        if self._painting:
            self._painting = False
            if (self.tool not in (self.TOOL_PENCIL, self.TOOL_BUCKET)
                    and self._shape_anchor is not None and self._shape_cur is not None):
                self._apply_shape()
            else:
                if self._batch_changes is not None:
                    self.end_batch()
                self.painting_finished.emit()
            self._shape_anchor = None
            self._shape_cur = None
            self._last_painted = None
            self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return

        step = 1 if delta > 0 else -1
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom_level + step))
        if new_zoom == self.zoom_level:
            return

        p = event.position()
        cursor_x = int(p.x())
        cursor_y = int(p.y())

        cell_old = self._cell_size()
        cell_new = max(1, self.cell * new_zoom)

        world_x_num = cursor_x - self.pan_offset_x
        world_y_num = cursor_y - self.pan_offset_y

        self.zoom_level = new_zoom

        self.pan_offset_x = cursor_x - (world_x_num * cell_new) // cell_old
        self.pan_offset_y = cursor_y - (world_y_num * cell_new) // cell_old

        self._clamp_pan_offset()
        self.update()


class CreateEditorWidget(QWidget):
    icon_ready = pyqtSignal(str, list, int, int, int)

    def get_frames_pixels_list(self) -> list[list[list[int]]]:
        return list(self.frames_pixels)

    def get_params(self) -> tuple[int, int, int]:
        return int(self.canvas.width_px), int(self.canvas.height_px), 1

    def __init__(self):
        super().__init__()
        self.setObjectName("createEditorRoot")
        self.active_index = 0
        self.frames_pixels: list[list[list[int]]] = []
        
        self.undo_stack: list[list[list[int]]] = []
        self.redo_stack: list[list[list[int]]] = []
        self.max_history = 30

        self._setup_ui()
        self._connect_signals()

        self._set_canvas_size(128, 64, recreate_frames_if_empty=True)
        self._ensure_frame(0)
        self._sync_canvas_from_active()
        self._emit_ready()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Левая колонка: инструменты + настройки ──
        left_panel = QWidget()
        left_panel.setMinimumWidth(252)
        left_panel.setMaximumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Инструменты
        self.tools_group = QGroupBox(tr("create.group_tools"))
        tools_layout = QVBoxLayout(self.tools_group)
        tools_layout.setSpacing(8)

        tool_row = QHBoxLayout()
        tool_row.setSpacing(6)
        self.tool_group_qt = QButtonGroup(self)
        self.tool_group_qt.setExclusive(True)
        self.tool_buttons: dict[str, QPushButton] = {}
        self._tool_specs = [
            ("pencil", "✏️", "create.tool_pencil"),
            ("line", "📏", "create.tool_line"),
            ("rect", "▭", "create.tool_rect"),
            ("square", "◻", "create.tool_square"),
            ("circle", "◯", "create.tool_circle"),
            ("triangle", "△", "create.tool_triangle"),
            ("bucket", "🪣", "create.tool_bucket"),
        ]
        for tool_id, icon, tr_key in self._tool_specs:
            btn = QPushButton(icon)
            btn.setCheckable(True)
            btn.setObjectName("toolButton")
            btn.setToolTip(tr(tr_key))
            btn.setFixedSize(34, 32)
            self.tool_group_qt.addButton(btn)
            btn.clicked.connect(lambda _c=False, tid=tool_id: self._on_tool_button(tid))
            self.tool_buttons[tool_id] = btn
            tool_row.addWidget(btn)
        self.tool_buttons["pencil"].setChecked(True)
        tool_row.addStretch(1)
        tools_layout.addLayout(tool_row)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(6)
        self.lbl_brush_size = QLabel(tr("create.lbl_brush_size"))
        opt_row.addWidget(self.lbl_brush_size)
        self.spin_brush = QSpinBox()
        self.spin_brush.setRange(1, 16)
        self.spin_brush.setValue(1)
        self.spin_brush.setFixedWidth(54)
        opt_row.addWidget(self.spin_brush)
        self.chk_fill = QCheckBox(tr("create.chk_fill"))
        opt_row.addWidget(self.chk_fill)
        opt_row.addStretch(1)
        tools_layout.addLayout(opt_row)

        # Отдельная строка: круглая кисть (чтобы не вылезать за ширину карточки)
        round_row = QHBoxLayout()
        round_row.setSpacing(6)
        self.chk_round = QCheckBox(tr("create.chk_round"))
        round_row.addWidget(self.chk_round)
        round_row.addStretch(1)
        tools_layout.addLayout(round_row)
        left_layout.addWidget(self.tools_group)

        # Настройки
        self.settings_group = QGroupBox(tr("create.group_settings"))
        self.settings_layout = QFormLayout(self.settings_group)
        self.settings_layout.setVerticalSpacing(8)
        self.settings_layout.setHorizontalSpacing(8)

        self.name_png_edit = QLineEdit("icon")
        self.spin_w = QSpinBox(); self.spin_w.setRange(1, 128); self.spin_w.setValue(128)
        self.spin_h = QSpinBox(); self.spin_h.setRange(1, 128); self.spin_h.setValue(64)

        self.settings_layout.addRow(tr("create.lbl_name_png"), self.name_png_edit)
        self.settings_layout.addRow(tr("create.lbl_width"), self.spin_w)
        self.settings_layout.addRow(tr("create.lbl_height"), self.spin_h)
        left_layout.addWidget(self.settings_group)
        left_layout.addStretch(1)

        splitter.addWidget(left_panel)

        # ── Правая колонка: холст + статус + кадры ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 0, 0)
        right_layout.setSpacing(8)

        self.canvas_group = QGroupBox(tr("create.group_canvas"))
        canvas_layout = QVBoxLayout(self.canvas_group)
        canvas_layout.setContentsMargins(6, 6, 6, 6)

        self.canvas = PixelCanvas(128, 64, cell=4)
        canvas_layout.addWidget(self.canvas, 1)
        right_layout.addWidget(self.canvas_group, 1)

        self.lbl_status = QLabel(trf("create.status", count=1, active=0))
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setObjectName("createStatus")
        right_layout.addWidget(self.lbl_status)

        # Кадры — кинолента с мини-превью
        self.frames_group = QGroupBox(tr("create.group_frames"))
        frames_layout = QVBoxLayout(self.frames_group)
        frames_layout.setSpacing(6)

        self.frame_list = QListWidget()
        self.frame_list.setObjectName("createFrameList")
        self.frame_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.frame_list.setFlow(QListWidget.Flow.LeftToRight)
        self.frame_list.setWrapping(False)
        self.frame_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.frame_list.setMovement(QListWidget.Movement.Static)
        self.frame_list.setIconSize(QSize(64, 32))
        self.frame_list.setGridSize(QSize(84, 64))
        self.frame_list.setFixedHeight(84)
        # Меньший внутренний padding (чем глобальный 10px/14px) только для киноленты,
        # чтобы подпись «Кадр N» не наезжала на рамку миниатюры.
        self.frame_list.setStyleSheet("QListWidget::item { padding: 6px 12px; }")
        frames_layout.addWidget(self.frame_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_defs = [
            ("btn_add_frame", "➕", "create.btn_add_frame"),
            ("btn_remove_frame", "❌", "create.btn_remove_frame"),
            ("btn_prev", "⬅️", "create.btn_prev"),
            ("btn_next", "➡️", "create.btn_next"),
            ("btn_clear", "🧼", "create.btn_clear"),
            ("btn_dup_frame", "📑", "create.btn_dup_frame"),
        ]
        for attr, emoji, tr_key in btn_defs:
            btn = QPushButton(emoji)
            btn.setObjectName("compactBtn")
            btn.setToolTip(tr(tr_key))
            btn.setFixedSize(34, 28)
            setattr(self, attr, btn)
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        frames_layout.addLayout(btn_row)

        onion_row = QHBoxLayout()
        self.chk_onion = QCheckBox(tr("create.chk_onion"))
        onion_row.addWidget(self.chk_onion)
        onion_row.addStretch(1)
        frames_layout.addLayout(onion_row)

        right_layout.addWidget(self.frames_group, 0)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 900])

        root.addWidget(splitter, 1)

    def retranslate(self):
        """Обновляет тексты при смене языка."""
        self.settings_group.setTitle(tr("create.group_settings"))
        self.settings_layout.labelForField(self.name_png_edit).setText(tr("create.lbl_name_png"))
        self.settings_layout.labelForField(self.spin_w).setText(tr("create.lbl_width"))
        self.settings_layout.labelForField(self.spin_h).setText(tr("create.lbl_height"))
        self.tools_group.setTitle(tr("create.group_tools"))
        self.lbl_brush_size.setText(tr("create.lbl_brush_size"))
        self.chk_fill.setText(tr("create.chk_fill"))
        self.chk_round.setText(tr("create.chk_round"))
        self.chk_onion.setText(tr("create.chk_onion"))
        self.btn_dup_frame.setText(tr("create.btn_dup_frame"))
        for tool_id, _icon, tr_key in self._tool_specs:
            self.tool_buttons[tool_id].setToolTip(tr(tr_key))
        self.canvas_group.setTitle(tr("create.group_canvas"))
        self.frames_group.setTitle(tr("create.group_frames"))
        self.btn_add_frame.setToolTip(tr("create.btn_add_frame"))
        self.btn_remove_frame.setToolTip(tr("create.btn_remove_frame"))
        self.btn_prev.setToolTip(tr("create.btn_prev"))
        self.btn_next.setToolTip(tr("create.btn_next"))
        self.btn_clear.setToolTip(tr("create.btn_clear"))
        self.btn_dup_frame.setToolTip(tr("create.btn_dup_frame"))
        self._update_status()
        for i in range(self.frame_list.count()):
            self.frame_list.item(i).setText(trf("create.frame_item", index=i))

    def _connect_signals(self):
        self.canvas.pixel_changed.connect(self._on_canvas_pixel_changed)
        self.canvas.pixels_batch_changed.connect(self._on_pixels_batch_changed)
        self.canvas.painting_started.connect(self._save_state)
        self.canvas.painting_finished.connect(self._on_painting_finished)
        self.canvas.brush_size_changed.connect(self._on_canvas_brush_size)
        self.canvas.tool_changed.connect(self._on_canvas_tool)

        self.btn_add_frame.clicked.connect(self._add_frame)
        self.btn_remove_frame.clicked.connect(self._remove_active_frame)
        self.btn_dup_frame.clicked.connect(self._duplicate_frame)
        self.btn_prev.clicked.connect(lambda: self._change_active(-1))
        self.btn_next.clicked.connect(lambda: self._change_active(1))
        self.btn_clear.clicked.connect(self._clear_active_frame)

        self.name_png_edit.textChanged.connect(self._emit_ready)
        self.frame_list.currentRowChanged.connect(self._on_list_selection)

        self.spin_w.valueChanged.connect(self._on_canvas_size_changed)
        self.spin_h.valueChanged.connect(self._on_canvas_size_changed)
        self.spin_brush.valueChanged.connect(self.canvas.set_brush_size)
        self.chk_fill.toggled.connect(self.canvas.set_fill_shapes)
        self.chk_round.toggled.connect(self.canvas.set_round_brush)
        self.chk_onion.toggled.connect(self._update_overlay)

    def keyPressEvent(self, event):
        """Горячие клавиши: Undo/Redo (Ctrl+Z/Y) и размер кисти ([ / ])."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.undo()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Y:
                self.redo()
                event.accept()
                return
        if event.key() == Qt.Key.Key_BracketLeft:
            self.spin_brush.setValue(self.spin_brush.value() - 1)
            event.accept()
            return
        if event.key() == Qt.Key.Key_BracketRight:
            self.spin_brush.setValue(self.spin_brush.value() + 1)
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_canvas_size_changed(self):
        w = int(self.spin_w.value())
        h = int(self.spin_h.value())
        self._set_canvas_size(w, h, recreate_frames_if_empty=False)

    def _create_blank_frame(self, w: int, h: int) -> list[list[int]]:
        return [[0 for _ in range(w)] for _ in range(h)]

    def _set_canvas_size(self, w: int, h: int, recreate_frames_if_empty: bool):
        old_w = self.canvas.width_px
        old_h = self.canvas.height_px
        
        self.canvas.set_canvas_size(w, h)

        if not self.frames_pixels and recreate_frames_if_empty:
            self.frames_pixels = [self._create_blank_frame(w, h)]
            self.active_index = 0
            self._refresh_frame_list()
            return

        if not self.frames_pixels:
            self.frames_pixels = [self._create_blank_frame(w, h)]
            self.active_index = 0
            self._refresh_frame_list()
            return

        # УМНОЕ ИЗМЕНЕНИЕ РАЗМЕРА: сохраняем нарисованные пиксели
        self._resize_frames(w, h, old_w, old_h)
        
        self.active_index = min(self.active_index, len(self.frames_pixels) - 1)
        self._refresh_frame_list()
        self._sync_canvas_from_active()
        self._emit_ready()

    def _resize_frames(self, new_w: int, new_h: int, old_w: int, old_h: int):
        """Изменяет размер всех кадров, сохраняя существующие пиксели"""
        for i in range(len(self.frames_pixels)):
            old_frame = self.frames_pixels[i]
            new_frame = self._create_blank_frame(new_w, new_h)
            
            copy_h = min(old_h, new_h)
            copy_w = min(old_w, new_w)
            
            for y in range(copy_h):
                for x in range(copy_w):
                    new_frame[y][x] = old_frame[y][x]
                    
            self.frames_pixels[i] = new_frame

    def _ensure_frame(self, idx: int):
        while len(self.frames_pixels) <= idx:
            w = self.canvas.width_px
            h = self.canvas.height_px
            self.frames_pixels.append(self._create_blank_frame(w, h))

        if self.frame_list.count() < len(self.frames_pixels):
            self._refresh_frame_list()

    def _refresh_frame_list(self):
        self.frame_list.clear()
        w = self.canvas.width_px
        h = self.canvas.height_px
        for i in range(len(self.frames_pixels)):
            item = QListWidgetItem(trf("create.frame_item", index=i))
            item.setIcon(self._make_frame_icon(self.frames_pixels[i], w, h))
            item.setToolTip(trf("create.frame_item", index=i))
            self.frame_list.addItem(item)
        if self.frames_pixels:
            self.frame_list.setCurrentRow(self.active_index)

    def _make_frame_icon(self, frame: list[list[int]], w: int, h: int) -> QIcon:
        """Миниатюра кадра для киноленты: тёмный фон + светлые пиксели."""
        img = QImage(w, h, QImage.Format.Format_Grayscale8)
        buf = img.bits()
        buf.setsize(w * h)
        mv = memoryview(buf)
        for y in range(h):
            row = frame[y]
            base = y * w
            for x in range(w):
                mv[base + x] = 0xFF if row[x] else 0x00
        thumb = img.scaled(64, 32, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        return QIcon(QPixmap.fromImage(thumb))

    def _on_painting_finished(self):
        """Обновляет миниатюру активного кадра после штриха/фигуры."""
        if self.frame_list.currentRow() != self.active_index:
            return
        item = self.frame_list.currentItem()
        if item is not None:
            item.setIcon(self._make_frame_icon(
                self.frames_pixels[self.active_index], self.canvas.width_px, self.canvas.height_px))

    def _sync_canvas_from_active(self):
        self.canvas.set_pixels(self.frames_pixels[self.active_index])
        self._update_overlay()
        self._update_status()

    def _update_overlay(self):
        """Onion skin: показывает предыдущий кадр полупрозрачным под текущим."""
        if (self.chk_onion.isChecked()
                and self.active_index > 0
                and self.active_index < len(self.frames_pixels)):
            self.canvas.set_overlay(self.frames_pixels[self.active_index - 1], True)
        else:
            self.canvas.set_overlay(None, False)

    def _duplicate_frame(self):
        """Добавляет кадр как копию текущего (удобно для анимаций)."""
        new_frame = copy.deepcopy(self.frames_pixels[self.active_index])
        self.frames_pixels.append(new_frame)
        self.active_index = len(self.frames_pixels) - 1
        self._refresh_frame_list()
        self._sync_canvas_from_active()
        self._emit_ready()

    def _on_tool_button(self, tool_id: str):
        self.canvas.set_tool(tool_id)

    def _on_canvas_brush_size(self, size: int):
        self.spin_brush.setValue(size)

    def _on_canvas_tool(self, tool: str):
        btn = self.tool_buttons.get(tool)
        if btn is not None:
            btn.setChecked(True)

    def _update_status(self):
        self.lbl_status.setText(trf("create.status", count=len(self.frames_pixels), active=self.active_index))

    def _on_canvas_pixel_changed(self, x: int, y: int, v: int):
        self.frames_pixels[self.active_index][y][x] = 1 if v else 0
        self._emit_ready()

    def _on_pixels_batch_changed(self, changes):
        """Пакет изменений (фигура/штрих) применяется к кадру за один приём — быстро."""
        frame = self.frames_pixels[self.active_index]
        for x, y, v in changes:
            frame[y][x] = v
        self._emit_ready()


    # --- Undo / Redo Logic ---
    def _save_state(self):
        """Сохраняет текущий кадр в историю перед изменением"""
        self.undo_stack.append(copy.deepcopy(self.frames_pixels[self.active_index]))
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(copy.deepcopy(self.frames_pixels[self.active_index]))
        self.frames_pixels[self.active_index] = self.undo_stack.pop()
        self._sync_canvas_from_active()
        self._emit_ready()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(copy.deepcopy(self.frames_pixels[self.active_index]))
        self.frames_pixels[self.active_index] = self.redo_stack.pop()
        self._sync_canvas_from_active()
        self._emit_ready()
    # -------------------------

    def _add_frame(self):
        w = self.canvas.width_px
        h = self.canvas.height_px
        self.frames_pixels.append(self._create_blank_frame(w, h))
        self.active_index = len(self.frames_pixels) - 1
        self._refresh_frame_list()
        self._sync_canvas_from_active()
        self._emit_ready()

    def _remove_active_frame(self):
        if not self.frames_pixels:
            return

        if len(self.frames_pixels) == 1:
            w = self.canvas.width_px
            h = self.canvas.height_px
            self.frames_pixels[0] = self._create_blank_frame(w, h)
            self.active_index = 0
            self._sync_canvas_from_active()
            self._emit_ready()
            return

        self.frames_pixels.pop(self.active_index)
        self.active_index = max(0, min(self.active_index, len(self.frames_pixels) - 1))

        self._refresh_frame_list()
        self._sync_canvas_from_active()
        self._emit_ready()

    def _clear_active_frame(self):
        self.frames_pixels[self.active_index] = self._create_blank_frame(self.canvas.width_px, self.canvas.height_px)
        self._sync_canvas_from_active()
        self._emit_ready()

    def _change_active(self, delta: int):
        new_idx = self.active_index + delta
        if new_idx < 0 or new_idx >= len(self.frames_pixels):
            return
        self.active_index = new_idx
        self._sync_canvas_from_active()

    def _on_list_selection(self, row: int):
        if row < 0 or row >= len(self.frames_pixels):
            return
        if row == self.active_index:
            return
        self.active_index = row
        self._sync_canvas_from_active()
        self._emit_ready()

    def _emit_ready(self):
        if not self.frames_pixels:
            return

        app_name = self.name_png_edit.text()
        fps = 1
        w = int(self.canvas.width_px)
        h = int(self.canvas.height_px)

        self.icon_ready.emit(app_name, self.frames_pixels, w, h, fps)
