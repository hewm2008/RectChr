#!/bin/sh
# RectChr GUI launcher (Linux/macOS)
DIR=$(cd "$(dirname "$0")" && pwd)

# packaged app first
for d in "$DIR/dist/RectChrGUI" "$DIR/RectChrGUI"; do
    if [ -x "$d/RectChrGUI" ]; then exec "$d/RectChrGUI"; fi
done

# dev mode: needs python3 (>=3.9)
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Please install Python 3.9+ first."
    echo "未找到 python3，请先安装 Python 3.9+。"
    exit 1
fi

# PySide6 present?
if ! python3 -c "import PySide6" >/dev/null 2>&1; then
    echo "============================================================"
    echo " 首次启动需要安装 PySide6（约 1-2 分钟），请稍候..."
    echo " First launch: installing PySide6 (about 1-2 minutes)..."
    echo "============================================================"
    ok=0
    python3 -m pip install PySide6 >/dev/null 2>&1 && ok=1
    if [ "$ok" -eq 0 ]; then
        echo "  默认源失败，尝试 --user 安装 / trying --user install..."
        python3 -m pip install --user PySide6 >/dev/null 2>&1 && ok=1
    fi
    if [ "$ok" -eq 0 ]; then
        echo "  失败，尝试清华镜像源 / trying Tsinghua mirror..."
        python3 -m pip install --user -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6 >/dev/null 2>&1 && ok=1
    fi
    if [ "$ok" -eq 0 ]; then
        python3 -m ensurepip >/dev/null 2>&1
        python3 -m pip install --user PySide6 >/dev/null 2>&1 && ok=1
    fi
    if [ "$ok" -eq 0 ]; then
        echo "PySide6 自动安装失败 / automatic install failed."
        echo "请手动安装 / Please install manually:  python3 -m pip install PySide6"
        echo "（可能缺少权限或网络受限 / permission or network issue）"
        exit 1
    fi
    if ! python3 -c "import PySide6" >/dev/null 2>&1; then
        echo "PySide6 安装后仍无法导入 / still not importable after install."
        exit 1
    fi
    echo "PySide6 安装完成 / PySide6 installed."
fi

exec python3 "$DIR/gui/main.py" "$@"
