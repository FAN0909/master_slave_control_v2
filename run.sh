#!/usr/bin/env bash
set -euo pipefail

# 无论从哪个目录调用，都以项目根目录作为工作目录。
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
UIC="$PROJECT_ROOT/.venv/bin/pyside6-uic"

if [[ ! -x "$PYTHON" || ! -x "$UIC" ]]; then
    echo "启动失败：请确认 .venv 已创建，并已安装 PySide6。" >&2
    exit 1
fi

# 例如：src/ui/MainWindow.ui -> src/ui/ui_MainWindow.py。
# ui_*.py 为自动生成文件，请直接修改对应的 .ui 文件。
while IFS= read -r -d '' ui_file; do
    output="$(dirname -- "$ui_file")/ui_$(basename -- "$ui_file" .ui).py"
    echo "编译 UI：$ui_file -> $output"
    "$UIC" "$ui_file" -o "$output"
done < <(find src -type f -name '*.ui' -print0)

echo "启动 src/main.py"
exec "$PYTHON" -m src.main "$@"
