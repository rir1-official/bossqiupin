#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="$PROJECT_DIR/.venv312/bin/python"
TORCH_LIB="$PROJECT_DIR/.venv312/lib/python3.12/site-packages/torch/lib"
SKLEARN_LIB="$PROJECT_DIR/.venv312/lib/python3.12/site-packages/sklearn/.dylibs"
FAISS_LIB="$PROJECT_DIR/.venv312/lib/python3.12/site-packages/faiss/.dylibs"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "Project Python was not found: $PYTHON_BIN" >&2
    echo "Create it with: bundled Python 3.12 -m venv .venv312 && .venv312/bin/python -m pip install -r requirements.txt" >&2
    exit 1
fi

# Use the project-owned Python 3.12 environment and bundled OpenMP runtime.
export DYLD_LIBRARY_PATH="$TORCH_LIB:$SKLEARN_LIB:$FAISS_LIB${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"

# Keep the macOS PyTorch CPU/OpenMP fallback single-threaded. The default
# multi-threaded path has produced native SIGSEGV crashes during embedding.
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
export KMP_INIT_AT_FORK="${KMP_INIT_AT_FORK:-FALSE}"
export KMP_BLOCKTIME="${KMP_BLOCKTIME:-0}"
export KMP_AFFINITY="${KMP_AFFINITY:-disabled}"
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"
export TORCH_NUM_THREADS="${TORCH_NUM_THREADS:-1}"
export TORCH_NUM_INTEROP_THREADS="${TORCH_NUM_INTEROP_THREADS:-1}"
export PYTHONMALLOC="${PYTHONMALLOC:-malloc}"
export MPLBACKEND="${MPLBACKEND:-Agg}"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

if [ "${PYTHON_DIAGNOSTICS:-0}" = "1" ]; then
    echo "Python executable: $PYTHON_BIN" >&2
    echo "Python target: $(readlink "$PYTHON_BIN" 2>/dev/null || printf '%s' 'regular file')" >&2
    echo "Python version: $($PYTHON_BIN --version 2>&1)" >&2
    echo "OpenMP threads: OMP=$OMP_NUM_THREADS MKL=$MKL_NUM_THREADS VECLIB=$VECLIB_MAXIMUM_THREADS" >&2
fi

exec "$PYTHON_BIN" "$@"
