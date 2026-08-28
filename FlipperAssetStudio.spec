# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: сборка Flipper Asset Studio в ОДИН .exe без доп. папок.

Результат: dist/FlipperAssetStudio.exe
Иконки и логотип упаковываются внутрь файла и распаковываются
во временную папку sys._MEIPASS при запуске (см. ui/resources.py).
"""
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icons', 'assets/icons'),
        ('assets/logo/fast_logo.png', 'assets/logo'),
        ('assets/logo/fast_logo.ico', 'assets/logo'),
    ],
    hiddenimports=collect_submodules('core') + collect_submodules('ui'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FlipperAssetStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo/fast_logo.ico',
)