from src.word_reader import extract_document


def test_reads_paragraphs_and_table_in_order(sample_docx):
    result = extract_document(sample_docx, "x")
    assert result["normalized_text"]
    assert result["normalized_text"].index("QUYẾT ĐỊNH") < result["normalized_text"].index("Ngày ban hành")
    for block in result["blocks"]:
        assert result["normalized_text"][block["start_char"]:block["end_char"]] == block["text"]


def test_repeat_is_deterministic(sample_docx):
    assert extract_document(sample_docx, "x") == extract_document(sample_docx, "x")
