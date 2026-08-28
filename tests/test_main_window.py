"""UI-тесты главного окна: сворачивание левого меню и компоновка вкладки «Анимация»."""

import sys
import unittest

from PyQt6.QtWidgets import QApplication, QListWidget

from ui.main_window import MainWindow


class TestMainWindowLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        self.win = MainWindow()
        self.win.show()

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()

    # ── Пункт 3: левое меню можно «задвинуть» / скрыть ──

    def test_nav_collapsible_via_button(self):
        self.assertFalse(self.win.nav_list.isHidden())
        self.win._toggle_nav_menu()
        self.assertTrue(self.win.nav_list.isHidden())
        self.assertTrue(self.win.btn_menu.text().startswith("▶"))
        self.win._toggle_nav_menu()
        self.assertFalse(self.win.nav_list.isHidden())
        self.assertTrue(self.win.btn_menu.text().startswith("◀"))

    def test_nav_splitter_allows_collapse_of_left_menu(self):
        # левый (индекс 0) можно схлопнуть, правый блок с вкладками — нет
        self.assertTrue(self.win.main_splitter.isCollapsible(0))
        self.assertFalse(self.win.main_splitter.isCollapsible(1))

    # ── Пункт 2: предпросмотр над кадрами, DnD в левом блоке ──

    def test_anim_preview_above_timeline(self):
        right_layout = self.win.anim_right.layout()
        idx_preview = right_layout.indexOf(self.win.anim_preview_group)
        idx_timeline = right_layout.indexOf(self.win.anim_timeline)
        self.assertGreaterEqual(idx_preview, 0)
        self.assertGreater(
            idx_timeline, idx_preview,
            "Предпросмотр анимации должен располагаться над таймлайном с кадрами",
        )

    def test_anim_dnd_in_left_block(self):
        self.assertIs(
            self.win.anim_timeline.drop_area.parent(), self.win.anim_left,
            "DnD-область должна жить в левом блоке вкладки анимации",
        )

    # ── Пункт 1: подписи «Кадр 1/2/…» снизу миниатюры (как во вкладке «Создание») ──

    def test_anim_frame_list_icon_mode(self):
        self.assertEqual(
            self.win.anim_timeline.frame_list.viewMode(),
            QListWidget.ViewMode.IconMode,
            "Кинолента анимации должна показывать подпись кадра снизу миниатюры",
        )

    def test_anim_frame_list_labels(self):
        from core.animation_manager import FlipperAnimationManager
        from PyQt6.QtGui import QPixmap

        tl = self.win.anim_timeline
        m = FlipperAnimationManager()
        for i in range(3):
            m.add_frame_bytes(f"/tmp/f{i}.png", bytes([i]), dither_level=1)
            m.frames[-1]["preview"] = QPixmap(10, 10)
        # подмена менеджера: мини-превью уже полагается на QPixmap, поэтому просто
        # заполняем список кадров виджета напрямую
        tl.manager = m
        tl._refresh_list()
        self.assertEqual(tl.frame_list.count(), 3)
        for i in range(3):
            self.assertIn(str(i), tl.frame_list.item(i).text())


if __name__ == "__main__":
    unittest.main()