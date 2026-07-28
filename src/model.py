from __future__ import annotations

import random


def set_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np
        import torch
        np.random.seed(seed); torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
    except ImportError:
        pass


def load_model(checkpoint: str, label_map: dict[str, int] | None = None):
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    kwargs = {}
    if label_map:
        kwargs = {"num_labels": len(label_map), "label2id": label_map,
                  "id2label": {v: k for k, v in label_map.items()},
                  "ignore_mismatched_sizes": True}
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(checkpoint, **kwargs)
    return tokenizer, model
