""""参数总览" tab: every enabled parameter across all sections on ONE page,
rendered in the same row style as the section forms — and editable.

Edits write straight into the model and are announced through
`param_changed(scope, key, value)`; MainWindow routes them to the owning
tabs (mutual sync, origin skipped via Qt sender()).
File rows carry working 浏览/× buttons and join the files sync chain."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from ..core.conf_io import abspath_for
from ..core.schema import Schema
from ..i18n import I18N
from ..theme import make_card
from .param_form import ParamRow


class ParamsSummaryTab(QWidget):
    param_changed = Signal(object, str, object)   # scope, key, value
    files_changed = Signal(list)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._rows = {}          # (scope, key) -> ParamRow
        self._file_rows = {}     # file index -> QLineEdit
        self._headers = {}       # section key -> header widget
        self._sec_order = []     # section keys in display order
        self._building = False

        self.sec_list = QListWidget()
        self.sec_list.setMaximumWidth(175)
        self.sec_list.currentRowChanged.connect(self._nav_to_section)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        self.sec_title = QLabel("<b>%s</b>" % I18N.tr("show_params"))
        left.addWidget(self.sec_title)
        left.addWidget(self.sec_list)
        note = QLabel(I18N.tr("summary_nav_note"))
        note.setWordWrap(True)
        note.setStyleSheet("color: palette(mid);")
        left.addWidget(note)

        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.addLayout(left, 0)
        root.addWidget(self.scroll, 1)

        self.refresh()

    # ------------------------------------------------------------- refresh
    def set_model(self, model):
        self.model = model
        self.refresh()

    def refresh(self):
        """Rebuild the whole flat listing from the model (click = refresh)."""
        if self._building:
            return
        self._building = True
        try:
            old = self.scroll.takeWidget()
            if old is not None:
                old.setParent(None)
                old.deleteLater()
            self._rows.clear()
            self._file_rows.clear()
            self._headers.clear()
            self._sec_order = []

            central = QFrame()
            central.setObjectName("formPage")
            lay = QVBoxLayout(central)
            lay.setContentsMargins(10, 10, 10, 10)
            lay.setSpacing(12)

            secs = self._sections()
            if not secs:
                lay.addWidget(QLabel(I18N.tr("params_none")))
            for sec in secs:
                card, v = make_card(self._section_label(sec))
                self._headers[sec] = card
                self._sec_order.append(sec)
                if sec == "global":
                    for i, f in enumerate(self.model.files):
                        if f:
                            v.addWidget(self._make_file_row(i, f))
                    entries = [(k, self.model.global_params[k])
                               for k in sorted(self.model.global_params)]
                elif sec == "track":
                    entries = [(k, self.model.track_all[k])
                               for k in sorted(self.model.track_all)]
                else:
                    tp = self.model.tracks.get(sec, {})
                    entries = [(k, tp[k]) for k in sorted(tp)]
                if not entries:
                    v.addWidget(QLabel(I18N.tr("params_none")))
                for key, value in entries:
                    row = self._make_param_row(sec, key, value)
                    v.addWidget(row)
                    self._rows[(sec, key)] = row
                lay.addWidget(card)

            lay.addStretch(1)
            self.scroll.setWidget(central)
            self._sync_sec_list(secs)
        finally:
            self._building = False

    def _sections(self):
        """Section keys that currently hold content, in display order."""
        secs = []
        if any(self.model.files) or self.model.global_params:
            secs.append("global")
        if self.model.track_all:
            secs.append("track")            # model scope string for trackALL
        secs += [i for i in sorted(self.model.tracks) if self.model.tracks[i]]
        return secs

    @staticmethod
    def _section_label(sec):
        if sec == "global":
            return I18N.tr("global_tab")
        if sec == "track":
            return I18N.tr("track_all_tab")
        return I18N.tr("track_tab", n=sec)

    def _sync_sec_list(self, secs):
        """Mirror the section list to the left navigator (no filtering)."""
        cur = self.sec_list.currentRow()
        self.sec_list.blockSignals(True)
        self.sec_list.clear()
        for sec in secs:
            self.sec_list.addItem(self._section_label(sec))
        if 0 <= cur < len(secs):
            self.sec_list.setCurrentRow(cur)
        self.sec_list.blockSignals(False)

    def _nav_to_section(self, row_i):
        """Left list = navigation: TOP-ALIGN the section (no centering)."""
        if self._building or not (0 <= row_i < len(self._sec_order)):
            return
        header = self._headers.get(self._sec_order[row_i])
        if header is not None:
            y = header.y() - 8
            self.scroll.verticalScrollBar().setValue(max(0, y))
            self.scroll.horizontalScrollBar().setValue(0)

    # ------------------------------------------------------------- sync
    def sync_value(self, scope, key, value):
        """External change: update the matching row (hide when cleared)."""
        row = self._rows.get((scope, key))
        if row is not None:
            row.set_external(value)
            row.setVisible(value not in (None, ""))

    def sync_files(self, files):
        """External file-list change: update row texts in place (no focus
        loss while typing); only structural index changes rebuild."""
        new_ids = [i for i, f in enumerate(files) if f]
        if new_ids != list(self._file_rows.keys()):
            self.refresh()
            return
        for idx, edit in self._file_rows.items():
            new = files[idx] if idx < len(files) else ""
            if edit.text() != new:
                edit.setText(new)
                edit.setToolTip(new)

    # ------------------------------------------------------------- rows
    def _make_param_row(self, scope, key, value):
        p = dict(Schema.param(key) or {
            "name": key, "type": "text", "importance": 0,
            "label_zh": key, "label_en": key, "desc_zh": "", "desc_en": "",
            "old_names": [], "choices": None, "min": None, "max": None,
            "default": None,
        })
        row = ParamRow(p, value)
        row.changed.connect(lambda k, v, s=scope: self._on_row_changed(s, k, v))
        return row

    def _make_file_row(self, idx, path):
        cont = QWidget()
        lay = QHBoxLayout(cont)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lab = QLabel("File%d" % (idx + 1))
        lab.setMinimumWidth(44)
        edit = QLineEdit(path)
        edit.setMinimumWidth(80)
        edit.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        edit.setToolTip(path)
        edit.textEdited.connect(lambda s, i=idx: self._file_edited(i, s))
        edit.textEdited.connect(edit.setToolTip)
        browse = QPushButton(I18N.tr("choose"))
        browse.setFixedWidth(70)
        browse.clicked.connect(lambda _c=False, i=idx: self._file_browse(i))
        rm = QPushButton("×")
        rm.setFixedWidth(24)
        rm.setToolTip(I18N.tr("remove_file"))
        rm.clicked.connect(lambda _c=False, i=idx: self._file_removed(i))
        lay.addWidget(lab)
        lay.addWidget(edit, 1)
        lay.addWidget(browse)
        lay.addWidget(rm)
        self._file_rows[idx] = edit
        return cont

    def _emit_files(self):
        self.files_changed.emit(list(self.model.files))

    def _file_edited(self, idx, text):
        self.model.files[idx] = text.strip()
        self._emit_files()

    def _file_browse(self, idx):
        start = self.model.files[idx] if idx < len(self.model.files) else ""
        f, _ = QFileDialog.getOpenFileName(self, I18N.tr("add_file"),
                                           start or ".", "Data (*.df *.txt *.tsv *.gz *.conf);;All (*)")
        if f:
            self.model.files[idx] = f
            self.refresh()
            self._emit_files()

    def _file_removed(self, idx):
        if idx == 0:
            self.model.files[0] = ""        # File1 stays, only clear it
        else:
            del self.model.files[idx]
        self.refresh()
        self._emit_files()

    def _on_row_changed(self, scope, key, value):
        self.model.set_param(scope, key, value)
        self.param_changed.emit(scope, key, value)
