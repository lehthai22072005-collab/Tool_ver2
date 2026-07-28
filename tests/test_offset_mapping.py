from src.text_normalization import normalize_with_mapping
from src.offset_mapping import normalized_span_to_raw


def test_mapping_points_into_raw_text():
    raw="  luật   Việt Nam "
    normalized,mapping=normalize_with_mapping(raw)
    assert normalized=="luật Việt Nam"
    assert all(0 <= i < len(raw) for i in mapping)
    raw_start,raw_end=normalized_span_to_raw(mapping,0,4)
    assert raw[raw_start:raw_end].strip().startswith("luật")
