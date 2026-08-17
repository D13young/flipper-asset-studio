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
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.animation_manager import FlipperAnimationManager
from core.image_processor import FlipperImageProcessor
from ui.drag_drop_widget import DragDropArea
from ui.background import BackgroundRunner
from ui.i18n import tr, trf

class AnimationTimelineWidget(QWidget):
    frames_updated = pyqtSignal(list)
    meta_updated = pyqtSignal(str)

    def __init__(self, manager: FlipperAnimationManager):
        super().__init__()
        self.manager = manager
        self._bg = BackgroundRunner(self)
        self._reprocess_gen = 0  # защита от устаревших результатов репроцесса
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(4, 4, 4, 4)

        # Drag-and-Drop область для кадров
        # кадры добавляются в FlipperAnimationManager и автоматически триггерят обновление UI/preview/meta.

        self.drop_area = DragDropArea(tr("anim.drag_title"), [".png"])
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
        self.btn_add = QPushButton(tr("anim.btn_add"))
        self.btn_up = QPushButton(tr("anim.btn_up"))
        self.btn_down = QPushButton(tr("anim.btn_down"))
        self.btn_remove = QPushButton(tr("anim.btn_remove"))
        self.btn_clear = QPushButton(tr("anim.btn_clear"))
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        # Параметры анимации
        self.param_group = QGroupBox(tr("anim.group_params"))
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

        self.lbl_dither = QLabel(tr("anim.lbl_dither"))
        self.lbl_fps = QLabel(tr("anim.lbl_fps"))
        self.lbl_duration = QLabel(tr("anim.lbl_duration"))
        self.lbl_name = QLabel(tr("anim.lbl_name"))
        self.lbl_bh_min = QLabel(tr("anim.lbl_bh_min"))
        self.lbl_bh_max = QLabel(tr("anim.lbl_bh_max"))
        self.lbl_lv_min = QLabel(tr("anim.lbl_lv_min"))
        self.lbl_lv_max = QLabel(tr("anim.lbl_lv_max"))
        self.lbl_weight = QLabel(tr("anim.lbl_weight"))

        param_layout.addWidget(self.lbl_dither, 0, 0)
        param_layout.addWidget(self.spin_dither_level, 0, 1)
        param_layout.addWidget(self.lbl_fps, 0, 2)
        param_layout.addWidget(self.spin_fps, 0, 3)

        param_layout.addWidget(self.lbl_duration, 1, 0)
        param_layout.addWidget(self.spin_duration, 1, 1)
        param_layout.addWidget(self.lbl_name, 1, 2)
        param_layout.addWidget(self.line_name, 1, 3)

        param_layout.addWidget(self.lbl_bh_min, 2, 0)
        param_layout.addWidget(self.spin_bh_min, 2, 1)
        param_layout.addWidget(self.lbl_bh_max, 2, 2)
        param_layout.addWidget(self.spin_bh_max, 2, 3)

        param_layout.addWidget(self.lbl_lv_min, 3, 0)
        param_layout.addWidget(self.spin_lv_min, 3, 1)
        param_layout.addWidget(self.lbl_lv_max, 3, 2)
        param_layout.addWidget(self.spin_lv_max, 3, 3)

        param_layout.addWidget(self.lbl_weight, 4, 0)
        param_layout.addWidget(self.spin_weight, 4, 1)

        param_layout.setColumnStretch(1, 1)
        param_layout.setColumnStretch(3, 1)

        self.param_group.setLayout(param_layout)
        layout.addWidget(self.param_group)

    def retranslate(self):
        """Обновляет тексты при смене языка."""
        self.drop_area.set_text(tr("anim.drag_title"))
        self.btn_add.setText(tr("anim.btn_add"))
        self.btn_up.setText(tr("anim.btn_up"))
        self.btn_down.setText(tr("anim.btn_down"))
        self.btn_remove.setText(tr("anim.btn_remove"))
        self.btn_clear.setText(tr("anim.btn_clear"))
        self.param_group.setTitle(tr("anim.group_params"))
        self.lbl_dither.setText(tr("anim.lbl_dither"))
        self.lbl_fps.setText(tr("anim.lbl_fps"))
        self.lbl_duration.setText(tr("anim.lbl_duration"))
        self.lbl_name.setText(tr("anim.lbl_name"))
        self.lbl_bh_min.setText(tr("anim.lbl_bh_min"))
        self.lbl_bh_max.setText(tr("anim.lbl_bh_max"))
        self.lbl_lv_min.setText(tr("anim.lbl_lv_min"))
        self.lbl_lv_max.setText(tr("anim.lbl_lv_max"))
        self.lbl_weight.setText(tr("anim.lbl_weight"))
        # Обновляем подписи кадров
        for i in range(self.frame_list.count()):
            self.frame_list.item(i).setText(trf("anim.frame_item", index=i))

    def _connect_signals(self):
        self.btn_add.clicked.connect(self._add_frames)
        self.btn_up.clicked.connect(lambda: self._move_frame(-1))
        self.btn_down.clicked.connect(lambda: self._move_frame(1))
        self.btn_remove.clicked.connect(self._remove_frame)
        self.btn_clear.clicked.connect(self._clear_frames)

        for widget in [self.spin_fps, self.spin_duration, self.spin_bh_min, self.spin_bh_max,
                       self.spin_lv_min, self.spin_lv_max, self.spin_weight]:
            widget.valueChanged.connect(self._emit_meta)

        self.spin_dither_level.valueChanged.connect(self._on_dither_level_changed)

        # QLineEdit меняется через textChanged
        self.line_name.textChanged.connect(self._emit_meta)

    def import_paths(self, paths):
        """Асинхронный импорт кадров: обработка PNG — в фоновом потоке (A2)."""
        paths = [p for p in paths if p]
        if not paths:
            return
        dither_level = int(self.spin_dither_level.value())
        self._bg.run(
            self._process_paths_to_bytes,
            on_done=self._apply_processed_frames,
            on_error=self._on_process_error,
            args=(sorted(paths), dither_level),
        )

    @staticmethod
    def _process_paths_to_bytes(paths, dither_level):
        """Обработка PNG без QPixmap — безопасно для фонового потока."""
        return [
            (p, FlipperImageProcessor.process_png_to_bytes(p, dither_level=dither_level))
            for p in paths
        ]

    def _apply_processed_frames(self, pairs):
        """Применяет результат импорта в UI-потоке (QPixmap создаём здесь)."""
        for path, fb in pairs:
            self.manager.add_frame_bytes(
                path, fb, dither_level=int(self.spin_dither_level.value())
            )
            self.manager.frames[-1]["preview"] = FlipperImageProcessor.bytes_to_preview(fb)
        self._refresh_list()
        self._emit_updates()

    def _on_process_error(self, message):
        QMessageBox.warning(self, tr("dlg.error"), message)

    def _on_frames_dropped(self, paths: list):
        self.import_paths(paths)

    def _add_frames(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("anim.select_frames"), "", "PNG Images (*.png)"
        )
        self.import_paths(paths)

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
            item = QListWidgetItem(trf("anim.frame_item", index=i))
            pm = f["preview"].scaled(96, 48, Qt.AspectRatioMode.KeepAspectRatio)
            from PyQt6.QtGui import QIcon
            item.setIcon(QIcon(pm))

            item.setData(Qt.ItemDataRole.UserRole, i)
            self.frame_list.addItem(item)

    def _emit_updates(self):
        self.frames_updated.emit(self.manager.get_frame_bytes_list())
        self._emit_meta()

    def _on_dither_level_changed(self):
        # Пересчёт кадров в фоновом потоке; превью строится в UI-потоке (A2).
        if not self.manager.frames:
            return
        dither_level = int(self.spin_dither_level.value())
        self._reprocess_gen += 1
        gen = self._reprocess_gen

        def _done(pairs):
            # Применяем только результат последнего запроса (защита от гонки).
            if gen == self._reprocess_gen:
                self._apply_reprocessed_frames(pairs)

        self._bg.run(
            self.manager.reprocess_frames_to_bytes,
            on_done=_done,
            on_error=self._on_process_error,
            args=(dither_level,),
        )

    def _apply_reprocessed_frames(self, pairs):
        dither_level = int(self.spin_dither_level.value())
        for path, fb in pairs:
            for f in self.manager.frames:
                if f.get("path") == path:
                    f["bytes"] = fb
                    f["dither_level"] = dither_level
                    f["preview"] = FlipperImageProcessor.bytes_to_preview(fb)
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
