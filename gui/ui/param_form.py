"""Reusable parameter form built from the schema (one instance per section)."""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QScrollArea,
                               QSpinBox, QVBoxLayout, QWidget)

from ..core.schema import Schema
from ..i18n import I18N
from ..theme import make_card
from .files_panel import FilesBar

WIDE = 999999999


def _fmt_label(p):
    lang = I18N.lang()
    label = p.get("label_zh" if lang == "zh" else "label_en") or p["name"]
    if lang == "zh":
        return "%s  (%s)" % (label, p["name"]) if label != p["name"] else p["name"]
    return "%s  (%s)" % (label, p["name"]) if label != p["name"] else p["name"]


def _fmt_tooltip(p):
    zh = p.get("desc_zh") or ""
    en = p.get("desc_en") or ""
    tip = p["name"]
    if zh:
        tip += "\nZH: " + zh
    if en:
        tip += "\nEN: " + en
    rng = _range_text(p)
    if rng:
        tip += "\n" + rng
    d = p.get("default")
    if d not in (None, ""):
        tip += "\n" + (("默认: %s" if I18N.lang() == "zh" else "Default: %s") % d)
    old = p.get("old_names") or []
    if old:
        tip += "\nlegacy: " + ", ".join(old)
    return tip


def _range_text(p):
    """Numeric bounds as display text, e.g. '范围 5–∞' / 'range 5–∞'."""
    if p.get("type") not in ("int", "float"):
        return ""
    mn, mx = p.get("min"), p.get("max")
    if mn is None and mx is None:
        return ""
    lo = "-∞" if mn is None else str(mn)
    hi = "∞" if mx is None else str(mx)
    return ("范围 %s–%s" if I18N.lang() == "zh" else "range %s–%s") % (lo, hi)


def _default_hint_text(p):
    """Engine-grounded default hint: dynamic hint first, else the static default."""
    lang = I18N.lang()
    hint = p.get("default_hint_zh" if lang == "zh" else "default_hint_en") \
        or p.get("default_hint_zh")     # fall back to zh hint for en when missing
    rng = _range_text(p)
    if hint:
        return "%s（%s）" % (hint, rng) if rng else hint
    d = p.get("default")
    if d not in (None, ""):
        base = ("默认: %s" if lang == "zh" else "Default: %s") % d
        return "%s（%s）" % (base, rng) if rng else base
    return rng


class ColorButton(QPushButton):
    picked = Signal(str)          # a color was chosen in the dialog

    def __init__(self, value="", parent=None):
        super().__init__(parent)
        self.setFixedWidth(70)
        self.value = value
        self._apply()
        self.clicked.connect(self._pick)

    def _apply(self):
        if self.value and self.value.startswith("#"):
            self.setText("")
            self.setStyleSheet("background-color:%s;border:1px solid palette(mid);"
                               % self.value)
        else:
            self.setStyleSheet("")
            self.setText(self.value or "…")

    def _pick(self):
        c = QColorDialog.getColor(QColor(self.value) if self.value.startswith("#") else QColor("#888888"),
                                  self, "", QColorDialog.ShowAlphaChannel)
        if c.isValid():
            self.value = c.name(QColor.HexArgb) if c.alpha() < 255 else c.name()
            self._apply()
            self.picked.emit(self.value)


def _swatch_icon(colors, w=110, h=13):
    """Small color-chip strip as a QIcon (palette preview)."""
    pm = QPixmap(QSize(w, h))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    if colors:
        n = len(colors)
        cw = max(2, w // n)
        for i, c in enumerate(colors[: w // cw]):
            p.fillRect(i * cw, 0, cw, h, QColor(c))
    else:
        p.fillRect(0, 0, w, h, QColor("#dddddd"))
    p.end()
    from PySide6.QtGui import QIcon
    return QIcon(pm)


class PaletteButton(QPushButton):
    """Shows the current palette name + mini swatch strip; opens the picker."""

    def __init__(self, value="", parent=None):
        super().__init__(parent)
        self.value = value or ""
        self.setFixedWidth(170)
        self._apply()
        # NOTE: no self-connect here — the owning ParamRow connects the click
        # to _pick_palette, which updates BOTH the swatch and the text field.
        # Connecting here too used to open the chooser twice per click.

    def _apply(self):
        colors = Schema.palette_colors(self.value)
        self.setIcon(_swatch_icon(colors))
        self.setIconSize(QSize(80, 13))
        self.setText(" " + (self.value if self.value else I18N.tr("palette_none")))

    def set_palette(self, name):
        self.value = (name or "").strip()
        self._apply()


class PaletteDialog(QDialog):
    """Searchable palette chooser: builtin RColorBrewer + ColorsBrewer files."""

    def __init__(self, current="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(I18N.tr("palette_pick"))
        self.setMinimumSize(430, 520)
        self.chosen = None
        self._rows = []

        lay = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(I18N.tr("filter"))
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)

        clear = QPushButton(I18N.tr("palette_clear"))
        clear.clicked.connect(self._clear)
        lay.addWidget(clear)

        from PySide6.QtWidgets import QScrollArea
        area = QScrollArea()
        area.setWidgetResizable(True)
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(2, 2, 2, 2)
        pals = Schema.palettes()
        groups = [
            (I18N.tr("palette_builtin_qual"), [n for n, e in sorted(pals["builtin"].items())
                                               if e.get("qualitative")]),
            (I18N.tr("palette_builtin_seq"), [n for n, e in sorted(pals["builtin"].items())
                                              if not e.get("qualitative")]),
            (I18N.tr("palette_files"), sorted(pals["files"].keys())),
        ]
        for title, names in groups:
            names = [n for n in names if Schema.palette_colors(n)]
            if not names:
                continue
            v.addWidget(QLabel("<b>%s</b>" % title))
            for n in names:
                entry = pals["builtin"].get(n) or pals["files"].get(n)
                cnt = entry.get("max") or len(entry.get("colors") or [])
                btn = QPushButton(" %s (%s)" % (n, cnt))
                btn.setIcon(_swatch_icon(Schema.palette_colors(n)))
                btn.setIconSize(QSize(110, 13))
                btn.setStyleSheet("text-align:left;")
                if n == current:
                    btn.setStyleSheet("text-align:left;border:2px solid #4a90d9;")
                btn.clicked.connect(lambda _c=False, name=n: self._select(name))
                v.addWidget(btn)
                self._rows.append((btn, n.lower()))
        v.addStretch(1)
        area.setWidget(central)
        lay.addWidget(area, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _select(self, name):
        self.chosen = name
        self.accept()

    def _clear(self):
        self.chosen = ""
        self.accept()

    def _filter(self, text):
        text = text.strip().lower()
        for btn, key in self._rows:
            btn.setVisible(text in key)


class ParamRow(QWidget):
    """One parameter row: [enable] key  editor."""
    changed = Signal(str, object)          # key, value ('' = unset)

    def __init__(self, param, value, parent=None):
        super().__init__(parent)
        self.param = param
        self.key = param["name"]
        self._building = True

        self.enable = QCheckBox()
        self.enable.setToolTip(I18N.tr("enabled"))
        self.label = QLabel(_fmt_label(param))
        self.label.setToolTip(_fmt_tooltip(param))
        self.label.setMinimumWidth(230)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.editor = self._make_editor(param, value)

        # engine-grounded default hint (right aligned, theme-aware gray)
        self.default_label = None
        hint = _default_hint_text(param)
        if hint:
            self.default_label = QLabel(hint)
            self.default_label.setStyleSheet("color: palette(mid);")
            self.default_label.setToolTip(hint)
            self.editor_lay.addWidget(self.default_label)
        self._apply_placeholder(param, value)

        # int/float editors are fixed-width: without a trailing stretch the
        # row's leftover width leaks into the checkbox/label (rows without a
        # hint had no other expanding item), pushing the editor to the right
        if param.get("type") in ("int", "float"):
            self.editor_lay.addStretch(1)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.addWidget(self.enable)
        lay.addWidget(self.label)
        lay.addLayout(self.editor_lay, 1)

        self.enable.toggled.connect(self._on_toggle)
        self.enable.setChecked(value != "" and value is not None)
        self._building = False
        self._sync_enabled()

    # ------------------------------------------------------------- editors
    def _apply_placeholder(self, p, value):
        """Show the engine default as placeholder in free-text editors."""
        d = p.get("default")
        if d in (None, "") or value not in ("", None):
            return
        if hasattr(self, "_color_txt"):
            self._color_txt.setPlaceholderText(str(d))
        elif hasattr(self, "_file_edit"):
            self._file_edit.setPlaceholderText(str(d))
        elif isinstance(getattr(self, "_editor", None), QLineEdit):
            self._editor.setPlaceholderText(str(d))

    @staticmethod
    def _initial_value(p, value):
        """Effective initial editor value: explicit value first, else engine default."""
        if value not in ("", None):
            return str(value)
        d = p.get("default")
        return "" if d in (None, "") else str(d)

    def _make_palette_editor(self, p, value):
        """Palette picker button (swatch preview + chooser) + manual entry."""
        lay = self.editor_lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        init = self._initial_value(p, value)
        btn = PaletteButton(init)
        txt = QLineEdit(init)
        txt.setPlaceholderText("GnYlRd / Paired / npg …")
        btn.clicked.connect(self._pick_palette)
        lay.addWidget(btn)
        lay.addWidget(txt, 1)
        self._editor = txt
        self._palette_btn = btn
        self._bind_line(txt)
        return lay

    def _pick_palette(self):
        dlg = PaletteDialog(self._palette_btn.value, self)
        if dlg.exec() == QDialog.Accepted and dlg.chosen is not None:
            self._palette_btn.set_palette(dlg.chosen)
            self._editor.setText(dlg.chosen)       # fires textChanged -> emit

    def _make_editor(self, p, value):
        t = p.get("type") or "text"
        lay = self.editor_lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        w = None

        if p["name"] == "colormap_brewer_name":
            return self._make_palette_editor(p, value)

        if t == "bool":
            w = QComboBox()
            w.addItem("", "")
            w.addItem("1", "1")
            # presence-only flags: the engine acts on the key merely EXISTING,
            # so offering "0" (which reads as "off") would silently trigger the
            # behaviour — only offer unset / enabled.
            if p.get("presence_only"):
                val = "" if value is None else str(value)
                if val not in ("", "1"):
                    # an imported conf may already carry e.g. "0"; keep it
                    # visible so saving never silently drops the key
                    w.addItem(val, val)
                idx = w.findData(val) if val else 0
                w.setCurrentIndex(idx if idx >= 0 else 0)
                w.setToolTip(I18N.tr("presence_only_tip"))
            else:
                w.addItem("0", "0")
                w.setCurrentIndex(
                    {None: 0, "": 0, "1": 1, "0": 2, 1: 1, 0: 2}.get(value, 0)
                    if not isinstance(value, bool) else (1 if value else 2))
        elif t == "enum":
            w = QComboBox()
            w.addItem("", "")
            for c in p.get("choices") or []:
                w.addItem(str(c), str(c))
            if value != "" and w.findData(str(value)) < 0:
                w.addItem(str(value), str(value))
            init = self._initial_value(p, value)
            idx = w.findData(init) if init else 0
            w.setCurrentIndex(idx if idx >= 0 else 0)
        elif t == "int":
            w = QSpinBox()
            lo = p.get("min") if p.get("min") is not None else -WIDE
            hi = p.get("max") if p.get("max") is not None else WIDE
            if lo == hi:
                hi = lo + 1
            w.setRange(lo, hi)
            w.setFixedWidth(140)
            try:
                init = int(float(self._initial_value(p, value) or 0))
                w.setValue(min(max(init, lo), hi))
            except (TypeError, ValueError, OverflowError):
                w.setValue(0)
        elif t == "float":
            w = QDoubleSpinBox()
            w.setDecimals(6)
            # honour the schema range exactly like the int editor does,
            # otherwise tooltips advertise limits the editor does not enforce
            lo = p.get("min") if p.get("min") is not None else -1e18
            hi = p.get("max") if p.get("max") is not None else 1e18
            if lo == hi:
                hi = lo + 1
            w.setRange(lo, hi)
            w.setFixedWidth(160)
            try:
                init = float(self._initial_value(p, value) or 0.0)
                w.setValue(min(max(init, lo), hi))
            except (TypeError, ValueError):
                w.setValue(0.0)
        elif t == "color":
            w = ColorButton(self._initial_value(p, value))
            txt = QLineEdit()
            txt.setPlaceholderText("#RRGGBB")
            txt.setText(self._initial_value(p, value))
            txt.textChanged.connect(lambda s, b=w: (setattr(b, "value", s), b._apply()))
            w.picked.connect(txt.setText)     # swatch chooser -> hex field
            lay.addWidget(w)
            lay.addWidget(txt, 1)
            self._color_btn, self._color_txt = w, txt
            self._bind_color()
            return lay
        elif t == "file":
            w = QLineEdit()
            w.setText("" if value is None else str(value))
            btn = QPushButton(I18N.tr("choose"))
            btn.setFixedWidth(70)
            btn.clicked.connect(self._browse)
            lay.addWidget(w, 1)
            lay.addWidget(btn)
            self._file_edit = w
            self._bind_line(w)
            return lay
        else:  # text
            w = QLineEdit()
            w.setText(self._initial_value(p, value))
            lay.addWidget(w, 1)
            self._editor = w
            self._bind_line(w)
            return lay

        lay.addWidget(w, 1 if t in ("bool", "enum") else 0)
        if t == "bool":
            w.currentIndexChanged.connect(self._emit_combo)
        elif t == "enum":
            w.currentIndexChanged.connect(self._emit_combo)
        elif t == "int":
            w.valueChanged.connect(lambda v: self._emit_value(int(v)))
        elif t == "float":
            w.valueChanged.connect(lambda v: self._emit_value(float(v)))
        self._editor = w
        return lay

    def _bind_line(self, edit):
        edit.textChanged.connect(lambda s: self._emit_value(s))

    def _bind_color(self):
        self._color_txt.textChanged.connect(lambda s: self._emit_value(s))

    def _browse(self):
        from PySide6.QtWidgets import QFileDialog
        f, _ = QFileDialog.getOpenFileName(self)
        if f:
            self._file_edit.setText(f)

    # ------------------------------------------------------------- events
    @staticmethod
    def _fmt_num(v):
        """Normalize numeric editor values: 1.0 -> '1', keep real decimals."""
        if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return str(v)

    def _emit_value(self, v):
        if self._building:
            return
        if isinstance(v, float):
            v = self._fmt_num(v)
        self.changed.emit(self.key, "" if v in (None, "") else str(v))

    def _emit_combo(self, _i):
        self._emit_value(self._editor.currentData())

    def _on_toggle(self, on):
        if self._building:
            return
        self._sync_enabled()
        if not on:
            self._emit_value("")
        elif self.param.get("type") == "bool":
            self._emit_value("1")
        else:
            cur = self._current_editor_value()
            self._emit_value(cur)

    def _current_editor_value(self):
        t = self.param.get("type")
        if t in ("bool", "enum"):
            return self._editor.currentData() or ""
        if t == "int":
            return str(self._editor.value())
        if t == "float":
            return self._fmt_num(self._editor.value())
        if t == "color":
            return self._color_txt.text()
        if t == "file":
            # file editors keep their text in _file_edit, not _editor; without
            # this branch re-enabling the row emitted "" and dropped the path
            return self._file_edit.text() if hasattr(self, "_file_edit") else ""
        return self._editor.text() if hasattr(self, "_editor") else ""

    def _sync_enabled(self):
        for w in self.findChildren(QWidget):
            if w is self.enable or w is self.label or w is self.default_label:
                continue                     # hint stays readable when unchecked
            w.setEnabled(self.enable.isChecked())

    def set_external(self, value):
        """Update editors from the model WITHOUT re-emitting (cross-tab sync)."""
        self._building = True
        value = "" if value is None else str(value)
        try:
            self.enable.setChecked(value != "")
            t = self.param.get("type") or "text"
            if t == "bool":
                if self.param.get("presence_only"):
                    idx = self._editor.findData(value)
                    self._editor.setCurrentIndex(idx if idx >= 0 else 0)
                else:
                    idx = {None: 0, "": 0, "1": 1, "0": 2}.get(value, 0)
                    self._editor.setCurrentIndex(idx)
            elif t == "enum":
                idx = self._editor.findData(value)
                if idx < 0 and value:
                    self._editor.addItem(value, value)
                    idx = self._editor.findData(value)
                self._editor.setCurrentIndex(idx if idx >= 0 else 0)
            elif t == "int":
                try:
                    self._editor.setValue(int(float(value)) if value else 0)
                except (TypeError, ValueError, OverflowError):
                    self._editor.setValue(0)
            elif t == "float":
                try:
                    self._editor.setValue(float(value) if value else 0.0)
                except (TypeError, ValueError, OverflowError):
                    self._editor.setValue(0.0)
            elif t == "color":
                self._color_txt.setText(value)
                self._color_btn.value = value
                self._color_btn._apply()
            elif t == "file":
                self._file_edit.setText(value)
            elif self.param["name"] == "colormap_brewer_name":
                self._editor.setText(value)
                self._palette_btn.set_palette(value)   # keep the swatch in sync
            else:
                self._editor.setText(value)
            self._apply_placeholder(self.param, value)
        finally:
            self._building = False
        self._sync_enabled()

    def current_value(self):
        if not self.enable.isChecked():
            return ""
        return self._current_editor_value()


class ParamForm(QWidget):
    """Category list + scrollable rows for one conf section."""
    any_changed = Signal(str, object)
    plot_type_changed = Signal(str)
    files_changed = Signal(list)
    param_changed = Signal(object, str, object)   # scope, key, value

    def __init__(self, scope, model, parent=None, exclude=None):
        super().__init__(parent)
        self.scope = scope
        # schema lookups need the section kind ("global"/"track"); per-track
        # forms use an int index (their model methods are int-aware already)
        self._schema_scope = "track" if isinstance(scope, int) else scope
        self.model = model
        self.exclude = exclude or set()
        self.plot_filter = None          # current plot_type or None = all
        self.show_all = False
        self._rows = {}
        self.files_bar = None            # embedded FilesBar (files category only)

        self.cat_list = QListWidget()
        self.cat_list.setMaximumWidth(175)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(I18N.tr("filter"))
        self.filter_edit.setToolTip(I18N.tr("filter_tip"))
        self.filter_edit.setMaximumWidth(175)
        self.show_all_cb = QCheckBox(I18N.tr("show_all_params"))
        self.show_all_cb.setToolTip(I18N.tr("show_all_tip"))
        self.show_all_cb.setMaximumWidth(175)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(self.filter_edit)
        left.addWidget(self.cat_list)
        left.addWidget(self.show_all_cb)

        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.addLayout(left, 0)
        root.addWidget(self.scroll, 1)

        self.cat_list.currentTextChanged.connect(lambda _s: self._fill_rows())
        self.filter_edit.textChanged.connect(lambda _s: self._fill_rows())
        self.show_all_cb.toggled.connect(self._toggled_all)

        # persistent FilesBar (global form only): reparented into the card
        # on demand instead of being recreated (and deleteLater'd) on every
        # category switch — a stale reference to the deleted C++ object
        # crashed on macOS ("QVBoxLayout already deleted")
        if self.scope == "global":
            self.files_bar = FilesBar()
            self.files_bar.set_files(list(self.model.files))
            self.files_bar.changed.connect(self._on_files_bar_changed)

        self.rebuild()

    # ------------------------------------------------------------- build
    def rebuild(self):
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        self._cats = Schema.by_category(self._schema_scope)
        for cat, params in self._cats.items():
            n = self._lang_cat(cat)
            it = QListWidgetItem("%s (%d)" % (n, len(params)))
            it.setData(Qt.UserRole, cat)     # stable key (labels may contain "(")
            self.cat_list.addItem(it)
        self.cat_list.blockSignals(False)
        if self.cat_list.count():
            self.cat_list.setCurrentRow(0)
        self._fill_rows()

    def _lang_cat(self, cat):
        c = Schema.categories().get(cat, {})
        return c.get(I18N.lang(), c.get("zh", cat))

    def _toggled_all(self, _on):
        self.show_all = self.show_all_cb.isChecked()
        self._fill_rows()

    def set_plot_filter(self, plot_type):
        self.plot_filter = plot_type
        self._fill_rows()

    @staticmethod
    def _param_allowed(p, plot_filter, show_all):
        if not show_all and p.get("importance", 0) == 0 and not p.get("default") \
                and p["name"] not in ("background_color", "show_columns"):
            return False
        rel = p.get("plot_types") or []
        if plot_filter and rel:
            return plot_filter in rel
        return True

    def _fill_rows(self):
        # explicitly retire the previous central widget (filter typing and
        # category switches rebuild frequently): never leave orphaned rows.
        # Detach the persistent FilesBar first, otherwise deleting the old
        # central card would destroy it too ("C++ object already deleted").
        if self.files_bar is not None:
            self.files_bar.setParent(self)
        old = self.scroll.takeWidget()
        if old is not None:
            old.setParent(None)
            old.deleteLater()
        central = QFrame()
        central.setObjectName("formPage")
        lay = QVBoxLayout(central)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        sel = self.cat_list.currentItem()
        want = sel.data(Qt.UserRole) if sel else None
        flt = self.filter_edit.text().strip().lower()
        self._rows = {}

        def add_card_rows(card_lay, params):
            for p in params:
                if p["name"] in self.exclude or p.get("category") == "files":
                    continue                 # File1/FileN live in the FilesBar
                value = self.model.get_param(self.scope, p["name"])
                row = ParamRow(p, value)
                row.changed.connect(self._on_row_changed)
                card_lay.addWidget(row)
                self._rows[p["name"]] = row

        # ---- special section: data files (embedded FilesBar, card style)
        if self.scope == "global" and want == "files" and not flt:
            card, v = make_card(I18N.tr("data_files"))
            v.addWidget(QLabel(I18N.tr("file_hint")))
            # sync latest file list (no-op when unchanged), then reparent the
            # single persistent bar into this freshly built card
            self.files_bar.set_files(list(self.model.files))
            v.addWidget(self.files_bar)
            lay.addWidget(card)
            lay.addStretch(1)
            self.scroll.setWidget(central)
            return

        if flt:
            # ---- global search: matching rows from ALL categories, one card each
            # (an explicit search overrides category selection and plot filter)
            for cat, params in self._cats.items():
                matched = [p for p in params
                           if p["name"] not in self.exclude
                           and p.get("category") != "files"
                           and (flt in p["name"].lower()
                                or flt in (p.get("label_zh") or "")
                                or flt in (p.get("label_en") or "").lower())]
                if not matched:
                    continue
                card, v = make_card(self._lang_cat(cat))
                for p in matched:
                    value = self.model.get_param(self.scope, p["name"])
                    row = ParamRow(p, value)
                    row.changed.connect(self._on_row_changed)
                    v.addWidget(row)
                    self._rows[p["name"]] = row
                lay.addWidget(card)
            if not self._rows:
                lay.addWidget(QLabel(I18N.tr("filter_nomatch")))
            lay.addStretch(1)
            self.scroll.setWidget(central)
            return

        # ---- normal: one grouped card for the selected category
        for cat, params in self._cats.items():
            if want is not None and cat != want:
                continue
            visible = [p for p in params
                       if p["name"] not in self.exclude
                       and p.get("category") != "files"
                       and self._param_allowed(p, self.plot_filter, self.show_all)]
            card, v = make_card(self._lang_cat(cat))
            for p in visible:
                value = self.model.get_param(self.scope, p["name"])
                row = ParamRow(p, value)
                row.changed.connect(self._on_row_changed)
                v.addWidget(row)
                self._rows[p["name"]] = row
            if not visible:
                # never leave a blank card: explain why nothing is listed
                cand = [p for p in params
                        if p["name"] not in self.exclude
                        and p.get("category") != "files"]
                if (cand and not self.show_all
                        and all(self._param_allowed(p, self.plot_filter, True)
                                for p in cand)
                        and any(not self._param_allowed(p, self.plot_filter, False)
                                for p in cand)):
                    msg = I18N.tr("cat_all_lowfreq")
                else:
                    msg = I18N.tr("filter_nomatch")
                hint = QLabel(msg)
                hint.setWordWrap(True)
                hint.setStyleSheet("color: palette(mid);")
                v.addWidget(hint)
            lay.addWidget(card)
        lay.addStretch(1)
        self.scroll.setWidget(central)

    def _on_files_bar_changed(self, files):
        self.model.files = list(files)
        self.files_changed.emit(list(files))

    def _on_row_changed(self, key, value):
        self.model.set_param(self.scope, key, value)
        self.any_changed.emit(key, value)
        self.param_changed.emit(self.scope, key, value)
        if key == "plot_type" and self.scope != "global":
            self.plot_type_changed.emit(value or "")

    def sync_row(self, key, value):
        """Cross-tab sync: update one row editor from an external change."""
        row = self._rows.get(key)
        if row is not None:
            row.set_external(value)

    def current_plot_type(self):
        return self.model.get_param(self.scope, "plot_type") or ""
