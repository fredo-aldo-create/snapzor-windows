# Snapzor.spec — PyInstaller (version optimisée)
# Build : pyinstaller Snapzor.spec
# Réduit drastiquement la taille en excluant les modules Qt inutiles

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Modules Qt à EXCLURE (Snapzor n'en a pas besoin)
qt_excludes = [
    # Modules lourds clairement inutiles
    'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel', 'PySide6.QtWebSockets',
    'PySide6.QtWebView', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization',
    'PySide6.QtPositioning', 'PySide6.QtLocation',
    'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtSerialPort',
    'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtHelp',
    'PySide6.QtNetwork', 'PySide6.QtNetworkAuth',
    'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtSensors',
    'PySide6.QtTextToSpeech', 'PySide6.QtUiTools', 'PySide6.QtDesigner',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets',
    'PySide6.QtQuick3D', 'PySide6.QtQuickControls2',
    'PySide6.QtSvg', 'PySide6.QtSvgWidgets',
    'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'PySide6.QtConcurrent', 'PySide6.QtXml',
    'PySide6.QtStateMachine', 'PySide6.QtSpatialAudio',
    # PyQt6 (au cas où il traînerait)
    'PyQt5', 'PyQt6',
    # Bibliothèques scientifiques inutiles
    'numpy', 'scipy', 'pandas', 'matplotlib',
    # Autres
    'tkinter', 'unittest', 'test', 'pydoc', 'doctest',
    'setuptools', 'pip', 'distutils',
]

a = Analysis(
    ['snapzor.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('snapzor/Snapzor.png', '.'),
        ('Snapzor.ico', '.'),
    ],
    hiddenimports=['mss'],
    hookspath=[],
    runtime_hooks=[],
    excludes=qt_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filtrage manuel des fichiers binaires Qt inutiles
def _keep(item):
    name = item[0].lower()
    # Plugins inutiles
    bad_plugins = (
        'qtwebengine', 'qt3d', 'qtmultimedia', 'qtcharts', 'qtdatavis',
        'qtpositioning', 'qtbluetooth', 'qtnfc', 'qtserialport', 'qtsql',
        'qtquick', 'qtqml', 'qtsvg', 'qtopengl', 'qtnetwork', 'qtwebsockets',
        'qtsensors', 'qtpdf', 'qtdesigner', 'qttest', 'qthelp',
    )
    for bad in bad_plugins:
        if bad in name:
            return False
    # Traductions : ne garder que français + anglais
    if '/translations/' in name or '\\translations\\' in name:
        if not any(t in name for t in ('qt_fr', 'qt_en', 'qtbase_fr', 'qtbase_en')):
            return False
    # Plugins d'image : ne garder que PNG/JPEG (déjà inclus en natif), retirer les exotiques
    if 'imageformats' in name:
        if any(fmt in name for fmt in ('qtiff', 'qwebp', 'qicns', 'qtga', 'qwbmp', 'qpdf')):
            return False
    return True

a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

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
    console=False,
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
