#!/usr/bin/env bash
set -euo pipefail

# 无论从哪个目录调用，都以项目根目录作为工作目录。
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
PYSIDE6_UIC="$PROJECT_ROOT/.venv/bin/pyside6-uic"
UI_DIR="$PROJECT_ROOT/src/ui"

if [[ ! -x "$PYTHON" ]]; then
    echo "启动失败：请确认 .venv 已创建，并已安装 PySide6。" >&2
    exit 1
fi

if [[ ! -x "$PYSIDE6_UIC" ]]; then
    echo "启动失败：找不到 pyside6-uic，请确认虚拟环境已安装 PySide6。" >&2
    exit 1
fi

shopt -s nullglob
for ui_file in "$UI_DIR"/*.ui; do
    py_file="${ui_file%.ui}.py"
    if [[ ! -f "$py_file" || "$ui_file" -nt "$py_file" ]]; then
        echo "编译 ${ui_file#"$PROJECT_ROOT"/}"
        "$PYSIDE6_UIC" "$ui_file" -o "$py_file"
    fi
done
shopt -u nullglob

echo "启动 src/main.py"
exec "$PYTHON" -m src.main "$@"
