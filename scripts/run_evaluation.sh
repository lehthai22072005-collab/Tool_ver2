#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" -m src.evaluate --predictions outputs/entities --ground-truth artifacts/dataset/test.jsonl --output reports/evaluation
