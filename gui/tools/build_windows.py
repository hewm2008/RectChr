#!/usr/bin/env python3
"""Assemble the distributable RectChrGUI bundle after PyInstaller.

Usage:
  pyinstaller gui/tools/RectChrGUI.spec --distpath dist --noconfirm
  python3 gui/tools/build_windows.py dist/RectChrGUI        (or the Linux dist dir)

NOTE: PyInstaller needs a Python built with shared libraries (libpython*.so /
python3xx.dll). Official python.org / conda builds on Windows have them, so
building the Windows exe works out of the box. Self-compiled *nix Pythons built
without --enable-shared will fail in PyInstaller; in that case ship the source
bundle (RectChrGUI.sh + gui/ + bin/) instead.

Resulting layout (double-click RectChrGUI.exe / RectChrGUI):
  RectChrGUI/
    RectChrGUI(.exe)          PyInstaller onedir app
    _internal/...             python runtime
    bin/RectChr + bin/lib/... Perl engine (patched, cross-platform)
    ColorsBrewer/             palettes
    gui_runtime/perl/         portable Strawberry Perl goes here (Windows)
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(dist_dir):
    dist_dir = Path(dist_dir)
    if not dist_dir.is_dir():
        sys.exit("dist dir not found: %s" % dist_dir)

    # engine + resources next to the executable
    dest_bin = dist_dir / "bin"
    shutil.copytree(ROOT / "bin" / "lib", dest_bin / "lib", dirs_exist_ok=True)
    shutil.copytree(ROOT / "bin" / "svg_kit", dest_bin / "svg_kit", dirs_exist_ok=True)
    for f in ("RectChr", "in.conf", "In-CN.conf", "In-EN.conf"):
        src = ROOT / "bin" / f
        if src.is_file():
            shutil.copy2(src, dest_bin / f)
    if (ROOT / "ColorsBrewer").is_dir():
        shutil.copytree(ROOT / "ColorsBrewer", dist_dir / "ColorsBrewer", dirs_exist_ok=True)

    # manual PDFs (the Help dialog opens them from the exe directory)
    for pdf in (list(ROOT.glob("RectChr_manual_*.pdf"))
                + list((ROOT / "gui" / "doc").glob("RectChr_GUI_manual_*.pdf"))
                + list((ROOT / "gui" / "doc").glob("RectChr_GUI_manual_*.docx"))):
        shutil.copy2(pdf, dist_dir / pdf.name)

    # portable perl placeholder
    rt = dist_dir / "gui_runtime" / "perl"
    rt.mkdir(parents=True, exist_ok=True)
    (rt / "PUT_PORTABLE_PERL_HERE.txt").write_text(
        "Windows: download 'strawberry-perl-N.N.N.N-portable.zip'\n"
        "and unzip so that this folder contains  perl/bin/perl.exe\n"
        "https://strawberryperl.com/releases.html\n", encoding="utf-8")

    print("bundle assembled:", dist_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist/RectChrGUI")
