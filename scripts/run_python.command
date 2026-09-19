#!/bin/zsh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

echo "项目 Python 已启动：$PROJECT_DIR/.venv312/bin/python"
echo "运行环境检查："
PYTHON_DIAGNOSTICS=1 ./scripts/python.sh -c 'import sys, torch; print("  executable:", sys.executable); print("  version:", sys.version.split()[0]); print("  torch:", torch.__version__); print("  mps:", torch.backends.mps.is_available())'
echo
echo "这是项目环境，不是 macOS 系统 Python.app。输入 Python 代码后按 Control-D 退出。"
exec ./scripts/python.sh -i
