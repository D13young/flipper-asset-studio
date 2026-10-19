"""Тесты вкладки Icons: выбор папки (Name) -> список файлов (File) -> экспорт.

Проверяет:
- пресеты ICON_PRESETS (папки/файлы/размеры);
- синхронизацию File с Name и автоподстановку W/H в IconEditorWidget;
- сигнал icon_ready с именем выбранной папки;
- экспорт: создаётся папка с именем Name и файл с именем File.
"""
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

# Безопасный рендеринг Qt в headless-окружении (CI / терминал)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from core.icon_builder import ICON_PRESETS


class TestIconPresets(unittest.TestCase):
    """Пресеты папок/файлов/размеров для вкладки Icons."""

    def test_preset_folders_order(self):
        self.assertEqual(
            list(ICON_PRESETS.keys()),
            ["Dolphin", "NFC", "RFID", "SubGhz", "Passport"],
        )

    def test_preset_files_and_sizes(self):
        self.assertEqual(ICON_PRESETS["Dolphin"]["DolphinSuccess_91x55"], (91, 55))
        self.assertEqual(ICON_PRESETS["NFC"]["NFC_dolphin_emulation_51x64"], (51, 64))
        self.assertEqual(ICON_PRESETS["RFID"]["RFIDDolphinReceive_97x61"], (97, 61))
        self.assertEqual(ICON_PRESETS["RFID"]["RFIDDolphinSend_97x61"], (97, 61))
        self.assertEqual(ICON_PRESETS["SubGhz"]["Fishing_123x52"], (123, 52))
        self.assertEqual(ICON_PRESETS["SubGhz"]["Scanning_123x52"], (123, 52))
        self.assertEqual(ICON_PRESETS["Passport"]["passport_128x64"], (128, 64))
        self.assertEqual(ICON_PRESETS["Passport"]["passport_bad_46x49"], (46, 49))
        self.assertEqual(ICON_PRESETS["Passport"]["passport_happy_46x49"], (46, 49))
        self.assertEqual(ICON_PRESETS["Passport"]["passport_okay_46x49"], (46, 49))

    def test_dims_match_file_suffix(self):
        # Имя файла содержит размер WxH — пресет обязан ему соответствовать
        for folder, files in ICON_PRESETS.items():
            for name, (w, h) in files.items():
                self.assertIn(
                    f"{w}x{h}", name,
                    f"[{folder}] размер {w}x{h} не совпадает с именем файла {name}",
                )


class TestIconEditorWidget(unittest.TestCase):
    """UI-логика виджета Icons: Name -> File -> W/H."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        from ui.icon_editor import IconEditorWidget
        self.w = IconEditorWidget()

    def tearDown(self):
        self.w.deleteLater()

    def test_default_selection_is_passport(self):
        self.assertEqual(self.w.name_cb.currentText(), "Passport")
        self.assertEqual(self.w.file_cb.currentText(), "passport_128x64")
        self.assertEqual((self.w.spin_w.value(), self.w.spin_h.value()), (128, 64))

    def test_subghz_file_list_and_dims(self):
        self.w.name_cb.setCurrentText("SubGhz")
        self.assertEqual(
            [self.w.file_cb.itemText(i) for i in range(self.w.file_cb.count())],
            ["Fishing_123x52", "Scanning_123x52"],
        )
        self.assertEqual(self.w.file_cb.currentText(), "Fishing_123x52")
        self.assertEqual((self.w.spin_w.value(), self.w.spin_h.value()), (123, 52))

    def test_dolphin_nfc_file_lists(self):
        self.w.name_cb.setCurrentText("Dolphin")
        self.assertEqual(self.w.file_cb.currentText(), "DolphinSuccess_91x55")
        self.assertEqual((self.w.spin_w.value(), self.w.spin_h.value()), (91, 55))

        self.w.name_cb.setCurrentText("NFC")
        self.assertEqual(self.w.file_cb.currentText(), "NFC_dolphin_emulation_51x64")
        self.assertEqual((self.w.spin_w.value(), self.w.spin_h.value()), (51, 64))

    def test_switch_file_updates_dims(self):
        self.w.name_cb.setCurrentText("RFID")
        self.w.file_cb.setCurrentText("RFIDDolphinSend_97x61")
        self.assertEqual((self.w.spin_w.value(), self.w.spin_h.value()), (97, 61))

    def test_passport_files_preserve_all_variants(self):
        self.w.name_cb.setCurrentText("Passport")
        self.assertEqual(
            [self.w.file_cb.itemText(i) for i in range(self.w.file_cb.count())],
            [
                "passport_128x64",
                "passport_bad_46x49",
                "passport_happy_46x49",
                "passport_okay_46x49",
            ],
        )
        # Выбор small-варианта подставляет 46x49
        self.w.file_cb.setCurrentText("passport_okay_46x49")
        self.assertEqual((self.w.spin_w.value(), self.w.spin_h.value()), (46, 49))

    def test_emit_ready_uses_folder_name(self):
        received = {}
        self.w.icon_ready.connect(
            lambda name, payload, w, h, d: received.update(name=name, w=w, h=h)
        )
        self.w.name_cb.setCurrentText("SubGhz")
        self.w._emit_ready()
        self.assertEqual(received["name"], "SubGhz")
        self.assertEqual((received["w"], received["h"]), (123, 52))


class TestIconsExportEndToEnd(unittest.TestCase):
    """Экспорт Icons: папка = Name, файл = File (как было с Passport)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def test_export_creates_folder_named_by_name(self):
        from PIL import Image
        from ui.main_window import MainWindow

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            src = tmp / "src.png"
            Image.new("L", (123, 52), 255).save(src, format="PNG")

            win = MainWindow()
            try:
                win.icon_editor.name_cb.setCurrentText("SubGhz")
                win.icon_editor.file_cb.setCurrentText("Fishing_123x52")
                win.icon_editor.add_frames([str(src)])

                msg = win._export_icons_pack(tmp / "out")

                self.assertIn("Fishing_123x52", msg)
                out_file = tmp / "out" / "SubGhz" / "Fishing_123x52.bmx"
                self.assertTrue(
                    out_file.exists(),
                    "Должен создаться out/SubGhz/Fishing_123x52.bmx",
                )
                # .bmx начинается с заголовка width/height (<II)
                w, h = struct.unpack("<II", out_file.read_bytes()[:8])
                self.assertEqual((w, h), (123, 52))
            finally:
                win.close()
                win.deleteLater()


if __name__ == "__main__":
    unittest.main()

