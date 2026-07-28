from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
from collections import Counter, defaultdict
from pathlib import Path


def _kind(path: Path) -> str:
    name = path.name.casefold()
    if path.suffix.casefold() in {".doc", ".docx"}:
        return "word"
    if name == "thuoc_tinh.json":
        return "attribute_json"
    if name == "luoc_do.json":
        return "schema_json"
    if path.suffix.casefold() == ".json":
        return "other_json"
    return "other"


def inventory(data_dir: str | Path, reports_dir: str | Path = "reports") -> dict:
    root, reports = Path(data_dir).resolve(), Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    rows, issues, names = [], [], defaultdict(list)
    counts, sizes = Counter(), Counter()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        kind = _kind(path)
        readable, error = True, ""
        if path.suffix.casefold() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                readable, error = False, str(exc)
        stat = path.stat()
        row = {"path": str(path), "relative_path": str(path.relative_to(root)),
               "name": path.name, "extension": path.suffix.casefold(), "kind": kind,
               "size_bytes": stat.st_size, "encoding": "utf-8-sig" if path.suffix.casefold() == ".json" else "binary",
               "readable": readable, "error": error}
        rows.append(row); counts[kind] += 1; sizes[kind] += stat.st_size
        names[path.name.casefold()].append(str(path))
        if not readable:
            issues.append({"severity": "error", "issue": "unreadable_file", "path": str(path), "detail": error})
    duplicates = {name: paths for name, paths in names.items() if len(paths) > 1}
    summary = {
        "data_dir": str(root), "total_files": len(rows), "counts_by_kind": dict(counts),
        "sizes_by_kind": dict(sizes), "unreadable_files": sum(not r["readable"] for r in rows),
        "duplicate_basenames": len(duplicates),
    }
    (reports / "data_inventory.json").write_text(
        json.dumps({"summary": summary, "duplicate_names": duplicates}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    _write_csv(reports / "data_inventory.csv", rows)
    _write_csv(reports / "data_quality_issues.csv", issues,
               ["severity", "issue", "path", "detail"])
    return summary


def _write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if fields:
            writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    print(json.dumps(inventory(args.data_dir, args.reports_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
