from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QFormLayout,
)

from core.image_processor import FlipperImageProcessor


class _CropPreviewWidget(QWidget):
    """Превью изображения + перетаскиваемая/растягиваемая рамка crop.
    """

    HANDLE_SIZE_PX = 8

    def __init__(self, *, parent: QWidget | None = None):
        super().__init__(parent)

        self._img_path: str | None = None
        self._img_pixmap: QPixmap | None = None

        self._output_w: int = 128
        self._output_h: int = 64

        # Crop box в координатах исходного изображения: (left, top, right, bottom)
        self._crop_left = 0
        self._crop_top = 0
        self._crop_right = 1
        self._crop_bottom = 1

        self._drag_mode: str | None = None  # move|l|t|r|b|lt|rt|lb|rb
        self._drag_start_pos_widget: tuple[int, int] | None = None
        self._crop_start: tuple[int, int, int, int] | None = None

        self.setMinimumSize(420, 240)
        self.setStyleSheet(
            "QWidget { background: #0a0a0a; border: 2px solid #333; color: #666; }"
        )

    def set_output_size(self, out_w: int, out_h: int):
        self._output_w = int(out_w)
        self._output_h = int(out_h)
        if self._img_pixmap:
            self._reset_crop_to_center()
            self.update()

    def set_image(self, img_path: str):
        self._img_path = img_path
        self._img_pixmap = QPixmap(img_path)
        if self._img_pixmap.isNull():
            self._img_pixmap = None
            return
        self._reset_crop_to_center()
        self.update()

    def _reset_crop_to_center(self):
        assert self._img_pixmap is not None
        src_w = self._img_pixmap.width()
        src_h = self._img_pixmap.height()

        # Рамка должна соответствовать выбранному выходному соотношению сторон.
        target_ratio = self._output_w / self._output_h

        # Ищем максимальную рамку внутри изображения с заданным ratio
        # crop_w / crop_h = target_ratio
        if src_w / src_h >= target_ratio:
            # ограничение по высоте
            crop_h = src_h
            crop_w = int(round(crop_h * target_ratio))
        else:
            # ограничение по ширине
            crop_w = src_w
            crop_h = int(round(crop_w / target_ratio))

        crop_w = max(1, min(src_w, crop_w))
        crop_h = max(1, min(src_h, crop_h))

        left = (src_w - crop_w) // 2
        top = (src_h - crop_h) // 2

        self._crop_left = int(left)
        self._crop_top = int(top)
        self._crop_right = int(left + crop_w)
        self._crop_bottom = int(top + crop_h)

    def get_crop_rect_in_source(self) -> tuple[int, int, int, int]:
        return (
            int(self._crop_left),
            int(self._crop_top),
            int(self._crop_right),
            int(self._crop_bottom),
        )

    # ---------- Маппинг координат widget -> source ----------

    def _source_to_widget_rect(self) -> QRect:
        if not self._img_pixmap:
            return QRect(0, 0, 0, 0)

        src_w = self._img_pixmap.width()
        src_h = self._img_pixmap.height()
        w = self.width()
        h = self.height()

        if src_w <= 0 or src_h <= 0 or w <= 0 or h <= 0:
            return QRect(0, 0, 0, 0)

        # Рисуем image с aspect-fit
        scale = min(w / src_w, h / src_h)
        draw_w = int(round(src_w * scale))
        draw_h = int(round(src_h * scale))
        x0 = (w - draw_w) // 2
        y0 = (h - draw_h) // 2

        left = x0 + int(round((self._crop_left / src_w) * draw_w))
        top = y0 + int(round((self._crop_top / src_h) * draw_h))
        right = x0 + int(round((self._crop_right / src_w) * draw_w))
        bottom = y0 + int(round((self._crop_bottom / src_h) * draw_h))

        return QRect(left, top, right - left, bottom - top)

    def _widget_point_to_source_point(self, px: int, py: int) -> tuple[int, int]:
        assert self._img_pixmap is not None
        src_w = self._img_pixmap.width()
        src_h = self._img_pixmap.height()

        w = self.width()
        h = self.height()

        scale = min(w / src_w, h / src_h)
        draw_w = src_w * scale
        draw_h = src_h * scale
        x0 = (w - draw_w) / 2
        y0 = (h - draw_h) / 2

        # переводим в координаты нарисованной области
        rel_x = (px - x0) / scale
        rel_y = (py - y0) / scale

        sx = int(round(rel_x))
        sy = int(round(rel_y))
        sx = max(0, min(src_w, sx))
        sy = max(0, min(src_h, sy))
        return sx, sy

    # ---------- Рисование ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.fillRect(self.rect(), QColor(10, 10, 10))

        if not self._img_pixmap:
            painter.setPen(QPen(QColor(120, 120, 120)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Загрузите JPG для превью")
            return

        # aspect-fit draw
        src_w = self._img_pixmap.width()
        src_h = self._img_pixmap.height()
        scale = min(self.width() / src_w, self.height() / src_h)
        draw_w = int(round(src_w * scale))
        draw_h = int(round(src_h * scale))
        x0 = (self.width() - draw_w) // 2
        y0 = (self.height() - draw_h) // 2

        target = QRect(x0, y0, draw_w, draw_h)
        painter.drawPixmap(target, self._img_pixmap)

        crop_rect_w = self._source_to_widget_rect()

        # overlay
        painter.setPen(QPen(QColor(0, 200, 255), 2))
        painter.drawRect(crop_rect_w)

        # dim outside rect
        dim = QColor(0, 0, 0, 90)
        painter.fillRect(self.rect(), dim)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # вырезаем overlay так, чтобы рамка area была видна
        painter.fillRect(crop_rect_w, QColor(0, 0, 0, 0))

        # handles
        handle_c = QColor(0, 200, 255)
        painter.setBrush(handle_c)
        hs = self.HANDLE_SIZE_PX

        def handle_at(x: int, y: int):
            painter.drawRect(QRect(x - hs // 2, y - hs // 2, hs, hs))

        # corners
        handle_at(crop_rect_w.left(), crop_rect_w.top())
        handle_at(crop_rect_w.right(), crop_rect_w.top())
        handle_at(crop_rect_w.left(), crop_rect_w.bottom())
        handle_at(crop_rect_w.right(), crop_rect_w.bottom())

    # ---------- Hit-testing / Drag ----------

    def _hit_test_handle(self, px: int, py: int) -> str | None:
        r = self._source_to_widget_rect()
        if r.width() <= 0 or r.height() <= 0:
            return None

        hs = self.HANDLE_SIZE_PX
        # corners
        corners = {
            "lt": (r.left(), r.top()),
            "rt": (r.right(), r.top()),
            "lb": (r.left(), r.bottom()),
            "rb": (r.right(), r.bottom()),
        }
        for k, (cx, cy) in corners.items():
            if abs(px - cx) <= hs and abs(py - cy) <= hs:
                return k

        # edges
        if r.adjusted(0, 0, 0, 0).left() <= px <= r.right() and abs(py - r.top()) <= hs:
            return "t"
        if abs(py - r.bottom()) <= hs:
            return "b"
        if abs(px - r.left()) <= hs:
            return "l"
        if abs(px - r.right()) <= hs:
            return "r"

        if r.contains(px, py):
            return "move"
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self._img_pixmap:
            return

        px = int(event.position().x())
        py = int(event.position().y())

        mode = self._hit_test_handle(px, py)
        if not mode:
            return

        self._drag_mode = mode
        self._drag_start_pos_widget = (px, py)
        self._crop_start = self.get_crop_rect_in_source()

    def mouseMoveEvent(self, event):
        if not self._img_pixmap:
            return
        px = int(event.position().x())
        py = int(event.position().y())

        mode = self._hit_test_handle(px, py)
        if not self._drag_mode:
            # курсоры
            if mode in {"lt", "rb"}:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif mode in {"rt", "lb"}:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif mode in {"l", "r"}:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif mode in {"t", "b"}:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif mode == "move":
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        if not self._drag_mode or not self._drag_start_pos_widget or not self._crop_start:
            return

        # Drag actual
        sx, sy = self._widget_point_to_source_point(px, py)
        start_left, start_top, start_right, start_bottom = self._crop_start

        left, top, right, bottom = start_left, start_top, start_right, start_bottom

        min_size = 2
        src_w = self._img_pixmap.width()
        src_h = self._img_pixmap.height()

        def clamp(v: int, a: int, b: int) -> int:
            return max(a, min(b, v))

        if self._drag_mode == "move":
            # move box maintaining size
            psx, psy = self._widget_point_to_source_point(*self._drag_start_pos_widget)
            dx = sx - psx
            dy = sy - psy
            w_box = right - left
            h_box = bottom - top
            left = clamp(left + dx, 0, src_w - w_box)
            top = clamp(top + dy, 0, src_h - h_box)
            right = left + w_box
            bottom = top + h_box

        else:
            # resize handles
            if self._drag_mode in {"l", "lt", "lb"}:
                left = clamp(sx, 0, right - min_size)
            if self._drag_mode in {"r", "rt", "rb"}:
                right = clamp(sx, left + min_size, src_w)
            if self._drag_mode in {"t", "lt", "rt"}:
                top = clamp(sy, 0, bottom - min_size)
            if self._drag_mode in {"b", "lb", "rb"}:
                bottom = clamp(sy, top + min_size, src_h)

            target_ratio = self._output_w / self._output_h
            cur_w = max(1, right - left)
            cur_h = max(1, bottom - top)
            cur_ratio = cur_w / cur_h

            # подгоняем по ближнему изменению
            if cur_ratio > target_ratio:
                new_w = int(round(cur_h * target_ratio))
                if self._drag_mode in {"l", "lt", "lb"}:
                    left = right - new_w
                else:
                    right = left + new_w
            else:
                new_h = int(round(cur_w / target_ratio))
                if self._drag_mode in {"t", "lt", "rt"}:
                    top = bottom - new_h
                else:
                    bottom = top + new_h

            left = clamp(left, 0, src_w - min_size)
            top = clamp(top, 0, src_h - min_size)
            right = clamp(right, left + min_size, src_w)
            bottom = clamp(bottom, top + min_size, src_h)

        self._crop_left, self._crop_top, self._crop_right, self._crop_bottom = (
            int(left),
            int(top),
            int(right),
            int(bottom),
        )
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag_mode = None
        self._drag_start_pos_widget = None
        self._crop_start = None


class JpegCropEditorWidget(QWidget):
    def __init__(self):
        super().__init__()

        self._input_path: str | None = None
        self._setup_ui()
        self._connect_signals()

        # init
        out_w, out_h = sorted(FlipperImageProcessor.VALID_ICON_SIZES)[0]
        self.size_combo.setCurrentText(f"{out_w}x{out_h}")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        controls_group = QGroupBox("📷 JPG → PNG crop")
        controls_layout = QFormLayout(controls_group)

        self.btn_load = QPushButton("Загрузить JPG")
        self.lbl_loaded = QLabel("Файл не выбран")
        self.lbl_loaded.setWordWrap(True)

        self.size_combo = QComboBox()
        fixed_sizes_sorted = sorted(FlipperImageProcessor.VALID_ICON_SIZES, key=lambda p: (p[0], p[1]))
        for w, h in fixed_sizes_sorted:
            self.size_combo.addItem(f"{w}x{h}", userData=(w, h))

        self.btn_export = QPushButton("Экспортировать PNG")

        controls_layout.addRow("Input:", self.btn_load)
        controls_layout.addRow("Loaded:", self.lbl_loaded)
        controls_layout.addRow("Output size:", self.size_combo)
        controls_layout.addRow("", self.btn_export)

        layout.addWidget(controls_group)


        preview_group = QGroupBox("Preview (drag рамка)")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_widget = _CropPreviewWidget()
        preview_layout.addWidget(self.preview_widget)

        self.lbl_hint = QLabel("Рамка соответствует выбранному output соотношению сторон. Можно двигать/тянуть за углы.")
        self.lbl_hint.setWordWrap(True)
        layout.addWidget(preview_group)
        preview_layout.addWidget(self.lbl_hint)

    def _connect_signals(self):
        self.btn_load.clicked.connect(self._on_load)
        self.btn_export.clicked.connect(self._on_export)
        self.size_combo.currentIndexChanged.connect(self._on_out_size_changed)



    def _selected_out_size(self) -> tuple[int, int]:
        data = self.size_combo.currentData()
        if not isinstance(data, tuple) or len(data) != 2:
            # fallback
            return 128, 64
        return int(data[0]), int(data[1])



    def _refresh_ui(self):
        self.btn_export.setEnabled(self._input_path is not None)

    def _on_out_size_changed(self):
        out_w, out_h = self._selected_out_size()
        self.preview_widget.set_output_size(out_w, out_h)
        self._refresh_ui()

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select JPG",
            "",
            "Images (*.jpg *.jpeg *.png)",
        )
        if not path:
            return

        self._input_path = path
        self.lbl_loaded.setText(Path(path).name)

        out_w, out_h = self._selected_out_size()
        self.preview_widget.set_output_size(out_w, out_h)
        self.preview_widget.set_image(path)

        self._refresh_ui()

    def _on_export(self):
        if not self._input_path:
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для PNG")
        if not out_dir:
            return

        out_w, out_h = self._selected_out_size()

        left, top, right, bottom = self.preview_widget.get_crop_rect_in_source()


        in_p = Path(self._input_path)
        out_path = Path(out_dir) / f"{in_p.stem}_{out_w}x{out_h}_customcrop.png"

        FlipperImageProcessor.export_jpg_custom_crop_to_png(
            input_path=str(self._input_path),
            output_path=str(out_path),
            output_w=out_w,
            output_h=out_h,
            crop_left=left,
            crop_top=top,
            crop_right=right,
            crop_bottom=bottom,
        )


        # Обновим превью (перерисовка рамки уже есть)
        self.preview_widget.update()


# --- Backward compatibility: if old preview exists ---

__all__ = ["JpegCropEditorWidget"]

