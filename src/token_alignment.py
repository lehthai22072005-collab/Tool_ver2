from __future__ import annotations


def align_bio(offsets: list[tuple[int, int]], entities: list[dict], label_map: dict[str, int]) -> list[int]:
    labels = []
    seen: set[tuple[int, int, str]] = set()
    for start, end in offsets:
        if end <= start:
            labels.append(-100); continue
        entity = next((e for e in entities if start < e["end_char"] and e["start_char"] < end), None)
        if entity is None:
            labels.append(label_map["O"]); continue
        key = (entity["start_char"], entity["end_char"], entity["label"])
        prefix = "I-" if key in seen else "B-"
        seen.add(key)
        labels.append(label_map[prefix + entity["label"]])
    return labels
