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

# На macOS PyInstaller может снять бит выполнения и оставить подпись без
# adhoc-кода, из-за чего .app не запускается ("Launchd job spawn failed").
chmod +x dist/FlipperAssetStudio 2>/dev/null || true

if [ "$(uname -s)" = "Darwin" ]; then
    echo "→ Ad-hoc подписываю бинарник (необходимо для запуска на Apple Silicon)"
    codesign --force --sign - dist/FlipperAssetStudio
    if [ -d "dist/FlipperAssetStudio.app" ]; then
        codesign --force --deep --sign - "dist/FlipperAssetStudio.app"
    fi
fi

echo ""
echo "✔ Готово:"
ls -la dist/