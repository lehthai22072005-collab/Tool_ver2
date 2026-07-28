from src.label_builder import find_spans, resolve_overlaps, value_variants


def test_date_variants_and_all_occurrences():
    text = "ngày 1 tháng 2 năm 2024; lặp lại 01/02/2024"
    spans = find_spans(text, "2024-02-01", "DATE")
    assert len(spans) == 2


def test_overlap_policy_keeps_longest_at_same_start():
    accepted, rejected = resolve_overlaps([
        {"start_char":0,"end_char":3,"label":"A"},
        {"start_char":0,"end_char":5,"label":"B"}])
    assert accepted[0]["end_char"] == 5
    assert len(rejected) == 1


def test_relation_title_adds_short_legal_reference_variant():
    variants = value_variants(
        "Nghị định số 19/2018/NĐ-CP Quy định chi tiết một số điều"
    )
    assert "Nghị định số 19/2018/NĐ-CP" in variants
