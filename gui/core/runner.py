"""Locate the Perl runtime + engine and run RectChr in a QProcess."""
import os
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QProcess, QProcessEnvironment, Signal

GUI_DIR = Path(__file__).resolve().parents[1]
ROOT = GUI_DIR.parent
if sys.platform == "darwin" and getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent.parent / "Resources"
ENGINE = ROOT / "bin" / "RectChr"


def find_perl():
    """Portable bundled perl first (Windows), then system PATH."""
    if os.name == "nt":
        candidates = []
        exe_dir = Path(sys.executable).parent          # PyInstaller onedir
        for base in (exe_dir, GUI_DIR, ROOT, Path.cwd()):
            candidates += [
                base / "gui_runtime" / "perl" / "perl" / "bin" / "perl.exe",
                base / "gui_runtime" / "perl" / "bin" / "perl.exe",
            ]
        for c in candidates:
            if c.is_file():
                return str(c)
    return shutil.which("perl") or shutil.which("perl.exe")


def find_engine():
    for base in (Path(sys.executable).parent, ROOT, Path.cwd()):
        cand = base / "bin" / "RectChr" if base != ROOT else ENGINE
        if cand.is_file():
            return cand
    return ENGINE if ENGINE.is_file() else None


class RectChrRunner(QObject):
    output = Signal(str)
    finished_ok = Signal(str)      # svg path
    failed = Signal(str)

    ENGINE_TIMEOUT_MS = 600000          # hard kill after 10 minutes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None
        self._out_base = ""
        self._reported = False             # one failure per run (timeout != double fail)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.setInterval(self.ENGINE_TIMEOUT_MS)
        self._timeout.timeout.connect(self._on_engine_timeout)

    def running(self):
        return self._proc is not None and self._proc.state() != QProcess.NotRunning

    def stop(self):
        if self.running():
            self._proc.kill()

    def run(self, conf_path, out_base):
        perl = find_perl()
        engine = find_engine()
        if not perl:
            self.failed.emit("perl-not-found")
            return
        if not engine or not engine.is_file():
            self.failed.emit("engine-not-found")
            return

        out_base = str(out_base)
        if out_base.lower().endswith(".svg"):
            out_base = out_base[:-4]

        self._proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("RECTCHR_NO_PNG", "1")
        self._proc.setProcessEnvironment(env)
        self._proc.setWorkingDirectory(str(ROOT))
        self._proc.readyReadStandardOutput.connect(self._drain_out)
        self._proc.readyReadStandardError.connect(self._drain_err)
        self._proc.finished.connect(self._on_finished)
        # Qt does NOT emit finished() when the process cannot start, so without
        # this a bad launch (not executable, loader error) left the UI busy
        # forever (Run/refresh/export disabled, no way back)
        self._proc.errorOccurred.connect(self._on_proc_error)
        self._out_base = out_base
        self._reported = False
        self._timeout.start()
        self._proc.start(perl, [str(engine), "-InConf", str(conf_path), "-OutPut", out_base])

    def _on_engine_timeout(self):
        if self.running():
            self._proc.kill()
            self._fail("engine-timeout (>600s)")

    def _fail(self, reason):
        """Emit `failed` at most once per run."""
        if self._reported:
            return
        self._reported = True
        self.failed.emit(reason)

    # ------------------------------------------------------------- slots
    def _drain_out(self):
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        if data:
            self.output.emit(data)

    def _drain_err(self):
        data = bytes(self._proc.readAllStandardError()).decode("utf-8", "replace")
        if data:
            self.output.emit(data)

    def _on_proc_error(self, err):
        from PySide6.QtCore import QProcess as _QP
        if err == _QP.FailedToStart:
            self._timeout.stop()
            self._fail("engine-start-failed")

    def _on_finished(self, code, status):
        from PySide6.QtCore import QProcess as _QP
        self._timeout.stop()
        # drain whatever is still buffered so the error log is complete
        self._drain_out()
        self._drain_err()
        svg = self._out_base + ".svg"
        crashed = status == _QP.CrashExit
        if not crashed and code == 0 and Path(svg).is_file():
            self._reported = True
            self.finished_ok.emit(svg)
        else:
            self._fail("crashed" if crashed else "exit=%s" % code)
