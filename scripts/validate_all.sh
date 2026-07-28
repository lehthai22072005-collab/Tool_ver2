#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" -m pytest
"$PYTHON" -m src.validate_outputs --input-dir outputs/entities --source-dir "${1:-output/documents}" --report reports/output_validation.json
