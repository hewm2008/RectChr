# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for RectChr GUI (Windows/Linux, onedir).
# Build:  pyinstaller gui/tools/RectChrGUI.spec --distpath dist
# The resulting layout is assembled further by gui/tools/build_windows.py
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent.parent      # repo root (spec lives in gui/tools)

datas = [
    (str(ROOT / "gui" / "resources" / "params_schema.json"), "gui/resources"),
]
if sys.platform == "darwin":
    datas += [(str(ROOT / "bin"), "bin"), (str(ROOT / "ColorsBrewer"), "ColorsBrewer")]
    datas += [(str(p), ".") for p in ROOT.glob("RectChr_manual_*.pdf")]
    datas += [(str(p), "gui/doc") for p in (ROOT / "gui/doc").glob("RectChr_GUI_manual_*.*")]

a = Analysis(
    [str(ROOT / "gui" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy.tests"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RectChrGUI",
    debug=False,
    strip=False,
    upx=False,
    console=False,          # windowed app
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="RectChrGUI",
)

if sys.platform == "darwin":
    import re
    import runpy
    # GUI_VERSION may carry a letter suffix ("1.50B"). Apple requires
    # CFBundleShortVersionString to be period-separated digits only, while
    # CFBundleVersion may additionally carry a trailing build suffix.
    raw = runpy.run_path(str(ROOT / "gui" / "__init__.py"))["GUI_VERSION"].lstrip("v")
    short_version = re.sub(r"[^0-9.]", "", raw) or "0"
    build_version = re.sub(r"[^0-9A-Za-z.]", "", raw) or short_version
    app = BUNDLE(
        coll,
        name="RectChr.app",
        icon=str(ROOT / "gui" / "resources" / "RectChr.icns"),
        bundle_identifier="org.hewm2008.RectChr",
        info_plist={
            "CFBundleName": "RectChr",
            "CFBundleDisplayName": "RectChr",
            "CFBundleShortVersionString": short_version,
            "CFBundleVersion": build_version,
            "NSHighResolutionCapable": True,
        },
    )
