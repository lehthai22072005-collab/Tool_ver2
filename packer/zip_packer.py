import zipfile
from pathlib import Path

from loguru import logger

from exporter.common import safe_filename


def pack_document(
    doc_number: str,
    docx_path: Path | None,
    json_path: Path | None,
    ner_path: Path | None,
    output_dir: str,
) -> Path:
    out_dir = Path(output_dir) / "zip"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_num = safe_filename(doc_number)
    zip_path = out_dir / f"{safe_num}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in [docx_path, json_path, ner_path]:
            if not path or not Path(path).exists():
                continue
            arcname = f"{safe_num}/{Path(path).name}"
            zip_file.write(path, arcname=arcname)
            logger.debug(f"Packed {arcname}")

    logger.info(f"ZIP saved: {zip_path}")
    return zip_path
