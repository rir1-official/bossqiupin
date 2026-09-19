#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "$PROJECT_DIR/scripts/python.sh" -m job_analysis.week1 "$@"
