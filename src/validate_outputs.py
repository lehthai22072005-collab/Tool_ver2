from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .word_reader import extract_document, sha256_file


def validate_outputs(input_dir: str, source_dir: str, report: str,
                     schema_path="configs/output_schema.json") -> dict:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors, warnings, checked, source_files = [], [], 0, set()
    for path in sorted(Path(input_dir).glob("*.json")):
        checked += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for error in validator.iter_errors(data):
                errors.append({"file": str(path), "check": "json_schema", "message": error.message})
            source = Path(data["source_file"])
            source_files.add(str(source.resolve()))
            if not source.exists():
                errors.append({"file": str(path), "check": "source_exists", "message": str(source)})
                continue
            if sha256_file(source) != data["source_sha256"]:
                errors.append({"file": str(path), "check": "source_sha256", "message": "hash mismatch"})
            document = extract_document(source, data["document_id"])
            text = document["normalized_text"]
            if len(text) != data["text_length"]:
                errors.append({"file": str(path), "check": "text_length", "message": "length mismatch"})
            seen = set()
            allowed_labels = {label[2:] for label in data["model"].get("label_map", {})
                              if label.startswith(("B-", "I-"))}
            for entity in data["entities"]:
                start, end = entity["start_char"], entity["end_char"]
                if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text)):
                    errors.append({"file": str(path), "check": "offset_range", "message": str(entity)})
                    continue
                if text[start:end] != entity["text"] or entity["normalized_text"] != entity["text"]:
                    errors.append({"file": str(path), "check": "span_text", "message": entity["entity_id"]})
                key = (entity["label"], start, end)
                if entity["label"] not in allowed_labels:
                    errors.append({"file": str(path), "check": "label_map", "message": entity["label"]})
                if key in seen:
                    errors.append({"file": str(path), "check": "duplicate_entity", "message": str(key)})
                seen.add(key)
            ordered = sorted(data["entities"], key=lambda e: (e["start_char"], e["end_char"]))
            for index, left in enumerate(ordered):
                for right in ordered[index + 1:]:
                    if right["start_char"] >= left["end_char"]:
                        break
                    errors.append({"file": str(path), "check": "overlap_policy",
                                   "message": f"{left['entity_id']} overlaps {right['entity_id']}"})
            if not data["entities"]:
                warnings.append({"file": str(path), "check": "zero_entities"})
        except Exception as exc:
            errors.append({"file": str(path), "check": "read", "message": str(exc)})
    selected = {str(p.resolve()) for p in Path(source_dir).rglob("*") if p.suffix.casefold() in {".doc", ".docx"}}
    missing = selected - source_files
    if missing:
        errors.append({"file": str(source_dir), "check": "input_accounting",
                       "message": f"{len(missing)} source files do not have output"})
    result = {"valid": not errors, "files_checked": checked, "errors": errors,
              "warnings": warnings, "selected_sources": len(selected), "missing_outputs": len(missing)}
    target = Path(report); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input-dir",required=True); p.add_argument("--source-dir",required=True)
    p.add_argument("--report",default="reports/output_validation.json"); a=p.parse_args()
    result=validate_outputs(a.input_dir,a.source_dir,a.report); print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["valid"] else 1)
if __name__=="__main__": main()
