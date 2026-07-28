#!/usr/bin/env bash
set -euo pipefail

cd /content/Tool-VBPL-Scraper
export HF_HOME=/content/huggingface
export HF_HUB_DISABLE_XET=1
export TOKENIZERS_PARALLELISM=false

DATASET_DIR="${DATASET_DIR:-artifacts/dataset}"
MODEL_OUTPUT_DIR="${MODEL_OUTPUT_DIR:-models/phobert_legal_ner_gpu}"
CONFIG_PATH="${CONFIG_PATH:-configs/stage2_colab.yaml}"

python -m pip install -q \
  "transformers==4.57.6" \
  "accelerate>=1.0,<2" \
  "seqeval>=1.2.2,<2" \
  "python-docx>=1.1,<2" \
  "PyYAML>=6,<7" \
  "jsonschema>=4.22,<5"

python - <<'PY'
import json
import platform
from pathlib import Path
import torch

info = {
    "python": platform.python_version(),
    "torch": torch.__version__,
    "cuda_available": torch.cuda.is_available(),
    "cuda": torch.version.cuda,
    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "gpu_memory_bytes": (
        torch.cuda.get_device_properties(0).total_memory
        if torch.cuda.is_available() else 0
    ),
}
Path("reports").mkdir(exist_ok=True)
Path("reports/colab_environment.json").write_text(
    json.dumps(info, indent=2), encoding="utf-8"
)
print(json.dumps(info, indent=2))
if not torch.cuda.is_available():
    raise SystemExit("Colab GPU is not available")
PY

resume_args=()
if [[ -d "$MODEL_OUTPUT_DIR/checkpoints" ]]; then
  latest_checkpoint="$(find "$MODEL_OUTPUT_DIR/checkpoints" -maxdepth 1 -type d \
    -name 'checkpoint-*' -printf '%f\n' | sort -V | tail -n 1)"
  if [[ -n "$latest_checkpoint" ]]; then
    resume_args=(--resume-from-checkpoint "$MODEL_OUTPUT_DIR/checkpoints/$latest_checkpoint")
    echo "Resuming from ${resume_args[1]}"
  fi
fi

python -m src.train \
  --dataset-dir "$DATASET_DIR" \
  --output-dir "$MODEL_OUTPUT_DIR" \
  --config "$CONFIG_PATH" \
  "${resume_args[@]}"

PACKAGE_MODEL_DIR="models/phobert_legal_ner_gpu"
if [[ "$MODEL_OUTPUT_DIR" != "$PACKAGE_MODEL_DIR" ]]; then
  mkdir -p "$PACKAGE_MODEL_DIR"
  cp -a "$MODEL_OUTPUT_DIR/best" "$PACKAGE_MODEL_DIR/"
  cp "$MODEL_OUTPUT_DIR/training_history.json" "$PACKAGE_MODEL_DIR/"
fi

python - <<'PY'
import os
from pathlib import Path
from safetensors.torch import load_file, save_file

checkpoint = Path("models/phobert_legal_ner_gpu/best/model.safetensors")
temporary = checkpoint.with_suffix(".fp16.safetensors")
state = load_file(checkpoint)
state = {
    name: tensor.half() if tensor.is_floating_point() else tensor
    for name, tensor in state.items()
}
save_file(state, temporary, metadata={"format": "pt"})
os.replace(temporary, checkpoint)
print(f"FP16 checkpoint bytes: {checkpoint.stat().st_size}")
PY

tar -cf /content/stage2_colab_model.tar \
  models/phobert_legal_ner_gpu/best \
  models/phobert_legal_ner_gpu/training_history.json

split -b 140M \
  /content/stage2_colab_model.tar \
  /content/stage2_colab_model.tar.part.
rm /content/stage2_colab_model.tar

if [[ -d artifacts/test_inputs && -f "$DATASET_DIR/test.jsonl" ]]; then
  python -m src.infer \
    --input artifacts/test_inputs \
    --model models/phobert_legal_ner_gpu/best \
    --output outputs_gpu/entities \
    --config "$CONFIG_PATH"

  python -m src.evaluate \
    --predictions outputs_gpu/entities \
    --ground-truth "$DATASET_DIR/test.jsonl" \
    --output reports/gpu_evaluation

  python -m src.validate_outputs \
    --input-dir outputs_gpu/entities \
    --source-dir artifacts/test_inputs \
    --report reports/gpu_output_validation.json

  tar -cf /content/stage2_colab_reports.tar \
    outputs_gpu reports/colab_environment.json reports/gpu_evaluation \
    reports/gpu_output_validation.json
else
  tar -cf /content/stage2_colab_reports.tar \
    reports/colab_environment.json
fi

sha256sum \
  /content/stage2_colab_model.tar.part.* \
  /content/stage2_colab_reports.tar \
  > /content/stage2_colab_result.sha256

echo "COLAB_STAGE2_COMPLETE:"
ls -lh /content/stage2_colab_model.tar.part.* \
  /content/stage2_colab_reports.tar \
  /content/stage2_colab_result.sha256
