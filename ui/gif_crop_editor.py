from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageSequence

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QFormLayout,
    QSlider,
    QMessageBox,
)

from core.image_processor import FlipperImageProcessor
from ui.jpg_crop_editor import CropPreviewWidget
from ui.drag_drop_widget import DragDropArea
from ui.background import BackgroundRunner
from ui.i18n import tr, trf


def _pil_to_preview_pixmap(img: Image.Image, max_dim: int = 640) -> QPixmap:
    """Преобразование кадра PIL в QPixmap для превью (с уменьшением размера)."""
    img = img.convert("RGBA")
    if img.width > max_dim or img.height > max_dim:
        img = img.copy()
        img.thumbnail((max_dim, max_dim), Image.Resampling.BILINEAR)
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class GifCropEditorWidget(QWidget):
    """Вкладка GIF → PNG: обрезает и экспортирует все кадры .gif.

    Рамка crop задаётся один раз на превью и применяется к каждому кадру.
    """

    def __init__(self):
        super().__init__()

        self._input_path: str | None = None
        self._frames_pil: list[Image.Image] = []
        self._preview_cache: dict[int, QPixmap] = {}
        self._exporting = False
        self._export_out_dir: str = ""
        self._bg = BackgroundRunner(self)

        self._setup_ui()
        self._connect_signals()

        # init
        out_w, out_h = sorted(FlipperImageProcessor.VALID_ICON_SIZES)[0]
        self.size_combo.setCurrentText(f"{out_w}x{out_h}")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Drag-and-Drop область
        self.drop_area = DragDropArea(
            tr("gif.drag_title"),
            [".gif"],
        )
        layout.addWidget(self.drop_area)

        self.controls_group = QGroupBox(tr("gif.group_controls"))
        self.controls_layout = QFormLayout(self.controls_group)

        self.btn_load = QPushButton(tr("gif.btn_load"))
        self.lbl_loaded = QLabel(tr("gif.loaded_default"))
        self.lbl_loaded.setWordWrap(True)

        self.size_combo = QComboBox()
        fixed_sizes_sorted = sorted(FlipperImageProcessor.VALID_ICON_SIZES, key=lambda p: (p[0], p[1]))
        for w, h in fixed_sizes_sorted:
            self.size_combo.addItem(f"{w}x{h}", userData=(w, h))

        self.lbl_frames = QLabel(tr("gif.lbl_frames"))

        self.btn_export = QPushButton(tr("gif.btn_export"))

        self.controls_layout.addRow(tr("jpg.lbl_input"), self.btn_load)
        self.controls_layout.addRow(tr("jpg.lbl_loaded"), self.lbl_loaded)
        self.controls_layout.addRow(tr("jpg.lbl_output_size"), self.size_combo)
        self.controls_layout.addRow(tr("gif.lbl_frames_label"), self.lbl_frames)
        self.controls_layout.addRow("", self.btn_export)

        layout.addWidget(self.controls_group)

        self.preview_group = QGroupBox(tr("gif.group_preview"))
        preview_layout = QVBoxLayout(self.preview_group)

        self.preview_widget = CropPreviewWidget(empty_hint=tr("gif.preview_hint"))
        preview_layout.addWidget(self.preview_widget)

        # Перебор кадров в превью
        frame_row = QHBoxLayout()
        self.lbl_frame = QLabel(tr("gif.lbl_frame"))
        frame_row.addWidget(self.lbl_frame)
        self.slider_frame = QSlider(Qt.Orientation.Horizontal)
        self.slider_frame.setRange(0, 0)
        self.slider_frame.setEnabled(False)
        self.lbl_frame_idx = QLabel("—")
        frame_row.addWidget(self.slider_frame, 1)
        frame_row.addWidget(self.lbl_frame_idx)
        preview_layout.addLayout(frame_row)

        self.lbl_hint = QLabel(tr("gif.lbl_hint"))
        self.lbl_hint.setWordWrap(True)
        preview_layout.addWidget(self.lbl_hint)

        layout.addWidget(self.preview_group)

    def retranslate(self):
        """Обновляет тексты при смене языка."""
        self.drop_area.set_text(tr("gif.drag_title"))
        self.controls_group.setTitle(tr("gif.group_controls"))
        self.btn_load.setText(tr("gif.btn_load"))
        self.btn_export.setText(tr("gif.btn_export"))
        self.controls_layout.labelForField(self.btn_load).setText(tr("jpg.lbl_input"))
        self.controls_layout.labelForField(self.lbl_loaded).setText(tr("jpg.lbl_loaded"))
        self.controls_layout.labelForField(self.size_combo).setText(tr("jpg.lbl_output_size"))
        self.controls_layout.labelForField(self.lbl_frames).setText(tr("gif.lbl_frames_label"))
        self.preview_group.setTitle(tr("gif.group_preview"))
        self.lbl_frame.setText(tr("gif.lbl_frame"))
        self.lbl_hint.setText(tr("gif.lbl_hint"))
        if not self._input_path or not self._frames_pil:
            self.lbl_loaded.setText(tr("gif.loaded_default"))
            self.lbl_frames.setText(tr("gif.lbl_frames"))
        else:
            self.lbl_frames.setText(trf("gif.lbl_frames_count", count=len(self._frames_pil)))

    def _connect_signals(self):
        self.btn_load.clicked.connect(self._on_load)
        self.btn_export.clicked.connect(self._on_export)
        self.size_combo.currentIndexChanged.connect(self._on_out_size_changed)
        self.slider_frame.valueChanged.connect(self._show_frame)
        self.drop_area.files_dropped.connect(self._on_drop)

    # ---------------- Selection helpers ----------------

    def _selected_out_size(self) -> tuple[int, int]:
        data = self.size_combo.currentData()
        if not isinstance(data, tuple) or len(data) != 2:
            # fallback
            return 128, 64
        return int(data[0]), int(data[1])

    def _refresh_ui(self):
        has_input = self._input_path is not None and bool(self._frames_pil)
        self.btn_export.setEnabled(has_input)
        self.slider_frame.setEnabled(bool(self._frames_pil))

    def _on_out_size_changed(self):
        out_w, out_h = self._selected_out_size()
        self.preview_widget.set_output_size(out_w, out_h)
        self._refresh_ui()

    # ---------------- Loading ----------------

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("gif.select_gif"),
            "",
            "GIF Animation (*.gif)",
        )
        if not path:
            return

        self._load_animation(path)

    def _on_drop(self, paths: list):
        if not paths:
            return
        self._load_animation(paths[0])

    def _load_animation(self, path: str):
        try:
            self._load_gif(path)
        except Exception as e:
            self._input_path = None
            self._frames_pil = []
            self._preview_cache.clear()
            self._refresh_ui()
            QMessageBox.critical(self, tr("dlg.error"), str(e))
            return

        self._input_path = path
        self.lbl_loaded.setText(Path(path).name)
        self.lbl_frames.setText(trf("gif.lbl_frames_count", count=len(self._frames_pil)))

        out_w, out_h = self._selected_out_size()
        self.preview_widget.set_output_size(out_w, out_h)

        if self.slider_frame.maximum() > 0:
            self.slider_frame.setValue(0)
        self._show_frame(self.slider_frame.value(), reset_crop=True)

        self._refresh_ui()

    def _load_gif(self, path: str):
        p = Path(path)
        if p.suffix.lower() != ".gif":
            raise ValueError(f"Файл не является GIF: {path}")

        img = Image.open(p)
        if img.width == 0 or img.height == 0:
            img.close()
            raise ValueError("GIF имеет нулевой размер")

        frames: list[Image.Image] = []
        try:
            n_frames = getattr(img, "n_frames", 1)
            if n_frames <= 0:
                raise ValueError("GIF не содержит кадров")

            for frame in ImageSequence.Iterator(img):
                frames.append(frame.convert("RGBA"))
                if len(frames) > 4096:
                    break
        finally:
            img.close()

        if not frames:
            raise ValueError("GIF не содержит кадров")

        self._frames_pil = frames
        self._preview_cache.clear()
        self.slider_frame.setRange(0, len(frames) - 1)

    # ---------------- Preview ----------------

    def _show_frame(self, idx: int, *, reset_crop: bool = False):
        if not self._frames_pil:
            return
        idx = max(0, min(len(self._frames_pil) - 1, int(idx)))

        pm = self._preview_cache.get(idx)
        if pm is None:
            pm = _pil_to_preview_pixmap(self._frames_pil[idx])
            self._preview_cache[idx] = pm

        # reset_crop=False: рамка crop сохраняется при переключении кадров
        self.preview_widget.set_pixmap(pm, reset_crop=reset_crop)
        self.lbl_frame_idx.setText(f"{idx + 1}/{len(self._frames_pil)}")

    # ---------------- Export ----------------

    def _on_export(self):
        if self._exporting or not self._input_path or not self._frames_pil:
            return

        out_dir = QFileDialog.getExistingDirectory(self, tr("gif.export_dir"))
        if not out_dir:
            return

        out_w, out_h = self._selected_out_size()
        left, top, right, bottom = self.preview_widget.get_crop_rect_in_source()

        # Экспорт всех кадров (до 4096) выполняется в фоновом потоке (A2),
        # чтобы UI не зависал на время обработки.
        self._exporting = True
        self._export_out_dir = out_dir
        self.btn_export.setEnabled(False)
        self.btn_export.setText(tr("gif.exporting"))

        self._bg.run(
            FlipperImageProcessor.export_gif_frames_custom_crop_to_png,
            on_done=self._on_export_done,
            on_error=self._on_export_error,
            kwargs={
                "input_path": str(self._input_path),
                "output_dir": out_dir,
                "output_w": out_w,
                "output_h": out_h,
                "crop_left": left,
                "crop_top": top,
                "crop_right": right,
                "crop_bottom": bottom,
            },
        )

    def _on_export_done(self, saved: list):
        self._exporting = False
        self.btn_export.setEnabled(True)
        self.btn_export.setText(tr("gif.btn_export"))
        msg = trf("gif.exported", count=len(saved), dir=self._export_out_dir)
        QMessageBox.information(self, tr("dlg.done"), msg)

    def _on_export_error(self, message: str):
        self._exporting = False
        self.btn_export.setEnabled(True)
        self.btn_export.setText(tr("gif.btn_export"))
        QMessageBox.critical(self, tr("dlg.error"), message)


__all__ = ["GifCropEditorWidget"]