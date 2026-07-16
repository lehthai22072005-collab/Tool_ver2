from pathlib import Path
from loguru import logger
from scraper.detail_scraper import VBDocument


def convert_to_docx(vb: VBDocument, out_dir: Path) -> Path:
    try:
        from docx import Document
        from docx.shared import Pt
        from htmldocx import HtmlToDocx
    except ImportError as exc:
        raise RuntimeError("Missing dependency python-docx or htmldocx. Install it with: pip install python-docx htmldocx") from exc

    file_path = out_dir / "noi_dung.docx"
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(13)

    doc.add_heading(vb.title or vb.doc_number or "Văn bản", level=1)
    
    # Init HtmlToDocx
    parser = HtmlToDocx()

    # Ghi nội dung văn bản
    doc.add_heading("Nội dung văn bản", level=2)
    
    if getattr(vb, "content_html", ""):
        html_str = vb.content_html
        
        # htmldocx has some issues with raw body without wrapping, so we wrap it
        if not html_str.strip().startswith("<"):
            html_str = f"<div>{html_str}</div>"
        
        try:
            parser.add_html_to_document(html_str, doc)
        except Exception as e:
            logger.error(f"Error converting HTML to DOCX: {e}")
            # Fallback to plain text if HTML parsing fails completely
            for line in vb.full_text.splitlines():
                if line.strip():
                    doc.add_paragraph(line.strip())
    else:
        # Fallback to older logic if no HTML content is found
        if vb.articles:
            for article in vb.articles:
                doc.add_heading(article.get("title", ""), level=3)
                for line in article.get("content", "").splitlines():
                    if line.strip():
                        doc.add_paragraph(line.strip())
        else:
            for line in vb.full_text.splitlines():
                if line.strip():
                    doc.add_paragraph(line.strip())

    doc.save(str(file_path))
    logger.info(f"Đã lưu DOCX nội dung: {file_path}")
    return file_path