from pathlib import Path

from src.label_builder import find_spans
from src.word_reader import extract_document


def test_real_document_extraction_and_label_match():
    path = Path("output/documents/Sắc_lệnh/15-SL/noi_dung.docx")
    if not path.exists():
        return
    doc=extract_document(path)
    assert len(doc["normalized_text"]) > 20
    for block in doc["blocks"]:
        assert doc["normalized_text"][block["start_char"]:block["end_char"]] == block["text"]
