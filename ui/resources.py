# ui/resources.py
"""Ресурсы приложения: пути к файлам и иконка/логотип.

Работает одинаково:
  - в разработке (папка assets/ в корне проекта);
  - в собранном одностраничном (--onefile) исполняемом файле PyInstaller,
    где ресурсы распаковываются во временную папку sys._MEIPASS.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap

# Корень проекта в режиме разработки.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_LOGO_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAALIAAACyCAYAAADmipVoAAAACXBIWXMAAC4jAAAuIwF4pT92AAAC"
    "3ElEQVR4nO3dzWkbURiG0RhcQ7bpyFWkgpB98N4YsndzrsEFOCSBQH4cS/LM3DvPnFPBRTy8fAiB"
    "rp+fn99xmqev73f1Yd09Pox+wmauRz9gNnuLlZ8OHbJoOw4VsnC78iGL9xhyIQv3mDIhC/jYdh+y"
    "gPlulyGLlz/tKmQB85JdhCxgXjN9yCLmFNOGLGDOMV3IAuYSU4UsYi41RcgC5q2GhyxiljA0ZBGz"
    "lCEhC5ilbR6yiFnDpiGLmLVsFrKIWdMmIYuYta0esojZwqohi5itrBayiNnSKiGLmK0tHrKIGWHR"
    "kEXMKIuFLGJGWiRkETPa8J9xwhLeHLI1ZgZvClnEzOLikEXMTNzIJFwUsjVmNmeHLGJm5LQg4ayQ"
    "rTGzssgknByyNWZmJ4UsYmbntCBByCS8GnLtrDjSH43f3t9cjX7DViwyCf8NubbGdFlkEl4M2Rqz"
    "JxaZhH+GbI3ZG4tMgpBJ+CtkZwV7ZJFJEDIJQibht5Ddx+yVRSZByCQImYRfIbuP2TOLTIKQSRAy"
    "CT9Cdh+zdxaZBCGTIGQShEyCkEkQMglCJuHad8gUWGQShEyCkEkQMglCJkHIJAiZBCGTIGQShEyC"
    "kEkQMglCJuFwIX/+8HH0Ezbz5dPDYX7ZeLiQaRIyCUImQcgkCJkEIZMgZBKETIKQSRAyCUImQcgk"
    "CJkEIZMgZBKETIKQSRAyCUImQcgkCJkEIZMgZBKETIKQSRAyCUImQcgkCJkEIZMgZBKETIKQSRAy"
    "CUImQcgkCJkEIZMgZBKETIKQSRAyCUImQcgkHC7ku8eH0U/YzO39zdXoN2zlcCHTJGQShEyCkEkQ"
    "MglCJkHIJAiZBCGTIGQShEyCkEkQMglCJkHIJAiZBCGTIGQShEyCkEkQMglCJkHIJAiZBCGTIGQS"
    "hEyCkEkQMglCJkHIJAiZBCGTIGQShEyCkEkQMglCJkHIJAiZBCGTIGQShEyCkEn4BhQtjtCPZqmt"
    "AAAAAElFTkSuQmCC"
)


def resource_path(relative: str) -> Path:
    """Возвращает абсолютный путь к ресурсу приложения.

    В собранном PyInstaller-файле данные распакованы во временную папку
    sys._MEIPASS, поэтому ищем их там, иначе — в корне проекта.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return _PROJECT_ROOT / relative


def _logo_pixmap() -> QPixmap:
    pm = QPixmap()
    png = resource_path("assets/logo/fast_logo.png")
    if png.is_file():
        pm.load(str(png))
    else:
        # Фолбэк на встроенный в исполняемый файл логотип.
        pm.loadFromData(base64.b64decode(_LOGO_PNG_B64))
    return pm


def app_icon() -> QIcon:
    """Иконка приложения (для панели задач, заголовка окна и Dock)."""
    icon = QIcon()
    icon.addPixmap(_logo_pixmap())
    return icon


def app_logo_pixmap(size: int = 22) -> QPixmap:
    """Логотип для встраивания в интерфейс."""
    return _logo_pixmap().scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )