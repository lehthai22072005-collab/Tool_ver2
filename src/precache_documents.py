from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .word_reader import cache_document, extract_document, sha256_file


def _cache_pair(pair: dict) -> tuple[bool, str]:
    try:
        target = Path("cache/extracted_documents") / f"{pair['document_id']}.json"
        source = Path(pair["word_file"])
        if target.exists():
            cached = json.loads(target.read_text(encoding="utf-8"))
            if cached.get("source_sha256") == sha256_file(source):
                return True, "cached"
        document = extract_document(source, pair["document_id"])
        cache_document(document, "cache/extracted_documents")
        return True, "extracted"
    except Exception as exc:
        return False, f"{pair.get('document_id', '')}: {exc}"


def precache(pairing_report: str, limit: int, workers: int = 2) -> dict:
    with Path(pairing_report).open(encoding="utf-8-sig", newline="") as stream:
        pairs = [row for row in csv.DictReader(stream) if row["status"] == "paired"]
    if limit and len(pairs) > limit:
        step = len(pairs) / limit
        pairs = [pairs[int(index * step)] for index in range(limit)]
    completed = cached = extracted = 0
    errors: list[str] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for ok, status in executor.map(_cache_pair, pairs, chunksize=8):
            completed += 1
            if ok and status == "cached":
                cached += 1
            elif ok:
                extracted += 1
            else:
                errors.append(status)
            if completed % 250 == 0:
                print(json.dumps({"completed": completed, "total": len(pairs),
                                  "cached": cached, "extracted": extracted,
                                  "errors": len(errors)}), flush=True)
    return {"completed": completed, "total": len(pairs), "cached": cached,
            "extracted": extracted, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairing-report", default="reports/pairing_report.csv")
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(precache(args.pairing_report, args.limit, args.workers),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
