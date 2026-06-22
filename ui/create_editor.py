from __future__ import annotations

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


from core.image_processor import FlipperImageProcessor


class PixelCanvas(QWidget):

    pixel_changed = pyqtSignal(int, int, int)

    def __init__(self, width_px: int = 128, height_px: int = 64, cell: int = 5, parent: QWidget | None = None):
        super().__init__(parent)
        self.cell = int(cell)
        self.width_px = int(width_px)
        self.height_px = int(height_px)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.pixels: list[list[int]] = [
            [0 for _ in range(self.width_px)] for _ in range(self.height_px)
        ]

        self._painting = False
        self._paint_mode = 1
        self._apply_geometry_limits()

    def _apply_geometry_limits(self):
        w = self.width_px * self.cell
        h = self.height_px * self.cell
        self.setMinimumHeight(h)
        self.updateGeometry()

    def set_canvas_size(self, width_px: int, height_px: int):
        width_px = int(width_px)
        height_px = int(height_px)

        if width_px <= 0 or height_px <= 0:
            return

        # Пересоздаём пиксельную матрицу под новый размер
        self.width_px = width_px
        self.height_px = height_px
        self.pixels = [[0 for _ in range(self.width_px)] for _ in range(self.height_px)]
        self._apply_geometry_limits()
        self.update()

    def set_pixels(self, pixels: list[list[int]]):
        if len(pixels) != self.height_px:
            raise ValueError("Invalid height")
        for y in range(self.height_px):
            if len(pixels[y]) != self.width_px:
                raise ValueError("Invalid width")

        self.pixels = [[1 if pixels[y][x] else 0 for x in range(self.width_px)] for y in range(self.height_px)]
        self.update()

    def clear(self):
        for y in range(self.height_px):
            for x in range(self.width_px):
                self.pixels[y][x] = 0
        self.update()

    def _pos_to_cell(self, pos_x: int, pos_y: int):
        x = pos_x // self.cell
        y = pos_y // self.cell
        if x < 0 or y < 0 or x >= self.width_px or y >= self.height_px:
            return None
        return x, y

    def _paint_cell(self, x: int, y: int, value: int):
        v = 1 if value else 0
        if self.pixels[y][x] == v:
            return
        self.pixels[y][x] = v
        self.pixel_changed.emit(x, y, v)
        self.update()

    def mousePressEvent(self, event):
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return

        cell = self._pos_to_cell(int(event.position().x()), int(event.position().y()))
        if cell is None:
            return

        self._painting = True
        self._paint_mode = 1 if event.button() == Qt.MouseButton.LeftButton else 0

        x, y = cell
        self._paint_cell(x, y, self._paint_mode)

    def mouseMoveEvent(self, event):
        if not self._painting:
            return

        cell = self._pos_to_cell(int(event.position().x()), int(event.position().y()))
        if cell is None:
            return

        x, y = cell
        self._paint_cell(x, y, self._paint_mode)

    def mouseReleaseEvent(self, event):
        self._painting = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width_px * self.cell, self.height_px * self.cell, QColor(10, 10, 10))

        on_color = QColor(230, 230, 230)
        grid_color = QColor(40, 40, 40)

        for y in range(self.height_px):
            for x in range(self.width_px):
                if self.pixels[y][x]:
                    painter.fillRect(x * self.cell, y * self.cell, self.cell, self.cell, on_color)

        painter.setPen(grid_color)
        for x in range(self.width_px + 1):
            painter.drawLine(x * self.cell, 0, x * self.cell, self.height_px * self.cell)
        for y in range(self.height_px + 1):
            painter.drawLine(0, y * self.cell, self.width_px * self.cell, y * self.cell)


class CreateEditorWidget(QWidget):
    # app_name, frames_bytes, w, h, fps
    icon_ready = pyqtSignal(str, list, int, int, int)

    def get_frames_bytes_list(self) -> list[bytes]:
        return list(self._frame_bytes)

    def get_params(self) -> tuple[int, int, int]:
        return int(self.canvas.width_px), int(self.canvas.height_px), int(self.spin_fps.value())

    def __init__(self):
        super().__init__()
        self.active_index = 0
        self.frames_pixels: list[list[list[int]]] = []
        self._frame_bytes: list[bytes] = []

        self._setup_ui()
        self._connect_signals()

        self._set_canvas_size(128, 64, recreate_frames_if_empty=True)
        self._ensure_frame(0)
        self._sync_canvas_from_active()
        self._emit_ready()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        settings_group = QGroupBox("⚙️ Settings")
        settings_layout = QFormLayout()

        self.app_name_edit = QLineEdit("SubGhz")
        self.spin_w = QSpinBox(); self.spin_w.setRange(1, 128); self.spin_w.setValue(128)
        self.spin_h = QSpinBox(); self.spin_h.setRange(1, 128); self.spin_h.setValue(64)

        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(1, 60)
        self.spin_fps.setValue(5)

        settings_layout.addRow("App Name:", self.app_name_edit)
        settings_layout.addRow("Width (px):", self.spin_w)
        settings_layout.addRow("Height (px):", self.spin_h)
        settings_layout.addRow("FPS (для анимации):", self.spin_fps)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        canvas_group = QGroupBox("🖼️ Canvas")
        canvas_layout = QVBoxLayout(canvas_group)

        # Уменьшаем визуальное поле: cell меньше и canvas фиксируем по высоте на уровне layout.
        self.canvas = PixelCanvas(128, 64, cell=4)
        # Сделаем меньше вертикальное “вытягивание”
        self.canvas.setMaximumHeight(260)
        canvas_layout.addWidget(self.canvas)


        layout.addWidget(canvas_group)

        frames_group = QGroupBox("Frames")
        frames_layout = QVBoxLayout(frames_group)

        self.frame_list = QListWidget()
        self.frame_list.setViewMode(QListWidget.ViewMode.ListMode)
        frames_layout.addWidget(self.frame_list)

        btn_layout = QHBoxLayout()
        self.btn_add_frame = QPushButton("➕ Add Frame")
        self.btn_remove_frame = QPushButton("❌ Remove")
        self.btn_prev = QPushButton("⬅️ Prev")
        self.btn_next = QPushButton("Next ➡️")
        self.btn_clear = QPushButton("🧼 Clear")

        btn_layout.addWidget(self.btn_add_frame)
        btn_layout.addWidget(self.btn_remove_frame)
        btn_layout.addWidget(self.btn_prev)
        btn_layout.addWidget(self.btn_next)
        btn_layout.addWidget(self.btn_clear)
        frames_layout.addLayout(btn_layout)

        # Сделаем Frames и Preview растягиваемыми / вертикальный splitter
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(120)
        self.preview_label.setStyleSheet(
            "QLabel { background: #0a0a0a; border: 2px solid #333; color: #888; font-size: 14px; }"
        )
        self.preview_label.setText("Нарисуйте пиксели")
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.preview_label)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(frames_group)
        splitter.addWidget(preview_group)

        # чтобы QListWidget и Preview корректно отдавали место при растяжении
        self.frame_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        splitter.setSizes([320, 200])
        layout.addWidget(splitter)

        self.lbl_status = QLabel("Кадры: 1 | Активный: 0")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)


    def _connect_signals(self):
        self.canvas.pixel_changed.connect(self._on_canvas_pixel_changed)

        self.btn_add_frame.clicked.connect(self._add_frame)
        self.btn_remove_frame.clicked.connect(self._remove_active_frame)
        self.btn_prev.clicked.connect(lambda: self._change_active(-1))
        self.btn_next.clicked.connect(lambda: self._change_active(1))
        self.btn_clear.clicked.connect(self._clear_active_frame)

        self.spin_fps.valueChanged.connect(self._emit_ready)
        self.app_name_edit.textChanged.connect(self._emit_ready)
        self.frame_list.currentRowChanged.connect(self._on_list_selection)

        self.spin_w.valueChanged.connect(self._on_canvas_size_changed)
        self.spin_h.valueChanged.connect(self._on_canvas_size_changed)

    def _on_canvas_size_changed(self):
        w = int(self.spin_w.value())
        h = int(self.spin_h.value())
        self._set_canvas_size(w, h, recreate_frames_if_empty=False)

    def _create_blank_frame(self, w: int, h: int) -> list[list[int]]:
        return [[0 for _ in range(w)] for _ in range(h)]

    def _set_canvas_size(self, w: int, h: int, recreate_frames_if_empty: bool):
        # Canvas
        self.canvas.set_canvas_size(w, h)

        # Frames
        if not self.frames_pixels and recreate_frames_if_empty:
            self.frames_pixels = [self._create_blank_frame(w, h)]
            self.active_index = 0
            self._refresh_frame_list()
            return

        # Если размеры меняются — пересобираем текущий active frame с центрированием
        if not self.frames_pixels:
            self.frames_pixels = [self._create_blank_frame(w, h)]
            self.active_index = 0
            self._refresh_frame_list()
            return

        self.frames_pixels = [self._create_blank_frame(w, h) for _ in range(len(self.frames_pixels))]
        self.active_index = min(self.active_index, len(self.frames_pixels) - 1)
        self._refresh_frame_list()
        self._sync_canvas_from_active()
        self._emit_ready()

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
            item = QListWidgetItem(f"Frame {i}")
            self.frame_list.addItem(item)
        if self.frames_pixels:
            self.frame_list.setCurrentRow(self.active_index)

    def _sync_canvas_from_active(self):
        self.canvas.set_pixels(self.frames_pixels[self.active_index])
        self._update_preview()
        self._update_status()

    def _update_status(self):
        self.lbl_status.setText(f"Кадры: {len(self.frames_pixels)} | Активный: {self.active_index}")

    def _on_canvas_pixel_changed(self, x: int, y: int, v: int):
        self.frames_pixels[self.active_index][y][x] = 1 if v else 0
        self._update_preview()
        self._emit_ready()

    def _update_preview(self):
        pixels = self.frames_pixels[self.active_index]
        w = self.canvas.width_px
        h = self.canvas.height_px

        data = FlipperImageProcessor.pack_pixels_to_flipper_bytes(pixels, width=w, height=h)
        pm = FlipperImageProcessor.bytes_to_preview(data, width=w, height=h, scale=3)
        self.preview_label.setPixmap(pm)

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

        app_name = self.app_name_edit.text()
        fps = int(self.spin_fps.value())
        w = int(self.canvas.width_px)
        h = int(self.canvas.height_px)

        frame_bytes = [
            FlipperImageProcessor.pack_pixels_to_flipper_bytes(frame, width=w, height=h)
            for frame in self.frames_pixels
        ]
        self._frame_bytes = frame_bytes

        self.icon_ready.emit(app_name, frame_bytes, w, h, fps)


