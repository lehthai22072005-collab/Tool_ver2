from __future__ import annotations

import argparse
import json
import random
import shutil
import time
from pathlib import Path

from .chunking import make_chunks
from .config import load_config
from .model import load_model, set_seed
from .token_alignment import align_bio


class NERDataset:
    def __init__(self, path, tokenizer, label_map, max_length, stride,
                 negative_ratio=None, seed=42, limit=None):
        self.items = []
        negative_count = 0
        for row in _iter_rows(path, limit):
            for chunk in make_chunks(row["text"], tokenizer, max_length, stride):
                item = {"input_ids": chunk["input_ids"], "attention_mask": chunk["attention_mask"],
                        "labels": align_bio(chunk["offset_mapping"], row["entities"], label_map)}
                o_id = label_map["O"]
                if any(label not in {-100, o_id} for label in item["labels"]):
                    self.items.append(item)
                else:
                    negative_count += 1
        if negative_ratio is not None:
            keep_negative = min(negative_count, int(len(self.items) * float(negative_ratio)))
            sampled_negative = []
            seen_negative = 0
            rng = random.Random(seed)
            if keep_negative:
                # A second streaming pass performs exact reservoir sampling without
                # materializing every all-O chunk in system RAM.
                for row in _iter_rows(path, limit):
                    for chunk in make_chunks(row["text"], tokenizer, max_length, stride):
                        item = {
                            "input_ids": chunk["input_ids"],
                            "attention_mask": chunk["attention_mask"],
                            "labels": align_bio(
                                chunk["offset_mapping"], row["entities"], label_map
                            ),
                        }
                        if any(label not in {-100, o_id} for label in item["labels"]):
                            continue
                        seen_negative += 1
                        if len(sampled_negative) < keep_negative:
                            sampled_negative.append(item)
                        else:
                            selected = rng.randrange(seen_negative)
                            if selected < keep_negative:
                                sampled_negative[selected] = item
            self.items.extend(sampled_negative)
            random.Random(seed).shuffle(self.items)
        else:
            # Preserve the original behavior for small datasets/configurations.
            for row in _iter_rows(path, limit):
                for chunk in make_chunks(row["text"], tokenizer, max_length, stride):
                    item = {
                        "input_ids": chunk["input_ids"],
                        "attention_mask": chunk["attention_mask"],
                        "labels": align_bio(
                            chunk["offset_mapping"], row["entities"], label_map
                        ),
                    }
                    if not any(label not in {-100, o_id} for label in item["labels"]):
                        self.items.append(item)
    def __len__(self): return len(self.items)
    def __getitem__(self, index): return self.items[index]


def _iter_rows(path, limit=None):
    with Path(path).open(encoding="utf-8") as source:
        yielded = 0
        for line in source:
            if not line.strip():
                continue
            yield json.loads(line)
            yielded += 1
            if limit is not None and yielded >= limit:
                return


def train(dataset_dir="artifacts/dataset", output_dir="models/phobert_legal_ner",
          config_path="configs/stage2.yaml", max_steps: int = -1, limit: int | None = None,
          freeze_base: bool = False,
          resume_from_checkpoint: str | None = None) -> dict:
    import torch
    from transformers import DataCollatorForTokenClassification, EarlyStoppingCallback, Trainer, TrainingArguments
    config = load_config(config_path); set_seed(config["seed"])
    label_map = json.loads(Path(dataset_dir, "label_map.json").read_text())
    id_to_label = {value: key for key, value in label_map.items()}
    tokenizer, model = load_model(config["model_name"], label_map)
    if freeze_base:
        for parameter in model.base_model.parameters():
            parameter.requires_grad = False
    train_ds = NERDataset(Path(dataset_dir, "train.jsonl"), tokenizer, label_map,
                          config["max_length"], config["stride"],
                          negative_ratio=config.get("negative_chunk_ratio"),
                          seed=config["seed"], limit=limit)
    val_ds = NERDataset(Path(dataset_dir, "validation.jsonl"), tokenizer, label_map,
                        config["max_length"], config["stride"],
                        negative_ratio=config.get("validation_negative_chunk_ratio"),
                        seed=config["seed"] + 1, limit=limit)
    test_path = Path(dataset_dir, "test.jsonl")
    test_ds = (
        NERDataset(test_path, tokenizer, label_map,
                   config["max_length"], config["stride"],
                   negative_ratio=config.get(
                       "test_negative_chunk_ratio",
                       config.get("validation_negative_chunk_ratio"),
                   ),
                   seed=config["seed"] + 2, limit=limit)
        if test_path.exists()
        else None
    )
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    def compute_metrics(result):
        import numpy as np
        from seqeval.metrics import f1_score, precision_score, recall_score
        ids = np.argmax(result.predictions, axis=-1)
        gold, predicted = [], []
        for prediction, labels in zip(ids, result.label_ids):
            keep = labels != -100
            gold.append([id_to_label[int(x)] for x in labels[keep]])
            predicted.append([id_to_label[int(x)] for x in prediction[keep]])
        return {"precision": precision_score(gold, predicted),
                "recall": recall_score(gold, predicted),
                "f1": f1_score(gold, predicted)}
    save_strategy = (
        config.get("save_strategy", "epoch") if max_steps < 0 else "steps"
    )
    keep_best = save_strategy != "no"
    args = TrainingArguments(
        output_dir=str(out / "checkpoints"), learning_rate=config["learning_rate"],
        per_device_train_batch_size=config["batch_size"],
        per_device_eval_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        num_train_epochs=config["epochs"], weight_decay=config["weight_decay"],
        warmup_ratio=config["warmup_ratio"], seed=config["seed"], data_seed=config["seed"],
        eval_strategy=(config.get("eval_strategy", "epoch")
                       if max_steps < 0 else "steps"),
        save_strategy=save_strategy,
        eval_steps=1 if max_steps > 0 else config.get("eval_steps"),
        save_steps=1 if max_steps > 0 else int(config.get("save_steps", 500)),
        max_steps=max_steps, load_best_model_at_end=keep_best, metric_for_best_model="f1",
        greater_is_better=True, report_to=[],
        fp16=bool(config.get("fp16", False) and torch.cuda.is_available()),
        save_total_limit=int(config.get("save_total_limit", 2)))
    entity_weight = float(config.get("entity_class_weight", 1.0))
    class_weights = torch.tensor(
        [1.0 if id_to_label[index] == "O" else entity_weight
         for index in range(len(id_to_label))],
        dtype=torch.float32,
    )

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False,
                         num_items_in_batch=None):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            loss = torch.nn.functional.cross_entropy(
                outputs.logits.reshape(-1, model.config.num_labels),
                labels.reshape(-1),
                weight=class_weights.to(outputs.logits.device),
                ignore_index=-100,
            )
            return (loss, outputs) if return_outputs else loss

    callbacks = (
        [EarlyStoppingCallback(config["early_stopping_patience"])]
        if keep_best else []
    )
    trainer = WeightedTrainer(model=model, args=args, train_dataset=train_ds, eval_dataset=val_ds,
                      data_collator=DataCollatorForTokenClassification(tokenizer),
                      compute_metrics=compute_metrics,
                      callbacks=callbacks)
    result = trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    # load_best_model_at_end has restored the checkpoint selected only from the
    # validation split. Evaluate the untouched test split exactly once here.
    test_metrics = (
        trainer.evaluate(test_ds, metric_key_prefix="test")
        if test_ds is not None
        else {}
    )
    save_names = ("best", "last") if config.get("save_last", True) else ("best",)
    for name in save_names:
        target = out / name; target.mkdir(parents=True, exist_ok=True)
        trainer.save_model(target); tokenizer.save_pretrained(target)
        (target / "label_map.json").write_text(json.dumps(label_map, indent=2), encoding="utf-8")
        shutil.copy2(config_path, target / "stage2.yaml")
    history = {"train_runtime": result.metrics.get("train_runtime"), "train_loss": result.metrics.get("train_loss"),
               "wall_time_seconds": time.time() - started, "train_chunks": len(train_ds),
               "validation_chunks": len(val_ds), "max_steps": max_steps,
               "test_chunks": len(test_ds) if test_ds is not None else 0,
               "test_metrics": test_metrics,
               "freeze_base": freeze_base,
               "resumed_from_checkpoint": resume_from_checkpoint,
               "best_model_checkpoint": trainer.state.best_model_checkpoint,
               "best_validation_f1": trainer.state.best_metric,
               "negative_chunk_ratio": config.get("negative_chunk_ratio"),
               "entity_class_weight": entity_weight}
    (out / "training_history.json").write_text(json.dumps({"summary": history, "log_history": trainer.state.log_history}, indent=2), encoding="utf-8")
    return history


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-dir", default="artifacts/dataset"); p.add_argument("--output-dir", default="models/phobert_legal_ner")
    p.add_argument("--config", default="configs/stage2.yaml"); p.add_argument("--max-steps", type=int, default=-1)
    p.add_argument("--limit", type=int)
    p.add_argument("--freeze-base", action="store_true",
                   help="Smoke-test fallback for memory-constrained CPU hosts; not full fine-tuning")
    p.add_argument("--resume-from-checkpoint",
                   help="Trainer checkpoint directory whose optimizer/scheduler state should be resumed")
    a = p.parse_args(); print(json.dumps(train(
        a.dataset_dir, a.output_dir, a.config, a.max_steps, a.limit,
        a.freeze_base, a.resume_from_checkpoint), indent=2))
if __name__ == "__main__": main()
