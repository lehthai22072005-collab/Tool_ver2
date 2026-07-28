from __future__ import annotations


def normalized_span_to_raw(mapping: list[int], start: int, end: int) -> tuple[int, int]:
    if not (0 <= start < end <= len(mapping)):
        raise ValueError(f"Invalid normalized span [{start}, {end}) for mapping of {len(mapping)}")
    return mapping[start], mapping[end - 1] + 1


def find_block(blocks: list[dict], start: int, end: int | None = None) -> dict | None:
    end = start + 1 if end is None else end
    return next((block for block in blocks
                 if block["start_char"] <= start and end <= block["end_char"]), None)
