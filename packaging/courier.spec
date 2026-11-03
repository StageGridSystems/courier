# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Courier (Windows .exe / Linux binary).
# Build:  pyinstaller packaging/courier.spec

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).resolve().parent  # noqa: F821
src = root / "src"

a = Analysis(  # noqa: F821
    [str(src / "courier" / "__main__.py")],
    pathex=[str(src)],
    binaries=[],
    datas=[
        (str(src / "courier" / "resources"), "courier/resources"),
    ],
    hiddenimports=[
        "keyring.backends",
        "keyring.backends.fail",
        "keyring.backends.null",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Courier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(src / "courier" / "resources" / "icons" / "courier.svg")
    if sys.platform != "win32"
    else None,
)
