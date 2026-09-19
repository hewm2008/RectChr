"""Minimal bilingual (zh/en) UI strings for the RectChr GUI."""

LANGS = ("zh", "en")

STRINGS = {
    "cite": {"zh": "引用", "en": "Cite"},
    "cite_intro": {"zh": "如果RectChr对你有帮助，欢迎在分享使用体验或相关成果时附上本项目的 GitHub 链接，方便更多人找到它。感谢你的支持", "en": "If RectChr is helpful to you, please consider including this project's GitHub link when sharing your experience or related results so that more people can find it. Thank you for your support!"},
    "copy_citation": {"zh": "复制引用", "en": "Copy citation"},
    "citation_copied": {"zh": "引用已复制", "en": "Citation copied"},
    "open_github": {"zh": "打开 GitHub", "en": "Open GitHub"},
    "app_title":        {"zh": "RectChr 图形界面",        "en": "RectChr GUI"},
    "run":              {"zh": "运行绘图",                "en": "Run"},
    "open_conf":        {"zh": "打开配置…",               "en": "Open conf…"},
    "save_conf":        {"zh": "保存配置…",               "en": "Save conf…"},
    "export_png":       {"zh": "导出 PNG…",              "en": "Export PNG…"},
    "export_svg":       {"zh": "导出SVG",                "en": "Export SVG"},
    "export_svg_tip":   {"zh": "将当前预览的 SVG 原样另存（与预览字节一致）", "en": "Save the exact SVG shown in the preview"},
    "export_pdf":       {"zh": "导出 PDF…",              "en": "Export PDF…"},
    "language":         {"zh": "语言",                    "en": "Language"},
    "help":             {"zh": "帮助",                    "en": "Help"},
    "help_tip":         {"zh": "打开使用手册 PDF（F1）",   "en": "Open the manual PDF (F1)"},
    "about":            {"zh": "关于",                    "en": "About"},
    "about_tip":        {"zh": "版本与联系方式",           "en": "Version & contact"},
    "about_title":      {"zh": "关于 RectChr GUI",        "en": "About RectChr GUI"},
    "about_body":       {"zh": "<h3>RectChr GUI {gui_ver}</h3>"
                               "<p>引擎 / Engine: RectChr {engine_ver} (hewm2008)</p>"
                               "<p>多层级染色体（Chr）可视化工具，类 circos 矩形布局</p><hr>"
                               "<p>📧 邮箱：<a href=\"mailto:hewm2008@gmail.com\">hewm2008@gmail.com</a> / "
                               "<a href=\"mailto:hewm2008@qq.com\">hewm2008@qq.com</a></p>"
                               "<p>🏠 主页：<a href=\"https://github.com/hewm2008/RectChr\">github.com/hewm2008/RectChr</a></p>"
                               "<p>💬 QQ 交流群：<b>125293663</b></p>",
                           "en": "<h3>RectChr GUI {gui_ver}</h3>"
                                 "<p>Engine: RectChr {engine_ver} (hewm2008)</p>"
                                 "<p>Multi-level visualization of genomic variables on rectangular chromosomes (circos-like)</p><hr>"
                                 "<p>📧 Email: <a href=\"mailto:hewm2008@gmail.com\">hewm2008@gmail.com</a> / "
                                 "<a href=\"mailto:hewm2008@qq.com\">hewm2008@qq.com</a></p>"
                                 "<p>🏠 Home: <a href=\"https://github.com/hewm2008/RectChr\">github.com/hewm2008/RectChr</a></p>"
                                 "<p>💬 QQ Group: <b>125293663</b></p>"},
    "help_pick_title":  {"zh": "选择用法手册",           "en": "Choose a manual"},
    "help_pick_intro":  {"zh": "请选择要打开的用法手册：", "en": "Choose the manual to open:"},
    "help_pick_footer": {"zh": "PDF 将用系统默认阅读器打开；GUI 手册缺失时可一键生成", "en": "PDFs open in your system viewer; missing GUI manuals can be generated on the fly"},
    "help_engine_zh":   {"zh": "引擎手册 · 中文（Linux 命令行用法）", "en": "Engine manual · Chinese (CLI usage)"},
    "help_engine_en":   {"zh": "引擎手册 · English（Linux 命令行用法）", "en": "Engine manual · English (CLI usage)"},
    "help_gui_zh":      {"zh": "GUI 手册 · 中文（图形界面用法）", "en": "GUI manual · Chinese (GUI usage)"},
    "help_gui_en":      {"zh": "GUI 手册 · English（图形界面用法）", "en": "GUI manual · English (GUI usage)"},
    "help_bundled":     {"zh": "已附带",                  "en": "bundled"},
    "help_missing_tag": {"zh": "未附带",                  "en": "not bundled"},
    "help_generate":    {"zh": "生成并打开",              "en": "Generate & open"},
    "help_generated":   {"zh": "已生成：{f}",             "en": "Generated: {f}"},
    "help_word":        {"zh": "Word",                   "en": "Word"},
    "help_word_tip":    {"zh": "打开 Word（.docx）版手册，便于编辑/打印", "en": "Open the editable Word (.docx) manual"},
    "data_files":       {"zh": "数据文件",                "en": "Data files"},
    "add_file":         {"zh": "添加文件",                "en": "Add file"},
    "remove_file":      {"zh": "移除所选",                "en": "Remove selected"},
    "file_hint":        {"zh": "格式: Chr Start End Value1 …（支持 .gz）", "en": "Format: Chr Start End Value1 … (.gz supported)"},
    "data_preview":     {"zh": "数据预览（前 20 行）",     "en": "Data preview (first 20 rows)"},
    "global_tab":       {"zh": "全局参数",                "en": "Global"},
    "track_all_tab":    {"zh": "trackALL（所有层默认）",  "en": "trackALL (defaults)"},
    "track_tab":        {"zh": "Track {n}",               "en": "Track {n}"},
    "add_track":        {"zh": "＋ 添加/转到",            "en": "＋ Add/goto"},
    "remove_track":     {"zh": "－ 移除该 Track",         "en": "－ Remove"},
    "add_track_tip":    {"zh": "添加该编号的 track 配置段（已存在则直接跳到该页）；未配置的层用默认渲染", "en": "Create this track section (or jump to it if it exists); untouched layers render with defaults"},
    "track_add_which":  {"zh": "添加编号",                "en": "Add #"},
    "track_remove_which": {"zh": "移除编号",              "en": "Remove #"},
    "tracks_count":     {"zh": "已配置 track 段：{n}",    "en": "Configured track sections: {n}"},
    "auto_mode":        {"zh": "未配置任何 track 段（各层使用默认渲染）", "en": "No track sections (all layers use engine defaults)"},
    "remove_last_track": {"zh": "将移除最后一个 track 配置段（其余层使用默认渲染）。继续？", "en": "This removes the last track section (other layers use defaults). Continue?"},
    "palette_none":       {"zh": "（未使用）",           "en": "(not used)"},
    "palette_pick":       {"zh": "选择调色板",           "en": "Choose a palette"},
    "palette_clear":      {"zh": "清除（不使用调色板）",  "en": "Clear (no palette)"},
    "palette_builtin_qual": {"zh": "内置 RColorBrewer · 定性/分类", "en": "Built-in RColorBrewer · qualitative"},
    "palette_builtin_seq":  {"zh": "内置 RColorBrewer · 连续/渐变", "en": "Built-in RColorBrewer · sequential/diverging"},
    "palette_files":      {"zh": "ColorsBrewer 扩展目录", "en": "ColorsBrewer extension folder"},
    "view_menu":        {"zh": "视图",                    "en": "View"},
    "menu_file":        {"zh": "文件",                    "en": "File"},
    "reset_layout":     {"zh": "重置布局",                "en": "Reset layout"},
    "right_dock_title": {"zh": "参数",                    "en": "Parameters"},
    "log_dock_title":   {"zh": "运行日志",                "en": "Run log"},
    "track_manage":     {"zh": "Track 管理",              "en": "Track manager"},
    "auto_refresh":     {"zh": "自动刷新",                "en": "Auto refresh"},
    "auto_refresh_tip": {"zh": "参数修改后自动重跑引擎并刷新预览", "en": "Re-run the engine automatically after parameter edits"},
    "show_params":      {"zh": "参数总览",                "en": "Parameters"},
    "params_none":      {"zh": "（尚未设置任何参数）",     "en": "(no parameters set)"},
    "summary_nav_note": {"zh": "点击左侧段名可快速定位",   "en": "Click a section to jump to it"},
    "refresh_preview":  {"zh": "🔄 刷新预览",             "en": "🔄 Refresh preview"},
    "refresh_tip":      {"zh": "用当前参数重新运行并刷新预览图（F5）", "en": "Re-run with current parameters and refresh the preview (F5)"},
    "stale_running":    {"zh": "参数已修改，正在重新渲染…", "en": "Parameters changed — re-rendering…"},
    "stale_manual":     {"zh": "参数已修改，点击刷新预览",   "en": "Parameters changed — click Refresh preview"},
    "stale_fail_hint":  {"zh": "自动刷新失败，详见运行日志", "en": "Auto refresh failed — see the run log"},
    "show_all_params":  {"zh": "显示全部参数",           "en": "Show all params"},
    "enabled":          {"zh": "启用",                    "en": "On"},
    "plot_type":        {"zh": "画图类型 plot_type",      "en": "Plot type"},
    "data_source":      {"zh": "数据来源",                "en": "Data source"},
    "running":          {"zh": "正在运行 RectChr …",      "en": "Running RectChr …"},
    "already_running":  {"zh": "上一次运行还在进行中，请等待完成", "en": "A run is still in progress, please wait"},
    "run_fail_title":   {"zh": "运行失败",                "en": "Run failed"},
    "run_fail_msg":     {"zh": "RectChr 引擎未成功出图（原因：{reason}）。详细输出见下方/运行日志页：", "en": "The engine did not produce a figure (reason: {reason}). See the run log below:"},
    "done_ok":          {"zh": "完成：{f}",               "en": "Done: {f}"},
    "done_fail":        {"zh": "运行失败，请查看运行日志", "en": "Run failed, see the log tab"},
    "no_file1":         {"zh": "请先添加 File1 数据文件",  "en": "Please add the File1 data file first"},
    "file_missing":     {"zh": "文件不存在：{f}",         "en": "File not found: {f}"},
    "perl_missing":     {"zh": "未找到 Perl。Windows 请将便携版 Perl 放到 gui_runtime/perl/，Linux 请安装 perl。", "en": "Perl not found. On Windows put portable Perl under gui_runtime/perl/, on Linux install perl."},
    "conf_written":     {"zh": "配置已写入 {f}",          "en": "Conf written to {f}"},
    "conf_loaded":      {"zh": "已载入配置 {f}",          "en": "Conf loaded from {f}"},
    "export_done":      {"zh": "已导出 {f}",              "en": "Exported {f}"},
    "no_preview":       {"zh": "尚无预览。请先运行绘图。", "en": "No preview yet. Run first."},
    "filter":           {"zh": "筛选参数…",              "en": "Filter params…"},
    "filter_tip":       {"zh": "跨全部分类搜索参数",       "en": "Search across all groups"},
    "show_all_tip":     {"zh": "同时显示其他画图类型的参数", "en": "Also show params of other plot types"},
    "filter_nomatch":   {"zh": "没有匹配的参数",           "en": "No matching parameters"},
    "cat_all_lowfreq":  {"zh": "该分类参数均为低频参数，请勾选“显示全部参数”",
                         "en": 'All parameters here are low-frequency; tick "Show all params" to display them'},
    "presence_only_tip": {"zh": "该项只要存在就生效，写 0 也会生效；留空 = 不生效",
                          "en": "The engine acts on this key merely existing — writing 0 "
                                "also triggers it; leave empty to disable"},
    "open_failed":      {"zh": "无法打开该文件（系统未注册打开方式）",
                         "en": "Could not open the file (no handler registered)"},
    "files_folded_hint": {"zh": "已配置 {n} 个文件，此处仅显示列表；请用左侧「数据文件」面板编辑",
                          "en": "Configured {n} files — listed here for reference; "
                                "edit them in the left Data files panel"},
    "loading_tracks":   {"zh": "正在载入 {n} 个轨道…", "en": "Loading {n} tracks…"},
    "new_project":      {"zh": "新建",                    "en": "New"},
    "choose":           {"zh": "选择…",                   "en": "Browse…"},
    "invalid_columns":  {"zh": "show_columns 格式应为 File1:4 或 File2:4,5", "en": "show_columns format: File1:4 or File2:4,5"},
    "save_conf_title":  {"zh": "保存 RectChr 配置",       "en": "Save RectChr conf"},
    "open_conf_title":  {"zh": "打开 RectChr 配置",       "en": "Open RectChr conf"},
    "animated_hint":    {"zh": "动态 SVG 请用浏览器打开：{f}", "en": "Animated SVG: open in a browser: {f}"},
    "err_title":        {"zh": "错误",                    "en": "Error"},
    "warn_title":       {"zh": "提示",                    "en": "Notice"},
}


class I18N:
    _lang = "zh"

    @classmethod
    def lang(cls):
        return cls._lang

    @classmethod
    def set_lang(cls, lang):
        if lang in LANGS:
            cls._lang = lang

    @classmethod
    def tr(cls, key, **kw):
        s = STRINGS.get(key, {})
        text = s.get(cls._lang) or s.get("zh") or key
        if kw:
            try:
                text = text.format(**kw)
            except (KeyError, IndexError):
                pass
        return text
