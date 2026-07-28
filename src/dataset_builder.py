from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from .label_builder import find_spans, resolve_overlaps
from .schema_analyzer import flatten
from .word_reader import cache_document, extract_document, sha256_file


def build_dataset(pairs: list[dict], schema: dict, output_dir="artifacts/dataset",
                  cache_dir="cache/extracted_documents", seed=42,
                  ratios=(.70, .15, .15), limit: int | None = None) -> dict:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    report_dir = Path("reports"); report_dir.mkdir(exist_ok=True)
    path_to_label = {p: label["name"] for label in schema["labels"] for p in label["source_json_paths"]}
    path_allow_multiple = {p: label["allow_multiple"] for label in schema["labels"]
                           for p in label["source_json_paths"]}
    rows, generation, ambiguous, unmatched = [], [], [], []
    usable = [p for p in pairs if p["status"] == "paired"]
    if limit and len(usable) > limit:
        step = len(usable) / limit
        usable = [usable[int(i * step)] for i in range(limit)]
    for pair in usable:
        try:
            cached_path = Path(cache_dir) / f"{pair['document_id']}.json"
            if cached_path.exists():
                doc = json.loads(cached_path.read_text(encoding="utf-8"))
                if doc.get("source_sha256") != sha256_file(Path(pair["word_file"])):
                    doc = extract_document(pair["word_file"], pair["document_id"])
                    cache_document(doc, cache_dir)
            else:
                doc = extract_document(pair["word_file"], pair["document_id"])
                cache_document(doc, cache_dir)
            attributes = {
                "attribute_json": json.loads(Path(pair["attribute_json"]).read_text(encoding="utf-8-sig")),
                "schema_json": json.loads(Path(pair["schema_json"]).read_text(encoding="utf-8-sig"))
                if pair.get("schema_json") else {},
            }
            candidates = []
            for path, value in flatten(attributes):
                if path not in path_to_label or value in (None, "", "--"):
                    continue
                spans = find_spans(doc["normalized_text"], value, path_to_label[path])
                if spans and not path_allow_multiple[path]:
                    spans = spans[:1]
                if spans:
                    candidates.extend(spans)
                    generation.append({"document_id": pair["document_id"], "json_path": path,
                        "value": str(value), "matches": len(spans), "status": "matched"})
                else:
                    unmatched.append({"document_id": pair["document_id"], "json_path": path, "value": str(value)})
            entities, rejected = resolve_overlaps(candidates)
            ambiguous.extend({"document_id": pair["document_id"], **x} for x in rejected)
            rows.append({"document_id": pair["document_id"], "source_file": pair["word_file"],
                         "source_sha256": doc["source_sha256"], "text": doc["normalized_text"],
                         "blocks": doc["blocks"], "entities": entities})
        except Exception as exc:
            generation.append({"document_id": pair["document_id"], "json_path": "",
                               "value": "", "matches": 0, "status": f"error: {exc}"})
    random.Random(seed).shuffle(rows)
    n = len(rows); n_train = int(n * ratios[0]); n_val = int(n * ratios[1])
    splits = {"train": rows[:n_train], "validation": rows[n_train:n_train+n_val],
              "test": rows[n_train+n_val:]}
    _jsonl(out / "documents.jsonl", rows)
    for name, values in splits.items():
        _jsonl(out / f"{name}.jsonl", values)
    labels = sorted({label["name"] for label in schema["labels"]})
    bio = ["O"] + [prefix + label for label in labels for prefix in ("B-", "I-")]
    (out / "label_map.json").write_text(json.dumps({label: i for i, label in enumerate(bio)}, indent=2), encoding="utf-8")
    _csv(report_dir / "label_generation_report.csv", generation)
    _csv(report_dir / "ambiguous_matches.csv", ambiguous)
    _csv(report_dir / "unmatched_ground_truth_values.csv", unmatched)
    distribution = {name: dict(Counter(e["label"] for d in docs for e in d["entities"]))
                    for name, docs in splits.items()}
    (report_dir / "dataset_distribution.json").write_text(json.dumps(distribution, ensure_ascii=False, indent=2), encoding="utf-8")
    hashes = {d["document_id"]: d["source_sha256"] for d in rows}
    leakage = any(set(x["document_id"] for x in splits[a]) & set(x["document_id"] for x in splits[b])
                  for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")))
    result = {"documents": n, "splits": {k: len(v) for k, v in splits.items()},
            "labels": labels, "leakage": leakage,
            "dataset_hash": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
            "limit": limit, "is_full_corpus": limit is None}
    (out / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _csv(path: Path, rows: list[dict]) -> None:
    fields = sorted(set().union(*(row.keys() for row in rows))) if rows else ["document_id"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
