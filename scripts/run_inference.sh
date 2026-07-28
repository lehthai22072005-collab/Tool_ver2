#!/usr/bin/env bash
set -euo pipefail
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" -m src.infer --input "$1" --model "${2:-models/phobert_legal_ner/best}" --output outputs/entities
