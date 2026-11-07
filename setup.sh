#!/usr/bin/env bash
set -euo pipefail

# 无论从哪个目录调用，都以项目根目录作为工作目录。
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 可通过 PYTHON=/path/to/python ./setup.sh 指定解释器；默认使用 Python 3.12。
PYTHON_BIN="${PYTHON:-python3.12}"
VENV_DIR="$PROJECT_ROOT/.venv"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    if [[ -n "${PYTHON:-}" ]]; then
        echo "安装失败：找不到指定的 Python 解释器 '$PYTHON_BIN'。" >&2
        exit 1
    fi

    if [[ -f /etc/debian_version ]] && command -v apt-get >/dev/null 2>&1; then
        echo "未找到 Python 3.12，尝试通过 apt 安装 Python 3.12 和 venv 支持。"
        if [[ "$EUID" -eq 0 ]]; then
            APT_GET=(apt-get)
        elif command -v sudo >/dev/null 2>&1; then
            APT_GET=(sudo apt-get)
        else
            echo "安装失败：安装 Python 3.12 需要 root 或 sudo 权限。" >&2
            exit 1
        fi
        "${APT_GET[@]}" update
        if ! "${APT_GET[@]}" install -y python3.12 python3.12-venv; then
            OS_ID=""
            OS_CODENAME=""
            if [[ -r /etc/os-release ]]; then
                # shellcheck disable=SC1091
                . /etc/os-release
                OS_ID="${ID:-}"
                OS_CODENAME="${VERSION_CODENAME:-}"
            fi

            if [[ "$OS_ID" == "ubuntu" && "$OS_CODENAME" == "jammy" ]]; then
                echo "Ubuntu 22.04 默认源不包含 Python 3.12，添加 deadsnakes PPA 后重试。"
                "${APT_GET[@]}" install -y software-properties-common
                if [[ "$EUID" -eq 0 ]]; then
                    add-apt-repository -y ppa:deadsnakes/ppa
                else
                    sudo add-apt-repository -y ppa:deadsnakes/ppa
                fi
                "${APT_GET[@]}" update
                "${APT_GET[@]}" install -y python3.12 python3.12-venv
            else
                echo "安装失败：当前 apt 软件源没有提供 Python 3.12。请为此系统配置 Python 3.12 软件源后重试。" >&2
                exit 1
            fi
        fi
    else
        echo "安装失败：找不到 Python 3.12，且当前系统不支持通过 apt 自动安装。" >&2
        exit 1
    fi
fi

# PySide6's Qt xcb platform plugin needs this runtime library on Debian/Ubuntu.
if [[ -f /etc/debian_version ]] && command -v apt-get >/dev/null 2>&1; then
    if ! dpkg-query -W -f='${Status}' libxcb-cursor0 2>/dev/null | grep -q 'install ok installed'; then
        echo "安装 Qt 图形界面所需系统库：libxcb-cursor0"
        if [[ "$EUID" -eq 0 ]]; then
            apt-get install -y libxcb-cursor0
        elif command -v sudo >/dev/null 2>&1; then
            sudo apt-get install -y libxcb-cursor0
        else
            echo "安装失败：安装 libxcb-cursor0 需要 root 或 sudo 权限。" >&2
            exit 1
        fi
    fi
fi

PYTHON_VERSION="$($PYTHON_BIN -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
if ! "$PYTHON_BIN" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
    echo "安装失败：requirements.txt 中的 LeRobot 需要 Python 3.12 或更新版本，当前是 $PYTHON_VERSION。" >&2
    exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "创建虚拟环境：$VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR" || {
        echo "创建虚拟环境失败。请确认系统已安装 Python venv 支持（Debian/Ubuntu 通常需要 python3-venv）。" >&2
        exit 1
    }
else
    echo "使用已有虚拟环境：$VENV_DIR"
fi

VENV_PYTHON_VERSION="$("$VENV_DIR/bin/python" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
if ! "$VENV_DIR/bin/python" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
    echo "安装失败：已有虚拟环境使用 Python $VENV_PYTHON_VERSION，但项目依赖需要 Python 3.12 或更新版本。" >&2
    echo "请先备份或移走 .venv，再指定 Python 3.12 运行，例如：" >&2
    echo "  mv .venv .venv-py${VENV_PYTHON_VERSION}" >&2
    echo "  PYTHON=python3.12 ./setup.sh" >&2
    exit 1
fi

echo "升级 pip 并安装 requirements.txt"
if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
    echo "虚拟环境中没有 pip，尝试使用 ensurepip 安装"
    if ! "$VENV_DIR/bin/python" -m ensurepip --upgrade; then
        PYTHON_MINOR="${PYTHON_VERSION%.*}"
        echo "安装失败：当前系统的 Python 未提供 ensurepip。" >&2
        echo "Debian/Ubuntu 可运行：sudo apt install python${PYTHON_MINOR}-venv" >&2
        echo "安装完成后重新运行 ./setup.sh（不要使用 sudo）。" >&2
        exit 1
    fi
fi
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_ROOT/requirements.txt"

echo "安装完成。运行 ./run.sh 启动项目。"
