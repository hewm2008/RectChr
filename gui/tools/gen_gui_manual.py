#!/usr/bin/env python3
"""Generate the RectChr GUI usage manuals (Simplified Chinese / English) as PDF.

Content is distilled from the original RectChr manuals (doc/) and the GUI's
own parameter schema (gui/resources/params_schema.json), so the parameter
tables always match the engine.  Rendering is pure Qt (QTextDocument +
QPrinter) — no pandoc/LaTeX needed, works headless.

Usage:
  python3 gui/tools/gen_gui_manual.py [dest_dir]      # default: gui/doc
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

GUI_DIR = Path(__file__).resolve().parents[1]
ROOT = GUI_DIR.parent
SCHEMA = ROOT / "gui" / "resources" / "params_schema.json"

NAMES = {"zh": "RectChr_GUI_manual_Chinese.pdf",
         "en": "RectChr_GUI_manual_English.pdf"}

_CSS = """
h1 { font-size: 19pt; }
h2 { font-size: 13.5pt; color: #0E9488; margin-top: 16px; }
h3 { font-size: 11.5pt; color: #333333; margin-top: 12px; }
body, p, li, td, th { font-size: 10pt; }
th { background-color: #e2f0ee; }
td, th { border: 1px solid #b9c6d2; padding: 3px 6px; }
table { border-collapse: collapse; width: 100%; }
.muted { color: #777777; }
code { font-family: Consolas, monospace; background-color: #f0f3f6; }
"""


def _load_schema_params():
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return data["params"], data.get("categories", {})


def _param_table(params, lang, category, exclude=()):
    """HTML table of one parameter category from the schema."""
    rows = []
    for p in params:
        if p.get("category") != category or p["name"] in exclude:
            continue
        label = p.get("label_zh" if lang == "zh" else "label_en") or p["name"]
        desc = p.get("desc_zh" if lang == "zh" else "desc_en") or ""
        default = p.get("default")
        default = str(default) if default not in (None, "") else "—"
        rng = ""
        if p.get("min") is not None:
            rng = "≥ %s" % p["min"]
        if p.get("max") is not None:
            rng = (rng + " " if rng else "") + "≤ %s" % p["max"]
        rows.append("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                    % (p["name"], label, default, rng, desc))
    if not rows:
        return ""
    head = ("<tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>"
            % (("参数", "说明", "默认值", "范围", "备注") if lang == "zh"
               else ("Parameter", "Description", "Default", "Range", "Notes")))
    return "<table>%s%s</table>" % (head, "".join(rows))


_PLOT_TYPES = [
    ("heatmap", "热图", "Heatmap",
     "区域统计值映射为颜色格子，基因组密度/Fst/深度等最常用类型",
     "colormap_low_color / colormap_mid_color / colormap_high_color / colormap_nlevels / Ymax / Ymin",
     "plot_type = heatmap"),
    ("highlights", "高亮", "Highlights",
     "区间背景着色，常用于标记选择区域、QTL 区间、着丝粒等",
     "background_color / track_bg_height_ratio",
     "plot_type = highlights"),
    ("point", "点图", "Scatter / point",
     "散点图，GWAS 曼哈顿图的常用画法",
     "cutoff_value / cutoff_color / log_p / track_point_size",
     "plot_type = point\ncutoff_y = 5"),
    ("line", "线图", "Line",
     "折线/曲线，展示连续值走势",
     "track_height / Ymax / Ymin",
     "plot_type = line"),
    ("hist", "柱状图", "Histogram",
     "柱状图；show_columns 给两列时可画上下对称双柱",
     "show_columns / track_height / yaxis_tick_show",
     "plot_type = hist\nshow_columns = File1:6,7"),
    ("text", "文本", "Text",
     "在对应区域显示文字（基因名/标记名等）",
     "track_text_size / track_text_angle / track_text_anchor",
     "plot_type = text\nshow_columns = File2:5"),
    ("shape", "形状", "Shape",
     "按区域绘制几何形状（圆形/方形/三角等 0-13 种）",
     "track_geom_shape / track_geom_shape_size",
     "plot_type = shape\ntrack_geom_shape = 3"),
    ("ridgeline", "山脊线", "Ridgeline",
     "山脊图，展示 QTL/分布的堆叠形态",
     "track_height / ridgeline 参数族",
     "plot_type = ridgeline"),
    ("PairWiseLink", "彩虹链接", "Pairwise link",
     "两个基因组/区间之间的彩虹连接线（共线性/变异）",
     "link_direction / link_linestyle / link_uniform_height",
     "plot_type = PairWiseLink"),
    ("LinkS", "自连接", "Self link",
     "染色体自身区域之间的连接",
     "link_direction / link_linestyle",
     "plot_type = LinkS"),
    ("heatmapAnimated", "动态热图", "Animated heatmap",
     "动态 SVG 热图，导出后用浏览器打开可播放动画",
     "colormap_* / Ymax / Ymin",
     "plot_type = heatmapAnimated"),
    ("histAnimated", "动态柱状图", "Animated histogram",
     "动态 SVG 柱状图，浏览器打开可播放动画",
     "track_height / show_columns",
     "plot_type = histAnimated"),
]


def _build_blocks(lang, gui_ver, engine_ver, params):
    """Content model: list of (kind, payload) blocks consumed by both the
    PDF (HTML) and DOCX renderers.  kinds: h1, h2, h3, p, note, ul, table, code."""
    zh = lang == "zh"
    B = []

    def h1(t): B.append(("h1", t))
    def h2(t): B.append(("h2", t))
    def h3(t): B.append(("h3", t))
    def p(t): B.append(("p", t))
    def note(t): B.append(("note", t))
    def code(t): B.append(("code", t))
    def ul(items): B.append(("ul", items))
    def table(head, rows): B.append(("table", (head, rows)))

    h1("RectChr GUI 使用手册" if zh else "RectChr GUI Manual")
    p("版本 %s · 引擎 RectChr %s · hewm2008" % (gui_ver, engine_ver))
    p("RectChr GUI 是 RectChr（类 circos 的多层级染色体可视化工具）的跨平台图形界面，"
      "同一份程序可在 Windows / Linux / macOS 运行。界面负责配置与预览，出图由 Perl 引擎完成。"
      if zh else
      "A cross-platform desktop interface for RectChr (a circos-like, multi-level"
      " chromosome visualization tool). The GUI writes the configuration; the Perl engine renders.")

    h2("2. 界面导览（三栏工作台）" if zh else "2. Interface (three-column workbench)")
    p("顶部工具栏与【文件 / 视图 / 帮助】菜单；全部功能均有菜单归属。"
      if zh else
      "Toolbar and the File/View/Help menu buttons; every function has a menu entry.")
    table(["区域", "内容"] if zh else ["Area", "Content"],
          [("左栏", "数据文件 File1..FileN（支持 .gz、双入口同步、前 20 行预览）"),
           ("中央", "预览画布（白纸）+ 刷新/自动刷新/导出 SVG/PDF + 过期提示浮层"),
           ("右栏", "参数面板：全局参数 / trackALL / Track N / 参数总览，顶部为 Track 管理卡"),
           ("底部", "运行日志（引擎输出与错误信息）")]
          if zh else
          [("Left", "Data files File1..FileN (.gz, dual-entry sync, 20-row preview)"),
           ("Center", "Preview canvas (white paper) + refresh/auto-refresh/export + stale hint"),
           ("Right", "Parameters: Global / trackALL / Track N / Parameters overview, Track manager card on top"),
           ("Bottom", "Run log (engine output and errors)")])
    p("菜单说明：【文件】新建 / 打开配置 / 保存配置 / 导出 SVG·PNG·PDF；"
      "【视图】三个面板的显隐开关 + 重置布局；【帮助】使用手册（中/英）+ 关于。"
      if zh else
      "Menus: File = New / Open / Save / Export SVG-PNG-PDF; View = show-hide the three"
      " panels + Reset layout; Help = manuals (zh/en) + About.")

    h2("3. 快速开始（五步出图）" if zh else "3. Quick start (five steps)")
    if zh:
        ul(["添加数据：左栏【添加文件】，格式 Chr Start End Value1 …，支持 .gz",
            "最小配置：只给 File1 即可出图（plot_type 默认 heatmap）",
            "运行：点【运行绘图】；或开启自动刷新，改完参数自动重跑",
            "调参：在右侧参数页签修改，画布左下角出现\"参数已修改\"提示，自动重跑后消失",
            "导出：预览条【导出SVG】【导出PDF】或菜单【导出PNG…】"])
    else:
        ul(["Add data: left panel Add file; format Chr Start End Value1 …, .gz supported",
            "Minimal config: File1 alone is enough (default plot_type = heatmap)",
            "Run: press Run; or enable Auto refresh and just edit parameters",
            "Tune: edit in the right-side tabs; a stale hint shows while re-rendering",
            "Export: Export SVG / Export PDF on the preview strip, or Export PNG in the File menu"])
    h3("最小配置示例（热图）" if zh else "Minimal heatmap example")
    code("SetParaFor=global\nFile1 = ./data.gz\n—— 只需一个数据文件，其余全部使用默认值。"
         if zh else "SetParaFor=global\nFile1 = ./data.gz\n—— one data file, everything else defaults.")

    h2("4. 数据格式与路径规则" if zh else "4. Data format & paths")
    p("输入为制表符/空格分隔的文本（支持 .gz）：Chr Start End Value1 Value2 …"
      " 前三列为区域（染色体/起/止），其后每列为一层 Track 的统计值；NA 表示该区域不绘制。"
      " show_columns 指定画哪列（如 File1:4,7）——不设置时第 N 层默认取 File1 的第 N+3 列。"
      " conf 里的相对路径以 conf 所在目录为基准解析；打开旧版 conf 时自动兼容老参数名"
      "（cutoff_value→cutoff_y、crBegin→colormap_low_color 等）。"
      if zh else
      "Tab/space separated text (.gz supported): Chr Start End Value1 …. The first three"
      " columns locate the region; each extra column feeds one track. NA skips a region."
      " show_columns picks columns (e.g. File1:4,7); by default layer N reads File1 column N+3."
      " Relative paths resolve against the conf directory; legacy parameter names are mapped"
      " automatically.")

    h2("5. 参数详解（按分类）" if zh else "5. Parameter reference (by category)")
    p("以下表格由 GUI 参数 schema 自动生成，默认值与取值范围即引擎真实值；"
      "在界面中每个参数行也会以灰色提示默认值。"
      if zh else
      "Generated from the GUI schema; defaults and ranges are the engine's real values.")
    cat_names = {
        "canvas": ("画布", "Canvas"), "chr": ("染色体", "Chromosomes"),
        "title": ("标题", "Title"), "axis": ("坐标轴", "Axes"),
        "track": ("轨道通用", "Track general"), "data": ("数据处理", "Data processing"),
        "label": ("轨道名称", "Track label"), "geometry": ("几何属性", "Geometry"),
        "color_legend": ("颜色与图例", "Colors & legend"), "svg": ("样式 (SVG)", "Style (SVG)"),
    }
    for cat in ["canvas", "chr", "title", "axis", "track", "data", "label",
                "geometry", "color_legend", "svg"]:
        zh_n, en_n = cat_names.get(cat, (cat, cat))
        rows = []
        for prm in params:
            if prm.get("category") != cat or prm["name"] in ("File1", "FileX", "plot_type"):
                continue
            label = prm.get("label_zh" if zh else "label_en") or prm["name"]
            desc = prm.get("desc_zh" if zh else "desc_en") or ""
            default = prm.get("default")
            default = str(default) if default not in (None, "") else "—"
            rng = ""
            if prm.get("min") is not None:
                rng = "≥ %s" % prm["min"]
            if prm.get("max") is not None:
                rng = (rng + " " if rng else "") + "≤ %s" % prm["max"]
            rows.append((prm["name"], label, default, rng, desc))
        if rows:
            table(["参数", "说明", "默认值", "范围", "备注"] if zh else
                  ["Parameter", "Description", "Default", "Range", "Notes"], rows)

    h2("6. 画图类型（plot_type）" if zh else "6. Plot types")
    p("共 13 种画法；在 Track 页签的 plot_type 下拉中切换，表单会联动显示对应参数。"
      if zh else
      "13 plot types; switch in the Track tab's plot_type combo — the form follows.")
    _PT = [
        ("heatmap", "热图", "Heatmap", "区域统计值映射为颜色格子，基因组密度/Fst/深度等最常用类型",
         "colormap_low_color / colormap_mid_color / colormap_high_color / colormap_nlevels / Ymax / Ymin"),
        ("highlights", "高亮", "Highlights", "区间背景着色，常用于标记选择区域、QTL 区间、着丝粒等",
         "background_color / track_bg_height_ratio"),
        ("point", "点图", "Scatter / point", "散点图，GWAS 曼哈顿图的常用画法",
         "cutoff_y / cutoff_color / log_p / track_point_size"),
        ("line", "线图", "Line", "折线/曲线，展示连续值走势", "track_height / Ymax / Ymin"),
        ("hist", "柱状图", "Histogram", "柱状图；show_columns 给两列时可画上下对称双柱",
         "show_columns / track_height / yaxis_tick_show"),
        ("text", "文本", "Text", "在对应区域显示文字（基因名/标记名等）",
         "track_text_size / track_text_angle / track_text_anchor"),
        ("shape", "形状", "Shape", "按区域绘制几何形状（圆形/方形/三角等 0-13 种）",
         "track_geom_shape / track_geom_shape_size"),
        ("ridgeline", "山脊线", "Ridgeline", "山脊图，展示 QTL/分布的堆叠形态", "track_height"),
        ("PairWiseLink", "彩虹链接", "Pairwise link", "两个基因组/区间之间的彩虹连接线（共线性/变异）",
         "link_direction / link_linestyle / link_uniform_height"),
        ("LinkS", "自连接", "Self link", "染色体自身区域之间的连接", "link_direction / link_linestyle"),
        ("heatmapAnimated", "动态热图", "Animated heatmap", "动态 SVG 热图，导出后用浏览器打开可播放动画",
         "colormap_* / Ymax / Ymin"),
        ("histAnimated", "动态柱状图", "Animated histogram", "动态 SVG 柱状图，浏览器打开可播放动画",
         "track_height / show_columns"),
    ]
    for name, zh_n, en_n, desc, keys in _PT:
        h3("%s（%s）" % (zh_n, name) if zh else "%s (%s)" % (en_n, name))
        p(desc)
        p(("关键参数：" if zh else "Key params: ") + keys.replace(" / ", "、"))
        code("plot_type = %s" % name)

    h2("7. 常见问题" if zh else "7. FAQ")
    if zh:
        ul(["提示未找到 Perl（Windows）：将便携版 Strawberry Perl 解压到 gui_runtime/perl/，"
            "或安装 Perl 并保持 PATH 可用。",
            "预览没有变化：画布左下角提示\"参数已修改\"时会自动重跑（自动刷新开启时）；"
            "关闭自动刷新后需点【🔄 刷新预览】/ F5。",
            "自动刷新失败：画布左下角红字提示，详细错误见运行日志面板。",
            "动态图：heatmapAnimated / histAnimated 在预览中为静态帧，用浏览器打开导出的 SVG 可看动画。",
            "面板 X 掉了：【视图】菜单重新勾选即可恢复；【重置布局】一键归位。",
            "打开旧 conf：老参数名自动映射（cutoff_value→cutoff_y 等）。"])
    else:
        ul(["Perl not found (Windows): unzip portable Strawberry Perl into gui_runtime/perl/, "
            "or keep Perl on PATH.",
            "Preview not changing: with Auto refresh ON the canvas re-renders automatically; "
            "otherwise press Refresh preview / F5.",
            "Auto refresh failed: red hint on the canvas; details in the Run log.",
            "Animations: animated plots show a static frame in the preview — open the "
            "exported SVG in a browser.",
            "Closed a panel: re-enable it in the View menu; Reset layout restores defaults.",
            "Legacy confs: old parameter names map automatically."])

    h2("8. 联系方式" if zh else "8. Contact")
    ul(["邮箱：hewm2008@gmail.com / hewm2008@qq.com" if zh else
        "Email: hewm2008@gmail.com / hewm2008@qq.com",
        "主页：https://github.com/hewm2008/RectChr" if zh else
        "Home: https://github.com/hewm2008/RectChr",
        "QQ 交流群：125293663" if zh else "QQ Group: 125293663"])
    return B


def _esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _blocks_to_html(B):
    out = []
    for kind, payload in B:
        if kind == "h1":
            out.append("<h1>%s</h1>" % _esc(payload))
        elif kind == "h2":
            out.append("<h2>%s</h2>" % _esc(payload))
        elif kind == "h3":
            out.append("<h3>%s</h3>" % _esc(payload))
        elif kind in ("p", "note"):
            out.append("<p>%s</p>" % _esc(payload))
        elif kind == "code":
            out.append("<code>%s</code>" % _esc(payload).replace("\n", "<br>"))
        elif kind == "ul":
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _esc(i) for i in payload))
        elif kind == "table":
            head, rows = payload
            out.append("<table><tr>%s</tr>%s</table>" % (
                "".join("<th>%s</th>" % _esc(h) for h in head),
                "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % _esc(c) for c in r)
                        for r in rows)))
    return "".join(out)


def _blocks_to_docx(B, path):
    import docx
    from docx.shared import Pt, RGBColor
    d = docx.Document()
    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    for kind, payload in B:
        if kind == "h1":
            d.add_heading(payload, level=0)
        elif kind == "h2":
            h = d.add_heading("", level=1)
            r = h.add_run(payload)
            r.font.color.rgb = RGBColor(0x0E, 0x94, 0x88)
        elif kind == "h3":
            d.add_heading(payload, level=2)
        elif kind == "p":
            d.add_paragraph(payload)
        elif kind == "note":
            pr = d.add_paragraph()
            r = pr.add_run(payload)
            r.italic = True
        elif kind == "code":
            pr = d.add_paragraph()
            r = pr.add_run(payload.replace("\n", "\n"))
            r.font.name = "Consolas"
            r.font.size = Pt(9)
        elif kind == "ul":
            for i in payload:
                d.add_paragraph(i, style="List Bullet")
        elif kind == "table":
            head, rows = payload
            t = d.add_table(rows=1 + len(rows), cols=len(head))
            t.style = "Table Grid"
            for j, htxt in enumerate(head):
                t.rows[0].cells[j].text = htxt
            for i, r in enumerate(rows, start=1):
                for j, c in enumerate(r):
                    t.rows[i].cells[j].text = str(c)
    d.save(str(path))


def _sections(lang, gui_ver, engine_ver, params):
    """Back-compat: full HTML body from the content model."""
    return _blocks_to_html(_build_blocks(lang, gui_ver, engine_ver, params))


def build_html(lang, gui_ver, engine_ver, params, blocks=None):
    B = blocks if blocks is not None else _build_blocks(lang, gui_ver, engine_ver, params)
    return ("<html><head><style>%s</style></head><body>%s</body></html>" % (_CSS, _blocks_to_html(B)))



def generate(dest_dir, langs=("zh", "en"), gui_ver="1.50", engine_ver="1.50"):
    """Render the manuals (PDF + Word); returns {lang: written Path}.

    Requires PySide6 (PDF) and optionally python-docx (Word)."""
    from PySide6.QtGui import QTextDocument
    from PySide6.QtPrintSupport import QPrinter

    params, _cats = _load_schema_params()
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    written = {}
    docx_ok = True
    try:
        import docx as _pydocx  # noqa: F401
    except ImportError:
        docx_ok = False
    for lang in langs:
        B = _build_blocks(lang, gui_ver, engine_ver, params)
        out = dest / NAMES[lang]
        doc = QTextDocument()
        doc.setHtml(build_html(lang, gui_ver, engine_ver, params, blocks=B))
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(out))
        doc.print_(printer)
        written[lang] = out
        if docx_ok:
            docx_out = dest / (NAMES[lang].replace(".pdf", ".docx"))
            _blocks_to_docx(B, docx_out)
    return written


def main():
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else GUI_DIR / "doc"
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    engine_ver = "1.50"
    try:
        import re
        m = re.search(r"Version\s*:\s*(\d+\.\d+)",
                      (ROOT / "bin" / "RectChr").read_text(errors="replace"))
        if m:
            engine_ver = m.group(1)
    except OSError:
        pass
    try:
        from gui import GUI_VERSION
    except ImportError:
        GUI_VERSION = "1.50"
    written = generate(dest, gui_ver=GUI_VERSION, engine_ver=engine_ver)
    for lang, p in written.items():
        print("%s: %s (%d bytes)" % (lang, p, p.stat().st_size))


if __name__ == "__main__":
    main()
