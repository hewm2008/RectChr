"""RectChr GUI main window: toolbar, files dock, parameter tabs, preview, runner."""
import re
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox,
                               QDockWidget, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMenu, QMessageBox,
                               QPlainTextEdit, QPushButton, QSizePolicy, QSpinBox,
                               QTabBar, QTabWidget, QToolBar, QToolButton, QVBoxLayout,
                               QWidget)

from .. import GUI_VERSION
from ..core.conf_io import ConfModel, abspath_for
from ..theme import make_card
from ..core.runner import ENGINE, GUI_DIR, ROOT, RectChrRunner, find_perl
from ..i18n import I18N
from .files_panel import FilesPanel
from .params_summary import ParamsSummaryTab
from .param_form import ParamForm
from .preview import PreviewView
from .logo import application_icon, logo_pixmap
from .track_tab import LazyPage, LazyTrackPage, TrackTab

SHOW_COLUMNS_RE = re.compile(r"^(File\d+:\d+(,\d+)*)(\s+File\d+:\d+(,\d+)*)*$")


class ParameterTabBar(QTabBar):
    def _position_close_buttons(self):
        for index in range(self.count()):
            button = self.tabButton(index, QTabBar.RightSide)
            if button is None:
                continue
            rect = self.tabRect(index)
            button.move(rect.right() - 7 - button.width(), rect.top() + 5)

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._position_close_buttons()

    def paintEvent(self, event):
        self._position_close_buttons()
        super().paintEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(application_icon())
        self.settings = QSettings("RectChr", "RectChrGUI")
        lang = self.settings.value("language", "zh")
        I18N.set_lang(str(lang))

        self.model = ConfModel()
        self.out_dir = Path(self.settings.value("out_dir", str(Path.home())))
        self.out_name = "RectChrGUI"
        self.runner = RectChrRunner(self)
        self.runner.output.connect(self._on_runner_output)
        self.runner.finished_ok.connect(self._on_run_ok)
        self.runner.failed.connect(self._on_run_fail)
        self._dirty = False

        self._build_central()
        self._build_dock()
        self._build_toolbar()
        self._build_statusbar()
        self._rebuild_param_tabs()
        self._resize_initial()
        self._update_title()

    def _resize_initial(self):
        """Open at 1400x900, clamped to the screen.

        Asking for a size larger than the screen (or resizing while the window
        is maximized) can make the Wayland compositor reject the committed
        buffer — 'xdg_surface buffer does not match the configured maximized
        state' — so never request more than the available geometry."""
        w, h = 1400, 900
        screen = QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            if avail.width() > 0 and avail.height() > 0:
                w, h = min(w, avail.width()), min(h, avail.height())
        self.resize(w, h)

    # ================================================================ UI
    def _build_toolbar(self):
        tb = QToolBar("main")
        tb.setObjectName("toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        # actions
        self.act_new = QAction(I18N.tr("new_project"), self)
        self.act_new.triggered.connect(self._new_project)
        self.act_open = QAction(I18N.tr("open_conf"), self)
        self.act_open.setShortcut(QKeySequence.Open)
        self.act_open.triggered.connect(self._open_conf)
        self.act_save = QAction(I18N.tr("save_conf"), self)
        self.act_save.setShortcut(QKeySequence.Save)
        self.act_save.triggered.connect(self._save_conf)
        self.act_run = QAction(I18N.tr("run"), self)
        self.act_run.triggered.connect(self._run)
        self.act_svg = QAction(I18N.tr("export_svg"), self)
        self.act_svg.triggered.connect(self._export_svg)
        self.act_png = QAction(I18N.tr("export_png"), self)
        self.act_png.triggered.connect(self._export_png)
        self.act_pdf = QAction(I18N.tr("export_pdf"), self)
        self.act_pdf.triggered.connect(self._export_pdf)
        self.act_help = QAction(I18N.tr("help"), self)
        self.act_help.setShortcut(QKeySequence.HelpContents)   # F1
        self.act_help.setToolTip(I18N.tr("help_tip"))
        self.act_help.triggered.connect(self._open_manual)
        self.act_about = QAction(I18N.tr("about"), self)
        self.act_about.setToolTip(I18N.tr("about_tip"))
        self.act_about.triggered.connect(self._show_about)
        self.act_reset_layout = QAction(I18N.tr("reset_layout"), self)
        self.act_reset_layout.triggered.connect(self._reset_layout)

        # ---- menu buttons (same row as the regular buttons)
        self.menu_file = QMenu(I18N.tr("menu_file"), self)
        self.btn_file_menu = None
        for a in (self.act_new, self.act_open, self.act_save):
            self.menu_file.addAction(a)
        self.menu_file.addSeparator()
        for a in (self.act_svg, self.act_png, self.act_pdf):
            self.menu_file.addAction(a)
        self.menu_view = QMenu(I18N.tr("view_menu"), self)
        self.btn_view_menu = None
        for d in (self.files_dock, self.params_dock, self.log_dock):
            self.menu_view.addAction(d.toggleViewAction())
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.act_reset_layout)
        self.menu_help = QMenu(I18N.tr("help"), self)
        self.btn_help_menu = None
        self.menu_help.addAction(self.act_help)
        self.menu_help.addAction(self.act_about)

        self.btn_file_menu = QToolButton()
        self.btn_file_menu.setMenu(self.menu_file)
        self.btn_file_menu.setPopupMode(QToolButton.InstantPopup)
        self.btn_file_menu.setText(I18N.tr("menu_file"))
        tb.addWidget(self.btn_file_menu)
        self.btn_view_menu = QToolButton()
        self.btn_view_menu.setMenu(self.menu_view)
        self.btn_view_menu.setPopupMode(QToolButton.InstantPopup)
        self.btn_view_menu.setText(I18N.tr("view_menu"))
        tb.addWidget(self.btn_view_menu)
        tb.addSeparator()

        # ---- high-frequency buttons
        self.act_new_btn = QAction(I18N.tr("new_project"), self)
        self.act_new_btn.triggered.connect(self._new_project)
        tb.addAction(self.act_new_btn)
        self.act_open_btn = QAction(I18N.tr("open_conf"), self)
        self.act_open_btn.triggered.connect(self._open_conf)
        tb.addAction(self.act_open_btn)
        self.act_refresh = QAction(I18N.tr("refresh_preview"), self)
        self.act_refresh.setShortcut(QKeySequence.Refresh)   # F5
        self.act_refresh.triggered.connect(self._run)
        tb.addAction(self.act_refresh)
        tb.addAction(self.act_run)
        tb.widgetForAction(self.act_run).setObjectName("primaryBtn")

        # language selector + help menu, right-aligned as a group
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        self.btn_cite = QToolButton()
        self.btn_cite.setObjectName("citationButton")
        self.btn_cite.setText(I18N.tr("cite"))
        self.btn_cite.clicked.connect(self._show_citation)
        tb.addWidget(self.btn_cite)
        self.btn_help_menu = QToolButton()
        self.btn_help_menu.setMenu(self.menu_help)
        self.btn_help_menu.setPopupMode(QToolButton.InstantPopup)
        self.btn_help_menu.setText(I18N.tr("help"))
        tb.addWidget(self.btn_help_menu)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("中文", "zh")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCurrentIndex(0 if I18N.lang() == "zh" else 1)
        self.lang_combo.currentIndexChanged.connect(self._switch_lang)
        tb.addWidget(QLabel(I18N.tr("language") + ": "))
        tb.addWidget(self.lang_combo)

    _MANUALS = [
        ("engine_zh", "RectChr_manual_Chinese_251006.pdf", "help_engine_zh"),
        ("engine_en", "RectChr_manual_English_251006.pdf", "help_engine_en"),
        ("gui_zh", "RectChr_GUI_manual_Chinese.pdf", "help_gui_zh"),
        ("gui_en", "RectChr_GUI_manual_English.pdf", "help_gui_en"),
    ]

    @staticmethod
    def _manual_bases(kind):
        exe_dir = Path(sys.executable).parent
        if kind.startswith("gui"):
            return (ROOT / "gui" / "doc", exe_dir / "gui" / "doc",
                    exe_dir, ROOT)
        return (ROOT, exe_dir, ROOT.parent)

    @classmethod
    def _find_manual(cls, kind, name):
        for base in cls._manual_bases(kind):
            cand = base / name
            if cand.is_file():
                return cand
        return None

    def _gui_doc_dir(self):
        """Writable directory for generated GUI manuals."""
        for d in (ROOT / "gui" / "doc",
                  Path(sys.executable).parent / "gui" / "doc",
                  self.out_dir):
            try:
                d.mkdir(parents=True, exist_ok=True)
                probe = d / ".probe"
                probe.write_text("", encoding="utf-8")
                probe.unlink()
                return d
            except OSError:
                continue
        return self.out_dir

    def _generate_gui_manual(self, kind, name):
        """Generate a missing GUI manual; returns the written Path or None."""
        try:
            import importlib.util
            script = None
            for base in (GUI_DIR, ROOT, Path(sys.executable).parent):
                cand = base / "tools" / "gen_gui_manual.py"
                if cand.is_file():
                    script = cand
                    break
            if script is None:
                raise FileNotFoundError("gen_gui_manual.py not found")
            spec = importlib.util.spec_from_file_location("gen_gui_manual", script)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            dest = self._gui_doc_dir()
            written = mod.generate(dest, langs=(kind[-2:],),
                                   gui_ver=GUI_VERSION,
                                   engine_ver=self._engine_version())
            return written.get(kind[-2:])
        except Exception as e:                    # noqa: BLE001
            self._show_error("generate-manual", e)
            return None

    def _open_manual(self):
        """Help button: choose one of the bundled/generated manuals."""
        from PySide6.QtCore import QUrl
        dlg = self._build_help_dialog()
        dlg.exec()

    def _build_help_dialog(self):
        """Construct the manual-chooser dialog (NO exec — safe for tests)."""
        from PySide6.QtCore import QUrl
        dlg = QDialog(self)
        dlg.setWindowTitle(I18N.tr("help_pick_title"))
        lay = QVBoxLayout(dlg)
        intro = QLabel(I18N.tr("help_pick_intro"))
        intro.setWordWrap(True)
        lay.addWidget(intro)

        def open_path(p):
            self._open_url(QUrl.fromLocalFile(str(p)))

        for kind, name, i18n_key in self._MANUALS:
            row = QHBoxLayout()
            found = self._find_manual(kind, name)
            desc = I18N.tr(i18n_key)
            btn = QPushButton(desc)
            btn.setStyleSheet("text-align:left; padding:6px;")
            row.addWidget(btn, 1)
            status = QLabel()
            if found is not None:
                status.setText(I18N.tr("help_bundled"))
                status.setStyleSheet("color: palette(mid);")
                btn.clicked.connect(lambda _c=False, p=found: open_path(p))
                # Word (.docx) companion for GUI manuals
                if kind.startswith("gui"):
                    docx_path = found.with_suffix(".docx")
                    word_btn = QPushButton(I18N.tr("help_word"))
                    word_btn.setToolTip(I18N.tr("help_word_tip"))
                    word_btn.setEnabled(docx_path.is_file())
                    word_btn.clicked.connect(
                        lambda _c=False, p=docx_path: open_path(p))
                    row.addWidget(word_btn)
            elif kind.startswith("gui"):
                btn.setText(desc + "  ·  " + I18N.tr("help_generate"))
                btn.clicked.connect(
                    lambda _c=False, k=kind, n=name, st=status, b=open_path:
                    self._generate_and_open(k, n, st, b))
                status.setText(I18N.tr("help_missing_tag"))
                status.setStyleSheet("color: palette(mid);")
            else:
                btn.setEnabled(False)
                status.setText(I18N.tr("help_missing_tag"))
                status.setStyleSheet("color: palette(mid);")
            row.addWidget(status)
            lay.addLayout(row)
        tip = QLabel(I18N.tr("help_pick_footer"))
        tip.setWordWrap(True)
        tip.setStyleSheet("color: palette(mid);")
        lay.addWidget(tip)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        bb.clicked.connect(dlg.accept)
        lay.addWidget(bb)
        return dlg

    def _generate_and_open(self, kind, name, status_label, open_fn):
        path = self._generate_gui_manual(kind, name)
        if path is None:
            return
        path = Path(path)
        status_label.setText(I18N.tr("help_generated", f=path.name))
        open_fn(path)

    def _open_url(self, url):
        """Hand a local file/URL to the desktop (blank if nothing registered)."""
        from PySide6.QtGui import QDesktopServices
        if not QDesktopServices.openUrl(url):
            self.statusBar().showMessage(I18N.tr("open_failed"), 6000)

    def _show_citation(self):
        self._build_citation_dialog().exec()

    def _build_citation_dialog(self):
        url = "https://github.com/hewm2008/RectChr"
        citation = "RectChr — GitHub repository. " + url
        dlg = QDialog(self)
        dlg.setWindowTitle(I18N.tr("cite"))
        lay = QVBoxLayout(dlg)
        intro = QLabel(I18N.tr("cite_intro"))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        text = QPlainTextEdit(citation)
        text.setObjectName("citationText")
        text.setReadOnly(True)
        text.setMinimumWidth(440)
        text.setMaximumHeight(90)
        lay.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        copy = buttons.addButton(I18N.tr("copy_citation"), QDialogButtonBox.ActionRole)
        copy.setObjectName("copyCitationButton")
        def copy_citation():
            QApplication.clipboard().setText(citation)
            copy.setText(I18N.tr("citation_copied"))
        copy.clicked.connect(copy_citation)
        github = buttons.addButton(I18N.tr("open_github"), QDialogButtonBox.ActionRole)
        github.setObjectName("openCitationGithubButton")
        github.clicked.connect(lambda: self._open_url(QUrl(url)))
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)
        return dlg

    def _show_about(self):
        dlg = self._build_about_dialog()
        dlg.exec()

    def _build_about_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(I18N.tr("about_title"))
        lay = QVBoxLayout(dlg)
        logo = QLabel()
        logo.setObjectName("aboutLogo")
        logo.setAccessibleName("RectChr")
        logo.setPixmap(logo_pixmap())
        logo.setAlignment(Qt.AlignCenter)
        lay.addWidget(logo)
        body = QLabel(I18N.tr("about_body", gui_ver=GUI_VERSION,
                              engine_ver=self._engine_version()))
        body.setTextFormat(Qt.RichText)
        body.setOpenExternalLinks(True)          # mailto / https via system
        body.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.TextSelectableByMouse)
        lay.addWidget(body)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        bb.clicked.connect(dlg.accept)
        lay.addWidget(bb)
        return dlg

    @staticmethod
    def _engine_version():
        """Engine version parsed from bin/RectChr, e.g. '1.50'."""
        try:
            m = re.search(r"Version\s*:\s*(\d+\.\d+)", ENGINE.read_text(errors="replace"))
            return m.group(1) if m else "1.50"
        except OSError:
            return "1.50"

    def _build_central(self):
        # central widget = the live preview (no longer a tab)
        self.preview = PreviewView()
        self.btn_refresh = QPushButton(I18N.tr("refresh_preview"))
        self.btn_refresh.setToolTip(I18N.tr("refresh_tip"))
        self.btn_refresh.setShortcut(QKeySequence.Refresh)   # F5
        self.btn_refresh.clicked.connect(self._run)
        self.chk_auto = QCheckBox(I18N.tr("auto_refresh"))
        self.chk_auto.setToolTip(I18N.tr("auto_refresh_tip"))
        self.chk_auto.setChecked(self.settings.value("auto_refresh", "0") in ("1", "true", True))
        self.chk_auto.toggled.connect(self._auto_toggled)
        self.btn_svg = QPushButton(I18N.tr("export_svg"))
        self.btn_svg.setToolTip(I18N.tr("export_svg_tip"))
        self.btn_svg.clicked.connect(self._export_svg)
        self.btn_pdf = QPushButton(I18N.tr("export_pdf"))
        self.btn_pdf.clicked.connect(self._export_pdf)
        strip_frame = QFrame()
        strip_frame.setObjectName("previewStrip")
        strip = QHBoxLayout(strip_frame)
        strip.setContentsMargins(8, 6, 8, 6)
        strip.setSpacing(6)
        strip.addWidget(self.btn_refresh)
        strip.addWidget(self.chk_auto)
        strip.addWidget(self.btn_svg)
        strip.addWidget(self.btn_pdf)
        strip.addStretch(1)
        pwrap = QWidget()
        play = QVBoxLayout(pwrap)
        play.setContentsMargins(8, 8, 8, 8)
        play.addWidget(strip_frame)
        play.addWidget(self.preview, 1)
        self._preview_stale = False
        self._preview_page = pwrap
        self.setCentralWidget(self._preview_page)

        # debounce timer for auto refresh (1.5 s after the last edit)
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.setInterval(1500)
        self._auto_timer.timeout.connect(self._flush_auto)
        self._auto_pending = False
        self._pending_manual = False
        self._last_run_auto = False

    def _build_dock(self):
        # left: data files (existing)
        self.files_panel = FilesPanel()
        self.files_panel.base_dir = self.out_dir
        self.files_panel.files_changed.connect(self._on_files_changed)
        self.files_panel.file1_analyzed.connect(self._on_file1_analyzed)
        dock = QDockWidget(I18N.tr("data_files"), self)
        dock.setObjectName("filesDock")
        dock.setWidget(self.files_panel)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.files_dock = dock

        # right: parameter tabs + Track 管理 row
        self._build_addrem_row()                     # sets self.addrem_row
        self.param_tabs = QTabWidget()
        self._param_tab_bar = ParameterTabBar()
        self.param_tabs.setTabBar(self._param_tab_bar)
        self.param_tabs.tabBar().setObjectName("parameterTabBar")
        self.param_tabs.setUsesScrollButtons(True)
        self.param_tabs.setDocumentMode(True)
        self.param_tabs.currentChanged.connect(lambda _i: self._refresh_summary_if_current())
        self.param_tabs.currentChanged.connect(self._on_tab_changed)
        right_wrap = QWidget()
        rlay = QVBoxLayout(right_wrap)
        rlay.setContentsMargins(4, 4, 4, 4)
        rlay.addWidget(self.addrem_row)
        rlay.addWidget(self.param_tabs, 1)
        rdock = QDockWidget(I18N.tr("right_dock_title"), self)
        rdock.setObjectName("paramsDock")
        rdock.setWidget(right_wrap)
        rdock.setFeatures(QDockWidget.DockWidgetMovable)   # essential: not closable
        self.addDockWidget(Qt.RightDockWidgetArea, rdock)
        self.params_dock = rdock

        # bottom: run log
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        ldock = QDockWidget(I18N.tr("log_dock_title"), self)
        ldock.setObjectName("logDock")
        ldock.setWidget(self.log)
        ldock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable
                          | QDockWidget.DockWidgetFloatable)
        ldock.setWidget(self.log)
        self.addDockWidget(Qt.BottomDockWidgetArea, ldock)
        self.log_dock = ldock

        # restore dock layout persisted from a previous session
        state = self.settings.value("dock_state")
        if state:
            self.restoreState(state)
        # default: compact log height -> more room for the preview above
        self.resizeDocks([ldock], [120], Qt.Vertical)

    def _build_addrem_row(self):
        """Compact Track 管理 card: single control row + status in the title."""
        addrem_card, card_lay = make_card(I18N.tr("track_manage"))
        self.addrem_row = addrem_card
        card_lay.setContentsMargins(10, 6, 10, 8)

        # status moves into the title row (muted, right aligned)
        title_item = card_lay.takeAt(0)
        title_label = title_item.widget()
        trow = QHBoxLayout()
        trow.addWidget(title_label)
        trow.addStretch(1)
        self.rem_status = QLabel()
        self.rem_status.setStyleSheet("color: palette(mid); font-size: 9pt;")
        trow.addWidget(self.rem_status)
        card_lay.insertLayout(0, trow)

        def _spin():
            s = QSpinBox()
            s.setRange(1, 999)
            s.setFixedWidth(64)
            return s
        n_max = max(self.model.tracks) if self.model.tracks else 0
        row = QHBoxLayout()
        row.setSpacing(4)
        self.add_spin = _spin()
        self.add_spin.setValue(n_max + 1)
        self.add_spin.setToolTip(I18N.tr("track_add_which"))
        add_label = QLabel("Track ID")
        add_label.setBuddy(self.add_spin)
        row.addWidget(add_label)
        row.addWidget(self.add_spin)
        self.add_btn = QPushButton(I18N.tr("add_track"))
        self.add_btn.setToolTip(I18N.tr("add_track_tip"))
        self.add_btn.clicked.connect(self._add_track)
        row.addWidget(self.add_btn)
        row.addSpacing(14)                        # 添加 | 移除 两组稍隔开
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: palette(mid);")
        row.addWidget(sep)
        row.addSpacing(10)
        self.rem_spin = _spin()
        self.rem_spin.setValue(n_max)
        self.rem_spin.setToolTip(I18N.tr("track_remove_which"))
        rem_label = QLabel("Track ID")
        rem_label.setBuddy(self.rem_spin)
        row.addWidget(rem_label)
        row.addWidget(self.rem_spin)
        self.rem_btn = QPushButton(I18N.tr("remove_track"))
        self.rem_btn.clicked.connect(self._remove_track)
        row.addWidget(self.rem_btn)
        row.addStretch(1)
        card_lay.addLayout(row)

    def _update_addrem_state(self):
        n_max = max(self.model.tracks) if self.model.tracks else 0
        self.add_spin.setValue(n_max + 1)       # default: next free number
        self.rem_spin.setValue(max(n_max, 1))
        self.rem_spin.setEnabled(n_max > 0)
        self.rem_btn.setEnabled(n_max > 0)
        if self.model.tracks:
            lst = ", ".join(str(k) for k in sorted(self.model.tracks))
            self.rem_status.setText(I18N.tr("tracks_count", n=lst))
        else:
            self.rem_status.setText(I18N.tr("auto_mode"))

    def _reset_layout(self):
        """Restore the default three-column layout: all docks visible in
        their original areas; clear the persisted dock state."""
        self.settings.remove("dock_state")
        for dock, area in ((self.files_dock, Qt.LeftDockWidgetArea),
                           (self.params_dock, Qt.RightDockWidgetArea),
                           (self.log_dock, Qt.BottomDockWidgetArea)):
            self.removeDockWidget(dock)
            self.addDockWidget(area, dock)
            dock.setVisible(True)

    def _build_statusbar(self):
        self.statusBar().showMessage("Perl: %s" % (find_perl() or I18N.tr("perl_missing")))

    def _rebuild_param_tabs(self, select=None):
        """(Re)create the tabs of the right-hand parameter dock.

        Track 管理 row and the central preview are NOT touched here. Track
        pages are lazy placeholders: only the one the user opens is built
        (a conf can declare dozens of tracks)."""
        self._rebuilding_tabs = True
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            pages = [getattr(self, "global_form", None),
                     getattr(self, "all_form", None),
                     getattr(self, "summary_tab", None)]
            pages += list((getattr(self, "track_pages", None) or {}).values())
            for w in pages:
                if w is None:
                    continue
                i = self.param_tabs.indexOf(w)
                if i >= 0:
                    self.param_tabs.removeTab(i)
                # removeTab() does NOT delete the page: without this every
                # rebuild leaks a whole form generation whose signals stay
                # connected
                w.setParent(None)
                w.deleteLater()

            pos = 0
            self.global_form = ParamForm("global", self.model)
            self.global_form.any_changed.connect(self._mark_dirty)
            self.global_form.param_changed.connect(self._route_param_change)
            self.global_form.files_changed.connect(self._on_bar_files_changed)
            self.param_tabs.insertTab(pos, self.global_form, I18N.tr("global_tab"))
            pos += 1

            self.all_form = ParamForm("track", self.model)
            self.all_form.any_changed.connect(self._mark_dirty)
            self.all_form.param_changed.connect(self._route_param_change)
            self.param_tabs.insertTab(pos, self.all_form, I18N.tr("track_all_tab"))
            pos += 1

            self.track_tabs = []                 # materialized TrackTabs only
            self.track_pages = {}                # idx -> LazyTrackPage
            for idx in sorted(self.model.tracks):
                page = LazyTrackPage(self.model, idx,
                                     on_built=self._on_track_page_built)
                self.track_pages[idx] = page
                self.param_tabs.insertTab(pos, page, page.tab_title())
                close_btn = QToolButton(self.param_tabs.tabBar())
                close_btn.setObjectName("trackCloseButton")
                close_btn.setText("×")
                close_btn.setAutoRaise(True)
                close_btn.setFixedSize(16, 16)
                close_btn.setToolTip(I18N.tr("remove_track") + " " + str(idx))
                close_btn.setAccessibleName(close_btn.toolTip())
                close_btn.clicked.connect(
                    lambda _checked=False, target=idx: self._remove_track_by_index(target))
                self.param_tabs.tabBar().setTabButton(pos, QTabBar.RightSide, close_btn)
                pos += 1

            self.summary_tab = LazyPage(build=lambda: ParamsSummaryTab(self.model),
                                        title_fn=lambda: I18N.tr("show_params"),
                                        on_built=self._on_summary_built)
            self.param_tabs.insertTab(pos, self.summary_tab, I18N.tr("show_params"))

            if select is not None:
                self.param_tabs.setCurrentWidget(select)
        finally:
            self._rebuilding_tabs = False
            QApplication.restoreOverrideCursor()
        self._materialize_current_track()
        self._update_addrem_state()

    # ------------------------------------------------------- lazy track pages
    def _materialize_current_track(self):
        w = self.param_tabs.currentWidget()
        if isinstance(w, LazyTrackPage):
            self._materialize_track(w)
        elif isinstance(w, LazyPage):
            self._materialize_lazy(w)

    def _on_tab_changed(self, _i):
        if getattr(self, "_rebuilding_tabs", False):
            return
        w = self.param_tabs.currentWidget()
        if isinstance(w, LazyTrackPage):
            self._materialize_track(w)
        elif isinstance(w, LazyPage):
            self._materialize_lazy(w)

    def _materialize_lazy(self, page):
        """Build a non-track lazy page (currently the summary) on first use."""
        if page.materialized():
            return page.widget
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            page.materialize()
        finally:
            QApplication.restoreOverrideCursor()
        return page.widget

    def _materialize_track(self, page):
        """Build a lazy track page on first use (busy cursor while it builds)."""
        if page.materialized():
            return page.tab
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage(I18N.tr("loading_tracks", n=page.index))
        try:
            page.materialize()
        finally:
            QApplication.restoreOverrideCursor()
            self.statusBar().clearMessage()
        return page.tab

    def _on_track_page_built(self, page):
        """Wire a freshly materialized TrackTab into the window."""
        tt = page.tab
        tt.changed.connect(self._mark_dirty)
        tt.plot_type_changed.connect(self._on_track_pt_changed)
        tt.param_changed.connect(self._route_param_change)
        if tt not in self.track_tabs:
            self.track_tabs.append(tt)
        i = self.param_tabs.indexOf(page)
        if i >= 0:
            self.param_tabs.setTabText(i, page.tab_title())

    def _on_summary_built(self, page):
        """Wire the summary page once it is first shown."""
        st = page.widget
        st.param_changed.connect(self._route_param_change)
        st.files_changed.connect(self._on_files_changed)

    # ================================================================ events
    def _switch_lang(self, _i):
        I18N.set_lang(self.lang_combo.currentData())
        self.settings.setValue("language", I18N.lang())
        try:
            self._refresh_texts()
        except Exception as e:                      # never block the form rebuild
            self.log.appendPlainText("[i18n ERROR] %s" % e)
        self._rebuild_param_tabs()

    def _refresh_texts(self):
        self.act_new.setText(I18N.tr("new_project"))
        self.act_open.setText(I18N.tr("open_conf"))
        self.act_save.setText(I18N.tr("save_conf"))
        self.act_run.setText(I18N.tr("run"))
        self.act_png.setText(I18N.tr("export_png"))
        self.act_pdf.setText(I18N.tr("export_pdf"))
        self.act_help.setText(I18N.tr("help"))
        self.act_help.setToolTip(I18N.tr("help_tip"))
        self.act_about.setText(I18N.tr("about"))
        self.act_about.setToolTip(I18N.tr("about_tip"))
        self.files_panel.title.setText("<b>%s</b>" % I18N.tr("data_files"))
        self.files_panel.hint.setText(I18N.tr("file_hint"))
        self.files_panel.add_btn.setText(I18N.tr("add_file"))
        self.files_panel.del_btn.setText(I18N.tr("remove_file"))
        self.files_panel.preview_label.setText("<b>%s</b>" % I18N.tr("data_preview"))
        self.btn_refresh.setText(I18N.tr("refresh_preview"))
        self.btn_refresh.setToolTip(I18N.tr("refresh_tip"))
        self.btn_svg.setText(I18N.tr("export_svg"))
        self.btn_svg.setToolTip(I18N.tr("export_svg_tip"))
        self.btn_pdf.setText(I18N.tr("export_pdf"))
        self.params_dock.setWindowTitle(I18N.tr("right_dock_title"))
        self.log_dock.setWindowTitle(I18N.tr("log_dock_title"))
        self.files_dock.setWindowTitle(I18N.tr("data_files"))
        self.menu_file.setTitle(I18N.tr("menu_file"))
        self.menu_view.setTitle(I18N.tr("view_menu"))
        self.menu_help.setTitle(I18N.tr("help"))
        self.btn_file_menu.setText(I18N.tr("menu_file"))
        self.btn_view_menu.setText(I18N.tr("view_menu"))
        self.btn_help_menu.setText(I18N.tr("help"))
        self.btn_cite.setText(I18N.tr("cite"))
        self.act_new_btn.setText(I18N.tr("new_project"))
        self.act_open_btn.setText(I18N.tr("open_conf"))
        self.act_refresh.setText(I18N.tr("refresh_preview"))
        self.act_refresh.setToolTip(I18N.tr("refresh_tip"))
        self.add_btn.setText(I18N.tr("add_track"))
        self.add_btn.setToolTip(I18N.tr("add_track_tip"))
        self.rem_btn.setText(I18N.tr("remove_track"))
        self.act_svg.setText(I18N.tr("export_svg"))
        self.act_png.setText(I18N.tr("export_png"))
        self.act_pdf.setText(I18N.tr("export_pdf"))
        self.act_reset_layout.setText(I18N.tr("reset_layout"))
        self.act_reset_layout.setText(I18N.tr("reset_layout"))
        self.btn_file_menu.setToolTip(I18N.tr("menu_file"))
        self.btn_view_menu.setToolTip(I18N.tr("view_menu"))
        self.btn_help_menu.setToolTip(I18N.tr("help"))

    def _refresh_summary_if_current(self):
        # never build/refresh the summary while the tabs are being recreated:
        # removing tabs makes Qt switch the current page around, which used to
        # materialize the whole summary table mid-rebuild
        if getattr(self, "_rebuilding_tabs", False):
            return
        st = getattr(self, "summary_tab", None)
        if st is not None and self.param_tabs.currentWidget() is st:
            st.refresh()

    def _route_param_change(self, scope, key, value):
        """Fan a param edit out to every OTHER editor of the same key.

        self.sender() identifies which widget originated the change, so the
        originating form is skipped (no echo loops); everything else syncs."""
        origin = self.sender()
        holders = [("global", self.global_form), ("track", self.all_form)]
        holders += [(tt.index, tt) for tt in self.track_tabs]
        for fscope, holder in holders:
            if holder is origin or fscope != scope:
                continue
            if isinstance(holder, TrackTab) and key == "plot_type":
                holder.sync_plot_type(value)
            elif isinstance(holder, TrackTab) and key == "show_columns":
                holder.sync_show_columns(value)
            elif isinstance(holder, TrackTab):
                holder.sync_param(key, value)
            else:
                holder.sync_row(key, value)
        st = getattr(self, "summary_tab", None)
        if st is not None and st is not origin:
            st.sync_value(scope, key, value)
        # the summary tab has no any_changed signal; mark explicitly so its
        # edits also flag the preview stale / schedule the auto rerun
        self._mark_dirty()

    def _mark_dirty(self, *_a):
        self._dirty = True
        # preview is now older than the parameters: tell the user
        self._preview_stale = True
        if self.chk_auto.isChecked():
            self.preview.show_stale(I18N.tr("stale_running"))
        else:
            self.preview.show_stale(I18N.tr("stale_manual"))
        # auto refresh: debounced re-run 1.5 s after the LAST edit
        if self.chk_auto.isChecked():
            self._auto_timer.start()

    def _auto_toggled(self, on):
        self.settings.setValue("auto_refresh", "1" if on else "0")
        if not on:
            self._auto_timer.stop()

    def _flush_auto(self):
        if not self.chk_auto.isChecked() or not self._preview_stale:
            return
        self._run(auto=True)

    def _set_run_busy(self, busy):
        self.act_run.setEnabled(not busy)
        self.act_refresh.setEnabled(not busy)     # F5 must obey the busy state too
        self.btn_refresh.setEnabled(not busy)
        self.btn_svg.setEnabled(not busy)
        self.btn_pdf.setEnabled(not busy)

    def _on_files_changed(self, files):
        self.model.files = list(files)
        if getattr(self, "_in_run_normalize", False):
            return                              # run's own normalization, not an edit
        bar = getattr(self.global_form, "files_bar", None)
        if bar is not None:
            bar.set_files(files)                # no-op when already in sync
        st = getattr(self, "summary_tab", None)
        if st is not None:
            st.sync_files(files)
        self._mark_dirty()

    def _on_bar_files_changed(self, files):
        # global-tab FilesBar -> left panel -> files_changed -> model (single path)
        self.files_panel.set_files(files)

    def _on_file1_analyzed(self, _path, n_value_cols):
        self.statusBar().showMessage(
            "File1: %d value columns -> track_num=%d suggested" % (n_value_cols, n_value_cols)
            if I18N.lang() == "en" else
            "File1 检测到 %d 个数值列，建议 track_num=%d" % (n_value_cols, n_value_cols))

    def _on_track_pt_changed(self, idx, _pt):
        page = (getattr(self, "track_pages", None) or {}).get(idx)
        if page is None:
            return
        i = self.param_tabs.indexOf(page)
        if i >= 0:
            self.param_tabs.setTabText(i, page.tab_title())

    # ================================================================ tracks
    def _add_track(self):
        """Create (or just jump to) the track section chosen by number.

        Sections are sparse: adding track3 does not create track1/track2 —
        the engine renders untouched layers with trackALL/global defaults."""
        n = self.add_spin.value()
        existed = n in self.model.tracks
        self.model.tracks.setdefault(n, {})
        if not existed:
            # the user is now driving the track count: pin track_num
            self.model.track_num_explicit = True
        self.model.sync_track_num()
        self._rebuild_param_tabs()
        page = (getattr(self, "track_pages", None) or {}).get(n)
        if page is not None:
            self.param_tabs.setCurrentWidget(page)   # triggers materialization
        if not existed:
            self._mark_dirty()

    def _remove_track(self):
        self._remove_track_by_index(self.rem_spin.value())

    def _remove_track_by_index(self, target):
        if target not in self.model.tracks:
            return
        if len(self.model.tracks) == 1:
            ret = QMessageBox.question(self, I18N.tr("warn_title"),
                                       I18N.tr("remove_last_track"),
                                       QMessageBox.Yes | QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self.model.tracks.pop(target, None)
        self.model.track_num_explicit = True     # user-driven track count
        self.model.sync_track_num()
        self._rebuild_param_tabs()
        self._mark_dirty()

    # ================================================================ conf
    def _new_project(self):
        self.model = ConfModel()
        self.files_panel.set_files([""])
        self._rebuild_param_tabs()
        self.preview.reset()
        self._dirty = False
        self._update_title()

    def _open_conf(self):
        path, _ = QFileDialog.getOpenFileName(self, I18N.tr("open_conf_title"),
                                              str(self.out_dir), "Conf (*.conf *.cofi *.txt);;All (*)")
        if not path:
            return
        try:
            self.model = ConfModel().load(path)
        except OSError as e:
            QMessageBox.critical(self, I18N.tr("err_title"), str(e))
            return
        self.files_panel.set_files(self.model.files)
        self._rebuild_param_tabs()
        self._dirty = False
        # work where the conf lives: run outputs land next to it, named after it
        self.out_dir = Path(path).parent
        self.out_name = Path(path).stem
        self.files_panel.base_dir = self.out_dir
        self.settings.setValue("out_dir", str(self.out_dir))
        self.statusBar().showMessage(I18N.tr("conf_loaded", f=path))
        self._update_title()

    def _save_conf(self):
        path, _ = QFileDialog.getSaveFileName(self, I18N.tr("save_conf_title"),
                                              str(self.out_dir / "rectchr_gui.conf"),
                                              "Conf (*.conf);;All (*)")
        if not path:
            return
        self.model.save(path)
        # saved-here-means-outputs-here: follow the conf file's directory too
        self.out_dir = Path(path).parent
        self.out_name = Path(path).stem
        self.files_panel.base_dir = self.out_dir
        self.settings.setValue("out_dir", str(self.out_dir))
        self.statusBar().showMessage(I18N.tr("conf_written", f=path))
        self._update_title()

    def _validate(self, auto=False):
        def warn(msg):
            if not auto:
                QMessageBox.warning(self, I18N.tr("warn_title"), msg)
        f1 = self.model.files[0] if self.model.files else ""
        if not f1:
            warn(I18N.tr("no_file1"))
            return False
        # user-typed relative paths resolve against the working dir
        f1_abs = abspath_for(f1, self.out_dir)
        if not Path(f1_abs).is_file():
            warn(I18N.tr("file_missing", f=f1_abs))
            return False
        sections = [("trackALL", self.model.track_all)] + \
                   [("track%d" % n, t) for n, t in sorted(self.model.tracks.items())]
        for name, sec in sections:
            sc = sec.get("show_columns", "")
            if sc and not SHOW_COLUMNS_RE.match(sc):
                warn("%s\n%s.show_columns = %s" % (I18N.tr("invalid_columns"), name, sc))
                return False
        return True

    # ================================================================ run
    def _run(self, auto=False):
        """Slot wrapper: never let an exception die silently under pythonw."""
        self._last_run_auto = auto
        try:
            self._run_impl(auto=auto)
        except Exception as e:                    # noqa: BLE001
            self._show_error("run", e, auto=auto)
            self._set_run_busy(False)

    def _run_impl(self, auto=False):
        if self.runner.running():
            # queue a rerun with the latest parameters; no blocking modal
            self._auto_pending = True
            self._pending_manual = self._pending_manual or (not auto)
            if not auto:
                self.statusBar().showMessage(I18N.tr("already_running"))
            return
        if not self._validate(auto=auto):
            return
        if not find_perl():
            QMessageBox.critical(self, I18N.tr("err_title"), I18N.tr("perl_missing"))
            return
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.settings.setValue("out_dir", str(self.out_dir))
        # user-typed relative paths -> absolute against the working dir, so
        # the saved conf and the engine never depend on the process CWD.
        # (the internal set_files must NOT mark dirty: that would schedule
        #  another auto-run -> infinite loop)
        self._in_run_normalize = True
        try:
            self.model.absolutize_paths(self.out_dir)
            self.files_panel.set_files(self.model.files)
        finally:
            self._in_run_normalize = False
        conf_path = self.out_dir / "rectchr_gui.conf"
        self.model.save(conf_path)
        # drop the stale SVG: a failed run must never leave the old figure
        # masquerading as fresh output
        self._svg_mtime_before = None
        old_svg = self.out_dir / (self.out_name + ".svg")
        if old_svg.is_file():
            self._svg_mtime_before = old_svg.stat().st_mtime
            try:
                old_svg.unlink()
            except OSError:
                pass                              # keep mtime check instead
        self.log.appendPlainText("$ perl bin/RectChr -InConf %s -OutPut %s" % (conf_path, self.out_dir / self.out_name))
        self.statusBar().showMessage(I18N.tr("running"))
        self._set_run_busy(True)
        self.runner.run(conf_path, self.out_dir / self.out_name)

    def _on_runner_output(self, text):
        self.log.appendPlainText(text.rstrip())

    def _on_run_ok(self, svg_path):
        self._set_run_busy(False)
        try:
            svg = Path(svg_path)
            if not svg.is_file():
                self._on_run_fail("no-svg-file")
                return
            mtime = svg.stat().st_mtime
            if self._svg_mtime_before is not None and mtime <= self._svg_mtime_before:
                self._on_run_fail("stale-svg")
                return
            if not self.preview.load_svg(svg_path):
                # antivirus / indexer may briefly lock the fresh file: retry
                QTimer.singleShot(150, lambda: self._retry_load(svg_path, 1))
                return
            self.statusBar().showMessage(I18N.tr("done_ok", f=svg_path))
            self._preview_stale = False
            self.preview.hide_stale()
            if self._auto_pending:
                self._auto_pending = False
                pm = self._pending_manual
                self._pending_manual = False
                QTimer.singleShot(0, lambda a=not pm: self._run(auto=a))
        except Exception as e:                    # noqa: BLE001
            self._show_error("run-ok", e)

    def _retry_load(self, svg_path, attempt):
        if self.preview.load_svg(svg_path):
            self.statusBar().showMessage(I18N.tr("done_ok", f=svg_path))
            # the render succeeded on retry: clear the stale banner and honour
            # a rerun that was queued while the first load was failing
            self._preview_stale = False
            self.preview.hide_stale()
            if self._auto_pending:
                self._auto_pending = False
                pm = self._pending_manual
                self._pending_manual = False
                QTimer.singleShot(0, lambda a=not pm: self._run(auto=a))
        elif attempt < 3:
            QTimer.singleShot(200, lambda: self._retry_load(svg_path, attempt + 1))
        else:
            self._on_run_fail("svg-render-failed")

    def _on_run_fail(self, reason):
        self._set_run_busy(False)
        tail = self.log.toPlainText()[-600:]
        self.log.appendPlainText("\n[FAIL] %s" % reason)
        self.statusBar().showMessage(I18N.tr("done_fail"))
        self.log_dock.setVisible(True)
        self.preview.show_stale(I18N.tr("stale_fail_hint"), error=True)
        # a queued (pending) rerun must survive a failed run, otherwise the
        # user's latest parameters never get rendered
        if self._auto_pending:
            self._auto_pending = False
            pm = self._pending_manual
            self._pending_manual = False
            QTimer.singleShot(0, lambda a=not pm: self._run(auto=a))
        # an auto-refresh failure must not block the user with a modal dialog;
        # it is already reported in the log, the status bar and the banner
        if not self._last_run_auto:
            QMessageBox.warning(self, I18N.tr("run_fail_title"),
                                I18N.tr("run_fail_msg", reason=reason) + "\n\n" + tail)

    def _show_error(self, where, exc, auto=False):
        import traceback
        tb = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        self.log.appendPlainText("[%s ERROR] %s" % (where, tb))
        if auto:
            self.statusBar().showMessage("[%s] %s" % (where, tb))
            return
        try:
            QMessageBox.critical(self, I18N.tr("err_title"), "[%s] %s" % (where, tb))
        except Exception:                          # noqa: BLE001
            pass

    # ================================================================ export
    def _export_png(self):
        if not self.preview.has_svg():
            QMessageBox.information(self, I18N.tr("warn_title"), I18N.tr("no_preview"))
            return
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox
        dlg = QDialog(self)
        dlg.setWindowTitle(I18N.tr("export_png"))
        form = QFormLayout(dlg)
        dsize = self.preview._renderer.defaultSize()
        spin = QSpinBox()
        spin.setRange(64, 30000)
        spin.setValue(dsize.width() * 2)
        form.addRow("width(px)", spin)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        out, _ = QFileDialog.getSaveFileName(self, I18N.tr("export_png"),
                                             str(self.out_dir / (self.out_name + ".png")), "PNG (*.png)")
        if not out:
            return
        if self.preview.export_png(out, spin.value()):
            self.statusBar().showMessage(I18N.tr("export_done", f=out))

    def _export_svg(self):
        """Save the exact SVG the preview is showing (byte-identical copy)."""
        try:
            src_path = self.preview.source_path()
            if not src_path:
                QMessageBox.information(self, I18N.tr("warn_title"), I18N.tr("no_preview"))
                return
            default = str(self.out_dir / (self.out_name + ".svg"))
            target, _ = QFileDialog.getSaveFileName(self, I18N.tr("export_svg"),
                                                    default, "SVG (*.svg);;All (*)")
            if not target:
                return
            import shutil
            if Path(target).resolve() == Path(src_path).resolve():
                self.statusBar().showMessage(I18N.tr("export_done", f=target))
                return
            shutil.copyfile(src_path, target)
            self.statusBar().showMessage(I18N.tr("export_done", f=target))
        except Exception as e:                    # noqa: BLE001
            self._show_error("export-svg", e)

    def _export_pdf(self):
        if not self.preview.has_svg():
            QMessageBox.information(self, I18N.tr("warn_title"), I18N.tr("no_preview"))
            return
        out, _ = QFileDialog.getSaveFileName(self, I18N.tr("export_pdf"),
                                             str(self.out_dir / (self.out_name + ".pdf")), "PDF (*.pdf)")
        if not out:
            return
        if self.preview.export_pdf(out):
            self.statusBar().showMessage(I18N.tr("export_done", f=out))

    # ================================================================ misc
    def _update_title(self, conf_stem=None):
        name = conf_stem or self.out_name
        self.setWindowTitle("%s — %s (%s)" % (I18N.tr("app_title"), name, self.out_dir))

    def closeEvent(self, ev):
        self.settings.setValue("dock_state", self.saveState())
        # detach first: killing the process makes it emit finished(), which
        # would re-enter _on_run_fail (modal dialog) while the window is closing
        if self.runner.running():
            try:
                self.runner.finished_ok.disconnect()
                self.runner.failed.disconnect()
                self.runner.output.disconnect()
            except (RuntimeError, TypeError):
                pass
        self.runner.stop()
        super().closeEvent(ev)
