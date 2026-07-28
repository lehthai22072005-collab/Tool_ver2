from __future__ import annotations


def decode_bio(predictions: list[dict]) -> list[dict]:
    entities, active = [], None
    for token in sorted(predictions, key=lambda x: (x["start_char"], x["end_char"])):
        label = token["label"]
        if label == "O" or label.startswith("B-") or (label.startswith("I-") and
                (active is None or active["label"] != label[2:] or token["start_char"] > active["end_char"] + 1)):
            if active:
                entities.append(active); active = None
        if label.startswith(("B-", "I-")):
            base = label[2:]
            if active is None:
                active = {"label": base, "start_char": token["start_char"], "end_char": token["end_char"],
                          "confidences": [token["confidence"]], "chunk_ids": [token["chunk_id"]]}
            elif active["label"] == base:
                active["end_char"] = max(active["end_char"], token["end_char"])
                active["confidences"].append(token["confidence"]); active["chunk_ids"].append(token["chunk_id"])
    if active: entities.append(active)
    return entities


def merge_entities(entities: list[dict]) -> list[dict]:
    merged = {}
    for entity in entities:
        key = (entity["label"], entity["start_char"], entity["end_char"])
        if key not in merged:
            merged[key] = entity
        else:
            merged[key]["confidences"].extend(entity["confidences"])
            merged[key]["chunk_ids"].extend(entity["chunk_ids"])
    return list(merged.values())
