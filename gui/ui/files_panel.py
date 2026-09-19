"""Data files panel: File1..FileN list + preview table (.gz supported)."""
import gzip
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QPushButton, QScrollArea,
                               QSizePolicy, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..i18n import I18N


def read_rows(path, limit=20):
    """Read up to `limit` whitespace-separated rows; supports .gz."""
    path = str(path)
    opener = gzip.open if path.lower().endswith(".gz") else open
    rows = []
    try:
        with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n\r")
                if line.strip():
                    rows.append(line.split())
                if len(rows) >= limit:
                    break
    except OSError:
        return []
    return rows


class FilesBar(QWidget):
    """Compact File1..FileN editor (rows of [FileN][path][browse][x]).

    Used inside the Global parameters tab; stays in sync with the left
    FilesPanel through the main window. ＋ appends an empty row first.

    A conf may declare dozens of inputs (e.g. 79 samples). Rendering one
    editable row per file made this card thousands of pixels tall, so above
    ROW_LIMIT rows we fold into a short read-only list and point at the left
    panel, which is the primary editor anyway."""
    changed = Signal(list)

    ROW_LIMIT = 8                  # <= this many files -> one editable row each
    FOLD_MAX_HEIGHT = 254          # folded list height cap (px)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files = [""]
        self._builds = 0
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.rows_lay = QVBoxLayout()
        self.rows_lay.setSpacing(2)
        self.root.addLayout(self.rows_lay)
        btns = QHBoxLayout()
        self.add_btn = QPushButton("＋ " + I18N.tr("add_file"))
        self.add_btn.clicked.connect(self._add_row)
        btns.addWidget(self.add_btn)
        btns.addStretch(1)
        self.root.addLayout(btns)
        self._build_rows()

    # ------------------------------------------------------------- state
    def current_files(self):
        return list(self._files)

    def folded(self):
        """True when the card is showing the compact read-only list."""
        return len(self._files) > self.ROW_LIMIT

    def set_files(self, files):
        files = list(files or [""])
        if not files:
            files = [""]
        if files == self._files:            # no-op when in sync (loop guard)
            return
        self._files = files
        self._build_rows()

    def retranslate(self):
        """Re-render rows after a language switch."""
        self._build_rows()

    # ------------------------------------------------------------- rows
    def _build_rows(self):
        self._builds += 1
        # guard: the underlying C++ layout may already be gone if the widget
        # was destroyed by a parent rebuild (platform-dependent timing)
        try:
            _ = self.rows_lay.count()
        except RuntimeError:
            return
        # tear down old rows completely: each row is a container QWidget;
        # detach it from this widget first (no painting residue), then
        # schedule deletion. Nested layouts alone would leave orphaned
        # child widgets stacked on top of the new rows.
        while self.rows_lay.count():
            item = self.rows_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            elif item.layout() is not None:
                self._teardown_layout(item.layout())
        self._row_containers = []
        if self.folded():
            self._build_folded()
            return
        self.add_btn.setVisible(True)
        for i, f in enumerate(self._files):
            cont = self._make_row(i, f)
            self._row_containers.append(cont)
            self.rows_lay.addWidget(cont)
        self.rows_lay.addStretch(1)

    def _build_folded(self):
        """Read-only summary + scrollable path list for large file sets."""
        hint = QLabel(I18N.tr("files_folded_hint", n=len(self._files)))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        self.rows_lay.addWidget(hint)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setMaximumHeight(self.FOLD_MAX_HEIGHT)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)
        for i, f in enumerate(self._files):
            it = QLabel("File%d: %s" % (i + 1, f or "—"))
            it.setTextInteractionFlags(Qt.TextSelectableByMouse)
            it.setToolTip(f)
            v.addWidget(it)
        v.addStretch(1)
        area.setWidget(inner)
        self.rows_lay.addWidget(area)
        # editing happens in the left data-files panel
        self.add_btn.setVisible(False)

    @staticmethod
    def _teardown_layout(lay):
        """Detach every widget managed by a (nested) layout."""
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            sub = item.layout()
            if sub is not None:
                FilesBar._teardown_layout(sub)

    def _make_row(self, idx, path):
        cont = QWidget()
        row = QHBoxLayout(cont)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        lab = QLabel("File%d" % (idx + 1))
        lab.setMinimumWidth(44)
        edit = QLineEdit(path)
        edit.setPlaceholderText(I18N.tr("file_hint"))
        # decouple the editor from style-dependent size hints: a very long
        # path must never stretch the row (which pushed the x / browse
        # buttons out of view on Windows); the text scrolls inside instead
        edit.setMinimumWidth(80)
        edit.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        edit.setToolTip(path)
        edit.textEdited.connect(lambda s, i=idx: self._path_edited(i, s))
        edit.textEdited.connect(edit.setToolTip)
        browse = QPushButton(I18N.tr("choose"))
        browse.setObjectName("fileBrowseBtn")
        browse.setFixedWidth(70)
        browse.clicked.connect(lambda _c=False, i=idx: self._browse(i))
        rm = QPushButton("×")
        rm.setObjectName("fileRemoveBtn")
        rm.setFixedWidth(28)
        rm.setToolTip(I18N.tr("remove_file"))
        rm.clicked.connect(lambda _c=False, i=idx: self._remove_row(i))
        row.addWidget(lab)
        row.addWidget(edit, 1)
        row.addWidget(browse)
        row.addWidget(rm)
        return cont

    # ------------------------------------------------------------- actions
    def _add_row(self):
        self._files.append("")
        self._build_rows()
        self.changed.emit(list(self._files))

    def _remove_row(self, idx):
        if idx == 0:
            self._files[0] = ""             # File1 stays, only clear it
        else:
            del self._files[idx]
        self._build_rows()
        self.changed.emit(list(self._files))

    def _path_edited(self, idx, text):
        self._files[idx] = text.strip()
        self.changed.emit(list(self._files))

    def _browse(self, idx):
        f, _ = QFileDialog.getOpenFileName(self, I18N.tr("add_file"),
                                           str(Path(self._files[idx] or Path.home()).parent
                                               if self._files[idx] else Path.home()),
                                           "Data (*.df *.txt *.tsv *.gz *.conf);;All (*)")
        if f:
            self._files[idx] = f
            self._build_rows()
            self.changed.emit(list(self._files))


class FilesPanel(QWidget):
    files_changed = Signal(list)
    file1_analyzed = Signal(str, int)       # path, number of value columns

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_dir = None               # resolve user-typed relative paths
        self._files = [""]                 # File1..FileN (kept in sync by set_files)
        self.title = QLabel("<b>%s</b>" % I18N.tr("data_files"))
        self.hint = QLabel(I18N.tr("file_hint"))
        self.hint.setWordWrap(True)

        self.listw = QListWidget()
        self.add_btn = QPushButton(I18N.tr("add_file"))
        self.del_btn = QPushButton(I18N.tr("remove_file"))
        btns = QHBoxLayout()
        btns.addWidget(self.add_btn)
        btns.addWidget(self.del_btn)
        btns.addStretch(1)

        self.preview_label = QLabel("<b>%s</b>" % I18N.tr("data_preview"))
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        lay = QVBoxLayout(self)
        lay.addWidget(self.title)
        lay.addWidget(self.hint)
        lay.addWidget(self.listw)
        lay.addLayout(btns)
        lay.addWidget(self.preview_label)
        lay.addWidget(self.table, 1)

        self.add_btn.clicked.connect(self._add)
        self.del_btn.clicked.connect(self._remove)
        self.listw.itemSelectionChanged.connect(self._show_preview)

    # ------------------------------------------------------------- actions
    def _add(self):
        start = str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(self, I18N.tr("add_file"), start,
                                                "Data (*.df *.txt *.tsv *.gz *.conf);;All (*)")
        model_files = self.current_files()
        for f in files:
            if model_files and model_files[0] == "":
                model_files[0] = f
            elif f not in model_files:
                model_files.append(f)
        self.set_files(model_files)

    def _remove(self):
        row = self.listw.currentRow()
        if row < 0:
            return
        files = self.current_files()
        if row == 0:
            files[0] = ""
        else:
            del files[row]
        self.set_files(files)

    # ------------------------------------------------------------- state
    def current_files(self):
        return list(getattr(self, "_files", [""]))

    def set_files(self, files):
        files = list(files) if files else [""]
        if not files:
            files = [""]
        if files == getattr(self, "_files", None):
            return                              # no-op when already in sync
        self._files = files
        self.listw.clear()
        for i, f in enumerate(files):
            self.listw.addItem("File%d: %s" % (i + 1, f if f else "—"))
        self.files_changed.emit(list(files))
        self._show_preview()

    # ------------------------------------------------------------- preview
    def _show_preview(self):
        row = self.listw.currentRow()
        files = self.current_files()
        if row < 0 or row >= len(files) or not files[row]:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        path = files[row]
        p = Path(path).expanduser()
        if not p.is_file() and self.base_dir and not p.is_absolute():
            p = Path(self.base_dir) / path      # relative -> working dir
        if not p.is_file():
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(I18N.tr("file_missing", f=path)))
            return
        rows = read_rows(str(p))
        if not rows:
            # unreadable/empty file: drop the previous file's table instead of
            # leaving its contents on screen
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        ncol = max(len(r) for r in rows)
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(ncol)
        for i, r in enumerate(rows):
            for j in range(ncol):
                self.table.setItem(i, j, QTableWidgetItem(r[j] if j < len(r) else ""))
        self.table.resizeColumnsToContents()
        if row == 0 and len(rows[0]) > 3:
            self.file1_analyzed.emit(path, len(rows[0]) - 3)
