from pathlib import Path

from src.infer import discover_inputs, document_id_for_input


def test_discover_inputs_keeps_symlink_parent_as_document_id(tmp_path):
    source_dir = tmp_path / "original"
    source_dir.mkdir()
    source = source_dir / "noi_dung.docx"
    source.write_bytes(b"test")

    selected_dir = tmp_path / "4058"
    selected_dir.mkdir()
    selected = selected_dir / "source.docx"
    selected.symlink_to(source)

    paths = discover_inputs([str(tmp_path)])

    assert paths == [selected.absolute()]
    assert document_id_for_input(paths[0]) == "4058"


def test_uploaded_word_uses_filename_as_document_id(tmp_path):
    uploaded = tmp_path / "quyet_dinh_10.docx"
    uploaded.write_bytes(b"test")

    assert document_id_for_input(uploaded) == "quyet_dinh_10"
