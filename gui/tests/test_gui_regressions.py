#!/usr/bin/env python3
"""Repeatable GUI regression tests (offscreen, no network, no user settings).

Run:  python3 gui/tests/test_gui_regressions.py
Also collectable by pytest (test_all). Covers the recent GUI rounds:
logo integration, plot_type icons, parameter tab bar styling, track close
buttons, Track ID row, lazy track pages and the packaging metadata.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings as _QS, Qt, QTimer  # noqa: E402
from PySide6.QtTest import QTest                   # noqa: E402
from PySide6.QtGui import QPalette                               # noqa: E402
from PySide6.QtWidgets import (QApplication, QLabel, QStyle, QStyleOptionTab,  # noqa: E402
                               QTabBar, QToolButton, QWidget)

failures = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + str(extra) if extra != "" else ""), flush=True)
    if not cond:
        failures.append(name)


def _visible_px(img, base):
    n = 0
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 30 and (abs(c.red() - base.red()) + abs(c.green() - base.green())
                                   + abs(c.blue() - base.blue())) > 60:
                n += 1
    return n


def _run_all():
    from PySide6.QtWidgets import QApplication, QMessageBox
    # one QApplication for the whole run, BEFORE any widget/pixmap work
    app = QApplication.instance() or QApplication(sys.argv)
    # keep tests off the user's real settings + modal dialogs captured
    _QS.setPath(_QS.IniFormat, _QS.UserScope, tempfile.mkdtemp(prefix="rectchr-test-"))
    _QS.setDefaultFormat(_QS.IniFormat)

    # -------------------------------------------------- logo integration
    from gui.ui.logo import LOGO_SVG, application_icon, logo_pixmap
    check("logo: embedded source identical to doc/RectChr_logo.svg",
          LOGO_SVG.strip() == (ROOT / "doc" / "RectChr_logo.svg").read_text(encoding="utf-8").strip())
    icon = application_icon()
    for size in (16, 32, 64, 256):
        img = icon.pixmap(size, size).toImage()
        check("logo: square icon renders at %dpx" % size,
              img.width() == size and _visible_px(img, img.pixelColor(0, 0)) > size * size // 4)
    full = logo_pixmap()
    img = full.toImage()
    check("logo: about pixmap is 2x landscape on paper",
          (full.width(), full.height()) == (538, 172) and full.devicePixelRatio() == 2
          and any(img.pixelColor(x, y).name() != "#ffffff"
                  for y in range(40, 140) for x in range(140, 400)))

    # -------------------------------------------------- plot_type icons
    from gui.core.schema import Schema
    from gui.ui.plot_icons import PLOT_ICON_NAMES, plot_type_icon
    from gui.theme import dark_palette, light_palette, stylesheet
    live = [pt["name"] for pt in Schema.plot_types() if not pt.get("legacy")]
    check("icons: every live plot type has artwork", set(live) <= PLOT_ICON_NAMES(),
          str(sorted(set(live) - PLOT_ICON_NAMES())))
    for dark, pal in ((False, light_palette()), (True, dark_palette())):
        app.setPalette(pal)
        bad = [n for n in live if _visible_px(plot_type_icon(n).pixmap(44, 44).toImage(),
                                              app.palette().color(QPalette.Base)) < 50]
        check("icons: visible on %s popup" % ("dark" if dark else "light"), not bad, str(bad))
    app.setPalette(light_palette())
    check("icons: cache honours (name, scheme, size)",
          plot_type_icon("ridgeline", 16) is not plot_type_icon("ridgeline", 32)
          and plot_type_icon("ridgeline") is plot_type_icon("ridgeline"))
    check("icons: unknown type has no icon",
          plot_type_icon("").isNull() and plot_type_icon("no_such_type").isNull())
    check("schema: plot_type aliases resolve to canonical",
          [Schema.resolve_plot_type(v) for v in ("lines", "histogram", "scatter", "points",
                                                 "shapes", "Shape", "LinkSelf", "pairwiselink",
                                                 "pairwiselinkV2", "histogramAnimated", "Link")]
          == ["line", "hist", "point", "point", "shape", "shape", "LinkS",
              "PairWiseLink", "PairWiseLinkV2", "histAnimated", "link"])
    check("schema: unknown/empty plot_type pass through",
          Schema.resolve_plot_type("no_such") == "no_such" and Schema.resolve_plot_type("") == "")

    # -------------------------------------------------- tab bar + tracks
    from gui.core.conf_io import ConfModel
    from gui.ui.main_window import MainWindow, ParameterTabBar
    win = MainWindow()
    check("window icon set", not win.windowIcon().isNull())
    win.model = ConfModel()
    win.model.tracks = {1: {}, 3: {}, 7: {}}
    win._rebuild_param_tabs()
    bar = win.param_tabs.tabBar()
    check("tab bar: ParameterTabBar installed + scroll buttons",
          isinstance(bar, ParameterTabBar) and win.param_tabs.usesScrollButtons())
    close_btn = lambda n: bar.tabButton(win.param_tabs.indexOf(win.track_pages[n]), QTabBar.RightSide)
    check("close buttons: only track tabs carry one",
          all(bar.tabButton(win.param_tabs.indexOf(p), QTabBar.RightSide) is None
              for p in (win.global_form, win.all_form, win.summary_tab))
          and all(close_btn(n) is not None for n in win.model.tracks))
    win.show()
    app.processEvents()
    for dark, pal, bg, border in ((False, light_palette(), "#dcebe9", "#a7c5c0"),
                                  (True, dark_palette(), "#203d3a", "#42645f")):
        app.setPalette(pal)
        app.setStyleSheet(stylesheet(dark))
        app.processEvents()
        bar.repaint()
        img = bar.grab().toImage()
        colors = {img.pixelColor(x, y).name() for y in range(img.height()) for x in range(img.width())}
        check("tab bar: card bg/border on %s" % ("dark" if dark else "light"),
              {bg, border} <= colors, str({bg, border} - colors))
        i = win.param_tabs.indexOf(win.track_pages[3])
        b, r = close_btn(3), bar.tabRect(i)
        opt = QStyleOptionTab()
        bar.initStyleOption(opt, i)
        text = bar.style().subElementRect(QStyle.SE_TabBarTabText, opt, bar)
        check("close buttons: top-right corner on %s, clear of the text"
              % ("dark" if dark else "light"),
              b.y() == r.y() + 5 and r.right() - b.geometry().right() == 8
              and b.width() == 16 and text.right() < b.x())
    app.setPalette(light_palette())
    app.setStyleSheet(stylesheet(False))
    QTest.mouseClick(close_btn(3), Qt.LeftButton)
    check("close buttons: mouse click removes the exact track",
          set(win.model.tracks) == {1, 7} and win._dirty)
    win._remove_track_by_index(99)
    check("close buttons: stale id removes nothing", set(win.model.tracks) == {1, 7})
    orig_question = QMessageBox.question
    QMessageBox.question = lambda *a, **k: QMessageBox.No
    close_btn(7).click()
    check("close buttons: last track can be cancelled",
          set(win.model.tracks) == {1})
    win._dirty = False
    QMessageBox.question = lambda *a, **k: QMessageBox.Yes
    close_btn(1).click()
    check("close buttons: last track confirm removes it", not win.model.tracks)
    QMessageBox.question = orig_question

    # Track ID labels + removal strictly by the entered number
    win.model.tracks = {1: {}, 3: {}, 7: {}}
    win._rebuild_param_tabs()
    labels = [x for x in win.addrem_row.findChildren(QLabel) if x.text() == "Track ID"]
    check("Track ID: label on both groups, bound to the spins",
          len(labels) == 2 and {x.buddy() for x in labels} == {win.add_spin, win.rem_spin})
    win.param_tabs.setCurrentWidget(win.track_pages[1])
    win.rem_spin.setValue(3)
    win.rem_btn.click()
    check("Track ID: removal follows the entered number, not the current tab",
          set(win.model.tracks) == {1, 7})
    win._dirty = False
    win.rem_spin.setValue(99)
    win.rem_btn.click()
    check("Track ID: missing number removes nothing",
          set(win.model.tracks) == {1, 7} and not win._dirty)

    # lazy track pages stay lazy on a big conf
    win.model = ConfModel().load(ROOT / "Scene_Usage/example04_RILBinMap/in1.conf")
    win._rebuild_param_tabs()
    check("lazy: 79-track conf loads without eager pages",
          len(win.track_pages) == 79 and not win.track_tabs
          and len(win.findChildren(QWidget)) < 1000,
          "%d widgets" % len(win.findChildren(QWidget)))
    win.param_tabs.setCurrentWidget(win.track_pages[40])
    app.processEvents()
    check("lazy: opening track40 materializes only it",
          len(win.track_tabs) == 1 and win.track_tabs[0].index == 40)
    check("lazy: close buttons exist for every track page",
          all(bar.tabButton(win.param_tabs.indexOf(p), QTabBar.RightSide) is not None
              for p in win.track_pages.values()))

    # -------------------------------------------------- plot_type alias spellings
    # a conf may use legacy engine spellings (lines/histogram/...); they must
    # normalize to the canonical name everywhere (model, combo icon, tab
    # title, form filter, saved conf)
    win.model = ConfModel().load(ROOT / "Scene_Usage/example07_Genetics/in1.conf")
    pts_loaded = [win.model.get_param(i, "plot_type") for i in (1, 2, 3, 4)]
    check("plot alias: conf values canonical on load",
          pts_loaded == ["line", "hist", "hist", "heatmap"], str(pts_loaded))
    win._rebuild_param_tabs()
    win.param_tabs.setCurrentWidget(win.track_pages[1])
    app.processEvents()
    combo = win.track_tabs[0].pt_combo
    check("plot alias: no bare lines item, current is line",
          combo.findData("lines") < 0 and combo.currentData() == "line")
    check("plot alias: every combo item carries artwork",
          all(not combo.itemIcon(i).isNull() for i in range(combo.count())))
    check("plot alias: tab title canonical",
          win.track_pages[1].tab_title().endswith("· line"))
    from gui.ui.param_form import ParamForm
    from gui.ui.track_tab import TrackTab
    check("plot alias: filter keeps line params, drops the alias",
          ParamForm._param_allowed(Schema.param("cutoff_y"), "line", True)
          and not ParamForm._param_allowed(Schema.param("cutoff_y"), "lines", True))
    m2 = ConfModel()
    m2.tracks = {1: {"plot_type": "histogram"}}
    tab2 = TrackTab(m2, 1)
    check("plot alias: TrackTab normalizes raw model values",
          tab2.pt_combo.currentData() == "hist" and tab2.pt_combo.findData("histogram") < 0)
    tab2.deleteLater()
    m3 = ConfModel()
    m3.tracks = {1: {"plot_type": "weird"}}
    tab3 = TrackTab(m3, 1)
    check("plot alias: unknown value keeps the bare fallback item",
          tab3.pt_combo.currentData() == "weird"
          and tab3.pt_combo.itemIcon(tab3.pt_combo.currentIndex()).isNull())
    tab3.deleteLater()
    saved = win.model.to_conf_text()
    t1 = saved.split("SetParaFor=track1\n", 1)[1].split("\nSetParaFor=", 1)[0]
    check("plot alias: save writes canonical spelling",
          "plot_type=line\n" in t1 and "plot_type=lines" not in saved)

    from unittest.mock import patch
    from PySide6.QtCore import QUrl
    from PySide6.QtWidgets import QPlainTextEdit, QPushButton, QToolBar, QDialogButtonBox
    from gui.i18n import I18N
    toolbar = win.btn_cite.parentWidget()
    widgets = [toolbar.widgetForAction(action) for action in toolbar.actions()]
    check("citation: immediately before Help",
          isinstance(toolbar, QToolBar) and widgets.index(win.btn_cite) + 1
          == widgets.index(win.btn_help_menu))
    for lang, button_text in (("zh", "引用"), ("en", "Cite")):
        win.lang_combo.setCurrentIndex(0 if lang == "zh" else 1)
        check("citation: toolbar language " + lang, win.btn_cite.text() == button_text)
        dlg = win._build_citation_dialog()
        try:
            text = dlg.findChild(QPlainTextEdit, "citationText")
            check("citation: text and read-only " + lang,
                  text.isReadOnly() and text.toPlainText() ==
                  "RectChr — GitHub repository. https://github.com/hewm2008/RectChr"
                  and any(label.text() == I18N.tr("cite_intro") and label.wordWrap()
                          for label in dlg.findChildren(QLabel)))
            dlg.findChild(QPushButton, "copyCitationButton").click()
            check("citation: clipboard " + lang, app.clipboard().text() == text.toPlainText())
            with patch.object(win, "_open_url") as opened:
                dlg.findChild(QPushButton, "openCitationGithubButton").click()
                check("citation: URL action " + lang, opened.call_args.args ==
                      (QUrl("https://github.com/hewm2008/RectChr"),))
            dlg.show()
            dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.Close).click()
            check("citation: close " + lang, not dlg.isVisible())
        finally:
            dlg.close()
            dlg.deleteLater()
    win.lang_combo.setCurrentIndex(0)
    win._dirty = False
    win.close()
    win.deleteLater()

    # -------------------------------------------------- packaging metadata
    spec = (ROOT / "gui" / "tools" / "RectChrGUI.spec").read_text(encoding="utf-8")
    check("packaging: spec bundles params_schema.json",
          "params_schema.json" in spec and "gui/resources" in spec)
    import runpy
    import struct
    from types import SimpleNamespace
    from PySide6.QtGui import QImage
    from gui import GUI_VERSION
    for platform in ("linux", "win32", "darwin"):
        calls = {}
        def capture(name):
            def build(*args, **kwargs):
                calls[name] = kwargs
                return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
            return build
        namespace = {name: capture(name) for name in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")}
        namespace["SPECPATH"] = str(ROOT / "gui/tools")
        with patch.object(sys, "platform", platform):
            exec(compile(spec, "RectChrGUI.spec", "exec"), namespace)
        data = calls["Analysis"]["datas"]
        check("packaging: real data inputs " + platform,
              all(Path(src).exists() for src, dest in data)
              and any(dest == "gui/resources" for src, dest in data))
        if platform == "darwin":
            bundle = calls["BUNDLE"]
            check("macOS: app identity and icon",
                  bundle["name"] == "RectChr.app" and Path(bundle["icon"]).is_file()
                  and bundle["info_plist"]["CFBundleDisplayName"] == "RectChr"
                  and bundle["info_plist"]["CFBundleName"] == "RectChr"
                  and bundle["info_plist"]["CFBundleVersion"] == GUI_VERSION.lstrip("v"))
            check("macOS: engine, palettes and manuals bundled",
                  {"bin", "ColorsBrewer", "gui/doc"} <= {dest for src, dest in data})
        else:
            check("packaging: no app bundle on " + platform, "BUNDLE" not in calls)
    with patch.object(sys, "platform", "darwin"), patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", "/Applications/RectChr.app/Contents/MacOS/RectChrGUI"):
        runner = runpy.run_path(str(ROOT / "gui/core/runner.py"))
    check("macOS: frozen engine resource path",
          runner["ENGINE"] == Path("/Applications/RectChr.app/Contents/Resources/bin/RectChr"))
    data = (ROOT / "gui/resources/RectChr.icns").read_bytes()
    check("macOS: ICNS header", data[:4] == b"icns" and struct.unpack(">I", data[4:8])[0] == len(data))
    offset = 8
    sizes = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset + 4:offset + 8])[0]
        assert length > 8 and offset + length <= len(data)
        image = QImage.fromData(data[offset + 8:offset + length], "PNG")
        assert not image.isNull() and image.width() == image.height()
        sizes.append(image.width())
        offset += length
    check("macOS: seven decoded icon sizes", sizes == [16, 32, 64, 128, 256, 512, 1024])
    import ast
    check("packaging: build_windows.py parses",
          ast.parse((ROOT / "gui" / "tools" / "build_windows.py").read_text(encoding="utf-8")) is not None)


def test_all():
    _run_all()
    if failures:
        raise AssertionError("GUI regression failures: %s" % failures)


if __name__ == "__main__":
    import faulthandler
    faulthandler.dump_traceback_later(300, exit=True)   # hard timeout w/ dump
    _run_all()
    print("", flush=True)
    if failures:
        print("GUI REGRESSIONS FAILED:", failures, flush=True)
        sys.exit(1)
    print("ALL GUI REGRESSION TESTS PASSED", flush=True)
