# RectChr GUI（跨平台桌面图形界面）

RectChr 的跨平台图形界面：**同一份代码运行于 Windows / Linux / macOS**，无需命令行即可完成
从数据导入、参数配置到预览、导出的完整流程。底层仍调用 RectChr Perl 引擎（本仓库已做跨平台改造）。

The cross-platform desktop GUI for RectChr. One codebase runs on Windows/Linux/macOS;
it drives the (cross-platform patched) Perl engine under the hood.

## 功能 / Features

- 数据文件管理：File1..FileN，支持 `.gz`，自动预览前 100 行、自动建议 track_num；
  左侧面板与"全局参数 → 数据文件"分类页双入口同步
- 全量参数表单：108 个参数（由 `NewParaList.xlsx` 自动生成 schema），
  按分类浏览、按 plot_type 联动过滤、中英双语说明、显示引擎真实默认值与取值范围
- 14 种 plot_type（heatmap / point / line / hist / highlights / text / shape /
  ridgeline / PairWiseLink / PairWiseLinkV2 / LinkS / heatmapAnimated /
  histAnimated / highlightsAnimated），下拉项带多彩 SVG 图标
- 调色板选择器：`colormap_brewer_name` 内置 35 个 RColorBrewer 色板（颜色取自引擎
  ColorPaletteManager，与实际渲染一致）+ ColorsBrewer 扩展目录 27 个，色条预览、搜索、可手填
- 双向配置：打开已有 `.conf`（自动兼容老参数名，如 `crBegin`→`colormap_low_color`），
  或从界面生成 `.conf` 交给命令行使用
- SVG 实时预览 + 缩放，导出高分辨率 PNG / PDF
- 中英双语界面，一键切换

## 快速开始 / Quick start

### 开发态运行（Linux / macOS）

```bash
pip install PySide6          # Python >= 3.9
./RectChrGUI.sh              # 或 python3 gui/main.py
```

### 开发态运行（Windows）

```
pip install PySide6
RectChrGUI.bat               (双击即可；或 python gui\main.py)
```

### 打包发行版（Windows 双击即用）

```bat
pip install pyinstaller
pyinstaller gui\tools\RectChrGUI.spec --distpath dist --noconfirm
python gui\tools\build_windows.py dist\RectChrGUI
```

产物目录结构：

```
RectChrGUI/
├── RectChrGUI.exe           双击运行
├── bin/                     Perl 引擎（已跨平台化）+ lib + svg_kit
├── ColorsBrewer/            色板
└── gui_runtime/perl/        放入便携版 Strawberry Perl
    （下载 strawberry-perl-...-portable.zip，解压为 gui_runtime/perl/perl/bin/perl.exe）
```

放入便携 Perl 后用户**零安装、零配置**，双击 `RectChrGUI.exe` 即可出图。
不放入 Perl 时也可用系统 PATH 中的 perl（Strawberry Perl 正常安装版亦可）。

Linux 打包同理（spec 同用）：`pyinstaller gui/tools/RectChrGUI.spec` 后再运行
`python3 gui/tools/build_windows.py dist/RectChrGUI` 组装发行目录（含手册与引擎），
无需便携 Perl（系统自带），直接运行 `dist/RectChrGUI/RectChrGUI`。

> 注意：PyInstaller 需要**共享库版 Python**（Windows 官方安装版自带 python3xx.dll，
> 开箱即用）。自行编译的 Linux Python 若未加 `--enable-shared`（只有 libpython*.a）
> 会打包失败——此时改用源码分发：整个仓库目录（含 gui/、bin/、RectChrGUI.sh）拷给用户，
> `pip install PySide6` 后运行 `RectChrGUI.sh` 即可。

### macOS 应用包与 Dock 名称

在 Mac 上使用已安装 PySide6 和 PyInstaller 的 Python 环境运行：

```bash
python3 gui/tools/gen_app_icon.py gui/resources/RectChr.icns
pyinstaller gui/tools/RectChrGUI.spec --distpath dist --noconfirm
open dist/RectChr.app
```

应用包设置名称为 `RectChr`，使用项目图标；引擎、色板、schema 和手册由 spec
直接纳入应用包，无需再运行 `build_windows.py`。运行绘图仍需可用的 Perl。
直接从 Python/IDE 启动时，Qt 显示名称已设为 `RectChr`，但 macOS Dock 仍可能
采用 Python 解释器名称；建议从 Finder 启动 `RectChr.app`。
打包必须在 macOS 本机完成；Dock 显示、签名及公证需在 Mac 上验证，Linux 测试不能替代。

## 引擎的跨平台改造（本仓库）

| 位置 | 原来 | 现在 |
|------|------|------|
| `bin/lib/ConfigDataLoader.pm` | `gzip -cd` 外部命令读 .gz | 纯 Perl `IO::Uncompress::Gunzip`（核心模块） |
| `bin/lib/ConfigDataLoader.pm` | `wc -l \| awk` 数色板行数 | 纯 Perl 行计数 |
| `bin/RectChr` | `` `date +%Y%m%d` `` | `POSIX strftime` |
| `bin/RectChr` | 子 shell 探测 SVG 模块（Windows 转义易碎） | 编译期 `require`，始终优先内置 svg_kit/SVG.pm（与原版行为一致） |
| `bin/lib/LocalUtils.pm` | 找不到 `convert` 就报错退出 | ImageMagick 纯可选；`RECTCHR_NO_PNG=1` 可跳过；规避 Windows 自带 `convert.exe`（NTFS 工具）陷阱 |
| `bin/lib/*.pm`（4 个模块） | 声明了 `@EXPORT_OK` 却没加载 `Exporter`，新版 Perl（5.36+，Windows 常见）报警告 "Attempt to call undefined import method…" | 补 `use Exporter 'import';`（LocalUtils / GenomicLinkPlot / RectChrPlot / ColorPaletteManager），各 Perl 版本下均无警告 |

回归保障：改造后 Linux 全部 22 个官方示例（Basic_Tutorials + Scene_Usage）共 36 个 SVG
与原版**字节级一致**。

另修复两个上游"示例配置参数被引擎静默忽略"的问题（GUI 生成配置时自动翻译为引擎真实键名）：

- `cutoff_value` → 引擎实际读 `cutoff_y`（GWAS 示例的分割线此前从未画出来）
- `colormap_legend_size` → 引擎实际读 `colormap_legend_sizeratio`

## 目录 / Layout

```
gui/
├── main.py                  入口
├── i18n.py                  中英双语文案
├── core/
│   ├── schema.py            参数 schema 加载
│   ├── conf_io.py           conf 模型 / 读写（含老参数别名翻译）
│   └── runner.py            QProcess 运行引擎（自动找 perl，Windows 优先便携版）
├── ui/
│   ├── main_window.py       主窗口
│   ├── files_panel.py       数据文件面板
│   ├── param_form.py        参数表单（分类树 + 动态过滤）
│   ├── track_tab.py         Track 页（plot_type 联动、惰加载）
│   ├── params_summary.py    参数总览表
│   ├── plot_icons.py        plot_type 多彩 SVG 图标（内嵌）
│   ├── logo.py              RectChr logo（内嵌 SVG：窗口图标 + 关于窗口）
│   └── preview.py           SVG 预览 + PNG/PDF 导出
├── resources/params_schema.json   由 NewParaList.xlsx 生成
├── tests/test_gui_regressions.py  GUI 回归测试（offscreen）
└── tools/
    ├── gen_schema.py        重新生成 schema：python3 gui/tools/gen_schema.py
    ├── RectChrGUI.spec      PyInstaller 打包配置
    └── build_windows.py     组装发行目录（含便携 Perl 说明）
```

## 已知限制 / Notes

- 动态 SVG（heatmapAnimated / histAnimated）在预览中显示静态帧；
  完整动画请在浏览器中打开 SVG（预览会给出提示）。
- 引擎的 PNG 转换（ImageMagick `convert`）为可选项；GUI 内直接由 Qt 渲染导出 PNG/PDF，
  不依赖 ImageMagick。
- schema 来自 `NewParaList.xlsx` 并与 Perl 代码交叉校验；若参数表更新，
  运行 `python3 gui/tools/gen_schema.py` 重新生成。
