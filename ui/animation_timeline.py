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
    QGridLayout,
    QLineEdit,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.animation_manager import FlipperAnimationManager
from ui.drag_drop_widget import DragDropArea

class AnimationTimelineWidget(QWidget):
    frames_updated = pyqtSignal(list)
    meta_updated = pyqtSignal(str)

    def __init__(self, manager: FlipperAnimationManager):
        super().__init__()
        self.manager = manager
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(4, 4, 4, 4)

        # Drag-and-Drop область для кадров
        # кадры добавляются в FlipperAnimationManager и автоматически триггерят обновление UI/preview/meta.

        self.drop_area = DragDropArea("📥 Перетащите PNG кадры сюда", [".png"])
        self.drop_area.files_dropped.connect(self._on_frames_dropped)
        layout.addWidget(self.drop_area)

        # Список кадров
        self.frame_list = QListWidget()
        from PyQt6.QtCore import QSize
        self.frame_list.setIconSize(QSize(96, 48))
        from PyQt6.QtWidgets import QListView
        self.frame_list.setFlow(QListView.Flow.LeftToRight)
        self.frame_list.setSpacing(4)

        layout.addWidget(self.frame_list)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Add Frames")
        self.btn_up = QPushButton("⬆️ Move Up")
        self.btn_down = QPushButton("⬇️ Move Down")
        self.btn_remove = QPushButton("❌ Remove")
        self.btn_clear = QPushButton("🧼 Clear")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        # Параметры анимации
        param_group = QGroupBox("⚙️ Animation Parameters")
        param_layout = QGridLayout()
        param_layout.setHorizontalSpacing(16)
        param_layout.setVerticalSpacing(8)

        self.spin_fps = QSpinBox(); self.spin_fps.setRange(1, 60); self.spin_fps.setValue(2)
        self.spin_duration = QSpinBox(); self.spin_duration.setRange(100, 99999); self.spin_duration.setValue(3600)
        self.line_name = QLineEdit("CustomDolphin")
        self.spin_bh_min = QSpinBox(); self.spin_bh_min.setRange(0, 14)
        self.spin_bh_max = QSpinBox(); self.spin_bh_max.setRange(0, 18); self.spin_bh_max.setValue(14)
        self.spin_lv_min = QSpinBox(); self.spin_lv_min.setRange(1, 30)
        self.spin_lv_max = QSpinBox(); self.spin_lv_max.setRange(1, 30); self.spin_lv_max.setValue(30)
        self.spin_weight = QSpinBox(); self.spin_weight.setRange(1, 20); self.spin_weight.setValue(8)

        self.spin_dither_level = QSpinBox(); self.spin_dither_level.setRange(0, 3); self.spin_dither_level.setValue(1)

        param_layout.addWidget(QLabel("Dither Level:"), 0, 0)
        param_layout.addWidget(self.spin_dither_level, 0, 1)
        param_layout.addWidget(QLabel("Frame Rate (FPS):"), 0, 2)
        param_layout.addWidget(self.spin_fps, 0, 3)

        param_layout.addWidget(QLabel("Duration (ms):"), 1, 0)
        param_layout.addWidget(self.spin_duration, 1, 1)
        param_layout.addWidget(QLabel("Animation Name:"), 1, 2)
        param_layout.addWidget(self.line_name, 1, 3)

        param_layout.addWidget(QLabel("Min Butthurt:"), 2, 0)
        param_layout.addWidget(self.spin_bh_min, 2, 1)
        param_layout.addWidget(QLabel("Max Butthurt:"), 2, 2)
        param_layout.addWidget(self.spin_bh_max, 2, 3)

        param_layout.addWidget(QLabel("Min Level:"), 3, 0)
        param_layout.addWidget(self.spin_lv_min, 3, 1)
        param_layout.addWidget(QLabel("Max Level:"), 3, 2)
        param_layout.addWidget(self.spin_lv_max, 3, 3)

        param_layout.addWidget(QLabel("Weight:"), 4, 0)
        param_layout.addWidget(self.spin_weight, 4, 1)

        param_layout.setColumnStretch(1, 1)
        param_layout.setColumnStretch(3, 1)

        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

    def _connect_signals(self):
        self.btn_add.clicked.connect(self._add_frames)
        self.btn_up.clicked.connect(lambda: self._move_frame(-1))
        self.btn_down.clicked.connect(lambda: self._move_frame(1))
        self.btn_remove.clicked.connect(self._remove_frame)
        self.btn_clear.clicked.connect(self._clear_frames)
        self.frame_list.currentRowChanged.connect(self._on_selection_changed)

        for widget in [self.spin_fps, self.spin_duration, self.spin_bh_min, self.spin_bh_max,
                       self.spin_lv_min, self.spin_lv_max, self.spin_weight]:
            widget.valueChanged.connect(self._emit_meta)

        self.spin_dither_level.valueChanged.connect(self._on_dither_level_changed)

        # QLineEdit меняется через textChanged
        self.line_name.textChanged.connect(self._emit_meta)

    def _on_frames_dropped(self, paths: list):
        if not paths:
            return
        dither_level = int(self.spin_dither_level.value())
        for p in sorted(paths):
            self.manager.add_frame(p, dither_level=dither_level)
        self._refresh_list()
        self._emit_updates()

    def _add_frames(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Animation Frames", "", "PNG Images (*.png)")
        if paths:
            dither_level = int(self.spin_dither_level.value())
            for p in sorted(paths):
                self.manager.add_frame(p, dither_level=dither_level)
            self._refresh_list()
            self._emit_updates()

    def _move_frame(self, direction):
        curr = self.frame_list.currentRow()
        if curr < 0: return
        new_idx = curr + direction
        if 0 <= new_idx < len(self.manager.frames):
            self.manager.move_frame(curr, new_idx)
            self._refresh_list()
            self.frame_list.setCurrentRow(new_idx)
            self._emit_updates()

    def _remove_frame(self):
        curr = self.frame_list.currentRow()
        if curr >= 0:
            self.manager.remove_frame(curr)
            self._refresh_list()
            self._emit_updates()

    def _clear_frames(self):
        # Удаляем все кадры из менеджера
        self.manager.frames.clear()
        self.manager.meta_params["passive_frames"] = 0
        self.manager.meta_params["frame_rate"] = self.spin_fps.value()
        self.manager.meta_params["dither_level"] = int(self.spin_dither_level.value())

        self._refresh_list()
        self._emit_updates()

    def _refresh_list(self):
        self.frame_list.clear()
        for i, f in enumerate(self.manager.frames):
            item = QListWidgetItem(f"Frame {i}")
            pm = f["preview"].scaled(96, 48, Qt.AspectRatioMode.KeepAspectRatio)
            from PyQt6.QtGui import QIcon
            item.setIcon(QIcon(pm))

            item.setData(Qt.ItemDataRole.UserRole, i)
            self.frame_list.addItem(item)

    def _on_selection_changed(self, row):
        pass

    def _emit_updates(self):
        self.frames_updated.emit(self.manager.get_frame_bytes_list())
        self._emit_meta()

    def _on_dither_level_changed(self):
        # Пересчёт текущих кадров, чтобы превью менялось сразу.
        dither_level = int(self.spin_dither_level.value())
        if self.manager.frames:
            self.manager.reprocess_frames(dither_level)
            self._refresh_list()
            self._emit_updates()

    def _emit_meta(self):

        self.manager.meta_params["frame_rate"] = self.spin_fps.value()
        self.manager.meta_params["duration"] = self.spin_duration.value()
        meta = self.manager.generate_meta_txt()
        manifest = self.manager.generate_manifest_txt(
            self.line_name.text(),
            self.spin_bh_min.value(), self.spin_bh_max.value(),
            self.spin_lv_min.value(), self.spin_lv_max.value(),
            self.spin_weight.value()
        )
        self.meta_updated.emit(f"--- meta.txt ---\n{meta}\n\n--- manifest.txt ---\n{manifest}")
