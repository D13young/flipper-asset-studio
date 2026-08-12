from __future__ import annotations

import copy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
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
    painting_finished = pyqtSignal()

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

    def _paint_cell(self, x: int, y: int, value: int):
        v = 1 if value else 0
        if self.pixels[y][x] == v:
            return
        self.pixels[y][x] = v
        self.pixel_changed.emit(x, y, v)
        self.update()

    def mousePressEvent(self, event):
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
        self._paint_cell(x, y, self._paint_mode)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_last_pos is not None:
            dx = int(event.position().x()) - int(self._pan_last_pos.x())
            dy = int(event.position().y()) - int(self._pan_last_pos.y())
            self.pan_offset_x += dx
            self.pan_offset_y += dy
            self._pan_last_pos = event.position()
            self._clamp_pan_offset()  # Ограничиваем выход за границы
            self.update()
            return

        if self._painting:
            p = event.position()
            cell = self._pos_to_cell(int(p.x()), int(p.y()))
            if cell is None:
                return
            x, y = cell
            self._paint_cell(x, y, self._paint_mode)
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
            self.painting_finished.emit()  # Сигнал для сохранения состояния в Undo

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

        self._clamp_pan_offset()  # Ограничиваем после зума
        self.update()


class CreateEditorWidget(QWidget):
    icon_ready = pyqtSignal(str, list, int, int, int)

    def get_frames_pixels_list(self) -> list[list[list[int]]]:
        return list(self.frames_pixels)

    def get_params(self) -> tuple[int, int, int]:
        # fps=1 (UI FPS/Preview убраны по ТЗ, но main_window ожидает fps)
        return int(self.canvas.width_px), int(self.canvas.height_px), 1

    def __init__(self):
        super().__init__()
        self.active_index = 0
        self.frames_pixels: list[list[list[int]]] = []
        
        # Undo / Redo стеки
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.settings_group = QGroupBox(tr("create.group_settings"))
        self.settings_layout = QFormLayout()

        self.name_png_edit = QLineEdit("icon")
        self.spin_w = QSpinBox(); self.spin_w.setRange(1, 128); self.spin_w.setValue(128)
        self.spin_h = QSpinBox(); self.spin_h.setRange(1, 128); self.spin_h.setValue(64)

        self.settings_layout.addRow(tr("create.lbl_name_png"), self.name_png_edit)
        self.settings_layout.addRow(tr("create.lbl_width"), self.spin_w)
        self.settings_layout.addRow(tr("create.lbl_height"), self.spin_h)
        self.settings_group.setLayout(self.settings_layout)
        layout.addWidget(self.settings_group)

        self.canvas_group = QGroupBox(tr("create.group_canvas"))
        canvas_layout = QVBoxLayout(self.canvas_group)

        self.canvas = PixelCanvas(128, 64, cell=4)
        canvas_layout.addWidget(self.canvas)
        layout.addWidget(self.canvas_group)

        self.frames_group = QGroupBox(tr("create.group_frames"))
        frames_layout = QVBoxLayout(self.frames_group)

        self.frame_list = QListWidget()
        self.frame_list.setViewMode(QListWidget.ViewMode.ListMode)
        self.frame_list.setMaximumHeight(90)
        frames_layout.addWidget(self.frame_list)

        btn_layout = QHBoxLayout()
        self.btn_add_frame = QPushButton(tr("create.btn_add_frame"))
        self.btn_remove_frame = QPushButton(tr("create.btn_remove_frame"))
        self.btn_prev = QPushButton(tr("create.btn_prev"))
        self.btn_next = QPushButton(tr("create.btn_next"))
        self.btn_clear = QPushButton(tr("create.btn_clear"))

        btn_layout.addWidget(self.btn_add_frame)
        btn_layout.addWidget(self.btn_remove_frame)
        btn_layout.addWidget(self.btn_prev)
        btn_layout.addWidget(self.btn_next)
        btn_layout.addWidget(self.btn_clear)
        frames_layout.addLayout(btn_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.frames_group)

        self.frame_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.setStretchFactor(0, 1)
        layout.addWidget(splitter)

        layout.setStretch(0, 0)
        layout.setStretch(1, 0)
        layout.setStretch(2, 1)
        layout.setStretch(3, 0)

        self.lbl_status = QLabel(trf("create.status", count=1, active=0))
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.lbl_status)

    def retranslate(self):
        """Обновляет тексты при смене языка."""
        self.settings_group.setTitle(tr("create.group_settings"))
        self.settings_layout.labelForField(self.name_png_edit).setText(tr("create.lbl_name_png"))
        self.settings_layout.labelForField(self.spin_w).setText(tr("create.lbl_width"))
        self.settings_layout.labelForField(self.spin_h).setText(tr("create.lbl_height"))
        self.canvas_group.setTitle(tr("create.group_canvas"))
        self.frames_group.setTitle(tr("create.group_frames"))
        self.btn_add_frame.setText(tr("create.btn_add_frame"))
        self.btn_remove_frame.setText(tr("create.btn_remove_frame"))
        self.btn_prev.setText(tr("create.btn_prev"))
        self.btn_next.setText(tr("create.btn_next"))
        self.btn_clear.setText(tr("create.btn_clear"))
        self._update_status()
        for i in range(self.frame_list.count()):
            self.frame_list.item(i).setText(trf("create.frame_item", index=i))

    def _connect_signals(self):
        self.canvas.pixel_changed.connect(self._on_canvas_pixel_changed)
        # Сохраняем состояние после завершения действия (mouseRelease) для Undo
        self.canvas.painting_finished.connect(self._save_state)

        self.btn_add_frame.clicked.connect(self._add_frame)
        self.btn_remove_frame.clicked.connect(self._remove_active_frame)
        self.btn_prev.clicked.connect(lambda: self._change_active(-1))
        self.btn_next.clicked.connect(lambda: self._change_active(1))
        self.btn_clear.clicked.connect(self._clear_active_frame)

        self.name_png_edit.textChanged.connect(self._emit_ready)
        self.frame_list.currentRowChanged.connect(self._on_list_selection)

        self.spin_w.valueChanged.connect(self._on_canvas_size_changed)
        self.spin_h.valueChanged.connect(self._on_canvas_size_changed)

    def keyPressEvent(self, event):
        """Горячие клавиши Undo/Redo"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.undo()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Y:
                self.redo()
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
        for i in range(len(self.frames_pixels)):
            item = QListWidgetItem(trf("create.frame_item", index=i))
            self.frame_list.addItem(item)
        if self.frames_pixels:
            self.frame_list.setCurrentRow(self.active_index)

    def _sync_canvas_from_active(self):
        self.canvas.set_pixels(self.frames_pixels[self.active_index])
        self._update_status()

    def _update_status(self):
        self.lbl_status.setText(trf("create.status", count=len(self.frames_pixels), active=self.active_index))

    def _on_canvas_pixel_changed(self, x: int, y: int, v: int):
        self.frames_pixels[self.active_index][y][x] = 1 if v else 0
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
        # fps=1 (UI FPS/Preview убраны по ТЗ, но main_window ожидает fps)
        fps = 1
        w = int(self.canvas.width_px)
        h = int(self.canvas.height_px)

        self.icon_ready.emit(app_name, self.frames_pixels, w, h, fps)
