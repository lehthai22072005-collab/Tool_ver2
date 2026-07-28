from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def validate_dataset(dataset_dir: str | Path) -> dict:
    root = Path(dataset_dir)
    label_map = json.loads((root / "label_map.json").read_text(encoding="utf-8"))
    split_rows: dict[str, list[dict]] = {}
    errors: list[str] = []
    distributions: dict[str, dict[str, int]] = {}

    for split in ("train", "validation", "test"):
        rows = [json.loads(line) for line in (root / f"{split}.jsonl").open(encoding="utf-8")]
        split_rows[split] = rows
        counts = Counter()
        for row in rows:
            text = row["text"]
            for entity in row["entities"]:
                label = entity["label"]
                counts[label] += 1
                if f"B-{label}" not in label_map or f"I-{label}" not in label_map:
                    errors.append(f"unknown label: {row['document_id']}:{label}")
                if text[entity["start_char"]:entity["end_char"]] != entity["text"]:
                    errors.append(f"invalid offset: {row['document_id']}:{label}")
        distributions[split] = dict(sorted(counts.items()))

    ids = {name: {row["document_id"] for row in rows} for name, rows in split_rows.items()}
    leakage = bool(
        (ids["train"] & ids["validation"])
        or (ids["train"] & ids["test"])
        or (ids["validation"] & ids["test"])
    )
    if leakage:
        errors.append("document leakage between splits")

    required_relation_labels = {"LOAI_QUAN_HE_VAN_BAN", "VAN_BAN_LIEN_QUAN"}
    missing_relation_labels = {
        split: sorted(required_relation_labels - set(distributions[split]))
        for split in distributions
    }
    for split, missing in missing_relation_labels.items():
        if missing:
            errors.append(f"{split} missing relation labels: {', '.join(missing)}")

    return {
        "valid": not errors,
        "documents": {name: len(rows) for name, rows in split_rows.items()},
        "leakage": leakage,
        "entity_distribution": distributions,
        "missing_relation_labels": missing_relation_labels,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    result = validate_dataset(args.dataset_dir)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
