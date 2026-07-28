from __future__ import annotations

import csv
import json
from pathlib import Path


def _item_id(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return str(data.get("metadata", {}).get("item_id")
                   or data.get("current_document", {}).get("item_id") or "")
    except Exception:
        return ""


def pair_documents(data_dir: str | Path, reports_dir: str | Path = "reports") -> list[dict]:
    root, reports = Path(data_dir).resolve(), Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    rows, unmatched = [], []
    for directory in sorted(p for p in root.rglob("*") if p.is_dir()):
        words = sorted([p for p in directory.iterdir() if p.is_file() and p.suffix.casefold() in {".doc", ".docx"}],
                       key=lambda p: (p.suffix.casefold() != ".docx", p.name))
        attrs = directory / "thuoc_tinh.json"
        schemas = directory / "luoc_do.json"
        if not words and not attrs.exists() and not schemas.exists():
            continue
        doc_id = _item_id(attrs) if attrs.exists() else (_item_id(schemas) if schemas.exists() else "")
        method = "shared_item_id_and_directory" if doc_id else "document_directory"
        if not doc_id:
            doc_id = directory.name
        if words:
            for index, word in enumerate(words):
                effective_id = doc_id if len(words) == 1 else f"{doc_id}__{index + 1}"
                status = "paired" if attrs.exists() and schemas.exists() else "partial"
                row = {"document_id": effective_id, "word_file": str(word),
                       "attribute_json": str(attrs) if attrs.exists() else "",
                       "schema_json": str(schemas) if schemas.exists() else "",
                       "pairing_method": method, "pairing_confidence": 1.0 if method.startswith("shared") else 0.8,
                       "status": status, "error_message": ""}
                rows.append(row)
                if status != "paired":
                    unmatched.append({**row, "reason": "missing_json_counterpart"})
        else:
            row = {"document_id": doc_id, "word_file": "",
                   "attribute_json": str(attrs) if attrs.exists() else "",
                   "schema_json": str(schemas) if schemas.exists() else "",
                   "pairing_method": method, "pairing_confidence": 0.0,
                   "status": "unmatched", "error_message": "No Word file in document directory"}
            rows.append(row); unmatched.append({**row, "reason": "missing_word"})
    fields = ["document_id", "word_file", "attribute_json", "schema_json",
              "pairing_method", "pairing_confidence", "status", "error_message"]
    _csv(reports / "pairing_report.csv", rows, fields)
    _csv(reports / "unmatched_files.csv", unmatched, fields + ["reason"])
    return rows


def _csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
