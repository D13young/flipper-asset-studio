import os
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QListWidget, QLabel, QTabWidget,
    QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QFileDialog, QMessageBox, QCheckBox, QTextEdit,
)

from PyQt6.QtCore import Qt, QSize, QTimer
from pathlib import Path


from core.image_processor import FlipperImageProcessor
from core.animation_manager import FlipperAnimationManager
from core.exporter import FlipperExporter
from ui.animation_timeline import AnimationTimelineWidget
from ui.icon_editor import IconEditorWidget
from core.icon_builder import FlipperIconBuilder
from ui.drag_drop_widget import DragDropArea
from ui.validator_widget import ValidatorWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flipper Asset Studio")
        self.resize(1280, 840)
        
        # Данные приложения
        self.current_asset_path = None
        self.anim_manager = FlipperAnimationManager()
        
        # Состояние анимации
        self.anim_timer = QTimer(self)
        self.anim_timer.setSingleShot(False)
        self.anim_timer.timeout.connect(self._next_anim_frame)
        self._anim_frames = []
        self._anim_idx = 0

        # Инициализация UI
        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Левая панель (Навигация) ---
        self.nav_list = QListWidget()
        self.nav_list.addItems([
            "️ Single Image",
            "🎞️ Animation Builder",
            "📜 Meta Preview",
            "📷 JPG Crop → PNG",
            "📱 Icons",
            "🔍 Validator",
            "📺 BM/BMX Preview",
        ])



        self.nav_list.setFixedWidth(220)
        splitter.addWidget(self.nav_list)

        # --- Правая панель (Контент) ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Вкладка: Single Image с Drag-and-Drop
        tab_single = QWidget()

        sl = QVBoxLayout(tab_single)
        
        # Drag-and-Drop область
        self.drag_drop = DragDropArea("📥 Перетащите PNG или нажмите Import", [".png"])
        self.drag_drop.files_dropped.connect(self._on_files_dropped)
        sl.addWidget(self.drag_drop)
        
        # Или обычный превью
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(384, 192)
        self.preview_label.setStyleSheet("QLabel { background: #0a0a0a; border: 2px solid #333; color: #666; font-size: 14px; }")
        self.preview_label.setText("📥 Импортируйте PNG")
        self.preview_label.setScaledContents(True)
        self.preview_label.setVisible(False)  # Скрыт по умолчанию
        sl.addWidget(self.preview_label)

        
        self.dither_cb = QCheckBox("Floyd-Steinberg Dithering")
        self.dither_cb.setChecked(True)
        sl.addWidget(self.dither_cb)

        # 2. Вкладка: Animation
        self.anim_preview = QLabel()
        self.anim_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.anim_preview.setFixedHeight(192)
        self.anim_preview.setStyleSheet("QLabel { background: #0a0a0a; border: 2px solid #333; color: #888; font-size: 14px; }")
        self.anim_preview.setText("Добавьте кадры для предпросмотра")
        
        self.anim_timeline = AnimationTimelineWidget(self.anim_manager)
        tab_anim = QWidget()
        al = QVBoxLayout(tab_anim)
        al.addWidget(self.anim_preview)
        al.addWidget(self.anim_timeline)

        # 3. Вкладка: Meta
        tab_meta = QWidget()
        ml = QVBoxLayout(tab_meta)
        self.meta_text = QTextEdit()
        self.meta_text.setReadOnly(True)
        self.meta_text.setStyleSheet("QTextEdit { background: #111; color: #0f0; font-family: 'Consolas', monospace; font-size: 12px; }")
        ml.addWidget(self.meta_text)
        tab_meta.setLayout(ml)

        # 4. Вкладка: Icons
        self.icon_editor = IconEditorWidget()
        tab_icons = QWidget()
        il = QVBoxLayout(tab_icons)
        il.addWidget(self.icon_editor)
        tab_icons.setLayout(il)

        # 5. Вкладка: Validator
        self.validator_widget = ValidatorWidget()
        tab_validator = QWidget()
        vl = QVBoxLayout(tab_validator)
        vl.addWidget(self.validator_widget)
        tab_validator.setLayout(vl)

        # 6. Вкладка: BM/BMX Preview
        self.bm_bmx_preview_drop = DragDropArea("📺 Drop .bm / .bmx to preview", [".bm", ".bmx"])
        self.bm_bmx_preview_label = QLabel()
        self.bm_bmx_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bm_bmx_preview_label.setMinimumSize(384, 192)
        self.bm_bmx_preview_label.setStyleSheet("QLabel { background: #0a0a0a; border: 2px solid #333; color: #666; font-size: 14px; }")
        self.bm_bmx_preview_label.setText("📺 Загружайте .bm / .bmx")
        self.bm_bmx_preview_label.setScaledContents(True)

        tab_bm_bmx = QWidget()
        bml = QVBoxLayout(tab_bm_bmx)
        bml.addWidget(self.bm_bmx_preview_drop)
        bml.addWidget(self.bm_bmx_preview_label)
        tab_bm_bmx.setLayout(bml)

        self.bm_bmx_preview_drop.files_dropped.connect(self._on_bm_bmx_files_dropped)

        # 7. Вкладка: Create (ручная отрисовка)

        from ui.create_editor import CreateEditorWidget
        from ui.jpg_crop_editor import JpegCropEditorWidget
        self.jpg_crop_editor = JpegCropEditorWidget()
        
        tab_jpg_crop = QWidget()
        jl = QVBoxLayout(tab_jpg_crop)
        jl.addWidget(self.jpg_crop_editor)
        tab_jpg_crop.setLayout(jl)

        self.create_editor = CreateEditorWidget()

        tab_create = QWidget()
        cl = QVBoxLayout(tab_create)
        cl.addWidget(self.create_editor)
        tab_create.setLayout(cl)

        # Сборка табов
        self.tabs = QTabWidget()
        self.tabs.addTab(tab_create, "➕ Create")
        self.tabs.addTab(tab_single, "🖼️ Single")
        self.tabs.addTab(tab_jpg_crop, "📷 JPG Crop")

        self.tabs.addTab(tab_anim, "🎞️ Animation")
        self.tabs.addTab(tab_meta, "📜 Meta")
        self.tabs.addTab(tab_icons, "📱 Icons")
        self.tabs.addTab(tab_validator, "🔍 Validator")
        self.tabs.addTab(tab_bm_bmx, "📺 BM/BMX")

        right_layout.addWidget(self.tabs)


        splitter.addWidget(right)
        splitter.setSizes([220, 1060])
        layout.addWidget(splitter)

    def _setup_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setFixedHeight(36)
        self.addToolBar(tb)
        
        # Кнопки
        self.btn_import = QPushButton(" Import PNG")
        self.btn_import.setFixedWidth(130)
        
        self.btn_export = QPushButton("💾 Export Pack")
        self.btn_export.setFixedWidth(130)

        self.btn_exit = QPushButton("🚪 Exit")
        self.btn_exit.setFixedWidth(90)

        tb.addWidget(self.btn_import)
        tb.addSeparator()
        tb.addWidget(self.btn_export)
        tb.addSeparator()
        tb.addWidget(self.btn_exit)

    def _setup_statusbar(self):
        self.statusBar().showMessage("Готово. Выберите PNG или добавьте кадры анимации.")

    def _connect_signals(self):
        # Кнопки
        self.btn_import.clicked.connect(self._import_png)
        self.btn_export.clicked.connect(self._export_pack)
        self.btn_exit.clicked.connect(self.close)
        
        # Чекбокс
        self.dither_cb.stateChanged.connect(self._process_single)

        
        # Навигация
        self.nav_list.currentRowChanged.connect(self.tabs.setCurrentIndex)
        
        # Таймлайн -> Превью и Мета
        self.anim_timeline.frames_updated.connect(self._on_anim_frames_updated)
        self.anim_timeline.meta_updated.connect(self.meta_text.setPlainText)
        
        # Изменение FPS -> Перезапуск таймера
        self.anim_timeline.spin_fps.valueChanged.connect(self._restart_animation)

        # Сигнал от редактора иконок
        self.icon_editor.icon_ready.connect(self._on_icon_data_ready)
        self.create_editor.icon_ready.connect(self._on_create_icon_data_ready)


    def _on_bm_bmx_files_dropped(self, files: list):
        if not files:
            return

        from core.bm_bmx_decoder import FlipperBmBmxDecoder
        from PyQt6.QtGui import QPixmap

        p = files[0]
        try:
            pm, w, h = FlipperBmBmxDecoder.load_frame_as_pixmap(p, scale=3)
            self.bm_bmx_preview_label.setPixmap(pm)
            self.bm_bmx_preview_label.setText("")
            self.statusBar().showMessage(f"✅ {Path(p).name} | {w}x{h}", 3000)
        except Exception as e:
            self.bm_bmx_preview_label.setPixmap(QPixmap())
            self.bm_bmx_preview_label.setText(f"❌ {e}")
            self.statusBar().showMessage(f"❌ {Path(p).name}: {e}", 5000)

    def _import_png(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PNG", "", "PNG Images (*.png)")
        if path:
            self.current_asset_path = path
            self.statusBar().showMessage(f"📄 {os.path.basename(path)}", 3000)
            self._process_single()



    def _process_single(self):
        if not self.current_asset_path:
            self.preview_label.setVisible(False)
            return

        try:
            dither_level = 1 if self.dither_cb.isChecked() else 0
            d = FlipperImageProcessor.process_png(self.current_asset_path, dither_level=dither_level)

            self.preview_label.setPixmap(d["preview"])
            self.preview_label.setVisible(True)
            self.statusBar().showMessage(f"✅ 128x64 | {d['byte_length']}B", 3000)
        except Exception as e:
            self.preview_label.setVisible(False)
            self.statusBar().showMessage(f"❌ Ошибка: {e}", 5000)


    def _on_icon_data_ready(self, app_name, paths, w, h, fps):
        """Вызывается, когда во вкладке Icons изменены данные"""
        pass

    def _on_create_icon_data_ready(self, app_name, frame_bytes_list, w, h, fps):
        """Вызывается, когда во вкладке Create изменены данные"""
        pass


    # --- Логика Анимации ---

    def _on_anim_frames_updated(self, frames_bytes):
        """Вызывается, когда в таймлайне изменились кадры"""
        self._anim_frames = frames_bytes
        self._anim_idx = 0
        if frames_bytes:
            self._restart_animation()
        else:
            self.anim_timer.stop()
            self.anim_preview.setText("Добавьте кадры")

    def _restart_animation(self):
        """Сброс и запуск таймера"""
        if not self._anim_frames: return
        
        self.anim_timer.stop()
        fps = max(1, self.anim_manager.meta_params["frame_rate"])
        self.anim_timer.setInterval(1000 // fps)
        self.anim_timer.start()
        
        self._next_anim_frame()

    def _next_anim_frame(self):
        """Тик таймера"""
        if not self._anim_frames: return
        
        # Циклический индекс
        idx = self._anim_idx % len(self._anim_frames)
        
        # Конвертация байтов в QPixmap
        pm = FlipperImageProcessor.bytes_to_preview(self._anim_frames[idx])
        self.anim_preview.setPixmap(pm)
        
        self._anim_idx += 1
        
    def _on_files_dropped(self, files: list):
        """Обработка сброшенных файлов"""
        if files:
            # Берем первый файл
            self.current_asset_path = files[0]
            self.statusBar().showMessage(f"📄 Drag&Drop: {len(files)} файл(ов)", 3000)
            self._process_single()
            
            active_tab = self.tabs.currentWidget()

            if active_tab == self.icon_editor.parent():
                for p in files:
                    item = self.icon_editor.frame_list.findItems(Path(p).name, Qt.MatchFlag.MatchExactly)
                    if item:
                        continue
                    from PyQt6.QtWidgets import QListWidgetItem
                    new_item = QListWidgetItem(Path(p).name)
                    new_item.setData(Qt.ItemDataRole.UserRole, p)
                    self.icon_editor.frame_list.addItem(new_item)
                self.icon_editor._emit_ready()

            elif active_tab == self.anim_timeline.parent():
                for f in files:
                    self.anim_manager.add_frame(f, dither_level=int(self.anim_timeline.spin_dither_level.value()))
                self.anim_timeline._refresh_list()
                self.anim_timeline._emit_updates()


            else:
                if len(files) > 1:
                    reply = QMessageBox.question(
                        self,
                        "Добавить в анимацию?",
                        f"Обнаружено {len(files)} файлов. Добавить их в анимацию?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.tabs.setCurrentIndex(1)
                        for f in files:
                            self.anim_manager.add_frame(f)

                        self.anim_timeline._refresh_list()
                        self.anim_timeline._emit_updates()



    def _import_png(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PNG", "", "PNG Images (*.png)")
        if path:
            self.current_asset_path = path
            self.statusBar().showMessage(f"📄 {os.path.basename(path)}", 3000)
            self._process_single()    

    # --- Логика Экспорта ---

    def _export_pack(self):
        # Определяем, какая вкладка активна
        active_tab = self.tabs.currentWidget()
        out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку экспорта")
        if not out_dir: return

        try:
            if active_tab == self.anim_timeline.parent(): 
                # ЭКСПОРТ АНИМАЦИИ (Дельфин)
                if not self.anim_manager.frames:
                    raise ValueError("Нет кадров анимации")
                
                meta = self.anim_manager.generate_meta_txt()
                manifest = self.anim_manager.generate_manifest_txt(
                    self.anim_timeline.line_name.text(),
                    self.anim_timeline.spin_bh_min.value(),
                    self.anim_timeline.spin_bh_max.value(),
                    self.anim_timeline.spin_lv_min.value(),
                    self.anim_timeline.spin_lv_max.value(),
                    self.anim_timeline.spin_weight.value(),
                )
                
                anim_name = self.anim_timeline.line_name.text()
                anims_out_dir = Path(out_dir) / "Anims"

                meta_txt = meta
                manifest_txt = manifest

                FlipperExporter.export_animation(
                    self.anim_manager.get_frame_bytes_list(),
                    meta_txt,
                    manifest_txt,
                    anim_name,
                    anims_out_dir,
                    compressed=False,

                    create_zip=False
                )

                anim_dir = anims_out_dir / anim_name
                (anim_dir / "manifest.txt").unlink(missing_ok=True)

                # Momentum ожидает manifest.txt в корне папки Anims/.
                (anims_out_dir / "manifest.txt").write_text(manifest_txt, encoding="utf-8")


                msg = "Анимация экспортирована!"

            elif active_tab == self.create_editor.parent():

                frame_bytes_list = self.create_editor.get_frames_bytes_list()
                w, h, fps = self.create_editor.get_params()
                app_name = self.create_editor.app_name_edit.text()

                count = len(frame_bytes_list)
                if count == 0:
                    raise ValueError("Нет кадров для экспорта")

                target_folder = Path(out_dir) / "Icons" / app_name
                FlipperIconBuilder.export_icon(
                    frame_bytes_list, w, h, fps,
                    output_folder=target_folder, compress=True
                )
                msg = f"Create: иконка/анимация '{app_name}' экспортирована!"

            elif active_tab == self.icon_editor.parent():


                # ЭКСПОРТ ИКОНКИ
                count = self.icon_editor.frame_list.count()
                if count == 0:
                    raise ValueError("Нет кадров иконки")
                
                paths = [self.icon_editor.frame_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(count)]
                w = self.icon_editor.spin_w.value()
                h = self.icon_editor.spin_h.value()
                fps = self.icon_editor.spin_fps.value()
                app_name = self.icon_editor.app_name_edit.text()

                # Конвертируем PNG в байты Flipper
                frame_bytes_list = []
                for p in paths:
                    proc = FlipperImageProcessor.process_png(p, dither=True)
                    frame_bytes_list.append(proc["bytes"])


                target_folder = Path(out_dir) / "Icons" / app_name
                (Path(out_dir) / "Anims").mkdir(parents=True, exist_ok=True)
                FlipperIconBuilder.export_icon(

                    frame_bytes_list, w, h, fps, 
                    output_folder=target_folder, compress=True
                )
                msg = f"Иконка для '{app_name}' экспортирована!"
            
            else:
                msg = "Выберите вкладку с контентом для экспорта"
            
            self.statusBar().showMessage(f"✅ {msg}", 5000)
            QMessageBox.information(self, "Готово", msg)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))