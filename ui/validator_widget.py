from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QFileDialog,
                             QProgressBar, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from pathlib import Path
from core.validator import FlipperAssetPackValidator, ValidationLevel

class ValidatorWidget(QWidget):
    """Виджет для валидации Asset Pack"""
    
    pack_validated = pyqtSignal(bool)  # Сигнал о результате валидации
    
    def __init__(self):
        super().__init__()
        self.validator = FlipperAssetPackValidator()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("📁 Выбрать Asset Pack")
        self.btn_validate = QPushButton("✅ Проверить")
        self.btn_validate.setEnabled(False)
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_validate)
        layout.addLayout(btn_layout)

        # Путь к папке
        self.lbl_path = QLabel("Папка не выбрана")
        self.lbl_path.setStyleSheet("QLabel { color: #888; font-style: italic; }")
        layout.addWidget(self.lbl_path)

        # Прогресс
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Результаты
        results_group = QGroupBox("📋 Результаты проверки")
        results_layout = QVBoxLayout()
        
        self.results_list = QListWidget()
        self.results_list.setAlternatingRowColors(True)
        self.results_list.setStyleSheet("""
            QListWidget {
                background-color: #0a0a0a;
                border: 1px solid #333;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #1a1a1a;
            }
        """)
        results_layout.addWidget(self.results_list)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Статистика
        self.lbl_stats = QLabel("Статистика: -")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setStyleSheet("QLabel { font-weight: bold; color: #666; }")
        layout.addWidget(self.lbl_stats)

        # Подключение сигналов
        self.btn_select.clicked.connect(self._select_pack)
        self.btn_validate.clicked.connect(self._validate_pack)

    def _select_pack(self):
        """Выбор папки Asset Pack"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Выберите папку Asset Pack",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.current_pack_path = Path(folder)
            self.lbl_path.setText(f"📂 {folder}")
            self.lbl_path.setStyleSheet("QLabel { color: #0f0; }")
            self.btn_validate.setEnabled(True)
            self.results_list.clear()
            self.lbl_stats.setText("Статистика: -")

    def _validate_pack(self):
        """Запуск валидации"""
        if not hasattr(self, 'current_pack_path'):
            return

        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Бесконечная анимация
        self.results_list.clear()
        
        # Запуск валидации
        results = self.validator.validate_pack(self.current_pack_path)
        
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        
        # Отображение результатов
        for i, result in enumerate(results):
            item = QListWidgetItem(self._format_result(result))
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            # Цвет в зависимости от уровня
            if result.level == ValidationLevel.ERROR:
                item.setForeground(QColor("#ff4444"))
                item.setBackground(QColor("#3a0000"))
            elif result.level == ValidationLevel.WARNING:
                item.setForeground(QColor("#ffaa00"))
                item.setBackground(QColor("#3a2a00"))
            elif result.level == ValidationLevel.SUCCESS:
                item.setForeground(QColor("#00ff00"))
                item.setBackground(QColor("#003a00"))
            else:
                item.setForeground(QColor("#888888"))
            
            self.results_list.addItem(item)
            
            # Анимация появления
            self.progress.setValue(int((i + 1) / len(results) * 100))

        # Статистика
        summary = self.validator.get_summary()
        stats_text = (
            f"📊 Всего: {sum(summary.values())} | "
            f"✅ Успешно: {summary['success']} | "
            f"ℹ️ Инфо: {summary['info']} | "
            f"⚠️ Предупреждения: {summary['warning']} | "
            f"❌ Ошибки: {summary['error']}"
        )
        self.lbl_stats.setText(stats_text)
        
        # Определение общего результата
        has_errors = summary['error'] > 0
        self.pack_validated.emit(not has_errors)
        
        self.progress.setVisible(False)

    def _format_result(self, result) -> str:
        """Форматирование строки результата"""
        icon = {
            ValidationLevel.ERROR: "❌",
            ValidationLevel.WARNING: "⚠️",
            ValidationLevel.SUCCESS: "✅",
            ValidationLevel.INFO: "ℹ️"
        }.get(result.level, "•")
        
        path_info = f" [{result.path}]" if result.path else ""
        return f"{icon} {result.message}{path_info}"

    def clear_results(self):
        """Очистка результатов"""
        self.results_list.clear()
        self.lbl_stats.setText("Статистика: -")
        self.btn_validate.setEnabled(False)