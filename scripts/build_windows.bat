@echo off
REM ──────────────────────────────────────────────────────────────────────────
REM Сборка Flipper Asset Studio в ОДИН исполняемый файл (.exe) без доп. папок.
REM Запускается на Windows. На macOS/Linux используйте scripts/build.sh.
REM Результат: dist\FlipperAssetStudio.exe (иконка и ресурсы внутри файла).
REM ──────────────────────────────────────────────────────────────────────────
cd /d "%~dp0\.."

echo =^> installing dependencies (PyQt6, Pillow, numpy, heatshrink2^) ...
pip install -r requirements.txt

echo =^> installing PyInstaller ...
pip install pyinstaller

echo =^> building onefile executable (icon and assets bundled inside) ...
pyinstaller --clean --noconfirm FlipperAssetStudio.spec

echo.
echo OK. Result:
dir /b dist\

pause