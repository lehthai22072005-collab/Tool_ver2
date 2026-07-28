#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" -m src.run_stage2 --data-dir "${1:-output/documents}" --work-dir . \
  --auto-train --run-inference --run-evaluation --validate-outputs
