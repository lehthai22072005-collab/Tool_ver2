from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .text_normalization import normalize_match_value
from .label_builder import value_variants
from .word_reader import cache_document, extract_document, sha256_file


# `luoc_do.json` also contains API identifiers and duplicated lookup tables.
# Only relation values that can occur as spans in the Word text become labels.
SCHEMA_SPAN_LABELS = {
    "schema_json.relations[].relation_type": "LOAI_QUAN_HE_VAN_BAN",
    "schema_json.relations[].documents[].title": "VAN_BAN_LIEN_QUAN",
}


def flatten(value: object, path: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from flatten(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for child in value:
            yield from flatten(child, f"{path}[]")
    else:
        yield path, value


def analyze_schema(pairs: list[dict], reports_dir="reports", configs_dir="configs",
                   sample_limit: int | None = None) -> dict:
    stats: dict[str, dict] = defaultdict(lambda: {
        "documents": 0, "values": 0, "exact": 0, "normalized": 0,
        "types": Counter(), "length": 0, "examples": []})
    structures = Counter()
    usable = [p for p in pairs if p["word_file"] and p["attribute_json"]]
    if sample_limit and len(usable) > sample_limit:
        step = len(usable) / sample_limit
        usable = [usable[int(i * step)] for i in range(sample_limit)]
    for pair in usable:
        try:
            cached_path = Path("cache/extracted_documents") / f"{pair['document_id']}.json"
            if cached_path.exists():
                document = json.loads(cached_path.read_text(encoding="utf-8"))
                if document.get("source_sha256") != sha256_file(Path(pair["word_file"])):
                    document = extract_document(pair["word_file"], pair["document_id"])
                    cache_document(document, "cache/extracted_documents")
            else:
                document = extract_document(pair["word_file"], pair["document_id"])
                cache_document(document, "cache/extracted_documents")
            text = document["normalized_text"]
            folded_text = text.casefold()
            data = {
                "attribute_json": json.loads(Path(pair["attribute_json"]).read_text(encoding="utf-8-sig")),
                "schema_json": json.loads(Path(pair["schema_json"]).read_text(encoding="utf-8-sig"))
                if pair.get("schema_json") else {},
            }
            structures[json.dumps(_shape(data), sort_keys=True, ensure_ascii=False)] += 1
            seen = set()
            for path, value in flatten(data):
                if value is None or str(value).strip() in {"", "--"}:
                    continue
                item = stats[path]; item["values"] += 1; item["types"][type(value).__name__] += 1
                item["length"] += len(str(value)); seen.add(path)
                variants = value_variants(value)
                if any(variant in text for variant in variants):
                    item["exact"] += 1
                elif any(normalize_match_value(variant) in folded_text for variant in variants):
                    item["normalized"] += 1
                if len(item["examples"]) < 5:
                    item["examples"].append(str(value)[:200])
            for path in seen:
                stats[path]["documents"] += 1
        except Exception:
            continue
    rows, labels, metadata, ignored = [], [], [], []
    total = max(len(usable), 1)
    excluded_suffixes = ("item_id", "url_toanvan")
    for path, item in sorted(stats.items()):
        match_rate = (item["exact"] + item["normalized"]) / max(item["values"], 1)
        avg_len = item["length"] / max(item["values"], 1)
        is_scalar = set(item["types"]) <= {"str", "int", "float"}
        is_document_metadata = (path.startswith("attribute_json.metadata.")
                                or path.startswith("schema_json.current_document."))
        schema_span_candidate = (not path.startswith("schema_json.")
                                 or path.endswith("documents[].title"))
        forced_schema_label = SCHEMA_SPAN_LABELS.get(path)
        entity = ((is_scalar and match_rate >= 0.20 and avg_len <= 250
                   and not path.endswith(excluded_suffixes) and not is_document_metadata
                   and schema_span_candidate)
                  or forced_schema_label is not None)
        reason = ("relation span from luoc_do.json"
                  if forced_schema_label else
                  "scalar value occurs in document text" if entity else
                  "metadata/non-span or insufficient text match")
        row = {"json_path": path, "document_count": item["documents"],
               "document_rate": item["documents"] / total, "value_count": item["values"],
               "exact_match_rate": item["exact"] / max(item["values"], 1),
               "normalized_match_rate": item["normalized"] / max(item["values"], 1),
               "combined_match_rate": match_rate, "average_length": avg_len,
               "types": "|".join(item["types"]), "is_span_entity": entity, "reason": reason}
        rows.append(row)
        if entity:
            name = (forced_schema_label
                    or path.upper().replace(".", "_").replace("[]", ""))
            labels.append({"name": name, "source_json_paths": [path], "description": reason,
                           "is_span_entity": True,
                           "allow_multiple": path.startswith("schema_json."),
                           "allow_nested": False,
                           "normalization_rules": ["unicode_nfc", "whitespace"], "examples": item["examples"]})
        elif is_document_metadata:
            metadata.append(path)
        else:
            ignored.append(path)
    schema = {"labels": labels, "metadata_fields": metadata, "ignored_fields": ignored, "schema_version": "1.0"}
    Path(configs_dir).mkdir(parents=True, exist_ok=True)
    Path(configs_dir, "entity_schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    Path(reports_dir, "json_schema_analysis.json").write_text(
        json.dumps({"variants": [{"shape": json.loads(k), "count": v} for k, v in structures.items()],
                    "fields": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(reports_dir, "schema_analysis_manifest.json").write_text(
        json.dumps({"sample_limit": sample_limit, "documents_analyzed": len(usable),
                    "is_full_corpus": sample_limit is None}, indent=2), encoding="utf-8")
    with Path(reports_dir, "entity_label_analysis.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["json_path"])
        writer.writeheader(); writer.writerows(rows)
    return schema


def _shape(value):
    if isinstance(value, dict):
        return {k: _shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_shape(value[0])] if value else []
    return type(value).__name__
