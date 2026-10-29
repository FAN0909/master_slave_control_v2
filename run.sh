#!/usr/bin/env bash
set -euo pipefail

# 无论从哪个目录调用，都以项目根目录作为工作目录。
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "启动失败：请确认 .venv 已创建，并已安装 PySide6。" >&2
    exit 1
fi

echo "启动 src/main.py"
exec "$PYTHON" -m src.main "$@"
