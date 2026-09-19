#!/usr/bin/env python3
"""RectChr GUI entry point.

Requires: Python 3.9+ with PySide6.
Run:  python3 gui/main.py            (from the RectChr root, any cwd works)
"""
import sys
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent
ROOT = GUI_DIR.parent
for p in (str(GUI_DIR), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is required:  pip install PySide6")
        return 2
    from gui.ui.logo import application_icon

    from gui.theme import apply_system_theme
    from gui.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("RectChr")
    app.setApplicationDisplayName("RectChr")
    app.setOrganizationName("RectChr")
    apply_system_theme(app)               # Fusion + follow OS light/dark (live)

    # under pythonw (no console) uncaught slot exceptions are invisible:
    # surface them in a dialog instead
    def _excepthook(etype, value, tb):
        import traceback
        from PySide6.QtCore import Qt
        msg = "".join(traceback.format_exception(etype, value, tb))[-2000:]
        sys.stderr.write(msg)
        try:
            from PySide6.QtWidgets import QMessageBox
            box = QMessageBox(QMessageBox.Critical, "RectChr GUI Error", msg)
            box.setTextInteractionFlags(Qt.TextSelectableByMouse)
            box.exec()
        except Exception:                                  # noqa: BLE001
            pass
    sys.excepthook = _excepthook

    app.setWindowIcon(application_icon())

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
