from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

from .chunking import make_chunks
from .config import config_hash, load_config
from .model import load_model, set_seed
from .postprocess import decode_bio, merge_entities
from .word_reader import extract_document


RELATION_TYPE_PATTERN = re.compile(
    r"\b(?:bản dịch|căn cứ ban hành|văn bản (?:được )?(?:dẫn chiếu|đính chính|"
    r"thay thế|giải thích|sửa đổi(?:,? bổ sung)?|hợp nhất))\b",
    flags=re.IGNORECASE,
)


def discover_inputs(inputs: list[str]) -> list[Path]:
    found: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            found.extend(p for p in path.rglob("*") if p.suffix.casefold() in {".doc", ".docx"})
        elif path.suffix.casefold() in {".doc", ".docx"}:
            found.append(path)
    # Keep the selected path (and therefore its dataset parent/document ID) even
    # when it is a symlink.  Deduplicate by the resolved source file.
    unique: dict[Path, Path] = {}
    for path in sorted(found):
        unique.setdefault(path.resolve(), path.absolute())
    return list(unique.values())


def document_id_for_input(path: Path) -> str:
    if path.stem.casefold() in {"source", "noi_dung"}:
        return path.parent.name
    return path.stem


def infer_document(path: Path, tokenizer, model, config: dict, checkpoint: str,
                   document_id: str | None = None) -> dict:
    import torch
    started = time.time()
    document = extract_document(path, document_id or document_id_for_input(path))
    chunks = make_chunks(document["normalized_text"], tokenizer, config["max_length"], config["stride"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device); model.eval(); predictions = []
    with torch.inference_mode():
        for chunk in chunks:
            ids = torch.tensor([chunk["input_ids"]], device=device)
            mask = torch.tensor([chunk["attention_mask"]], device=device)
            probabilities = model(input_ids=ids, attention_mask=mask).logits.softmax(-1)[0]
            scores, labels = probabilities.max(-1)
            for (start, end), score, label_id in zip(chunk["offset_mapping"], scores.tolist(), labels.tolist()):
                label = model.config.id2label.get(label_id, model.config.id2label.get(str(label_id), "O"))
                if end > start and (label == "O" or score >= config["confidence_threshold"]):
                    predictions.append({"start_char": start, "end_char": end, "label": label,
                                        "confidence": score, "chunk_id": chunk["chunk_id"]})
    decoded_per_chunk = []
    for chunk_id in sorted({item["chunk_id"] for item in predictions}):
        decoded_per_chunk.extend(decode_bio([item for item in predictions if item["chunk_id"] == chunk_id]))
    decoded = merge_entities(decoded_per_chunk)
    # Relation-type phrases are very sparse in the 500-document training set.
    # Keep PhoBERT as the primary extractor, but add exact, high-precision legal
    # phrases so a rare relation is not silently omitted from luocdo output.
    if "B-LOAI_QUAN_HE_VAN_BAN" in model.config.label2id:
        for match in RELATION_TYPE_PATTERN.finditer(document["normalized_text"]):
            decoded.append({
                "start_char": match.start(),
                "end_char": match.end(),
                "label": "LOAI_QUAN_HE_VAN_BAN",
                "confidences": [1.0],
                "chunk_ids": ["rule:relation_type"],
            })
    ranked = sorted(decoded, key=lambda e: (
        -(sum(e["confidences"]) / len(e["confidences"])),
        -(e["end_char"] - e["start_char"]), e["start_char"]))
    selected = []
    for candidate in ranked:
        if not any(candidate["start_char"] < other["end_char"] and
                   other["start_char"] < candidate["end_char"] for other in selected):
            selected.append(candidate)
    decoded = sorted(selected, key=lambda e: (e["start_char"], e["end_char"]))
    entities = []
    for i, entity in enumerate(decoded):
        start, end = entity["start_char"], entity["end_char"]
        block = next((b for b in document["blocks"] if b["start_char"] <= start < b["end_char"]), None)
        text = document["normalized_text"][start:end]
        rule_source = "rule:relation_type" in entity["chunk_ids"]
        entities.append({"entity_id": f"{document['document_id']}:e{i:06d}", "label": entity["label"],
                         "text": text, "normalized_text": text, "start_char": start, "end_char": end,
                         "paragraph_index": block["paragraph_index"] if block else None,
                         "block_id": block["block_id"] if block else None,
                         "confidence": sum(entity["confidences"]) / len(entity["confidences"]),
                         "chunk_ids": sorted(set(entity["chunk_ids"])),
                         "source": "relation_rule" if rule_source else "phobert"})
    warning = ["zero_entities"] if not entities else []
    return {"schema_version": "1.0", "document_id": document["document_id"],
            "source_file": str(path), "source_sha256": document["source_sha256"],
            "text_length": len(document["normalized_text"]),
            "model": {"name": config["model_name"], "checkpoint": checkpoint,
                      "label_map": model.config.label2id, "config_hash": config_hash(config)},
            "processing": {"word_extraction_method": document["extraction_method"],
                "normalization_version": config["normalization_version"],
                "word_segmentation": config["word_segmentation"], "max_length": config["max_length"],
                "stride": config["stride"], "num_chunks": len(chunks),
                "processing_time_seconds": time.time() - started},
            "entities": entities, "warnings": warning, "errors": []}


def run_inference(inputs: list[str], checkpoint: str, output="outputs/entities",
                  config_path="configs/stage2.yaml") -> dict:
    config = load_config(config_path); set_seed(config["seed"])
    tokenizer, model = load_model(checkpoint)
    paths, out = discover_inputs(inputs), Path(output); out.mkdir(parents=True, exist_ok=True)
    results, failures = [], []
    for path in paths:
        try:
            result = infer_document(path, tokenizer, model, config, checkpoint)
            target = out / f"{result['document_id']}.json"
            if target.exists():
                target = out / f"{result['document_id']}_{result['source_sha256'][:8]}.json"
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(result)
        except Exception as exc:
            failures.append({"source_file": str(path), "error": str(exc)})
    parent = out.parent
    with (parent / "entities.jsonl").open("w", encoding="utf-8") as f:
        for row in results: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    entity_rows = [{"document_id": d["document_id"], "source_file": d["source_file"], **e,
                    "chunk_ids": "|".join(e["chunk_ids"])} for d in results for e in d["entities"]]
    _csv(parent / "entities.csv", entity_rows, ["document_id", "source_file", "entity_id", "label", "text",
         "normalized_text", "start_char", "end_char", "paragraph_index", "confidence", "chunk_ids"])
    summaries = []
    for d in results:
        counts = Counter(e["label"] for e in d["entities"])
        summaries.append({"document_id": d["document_id"], "source_file": d["source_file"],
            "entity_count": len(d["entities"]), "labels": json.dumps(counts, ensure_ascii=False),
            "unique_normalized_values": len({e["normalized_text"].casefold() for e in d["entities"]}),
            "confidence_mean": sum(e["confidence"] for e in d["entities"]) / max(len(d["entities"]), 1),
            "confidence_min": min((e["confidence"] for e in d["entities"]), default=0),
            "confidence_max": max((e["confidence"] for e in d["entities"]), default=0)})
    _csv(parent / "entity_summary.csv", summaries)
    _csv(parent / "processing_failures.csv", failures, ["source_file", "error"])
    return {"inputs": len(paths), "success": len(results), "failures": len(failures),
            "entities": sum(len(d["entities"]) for d in results)}


def _csv(path, rows, fields=None):
    fields = fields or (list(rows[0]) if rows else ["document_id"])
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def main():
    p = argparse.ArgumentParser(); p.add_argument("--input", nargs="+", required=True)
    p.add_argument("--model", required=True); p.add_argument("--output", default="outputs/entities")
    p.add_argument("--config", default="configs/stage2.yaml")
    a = p.parse_args(); print(json.dumps(run_inference(a.input, a.model, a.output, a.config), indent=2))
if __name__ == "__main__": main()
