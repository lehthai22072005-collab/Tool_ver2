from src.text_normalization import normalize_text, normalize_with_mapping


def test_normalization_is_nfc_and_deterministic():
    value = "A\u0300  \r\n  B\u00a0–\u200bC"
    assert normalize_text(value) == "À\nB -C"
    assert normalize_text(value) == normalize_text(value)


def test_mapping_length_matches():
    text, mapping = normalize_with_mapping(" a   b ")
    assert text == "a b"
    assert len(text) == len(mapping)
