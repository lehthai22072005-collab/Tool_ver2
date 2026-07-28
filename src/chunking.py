from __future__ import annotations

import re


def make_chunks(text: str, tokenizer, max_length: int, stride: int) -> list[dict]:
    if not getattr(tokenizer, "is_fast", False):
        return _slow_tokenizer_chunks(text, tokenizer, max_length, stride)
    encoded = tokenizer(text, add_special_tokens=True, max_length=max_length,
        stride=stride, truncation=True, return_overflowing_tokens=True,
        return_offsets_mapping=True)
    chunks = []
    for i, input_ids in enumerate(encoded["input_ids"]):
        offsets = encoded["offset_mapping"][i]
        non_special = [(a, b) for a, b in offsets if b > a]
        chunks.append({"chunk_id": f"c{i:05d}", "input_ids": input_ids,
                       "attention_mask": encoded["attention_mask"][i], "offset_mapping": offsets,
                       "start_char": non_special[0][0] if non_special else 0,
                       "end_char": non_special[-1][1] if non_special else 0})
    return chunks


def _slow_tokenizer_chunks(text: str, tokenizer, max_length: int, stride: int) -> list[dict]:
    """Create offset-aware chunks for PhoBERT's Python tokenizer.

    Every BPE piece maps to its containing whitespace token. This keeps legal
    entity spans reversible without pretending the slow tokenizer exposes
    character offsets.
    """
    token_ids, offsets = [], []
    unknown = tokenizer.unk_token_id
    for match in re.finditer(r"\S+", text):
        pieces = tokenizer.tokenize(match.group())
        ids = tokenizer.convert_tokens_to_ids(pieces)
        token_ids.extend(unknown if value is None else value for value in ids)
        offsets.extend([(match.start(), match.end())] * len(ids))
    specials = tokenizer.num_special_tokens_to_add(pair=False)
    capacity = max_length - specials
    if capacity <= 0 or stride >= capacity:
        raise ValueError("max_length must exceed special tokens and stride")
    step = capacity - stride
    chunks = []
    for chunk_i, start in enumerate(range(0, max(len(token_ids), 1), step)):
        ids = token_ids[start:start+capacity]; local_offsets = offsets[start:start+capacity]
        input_ids = tokenizer.build_inputs_with_special_tokens(ids)
        special_mask = tokenizer.get_special_tokens_mask(ids, already_has_special_tokens=False)
        offset_iter = iter(local_offsets)
        mapped = [(0, 0) if special else next(offset_iter) for special in special_mask]
        non_special = [x for x in mapped if x[1] > x[0]]
        chunks.append({"chunk_id": f"c{chunk_i:05d}", "input_ids": input_ids,
            "attention_mask": [1] * len(input_ids), "offset_mapping": mapped,
            "start_char": non_special[0][0] if non_special else 0,
            "end_char": non_special[-1][1] if non_special else 0})
        if start + capacity >= len(token_ids):
            break
    return chunks
