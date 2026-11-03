# -*- mode: python ; coding: utf-8 -*-
# PyInstaller ONEDIR spec for Courier (fast startup; no onefile unpack).
# Build:  pyinstaller packaging/courier.spec

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
root = Path(SPECPATH).resolve().parent  # noqa: F821
src = root / "src"
win_dir = root / "packaging" / "windows"
icon_ico = win_dir / "courier.ico"
version_file = win_dir / "file_version_info.txt"

# QtWebEngine needs its helpers/resources; collect them explicitly.
we_datas: list = []
we_binaries: list = []
we_hidden: list = []
for pkg in (
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
):
    try:
        d, b, h = collect_all(pkg)
        we_datas += d
        we_binaries += b
        we_hidden += h
    except Exception:
        pass

datas = [
    (str(src / "courier" / "resources"), "courier/resources"),
    (str(src / "courier" / "composer" / "style_reference.html"), "courier/composer"),
    (str(src / "courier" / "guide"), "courier/guide"),
]
datas += we_datas

hiddenimports = [
    "keyring.backends",
    "keyring.backends.fail",
    "keyring.backends.null",
    "keyring.backends.chainer",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebChannel",
    "PySide6.QtNetwork",
    "PySide6.QtPrintSupport",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.QtOpenGL",
    "PySide6.QtPositioning",
    "PySide6.QtSvg",
]
if sys.platform == "win32":
    hiddenimports += [
        "keyring.backends.Windows",
        "win32timezone",
        "win32api",
        "win32cred",
    ]
hiddenimports += we_hidden

# Drop heavy / unused Qt modules; keep WebEngine stack intact.
excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtTextToSpeech",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtDesigner",
    "PySide6.QtTest",
    "PySide6.QtSql",
    "PySide6.QtXml",
]

a = Analysis(  # noqa: F821
    [str(src / "courier" / "__main__.py")],
    pathex=[str(src)],
    binaries=we_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe_kwargs = dict(
    exclude_binaries=True,
    name="Courier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "win32" and icon_ico.is_file():
    exe_kwargs["icon"] = str(icon_ico)
elif (src / "courier" / "resources" / "icons" / "courier.png").is_file():
    exe_kwargs["icon"] = str(src / "courier" / "resources" / "icons" / "courier.png")

if sys.platform == "win32" and version_file.is_file():
    exe_kwargs["version"] = str(version_file)

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    **exe_kwargs,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Courier",
    strip=False,
    upx=False,
    upx_exclude=[],
)
