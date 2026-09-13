# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for SketchBook (Windows onedir).

Build:
    .venv\\Scripts\\python.exe -m PyInstaller SketchBook.spec --noconfirm --clean
"""

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = Path(SPECPATH).resolve()

# Bundled data (QSS, icons, fonts, JSON configs, sounds, VERSION)
datas = [
    (str(ROOT / "VERSION"), "."),
    (str(ROOT / "gui" / "styles"), "gui/styles"),
]
_feed = ROOT / "update_feed.json"
if _feed.is_file():
    datas.append((str(_feed), "."))

# gui/ressources without heavy WIP/PSD assets
_ressources = ROOT / "gui" / "ressources"
if _ressources.is_dir():
    for dirpath, _dirnames, filenames in os.walk(_ressources):
        for name in filenames:
            if name.lower().endswith((".psd", ".psb")):
                continue
            full = Path(dirpath) / name
            rel_parent = full.parent.relative_to(ROOT)
            datas.append((str(full), str(rel_parent).replace("\\", "/")))

# Qt / PySide6 binaries and plugins
binaries = []
hiddenimports = [
    "qtpy",
    "qtpy.QtCore",
    "qtpy.QtGui",
    "qtpy.QtWidgets",
    "PySide6",
    "PIL",
    "certifi",
]
try:
    import certifi

    datas.append((certifi.where(), "certifi"))
except ImportError:
    pass
tmp_ret = collect_all("PySide6")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    [str(ROOT / "bootstrap.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="SketchBook",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "gui" / "ressources" / "icones" / "SketchBook.ico"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SketchBook",
)
