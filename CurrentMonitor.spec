# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

# Cross-platform icon handling
ROOT_DIR = os.path.dirname(os.path.abspath(SPEC))
if sys.platform == 'darwin':
    ICON_FILE = os.path.join(ROOT_DIR, 'app', 'resource', 'images', 'logo.icns')
elif sys.platform == 'win32':
    ICON_FILE = os.path.join(ROOT_DIR, 'app', 'resource', 'images', 'logo.ico')
else:
    ICON_FILE = None

datas = [('app', 'app'), ('core', 'core'), ('visualization.py', '.')]
hiddenimports = ['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtSvg', 'PySide6.QtSvgWidgets', 'qfluentwidgets', 'qfluentwidgets.common', 'qfluentwidgets.components', 'qfluentwidgets.window', 'qfluentwidgets._rc', 'pyqtgraph', 'pyqtgraph.exporters', 'numpy', 'pandas', 'scipy', 'scipy.signal', 'scipy.ndimage', 'PIL', 'serial', 'darkdetect', 'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_agg']
datas += collect_data_files('qfluentwidgets')
datas += collect_data_files('matplotlib')
hiddenimports += collect_submodules('qfluentwidgets')
hiddenimports += collect_submodules('matplotlib')


a = Analysis(
    ['flu_main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CurrentMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICON_FILE] if ICON_FILE else [],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CurrentMonitor',
)
# macOS app bundle (only created on macOS)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='CurrentMonitor.app',
        icon=ICON_FILE,
        bundle_identifier='com.d41sy.currentmonitor',
    )
