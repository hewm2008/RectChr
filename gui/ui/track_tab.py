"""One track tab: prominent plot_type/show_columns + filtered ParamForm."""
from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..core.schema import Schema
from ..i18n import I18N
from .param_form import ParamForm
from .plot_icons import plot_type_icon


def track_tab_title(model, index):
    """Tab caption for a track section (no widget construction needed)."""
    pt = model.get_param(index, "plot_type")
    base = I18N.tr("track_tab", n=index)
    return "%s · %s" % (base, pt) if pt else base


class LazyPage(QWidget):
    """Placeholder tab that builds its content the first time it is shown.

    Building one full ParamForm (or the whole summary table) per configured
    track does not scale: a conf with 79 track sections produced ~6000 widgets
    and blocked the UI for ~2.4 s on every rebuild (import, language switch,
    add/remove track). The model is the single source of truth, so building
    later is always correct.
    """

    def __init__(self, build, title_fn=None, on_built=None, parent=None):
        super().__init__(parent)
        self._build = build
        self._title_fn = title_fn
        self._on_built = on_built
        self.widget = None
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)

    def materialized(self):
        return self.widget is not None

    def materialize(self):
        """Build the real content (idempotent)."""
        if self.widget is None:
            self.widget = self._build()
            self._lay.addWidget(self.widget)
            if self._on_built is not None:
                self._on_built(self)
        return self.widget

    def tab_title(self):
        return self._title_fn() if self._title_fn is not None else ""

    # transparent delegation for callers that talk to the built widget; the
    # model is the source of truth, so syncing into a page that was never
    # opened is unnecessary (it reads the model when it is built)
    def refresh(self, *a, **k):
        return self.materialize().refresh(*a, **k)

    def sync_files(self, files):
        if self.materialized():
            self.widget.sync_files(files)

    def sync_value(self, scope, key, value):
        if self.materialized():
            self.widget.sync_value(scope, key, value)


class LazyTrackPage(LazyPage):
    """Lazy page for one sparse track section (carries its track index)."""

    def __init__(self, model, index, on_built=None, parent=None):
        super().__init__(build=None, title_fn=lambda: track_tab_title(model, index),
                         on_built=on_built, parent=parent)
        self.model = model
        self.index = index                    # 1-based track number
        self.tab = None                       # materialized TrackTab
        self._build = self._make_tab

    def _make_tab(self):
        self.tab = TrackTab(self.model, self.index)
        return self.tab


class TrackTab(QWidget):
    plot_type_changed = Signal(int, str)        # track index (1-based), plot_type
    param_changed = Signal(int, str, object)    # track index, key, value
    changed = Signal()

    def __init__(self, model, index, parent=None):
        super().__init__(parent)
        self.model = model
        self.index = index                       # 1-based
        self._building = True

        box = QGroupBox()
        lay = QHBoxLayout(box)
        lay.addWidget(QLabel(I18N.tr("plot_type")))
        self.pt_combo = QComboBox()
        self.pt_combo.setIconSize(QSize(18, 18))
        for pt in Schema.plot_types():
            if pt.get("legacy"):
                continue
            label = pt.get(I18N.lang(), pt["name"])
            self.pt_combo.addItem(plot_type_icon(pt["name"]),
                                  "%s (%s)" % (label, pt["name"]) if label != pt["name"] else pt["name"],
                                  pt["name"])
        # normalize a legacy spelling ("lines", "histogram", ...) so the combo
        # hits the canonical item (with its icon) instead of appending a bare one
        cur = Schema.resolve_plot_type(model.get_param(index, "plot_type"))
        if cur and self.pt_combo.findData(cur) < 0:
            self.pt_combo.addItem(cur, cur)
        self.pt_combo.setCurrentIndex(self.pt_combo.findData(cur))
        lay.addWidget(self.pt_combo)

        lay.addWidget(QLabel(I18N.tr("data_source")))
        self.sc_edit = QLineEdit(model.get_param(index, "show_columns"))
        self.sc_edit.setPlaceholderText("File1:4  /  File2:4,5")
        self.sc_edit.setMaximumWidth(260)
        lay.addWidget(self.sc_edit)
        lay.addStretch(1)

        self.form = ParamForm(index, model, exclude={"plot_type", "show_columns"})
        self.form.any_changed.connect(lambda _k, _v: self.changed.emit())
        self.form.plot_type_changed.connect(lambda pt: self.plot_type_changed.emit(self.index, pt))
        self.form.param_changed.connect(
            lambda _scope, k, v: self.param_changed.emit(self.index, k, v))

        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.addWidget(box)
        root.addWidget(self.form, 1)

        self.pt_combo.currentIndexChanged.connect(self._pt_changed)
        self.sc_edit.textChanged.connect(self._sc_changed)
        self._building = False
        self._apply_filter()

    def _apply_filter(self):
        pt = self.model.get_param(self.index, "plot_type")
        self.form.set_plot_filter(pt or None)

    def _pt_changed(self, _i):
        if self._building:
            return
        pt = self.pt_combo.currentData() or ""
        self.model.set_param(self.index, "plot_type", pt)
        self._apply_filter()
        self.plot_type_changed.emit(self.index, pt)
        self.changed.emit()

    def _sc_changed(self, text):
        if self._building:
            return
        self.model.set_param(self.index, "show_columns", text.strip())
        self.changed.emit()

    def sync_plot_type(self, pt):
        """Cross-tab sync: external plot_type change for this track."""
        self._building = True
        # no blank item in the combo: unset maps to -1 (empty display), never
        # fall back to index 0 or clearing would show the first type
        idx = self.pt_combo.findData(pt or "")
        self.pt_combo.setCurrentIndex(idx)
        self._building = False
        self.model.set_param(self.index, "plot_type", pt or "")
        self._apply_filter()
        self.changed.emit()

    def sync_param(self, key, value):
        self.form.sync_row(key, value)

    def sync_show_columns(self, value):
        """Cross-tab sync: external show_columns change for this track.

        show_columns is excluded from the inner form, so sync_param() cannot
        reach it — without this the header field kept the stale text and
        wrote it back over the model on the next edit."""
        value = value or ""
        if self.sc_edit.text() == value:
            return
        self._building = True
        self.sc_edit.setText(value)
        self._building = False
        self.model.set_param(self.index, "show_columns", value)

    def tab_title(self):
        return track_tab_title(self.model, self.index)
