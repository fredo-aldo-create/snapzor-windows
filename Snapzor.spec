# Snapzor.spec — PyInstaller
# Build : pyinstaller Snapzor.spec
# Le résultat se trouve dans dist\Snapzor\Snapzor.exe

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['snapzor.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('snapzor/Snapzor.png', '.'),
        ('Snapzor.ico', '.'),
    ],
    hiddenimports=collect_submodules('PySide6') + ['mss', 'PIL._tkinter_finder'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'test', 'pydoc'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Snapzor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # GUI sans console
    disable_windowed_traceback=False,
    icon='Snapzor.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Snapzor',
)
