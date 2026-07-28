from __future__ import annotations

import re
from datetime import datetime

from .text_normalization import normalize_text


def value_variants(value: object) -> list[str]:
    value = normalize_text(str(value))
    variants = [value]
    # A relation title can be long while the Word document cites only its
    # legal type and number, e.g. "Nghị định số 19/2018/NĐ-CP".
    legal_reference = re.match(r"^(.+?\bsố\s+\S+)", value, flags=re.IGNORECASE)
    if legal_reference:
        variants.append(legal_reference.group(1).rstrip(".,;:"))
    try:
        date = datetime.strptime(value, "%Y-%m-%d")
        variants.extend([
            f"{date.day:02d}/{date.month:02d}/{date.year}",
            f"{date.day}/{date.month}/{date.year}",
            f"ngày {date.day} tháng {date.month} năm {date.year}",
        ])
    except ValueError:
        pass
    compact = re.sub(r"\s*([/-])\s*", r"\1", value)
    variants.extend([compact, compact.replace("/", "-"), compact.replace("-", "/")])
    return list(dict.fromkeys(v for v in variants if v and v != "--"))


def find_spans(text: str, value: object, label: str) -> list[dict]:
    matches: dict[tuple[int, int], dict] = {}
    folded = text.casefold()
    for variant in value_variants(value):
        needle = variant.casefold()
        start = 0
        while needle and (pos := folded.find(needle, start)) >= 0:
            end = pos + len(variant)
            matches[(pos, end)] = {"start_char": pos, "end_char": end,
                "text": text[pos:end], "label": label, "match_method": "exact_casefold",
                "match_score": 100.0, "ambiguous": False}
            start = pos + max(len(variant), 1)
    return sorted(matches.values(), key=lambda x: (x["start_char"], x["end_char"]))


def resolve_overlaps(spans: list[dict]) -> tuple[list[dict], list[dict]]:
    accepted, rejected = [], []
    for span in sorted(spans, key=lambda x: (x["start_char"], -(x["end_char"] - x["start_char"]), x["label"])):
        conflict = next((x for x in accepted if span["start_char"] < x["end_char"] and x["start_char"] < span["end_char"]), None)
        if conflict:
            span = {**span, "rejection_reason": f"overlap_with_{conflict['label']}"}
            rejected.append(span)
        else:
            accepted.append(span)
    return sorted(accepted, key=lambda x: x["start_char"]), rejected
