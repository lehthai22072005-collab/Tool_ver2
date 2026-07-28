from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
import yaml

from .config import load_config
from .dataset_builder import build_dataset
from .evaluate import evaluate
from .infer import run_inference
from .inventory import inventory
from .pairing import pair_documents
from .schema_analyzer import analyze_schema
from .train import train
from .validate_outputs import validate_outputs


def environment_report(path="reports/environment.txt") -> None:
    packages = {}
    for name in ("torch", "transformers", "numpy", "pandas", "python-docx", "jsonschema"):
        try:
            from importlib.metadata import version
            packages[name] = version(name)
        except Exception: packages[name] = "not installed"
    try:
        import torch
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
        cuda = str(torch.version.cuda)
    except Exception: gpu, cuda = "none", "none"
    text = json.dumps({"python": sys.version, "platform": platform.platform(),
        "processor": platform.processor(), "gpu": gpu, "cuda": cuda, "packages": packages}, indent=2)
    Path(path).parent.mkdir(parents=True, exist_ok=True); Path(path).write_text(text, encoding="utf-8")


def run(args) -> dict:
    Path(args.work_dir).resolve()
    for directory in ("artifacts", "cache", "models", "outputs", "reports", "configs"):
        Path(directory).mkdir(exist_ok=True)
    environment_report()
    summary = {"started": time.time(), "status": "running"}
    inventory_path = Path("reports/data_inventory.json")
    if inventory_path.exists() and not args.force:
        summary["inventory"] = json.loads(inventory_path.read_text(encoding="utf-8"))["summary"]
    else:
        summary["inventory"] = inventory(args.data_dir)
    pairing_path = Path("reports/pairing_report.csv")
    if pairing_path.exists() and not args.force:
        with pairing_path.open(encoding="utf-8-sig", newline="") as f:
            pairs = list(csv.DictReader(f))
    else:
        pairs = pair_documents(args.data_dir)
    summary["pairing"] = {"total": len(pairs), "paired": sum(p["status"]=="paired" for p in pairs)}
    schema_path = Path("configs/entity_schema.json")
    schema_manifest_path = Path("reports/schema_analysis_manifest.json")
    schema_resumable = False
    if schema_manifest_path.exists():
        schema_manifest = json.loads(schema_manifest_path.read_text(encoding="utf-8"))
        schema_resumable = schema_manifest.get("sample_limit") == args.limit
    schema = (json.loads(schema_path.read_text(encoding="utf-8"))
              if schema_path.exists() and schema_resumable and not args.force
              else analyze_schema(pairs, sample_limit=args.limit))
    config = load_config()
    runtime_config = "configs/stage2.yaml"
    if args.model_name != config["model_name"]:
        config["model_name"] = args.model_name
        runtime_config = "reports/stage2_runtime.yaml"
        Path(runtime_config).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    dataset_manifest_path = Path("artifacts/dataset/manifest.json")
    dataset_resumable = False
    if dataset_manifest_path.exists():
        dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
        dataset_resumable = dataset_manifest.get("limit") == args.limit
    if Path("artifacts/dataset/test.jsonl").exists() and dataset_resumable and not args.force:
        summary["dataset"] = {"status": "resumed_existing"}
    else:
        summary["dataset"] = build_dataset(pairs, schema, seed=config["seed"],
           ratios=(config["train_ratio"],config["validation_ratio"],config["test_ratio"]), limit=args.limit)
    checkpoint = Path("models/phobert_legal_ner/best")
    training_history_path = Path("models/phobert_legal_ner/training_history.json")
    smoke_checkpoint = False
    if training_history_path.exists():
        history = json.loads(training_history_path.read_text(encoding="utf-8"))
        smoke_checkpoint = bool(history.get("summary", {}).get("freeze_base"))
    if args.auto_train and (args.force or not checkpoint.exists() or (smoke_checkpoint and args.limit is None)):
        summary["training"] = train(config_path=runtime_config, max_steps=args.max_steps, limit=args.limit)
    elif checkpoint.exists():
        summary["training"] = {"status": "resumed_existing", "checkpoint": str(checkpoint)}
    if args.run_inference:
        if not checkpoint.exists(): raise RuntimeError("Best checkpoint does not exist")
        summary["inference"] = run_inference([args.data_dir], str(checkpoint), config_path=runtime_config)
    if args.run_evaluation:
        summary["evaluation"] = evaluate("outputs/entities", "artifacts/dataset/test.jsonl")
    if args.validate_outputs:
        summary["validation"] = validate_outputs("outputs/entities", args.data_dir, "reports/output_validation.json")
    summary.update(status="complete", elapsed_seconds=time.time()-summary["started"])
    Path("reports/stage2_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    p=argparse.ArgumentParser(); p.add_argument("--data-dir",required=True); p.add_argument("--work-dir",default=".")
    p.add_argument("--model-name",default="vinai/phobert-base")
    p.add_argument("--auto-train",action="store_true"); p.add_argument("--run-inference",action="store_true")
    p.add_argument("--run-evaluation",action="store_true"); p.add_argument("--validate-outputs",action="store_true")
    p.add_argument("--force",action="store_true"); p.add_argument("--limit",type=int,
        help="Development/smoke limit; omit for the complete dataset")
    p.add_argument("--max-steps",type=int,default=-1)
    a=p.parse_args(); print(json.dumps(run(a),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
