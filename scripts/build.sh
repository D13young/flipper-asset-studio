#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# Сборка Flipper Asset Studio в ОДИН автономный исполняемый файл.
# Работает на macOS и Linux (на Windows используйте scripts/build_windows.bat).
#
# Результат:
#   macOS   → dist/FlipperAssetStudio.app  (внутри — onefile-бинарник с иконкой)
#   Linux   → dist/FlipperAssetStudio      (один ELF-файл)
#   Windows → scripts/build_windows.bat
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ Устанавливаю зависимости (PyQt6, Pillow, numpy, heatshrink2)…"
pip install -r requirements.txt

echo "→ Устанавливаю PyInstaller…"
pip install pyinstaller

echo "→ Собираю onefile-исполняемый файл (иконка и ресурсы внутри)…"
pyinstaller --clean --noconfirm FlipperAssetStudio.spec

echo ""
echo "✔ Готово:"
ls -la dist/