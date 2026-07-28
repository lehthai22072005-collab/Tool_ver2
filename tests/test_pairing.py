import json

from src.pairing import pair_documents


def test_pairing_uses_item_id(tmp_path, sample_docx):
    directory = tmp_path / "kind" / "stem"; directory.mkdir(parents=True)
    sample_docx.rename(directory / "noi_dung.docx")
    (directory/"thuoc_tinh.json").write_text(json.dumps({"metadata":{"item_id":"42"}}))
    (directory/"luoc_do.json").write_text(json.dumps({"current_document":{"item_id":"42"}}))
    rows = pair_documents(tmp_path, tmp_path/"reports")
    assert rows[0]["document_id"] == "42"
    assert rows[0]["pairing_confidence"] == 1.0
