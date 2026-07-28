from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


def load_config(path: str | Path = "configs/stage2.yaml") -> dict:
    with Path(path).open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    required = {"model_name", "max_length", "stride", "seed"}
    missing = required - config.keys()
    if missing:
        raise ValueError(f"Missing config keys: {sorted(missing)}")
    return config


def config_hash(config: dict) -> str:
    payload = json.dumps(config, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()
