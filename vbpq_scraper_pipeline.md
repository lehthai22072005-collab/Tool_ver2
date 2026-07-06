# Pipeline Cào Dữ Liệu VBPLTW — vbpl.vn/van-ban/trung-uong

> CẬP NHẬT: Site mới dùng trang danh sách `https://vbpl.vn/van-ban/trung-uong` và API gateway `https://vbpl-bientap-gateway.moj.gov.vn/api`.
> Danh sách: `POST /qtdc/public/doc/all` với `agencyLevel="TRUNG_UONG"`.
> Chi tiết/toàn văn: `GET /qtdc/public/doc/{uuid}`; toàn văn nằm ở `data.documentContent.content` dạng HTML và được chuyển sang text.
> Link mẫu: `https://vbpl.vn/van-ban/chi-tiet/thong-tu-08-2026-tt-nhnn-sua-doi-bo-sung-diem-a-khoan-4-dieu-20-thong-tu-so-22-2019-tt-nhnn-quy-dinh-cac-gioi-han-ty-le-bao-dam-an-toan-trong-hoat-dong-cua-ngan-hang-chi-nhanh-ngan-hang-nuoc-ngoai--7f147190-5009-11f1-a1c0-795b56a45f32`
> Tải riêng link mẫu: `python crawler_vbpl.py --url "https://vbpl.vn/van-ban/chi-tiet/thong-tu-08-2026-tt-nhnn-sua-doi-bo-sung-diem-a-khoan-4-dieu-20-thong-tu-so-22-2019-tt-nhnn-quy-dinh-cac-gioi-han-ty-le-bao-dam-an-toan-trong-hoat-dong-cua-ngan-hang-chi-nhanh-ngan-hang-nuoc-ngoai--7f147190-5009-11f1-a1c0-795b56a45f32"`

---


# Pipeline Cào Dữ Liệu VBPLTW — vbpl.vn/TW

> **Nguồn:** Cơ sở dữ liệu Văn bản pháp luật Trung ương tại `https://vbpl.vn/TW`  
> **Luồng:** Danh sách (phân trang) → Toàn văn + Thuộc tính → DOCX + JSON → NER BIO (ViLegalBERT) → ZIP

---

## Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Cài đặt](#2-cài-đặt)
3. [Cấu trúc URL vbpl.vn/TW](#3-cấu-trúc-url-vbplvntw)
4. [Cấu trúc thư mục dự án](#4-cấu-trúc-thư-mục-dự-án)
5. [config.py — Cấu hình tập trung](#5-configpy--cấu-hình-tập-trung)
6. [Bước 1 — Cào danh sách & tự động phân trang](#6-bước-1--cào-danh-sách--tự-động-phân-trang)
7. [Bước 2 — Cào chi tiết từng văn bản](#7-bước-2--cào-chi-tiết-từng-văn-bản)
8. [Bước 3 — Xuất DOCX](#8-bước-3--xuất-docx)
9. [Bước 4 — Xuất JSON thuộc tính](#9-bước-4--xuất-json-thuộc-tính)
10. [Bước 5 — NER với ViLegalBERT (BIO tagging)](#10-bước-5--ner-với-vilegalbert-bio-tagging)
11. [Bước 6 — Nén từng văn bản thành ZIP](#11-bước-6--nén-từng-văn-bản-thành-zip)
12. [Bước 7 — Orchestrator pipeline.py](#12-bước-7--orchestrator-pipelinepy)
13. [Sơ đồ luồng dữ liệu](#13-sơ-đồ-luồng-dữ-liệu)
14. [Lưu ý kỹ thuật & pháp lý](#14-lưu-ý-kỹ-thuật--pháp-lý)

---

## 1. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|---|---|
| Python | 3.9+ |
| Node.js | 18+ |
| npm | 8+ |
| RAM | 8 GB (16 GB nếu dùng GPU) |
| GPU (tuỳ chọn) | CUDA 11.8+ |

---

## 2. Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Cào web (vbpl.vn render phần lớn bằng server-side, dùng requests là đủ)
pip install requests beautifulsoup4 lxml playwright
playwright install chromium      # dự phòng cho các trang JS-heavy

# NLP / NER
pip install transformers torch underthesea

# Tiện ích
pip install tqdm loguru pydantic python-docx

# Tạo DOCX
npm install -g docx
```

---

## 3. Cấu trúc URL vbpl.vn/TW

| Mục đích | URL mẫu |
|---|---|
| Trang chủ VBPLTW | `https://vbpl.vn/TW/Pages/Home.aspx` |
| **Danh sách văn bản (tìm kiếm)** | `https://vbpl.vn/TW/Pages/vbpq-timkiem.aspx?TypeID=1&PageIndex=1` |
| Tìm kiếm nâng cao | `https://vbpl.vn/Pages/vbpq-timkiem.aspx` |
| **Toàn văn** | `https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=96172` |
| **Lược đồ (sơ đồ quan hệ)** | `https://vbpl.vn/tw/pages/vbpq-luocdo.aspx?ItemID=96172` |
| **Văn bản liên quan** | `https://vbpl.vn/tw/Pages/vbpq-vanbanlienquan.aspx?ItemID=96172` |

### Tham số query string trang danh sách

| Tham số | Ý nghĩa | Ví dụ |
|---|---|---|
| `TypeID` | Loại văn bản (xem bảng dưới) | `1` = Hiến pháp/Luật |
| `PageIndex` | Số trang (bắt đầu từ 1) | `PageIndex=2` |
| `Keyword` | Từ khoá tìm kiếm | `Keyword=thong+tu` |
| `DonViId` | Mã cơ quan ban hành | để trống = tất cả |

### Mã TypeID thường gặp

| TypeID | Loại văn bản |
|---|---|
| `1` | Hiến pháp / Luật / Pháp lệnh |
| `2` | Nghị định |
| `3` | Thông tư |
| `4` | Quyết định |
| `5` | Thông tư liên tịch |
| `6` | Nghị quyết |
| (để trống) | Tất cả loại |

> **Lưu ý:** Các mã này cần xác nhận lại bằng cách inspect Network tab trên trình duyệt khi lọc loại văn bản trên trang.

---

## 4. Cấu trúc thư mục dự án

```
vbpltw_pipeline/
├── config.py
├── pipeline.py                   # Orchestrator
├── scraper/
│   ├── list_scraper.py           # Cào danh sách + phân trang
│   └── detail_scraper.py         # Cào toàn văn + thuộc tính
├── exporter/
│   ├── to_docx.py
│   └── to_json.py
├── ner/
│   └── vilegalbert_ner.py
├── packer/
│   └── zip_packer.py
├── output/
│   ├── docx/
│   ├── json/
│   ├── ner/
│   └── zip/
└── logs/
```

---

## 5. config.py — Cấu hình tập trung

```python
# config.py
# ── Endpoint chính ──────────────────────────────────────────────────────────
BASE_URL     = "https://vbpl.vn"
AREA         = "TW"                          # Văn bản Trung ương
HOME_URL     = f"{BASE_URL}/{AREA}/Pages/Home.aspx"
LIST_URL     = f"{BASE_URL}/{AREA}/Pages/vbpq-timkiem.aspx"
DETAIL_URL   = f"{BASE_URL}/{AREA}/Pages/vbpq-toanvan.aspx"
RELATED_URL  = f"{BASE_URL}/{AREA}/Pages/vbpq-vanbanlienquan.aspx"

# ── Bộ lọc mặc định ─────────────────────────────────────────────────────────
# TypeID: "" = tất cả | "2" = Nghị định | "3" = Thông tư | "4" = Quyết định
DEFAULT_TYPE_ID = "3"     # Thông tư

# ── Kiểm soát tốc độ ────────────────────────────────────────────────────────
REQUEST_DELAY   = 1.5     # giây giữa các request
REQUEST_TIMEOUT = 30      # giây timeout mỗi request
MAX_RETRIES     = 3       # số lần thử lại khi lỗi

# ── Đầu ra ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = "output"

# ── HTTP Headers ─────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "Referer"        : "https://vbpl.vn/TW/Pages/Home.aspx",
}

# ── Mô hình NER ──────────────────────────────────────────────────────────────
# Tuỳ chọn:
#   "uitnlp/visobert"                      — ViSoBERT (mạnh, tốt cho pháp lý)
#   "vinai/phobert-base"                   — PhoBERT baseline
#   "/path/to/local/vilegalbert"           — Mô hình fine-tune local
NER_MODEL_NAME = "uitnlp/visobert"
NER_MAX_LENGTH = 512
NER_BATCH_SIZE = 8
```

---

## 6. Bước 1 — Cào danh sách & tự động phân trang

### `scraper/list_scraper.py`

```python
"""
Cào danh sách văn bản từ vbpl.vn/TW/Pages/vbpq-timkiem.aspx.
Tự động chuyển sang trang tiếp theo cho đến khi hết dữ liệu.

URL mẫu:
  https://vbpl.vn/TW/Pages/vbpq-timkiem.aspx?TypeID=3&PageIndex=1
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from loguru import logger
from config import LIST_URL, HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES


def _get(session: requests.Session, url: str, params: dict) -> requests.Response | None:
    """GET với retry tự động."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning(f"  Lần {attempt}/{MAX_RETRIES} thất bại: {e}")
            time.sleep(REQUEST_DELAY * attempt)
    return None


def _parse_total_pages(soup: BeautifulSoup) -> int:
    """
    Đọc tổng số trang từ thanh phân trang của vbpl.vn.

    vbpl.vn dùng pattern:
      <span>Trang 1/85</span>   hoặc   <a href="...PageIndex=85">85</a>
    """
    # Cách 1: text "Trang X/Y"
    pager_text = soup.get_text()
    m = re.search(r"Trang\s+\d+\s*/\s*(\d+)", pager_text)
    if m:
        return int(m.group(1))

    # Cách 2: link phân trang — lấy số lớn nhất
    page_links = soup.select("div.pager a, ul.pagination a, .pagerControl a")
    page_nums = []
    for a in page_links:
        pm = re.search(r"PageIndex=(\d+)", a.get("href", ""))
        if pm:
            page_nums.append(int(pm.group(1)))
        try:
            page_nums.append(int(a.get_text(strip=True)))
        except ValueError:
            pass
    return max(page_nums, default=1)


def _parse_list_page(soup: BeautifulSoup) -> list[dict]:
    """
    Trích xuất danh sách văn bản từ một trang kết quả.

    vbpl.vn/TW hiển thị dạng bảng hoặc danh sách ul.listVB / table.vbList.
    Mỗi hàng chứa: tên VB, số ký hiệu, ngày ban hành, cơ quan, trạng thái.
    Link chi tiết dạng: /TW/Pages/vbpq-toanvan.aspx?ItemID=XXXXX
    """
    items = []

    # ── Selector chính ───────────────────────────────────────────────────────
    rows = soup.select(
        "div.listVB div.item, "          # layout dạng div
        "ul.listVB li, "                 # layout dạng ul
        "table.vbList tbody tr, "        # layout dạng table
        ".search-result .result-item"   # fallback
    )

    for row in rows:
        link = row.select_one("a[href*='ItemID']")
        if not link:
            continue

        href = link.get("href", "")
        if not href.startswith("http"):
            href = "https://vbpl.vn" + href

        # Trích ItemID từ URL
        item_id_m = re.search(r"ItemID=(\d+)", href)
        item_id   = item_id_m.group(1) if item_id_m else ""

        # Lấy text từng cell (thứ tự tuỳ layout thực tế)
        cells = row.find_all(["td", "span", "div"], recursive=False)

        def cell_text(idx: int) -> str:
            return cells[idx].get_text(strip=True) if idx < len(cells) else ""

        items.append({
            "item_id"      : item_id,
            "url_toanvan"  : f"https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID={item_id}",
            "url_luocdo"   : f"https://vbpl.vn/tw/pages/vbpq-luocdo.aspx?ItemID={item_id}",
            "url_lienquan" : f"https://vbpl.vn/tw/Pages/vbpq-vanbanlienquan.aspx?ItemID={item_id}",
            "title"        : link.get_text(strip=True),
            "doc_number"   : cell_text(1),
            "doc_type"     : cell_text(2),
            "issue_date"   : cell_text(3),
            "issuer"       : cell_text(4),
            "status"       : cell_text(5),
        })

    return items


def scrape_all_pages(
    type_id  : str = "",
    keyword  : str = "",
    max_pages: int = 0,
) -> list[dict]:
    """
    Cào toàn bộ danh sách văn bản VBPLTW, tự động chuyển trang.

    Args:
        type_id  : Mã loại VB ("3" = Thông tư, "" = tất cả).
        keyword  : Từ khoá tìm kiếm.
        max_pages: Giới hạn trang. 0 = không giới hạn.

    Returns:
        list[dict] — mỗi phần tử mô tả một văn bản.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    all_items  = []
    page       = 1
    total_pages = None

    while True:
        params = {"PageIndex": page}
        if type_id:
            params["TypeID"] = type_id
        if keyword:
            params["Keyword"] = keyword

        logger.info(f"[Trang {page}{f'/{total_pages}' if total_pages else ''}] GET {LIST_URL}")
        resp = _get(session, LIST_URL, params)
        if resp is None:
            logger.error(f"Không thể tải trang {page}, dừng.")
            break

        soup  = BeautifulSoup(resp.text, "lxml")
        items = _parse_list_page(soup)

        if not items:
            logger.info("Không có văn bản ở trang này — kết thúc phân trang.")
            break

        all_items.extend(items)

        if total_pages is None:
            total_pages = _parse_total_pages(soup)
            logger.info(f"  Tổng trang phát hiện: {total_pages}")

        logger.info(f"  +{len(items)} VB | Tổng tích luỹ: {len(all_items)}")

        if page >= total_pages or (max_pages and page >= max_pages):
            logger.info("Đã cào xong tất cả trang.")
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    return all_items


if __name__ == "__main__":
    docs = scrape_all_pages(type_id="3", max_pages=3)  # thử 3 trang Thông tư
    print(f"Tổng: {len(docs)} văn bản")
```

---

## 7. Bước 2 — Cào chi tiết từng văn bản

### `scraper/detail_scraper.py`

```python
"""
Cào nội dung chi tiết từng văn bản từ vbpl.vn/TW.

Các trang cần truy cập cho mỗi ItemID:
  - /TW/Pages/vbpq-toanvan.aspx?ItemID=X   → toàn văn + bảng thuộc tính
  - /tw/Pages/vbpq-vanbanlienquan.aspx?ItemID=X → văn bản liên quan

Lưu ý: vbpl.vn dùng ASP.NET WebForms, nội dung render server-side,
        requests + BeautifulSoup là đủ (không cần Playwright).
        Nếu trang có CAPTCHA hoặc session kiểm tra, chuyển sang Playwright.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field, asdict
from loguru import logger
from config import HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class VBDocument:
    item_id        : str
    url_toanvan    : str
    title          : str
    doc_number     : str          # Số ký hiệu, vd: 13/2023/TT-BCT
    doc_type       : str          # Thông tư / Nghị định / ...
    issue_date     : str          # Ngày ban hành
    effective_date : str          # Ngày hiệu lực
    issuer         : str          # Cơ quan ban hành
    signer         : str          # Người ký
    signer_title   : str          # Chức vụ người ký
    gazette_number : str          # Số Công báo
    gazette_date   : str          # Ngày đăng Công báo
    field          : str          # Lĩnh vực
    scope          : str          # Phạm vi áp dụng
    status         : str          # Trạng thái hiệu lực
    full_text      : str          # Toàn văn
    articles       : list[dict]   # Danh sách điều khoản
    related_docs   : list[dict]   # Văn bản liên quan

    def to_dict(self) -> dict:
        return asdict(self)


# ── Helper ───────────────────────────────────────────────────────────────────

def _get(session: requests.Session, url: str) -> BeautifulSoup | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            logger.warning(f"  [{attempt}/{MAX_RETRIES}] {url}: {e}")
            time.sleep(REQUEST_DELAY * attempt)
    return None


# ── Parsers ──────────────────────────────────────────────────────────────────

# Mapping nhãn tiếng Việt → tên trường
_META_FIELD_MAP = {
    "số ký hiệu"       : "doc_number",
    "loại văn bản"     : "doc_type",
    "ngày ban hành"    : "issue_date",
    "ngày hiệu lực"    : "effective_date",
    "cơ quan ban hành" : "issuer",
    "người ký"         : "signer",
    "chức vụ"          : "signer_title",
    "số công báo"      : "gazette_number",
    "ngày công báo"    : "gazette_date",
    "lĩnh vực"         : "field",
    "phạm vi"          : "scope",
    "trạng thái"       : "status",
    "hiệu lực"         : "status",
}


def _parse_metadata(soup: BeautifulSoup) -> dict:
    """Trích bảng thuộc tính từ trang toanvan."""
    meta = {}

    # vbpl.vn hiển thị bảng thuộc tính trong div.vanbanContent hoặc table.thuoctinh
    info_block = soup.select_one(
        "table.thuoctinh, "
        "div.vanbanInfo table, "
        "#ctl00_Content_TableThongTin, "
        ".thong-tin-vb table"
    )

    if info_block:
        for row in info_block.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            key   = cells[0].get_text(strip=True).lower().rstrip(":")
            value = cells[1].get_text(separator=" ", strip=True)
            for pattern, field_name in _META_FIELD_MAP.items():
                if pattern in key:
                    meta[field_name] = value
                    break

    # Tiêu đề
    h1 = soup.select_one("h1.title-vb, .tieude, #ctl00_Content_lblTenVB, h1")
    meta["title"] = h1.get_text(strip=True) if h1 else ""

    return meta


def _parse_full_text(soup: BeautifulSoup) -> str:
    """Lấy toàn văn từ vùng nội dung chính."""
    content = soup.select_one(
        "div#toanvan, "
        "div.noidungVB, "
        "#ctl00_Content_divContent, "
        ".van-ban-content, "
        "div[class*='content']"
    )
    if content:
        return content.get_text(separator="\n", strip=True)
    return ""


def _parse_articles(full_text: str) -> list[dict]:
    """
    Phân tách từng Điều trong văn bản.
    Hỗ trợ cả "Điều 1." và "ĐIỀU 1." (viết hoa).
    """
    pattern = re.compile(
        r"((?:Điều|ĐIỀU)\s+\d+[\.\:\-]?\s*[^\n]*)\n(.*?)(?=(?:Điều|ĐIỀU)\s+\d+|$)",
        re.DOTALL
    )
    articles = []
    for m in pattern.finditer(full_text):
        header  = m.group(1).strip()
        body    = m.group(2).strip()
        num_m   = re.search(r"\d+", header)
        articles.append({
            "article_number": num_m.group(0) if num_m else "",
            "title"         : header,
            "content"       : body,
        })
    return articles


def _parse_related(soup: BeautifulSoup) -> list[dict]:
    """Lấy danh sách văn bản liên quan."""
    related = []
    for a in soup.select("div.listVBLienQuan a[href*='ItemID'], .vb-lienquan a[href*='ItemID']"):
        href    = a.get("href", "")
        item_m  = re.search(r"ItemID=(\d+)", href)
        related.append({
            "item_id": item_m.group(1) if item_m else "",
            "title"  : a.get_text(strip=True),
            "url"    : "https://vbpl.vn" + href if not href.startswith("http") else href,
        })
    return related


# ── Public API ───────────────────────────────────────────────────────────────

def scrape_document(item: dict) -> VBDocument | None:
    """
    Cào đầy đủ thông tin một văn bản.

    Args:
        item: Dict từ list_scraper (có item_id, url_toanvan, url_lienquan, ...).

    Returns:
        VBDocument hoặc None nếu lỗi.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    item_id     = item.get("item_id", "")
    url_toanvan = item.get("url_toanvan", "")
    url_lienquan= item.get("url_lienquan", "")

    # ── Trang toàn văn ───────────────────────────────────────────────────────
    soup_tv = _get(session, url_toanvan)
    if soup_tv is None:
        logger.error(f"Không tải được toàn văn ItemID={item_id}")
        return None

    meta      = _parse_metadata(soup_tv)
    full_text = _parse_full_text(soup_tv)
    articles  = _parse_articles(full_text)

    time.sleep(REQUEST_DELAY)

    # ── Trang văn bản liên quan ──────────────────────────────────────────────
    related = []
    if url_lienquan:
        soup_lq = _get(session, url_lienquan)
        if soup_lq:
            related = _parse_related(soup_lq)
        time.sleep(REQUEST_DELAY)

    return VBDocument(
        item_id        = item_id,
        url_toanvan    = url_toanvan,
        title          = meta.get("title",          item.get("title", "")),
        doc_number     = meta.get("doc_number",     item.get("doc_number", "")),
        doc_type       = meta.get("doc_type",       item.get("doc_type", "")),
        issue_date     = meta.get("issue_date",     item.get("issue_date", "")),
        effective_date = meta.get("effective_date", ""),
        issuer         = meta.get("issuer",         item.get("issuer", "")),
        signer         = meta.get("signer",         ""),
        signer_title   = meta.get("signer_title",   ""),
        gazette_number = meta.get("gazette_number", ""),
        gazette_date   = meta.get("gazette_date",   ""),
        field          = meta.get("field",          ""),
        scope          = meta.get("scope",          ""),
        status         = meta.get("status",         item.get("status", "")),
        full_text      = full_text,
        articles       = articles,
        related_docs   = related,
    )
```

---

## 8. Bước 3 — Xuất DOCX

### `exporter/to_docx.py`

```python
"""
Chuyển VBDocument → file DOCX định dạng pháp lý chuẩn.
Dùng thư viện python-docx (pip install python-docx).
"""

import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from loguru import logger
from scraper.detail_scraper import VBDocument


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name or "unknown")[:80]


def _add_info_table(doc: Document, vb: VBDocument) -> None:
    rows = [
        ("Số ký hiệu",      vb.doc_number),
        ("Loại văn bản",    vb.doc_type),
        ("Ngày ban hành",   vb.issue_date),
        ("Ngày hiệu lực",   vb.effective_date),
        ("Cơ quan ban hành",vb.issuer),
        ("Người ký",        vb.signer),
        ("Chức vụ",         vb.signer_title),
        ("Số Công báo",     vb.gazette_number),
        ("Ngày Công báo",   vb.gazette_date),
        ("Lĩnh vực",        vb.field),
        ("Trạng thái",      vb.status),
        ("Nguồn",           vb.url_toanvan),
    ]
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(rows):
        cell_label = table.cell(i, 0)
        cell_value = table.cell(i, 1)
        run_label  = cell_label.paragraphs[0].add_run(label)
        run_label.bold = True
        cell_value.paragraphs[0].add_run(value or "—")


def convert_to_docx(vb: VBDocument, output_dir: str) -> Path:
    """
    Tạo DOCX từ VBDocument.

    Cấu trúc file:
      - Tiêu đề văn bản (Heading 1)
      - Bảng thuộc tính
      - Từng Điều (Heading 3 + nội dung)
      - Văn bản liên quan (nếu có)

    Returns:
        Path đến file DOCX đã tạo.
    """
    out_path = Path(output_dir) / "docx"
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{_safe_filename(vb.doc_number)}.docx"

    doc = Document()

    # Phông mặc định phù hợp tiếng Việt
    for style_name in ("Normal",):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(13)

    # Tiêu đề
    h1 = doc.add_heading(vb.title, level=1)
    h1.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Số ký hiệu dưới tiêu đề
    p_num = doc.add_paragraph(vb.doc_number)
    p_num.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_num.runs[0].bold = True

    doc.add_paragraph()

    # Bảng thuộc tính
    doc.add_heading("THÔNG TIN VĂN BẢN", level=2)
    _add_info_table(doc, vb)
    doc.add_paragraph()

    # Nội dung
    doc.add_heading("NỘI DUNG VĂN BẢN", level=2)
    if vb.articles:
        for art in vb.articles:
            doc.add_heading(art["title"], level=3)
            for line in art["content"].split("\n"):
                line = line.strip()
                if line:
                    doc.add_paragraph(line)
    else:
        for line in vb.full_text.split("\n"):
            line = line.strip()
            if line:
                doc.add_paragraph(line)

    # Văn bản liên quan
    if vb.related_docs:
        doc.add_heading("VĂN BẢN LIÊN QUAN", level=2)
        for ref in vb.related_docs:
            doc.add_paragraph(
                f"• [{ref['doc_number'] or ref['title']}] {ref['title']}",
                style="List Bullet"
            )

    doc.save(str(file_path))
    logger.info(f"DOCX → {file_path}")
    return file_path
```

---

## 9. Bước 4 — Xuất JSON thuộc tính

### `exporter/to_json.py`

```python
"""
Lưu thuộc tính + cấu trúc điều khoản của VBDocument ra JSON.

JSON Schema (schema_version: "1.1"):
{
  "schema_version": "1.1",
  "source": "https://vbpl.vn/TW",
  "metadata": { ... },
  "articles": [ { "article_number", "title", "content" }, ... ],
  "related_docs": [ { "item_id", "title", "url" }, ... ]
}
"""

import json
import re
from pathlib import Path
from loguru import logger
from scraper.detail_scraper import VBDocument

SCHEMA_VERSION = "1.1"
SOURCE         = "https://vbpl.vn/TW"


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name or "unknown")[:80]


def convert_to_json(vb: VBDocument, output_dir: str) -> Path:
    out_path = Path(output_dir) / "json"
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{_safe_filename(vb.doc_number)}.json"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "source"        : SOURCE,
        "metadata": {
            "item_id"       : vb.item_id,
            "url_toanvan"   : vb.url_toanvan,
            "title"         : vb.title,
            "doc_number"    : vb.doc_number,
            "doc_type"      : vb.doc_type,
            "issue_date"    : vb.issue_date,
            "effective_date": vb.effective_date,
            "issuer"        : vb.issuer,
            "signer"        : vb.signer,
            "signer_title"  : vb.signer_title,
            "gazette_number": vb.gazette_number,
            "gazette_date"  : vb.gazette_date,
            "field"         : vb.field,
            "scope"         : vb.scope,
            "status"        : vb.status,
        },
        "articles"    : vb.articles,
        "related_docs": vb.related_docs,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON → {file_path}")
    return file_path
```

#### Ví dụ đầu ra JSON

```json
{
  "schema_version": "1.1",
  "source": "https://vbpl.vn/TW",
  "metadata": {
    "item_id"       : "96172",
    "url_toanvan"   : "https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=96172",
    "title"         : "Thông tư 13/2023/TT-BCT quy định về hạn ngạch thuế quan nhập khẩu muối, trứng gia cầm năm 2023",
    "doc_number"    : "13/2023/TT-BCT",
    "doc_type"      : "Thông tư",
    "issue_date"    : "01/06/2023",
    "effective_date": "15/07/2023",
    "issuer"        : "Bộ Công Thương",
    "signer"        : "Nguyễn Hồng Diên",
    "signer_title"  : "Bộ trưởng",
    "gazette_number": "571+572",
    "gazette_date"  : "20/07/2023",
    "field"         : "Xuất nhập khẩu",
    "status"        : "Còn hiệu lực"
  },
  "articles": [
    {
      "article_number": "1",
      "title": "Điều 1. Phạm vi điều chỉnh",
      "content": "Thông tư này quy định về hạn ngạch thuế quan nhập khẩu muối, trứng gia cầm năm 2023..."
    }
  ],
  "related_docs": [
    {
      "item_id": "90123",
      "title"  : "Nghị định 125/2017/NĐ-CP về biểu thuế xuất khẩu, nhập khẩu",
      "url"    : "https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=90123"
    }
  ]
}
```

---

## 10. Bước 5 — NER với ViLegalBERT (BIO tagging)

### `ner/vilegalbert_ner.py`

```python
"""
NER tiếng Việt pháp lý dùng ViSoBERT / PhoBERT.

Nhãn BIO:
  B-ORG  / I-ORG  : Cơ quan, tổ chức (Bộ Tư pháp, UBND tỉnh...)
  B-PER  / I-PER  : Cá nhân (tên người ký, người liên quan)
  B-LOC  / I-LOC  : Địa danh (Hà Nội, tỉnh Khánh Hoà...)
  B-LAW  / I-LAW  : Tên văn bản pháp luật (Thông tư 13/2023/TT-BCT...)
  B-DATE / I-DATE : Ngày tháng (01/06/2023, ngày 15 tháng 7...)
  B-NUM  / I-NUM  : Số hiệu, điều khoản (Điều 3, khoản 2...)
  O               : Không phải entity
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from loguru import logger
from config import NER_MODEL_NAME, NER_MAX_LENGTH, OUTPUT_DIR

# Label map — điều chỉnh theo mô hình cụ thể đang dùng
LABEL_MAP = {
    0: "O",
    1: "B-ORG",  2: "I-ORG",
    3: "B-PER",  4: "I-PER",
    5: "B-LOC",  6: "I-LOC",
    7: "B-LAW",  8: "I-LAW",
    9: "B-DATE", 10: "I-DATE",
    11: "B-NUM", 12: "I-NUM",
}

SPECIAL_TOKENS = {"[CLS]", "[SEP]", "[PAD]", "<s>", "</s>", "<pad>"}


@dataclass
class NEREntity:
    text       : str
    label      : str        # Nhãn thuần: ORG, PER, LOC, LAW, DATE, NUM
    start_char : int
    end_char   : int
    tokens     : list
    bio_tags   : list


class ViLegalBERTNER:

    def __init__(self, model_name: str = NER_MODEL_NAME):
        logger.info(f"Tải mô hình NER: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model     = AutoModelForTokenClassification.from_pretrained(model_name)
        self.device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device).eval()
        logger.info(f"Mô hình sẵn sàng trên {self.device}")

    def _predict_chunk(self, text: str, char_offset: int = 0) -> list[dict]:
        enc = self.tokenizer(
            text,
            return_tensors         ="pt",
            max_length             = NER_MAX_LENGTH,
            truncation             = True,
            padding                = True,
            return_offsets_mapping = True,
        )
        offsets = enc.pop("offset_mapping").squeeze(0)
        enc     = {k: v.to(self.device) for k, v in enc.items()}

        with torch.no_grad():
            logits = self.model(**enc).logits.squeeze(0)

        preds  = torch.argmax(logits, dim=-1).cpu().tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(
            enc["input_ids"].squeeze(0).cpu().tolist()
        )
        results = []
        for tok, pred, (s, e) in zip(tokens, preds, offsets.tolist()):
            if tok in SPECIAL_TOKENS:
                continue
            results.append({
                "token": tok,
                "tag"  : LABEL_MAP.get(pred, "O"),
                "start": s + char_offset,
                "end"  : e + char_offset,
            })
        return results

    def predict(self, text: str) -> list[NEREntity]:
        """Chạy NER toàn bộ văn bản, tự chia câu nếu quá dài."""
        # Chia câu theo dấu câu tiếng Việt
        sentences = re.split(r"(?<=[.!?;])\s+|\n", text)
        all_tokens: list[dict] = []
        offset = 0
        for sent in sentences:
            if sent.strip():
                all_tokens.extend(self._predict_chunk(sent, char_offset=offset))
            offset += len(sent) + 1

        return self._merge_bio(all_tokens, text)

    @staticmethod
    def _merge_bio(tokens: list[dict], original_text: str) -> list[NEREntity]:
        """Gộp các token B/I liền kề thành entity hoàn chỉnh."""
        entities = []
        current  = None

        for tok in tokens:
            tag = tok["tag"]
            if tag == "O":
                if current:
                    entities.append(current)
                    current = None
                continue

            bio, label = (tag.split("-", 1) + [""])[:2]

            if bio == "B" or (bio == "I" and (current is None or current["label"] != label)):
                if current:
                    entities.append(current)
                current = {
                    "label"     : label,
                    "start_char": tok["start"],
                    "end_char"  : tok["end"],
                    "tokens"    : [tok["token"]],
                    "bio_tags"  : [tag],
                }
            else:  # I- khớp label với current
                current["end_char"] = tok["end"]
                current["tokens"].append(tok["token"])
                current["bio_tags"].append(tag)

        if current:
            entities.append(current)

        return [
            NEREntity(
                text       = original_text[e["start_char"]:e["end_char"]],
                label      = e["label"],
                start_char = e["start_char"],
                end_char   = e["end_char"],
                tokens     = e["tokens"],
                bio_tags   = e["bio_tags"],
            )
            for e in entities
        ]


def annotate_document(
    json_path : Path,
    ner_model : ViLegalBERTNER,
    output_dir: str,
) -> Path:
    """
    Đọc file JSON văn bản, chạy NER trên từng điều khoản,
    lưu kết quả ra {doc_number}_ner.json.

    Output schema:
    {
      "metadata": { ... },           ← giữ nguyên từ JSON gốc
      "annotations": [
        {
          "article_number": "1",
          "article_title" : "Điều 1. ...",
          "entities": [
            {
              "text"      : "Bộ Công Thương",
              "label"     : "ORG",
              "start_char": 15,
              "end_char"  : 29,
              "bio_tags"  : ["B-ORG", "I-ORG", "I-ORG"]
            }
          ]
        }
      ]
    }
    """
    out_path = Path(output_dir) / "ner"
    out_path.mkdir(parents=True, exist_ok=True)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    annotations = []
    for art in data.get("articles", []):
        content = art.get("content", "").strip()
        if not content:
            continue
        entities = ner_model.predict(content)
        annotations.append({
            "article_number": art.get("article_number", ""),
            "article_title" : art.get("title", ""),
            "entities": [
                {
                    "text"      : e.text,
                    "label"     : e.label,
                    "start_char": e.start_char,
                    "end_char"  : e.end_char,
                    "bio_tags"  : e.bio_tags,
                }
                for e in entities
            ],
        })

    ner_path = out_path / json_path.name.replace(".json", "_ner.json")
    with open(ner_path, "w", encoding="utf-8") as f:
        json.dump(
            {"metadata": data.get("metadata", {}), "annotations": annotations},
            f, ensure_ascii=False, indent=2
        )

    logger.info(f"NER  → {ner_path}")
    return ner_path
```

---

## 11. Bước 6 — Nén từng văn bản thành ZIP

### `packer/zip_packer.py`

```python
"""
Nén 3 file của mỗi văn bản thành một ZIP riêng biệt.

Cấu trúc bên trong ZIP:
  {safe_num}/
  ├── {safe_num}.docx
  ├── {safe_num}.json
  └── {safe_num}_ner.json
"""

import re
import zipfile
from pathlib import Path
from loguru import logger


def _safe(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name or "unknown")[:80]


def pack_document(
    doc_number : str,
    docx_path  : Path | None,
    json_path  : Path | None,
    ner_path   : Path | None,
    output_dir : str,
) -> Path:
    """
    Tạo file ZIP cho một văn bản.

    Args:
        doc_number : Số hiệu văn bản (VD: 13/2023/TT-BCT).
        docx_path  : File DOCX (None nếu tạo không thành công).
        json_path  : File JSON thuộc tính.
        ner_path   : File JSON NER.
        output_dir : Thư mục đích lưu ZIP.

    Returns:
        Path đến file ZIP đã tạo.
    """
    out_path = Path(output_dir) / "zip"
    out_path.mkdir(parents=True, exist_ok=True)

    safe      = _safe(doc_number)
    zip_path  = out_path / f"{safe}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path, suffix in [
            (docx_path, ".docx"),
            (json_path, ".json"),
            (ner_path,  "_ner.json"),
        ]:
            if path and Path(path).exists():
                arcname = f"{safe}/{safe}{suffix}"
                zf.write(str(path), arcname=arcname)
                logger.debug(f"  + {arcname}")
            else:
                logger.debug(f"  (bỏ qua: {suffix} không tồn tại)")

    logger.info(f"ZIP  → {zip_path}")
    return zip_path
```

---

## 12. Bước 7 — Orchestrator pipeline.py

```python
"""
pipeline.py — Chạy toàn bộ pipeline từ đầu đến cuối.

Sử dụng:
  python pipeline.py                                   # Thông tư, tất cả trang
  python pipeline.py --type_id 3 --max_pages 10        # Thông tư, 10 trang
  python pipeline.py --type_id 2 --max_pages 5         # Nghị định, 5 trang
  python pipeline.py --type_id "" --keyword "bảo hiểm" # Tìm kiếm từ khoá
"""

import argparse
from pathlib import Path
from loguru import logger

from config import OUTPUT_DIR, DEFAULT_TYPE_ID
from scraper.list_scraper   import scrape_all_pages
from scraper.detail_scraper import scrape_document
from exporter.to_docx       import convert_to_docx
from exporter.to_json       import convert_to_json
from ner.vilegalbert_ner    import ViLegalBERTNER, annotate_document
from packer.zip_packer      import pack_document


def setup_logging() -> None:
    logger.add(
        "logs/pipeline_{time}.log",
        rotation ="50 MB",
        retention="30 days",
        encoding ="utf-8",
        level    ="INFO",
    )


def run_pipeline(
    type_id  : str = DEFAULT_TYPE_ID,
    keyword  : str = "",
    max_pages: int = 0,
) -> None:
    setup_logging()
    logger.info("=" * 70)
    logger.info(f"Pipeline VBPLTW | type_id='{type_id}' | keyword='{keyword}' | max_pages={max_pages or '∞'}")

    # ── 1. Danh sách ─────────────────────────────────────────────────────────
    logger.info("▶ BƯỚC 1 — Cào danh sách văn bản (vbpl.vn/TW)")
    doc_list = scrape_all_pages(
        type_id   = type_id,
        keyword   = keyword,
        max_pages = max_pages,
    )
    logger.info(f"  Tìm được: {len(doc_list)} văn bản")

    if not doc_list:
        logger.warning("Danh sách trống — kiểm tra lại TypeID hoặc kết nối mạng.")
        return

    # ── 2. Tải mô hình NER ──────────────────────────────────────────────────
    logger.info("▶ BƯỚC 2 — Tải mô hình NER (ViSoBERT)")
    ner_model = ViLegalBERTNER()

    # ── 3–6. Xử lý từng văn bản ─────────────────────────────────────────────
    logger.info("▶ BƯỚC 3–6 — Xử lý từng văn bản")
    success = failed = 0

    for idx, item in enumerate(doc_list, 1):
        logger.info(f"[{idx}/{len(doc_list)}] {item.get('doc_number','?')} — {item.get('title','')[:55]}...")

        # 3. Cào chi tiết
        vb = scrape_document(item)
        if not vb:
            logger.warning(f"  ✗ Bỏ qua (lỗi cào): ItemID={item.get('item_id')}")
            failed += 1
            continue

        # 4. DOCX
        docx_path = convert_to_docx(vb, OUTPUT_DIR)

        # 5. JSON
        json_path = convert_to_json(vb, OUTPUT_DIR)

        # 6. NER
        ner_path  = annotate_document(json_path, ner_model, OUTPUT_DIR)

        # 7. ZIP
        pack_document(
            doc_number = vb.doc_number or vb.item_id,
            docx_path  = docx_path,
            json_path  = json_path,
            ner_path   = ner_path,
            output_dir = OUTPUT_DIR,
        )

        success += 1

    # ── Tổng kết ─────────────────────────────────────────────────────────────
    logger.info("=" * 70)
    logger.info(f"Hoàn tất! Thành công: {success} | Thất bại: {failed}")
    logger.info(f"Kết quả tại: {Path(OUTPUT_DIR).resolve()}")
    logger.info(f"  DOCX : output/docx/")
    logger.info(f"  JSON : output/json/")
    logger.info(f"  NER  : output/ner/")
    logger.info(f"  ZIP  : output/zip/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline cào VBPLTW — vbpl.vn/TW")
    parser.add_argument("--type_id",   default=DEFAULT_TYPE_ID,
                        help="TypeID loại VB: 2=Nghị định, 3=Thông tư, 4=Quyết định, ''=tất cả")
    parser.add_argument("--keyword",   default="",
                        help="Từ khoá tìm kiếm (tuỳ chọn)")
    parser.add_argument("--max_pages", default=0, type=int,
                        help="Số trang tối đa (0 = không giới hạn)")
    args = parser.parse_args()

    run_pipeline(
        type_id   = args.type_id,
        keyword   = args.keyword,
        max_pages = args.max_pages,
    )
```

### Lệnh chạy

```bash
# Cào 10 trang Thông tư
python pipeline.py --type_id 3 --max_pages 10

# Cào tất cả Nghị định
python pipeline.py --type_id 2

# Tìm kiếm theo từ khoá, không giới hạn trang
python pipeline.py --type_id "" --keyword "bảo hiểm xã hội"

# Cào toàn bộ không lọc loại
python pipeline.py --type_id "" --max_pages 0
```

---

## 13. Sơ đồ luồng dữ liệu

```
https://vbpl.vn/TW/Pages/vbpq-timkiem.aspx?TypeID=3&PageIndex=1
                          │
                          │  (tự động chuyển PageIndex=2, 3, ... N)
                          ▼
              ┌────────────────────┐
              │  list_scraper.py   │
              │  scrape_all_pages  │
              └─────────┬──────────┘
                        │  list[dict]  { item_id, url_toanvan, ... }
                        ▼
              ┌────────────────────┐
              │ detail_scraper.py  │  ← /vbpq-toanvan.aspx?ItemID=X
              │  scrape_document   │  ← /vbpq-vanbanlienquan.aspx?ItemID=X
              └─────────┬──────────┘
                        │  VBDocument
              ┌─────────┴──────────┐
              ▼                    ▼
       ┌──────────┐        ┌──────────┐
       │ to_docx  │        │ to_json  │
       │  .docx   │        │  .json   │
       └────┬─────┘        └────┬─────┘
            │                  │
            │          ┌───────▼──────────────┐
            │          │  vilegalbert_ner.py   │  ← BIO tagging
            │          │   annotate_document   │    B-ORG, I-PER, B-LAW...
            │          └───────┬──────────────┘
            │                  │  _ner.json
            └────────┬─────────┘
                     ▼
           ┌─────────────────┐
           │  zip_packer.py  │
           │  pack_document  │
           └────────┬────────┘
                    ▼
        output/zip/{doc_number}.zip
          ├── {doc_number}.docx
          ├── {doc_number}.json
          └── {doc_number}_ner.json
```

---

## 14. Lưu ý kỹ thuật & pháp lý

### Vấn đề thường gặp với vbpl.vn

| Vấn đề | Giải pháp |
|---|---|
| Trang render bằng JS (một số phần) | Dùng `playwright` thay `requests` cho `detail_scraper` |
| Session hết hạn / CAPTCHA | Restart session, thêm cookie từ trình duyệt |
| Selector thay đổi sau cập nhật UI | Inspect Network tab → cập nhật selector trong `_parse_*` |
| Phân trang dùng `__doPostBack` (ASP.NET) | Bắt form POST thay vì GET, lấy `__VIEWSTATE` |
| Rate limiting (HTTP 429) | Tăng `REQUEST_DELAY`, thêm jitter ngẫu nhiên |
| Mã hoá tiếng Việt | Đảm bảo `resp.encoding = "utf-8"` sau mỗi response |

### Xử lý ASP.NET `__doPostBack` (nếu cần)

```python
# Nếu phân trang dùng POST thay GET:
import urllib.parse

def get_viewstate(soup: BeautifulSoup) -> dict:
    """Lấy các trường ẩn ASP.NET cần thiết cho POST."""
    return {
        "__VIEWSTATE"         : soup.find("input", {"id": "__VIEWSTATE"})["value"],
        "__VIEWSTATEGENERATOR": soup.find("input", {"id": "__VIEWSTATEGENERATOR"})["value"],
        "__EVENTVALIDATION"   : soup.find("input", {"id": "__EVENTVALIDATION"})["value"],
    }

def post_next_page(session, url, soup, page_num):
    hidden = get_viewstate(soup)
    data   = {
        **hidden,
        "__EVENTTARGET"  : "ctl00$Content$GridView1",   # tuỳ chỉnh
        "__EVENTARGUMENT": f"Page${page_num}",
    }
    resp = session.post(url, data=data, timeout=30)
    return BeautifulSoup(resp.text, "lxml")
```

### Pháp lý

- Dữ liệu từ **vbpl.vn** là tài liệu công theo Nghị định 52/2015/NĐ-CP — được phép sử dụng, cần **ghi nguồn**.
- Tuân thủ `robots.txt` và không cào quá 1 request/giây để tránh ảnh hưởng máy chủ nhà nước.
- Không phân phối lại toàn bộ database thương mại khi chưa có thoả thuận.

### Cải tiến khuyến nghị

- **Checkpoint SQLite**: Lưu ItemID đã xử lý để tiếp tục khi bị gián đoạn.
- **Retry thông minh**: Dùng `tenacity` với exponential backoff.
- **Song song hoá nhẹ**: `ThreadPoolExecutor(max_workers=2)` cho bước cào chi tiết.
- **Fine-tune NER**: Thu thập ~5.000 câu văn bản pháp lý, gán nhãn `B-LAW`/`I-LAW` thủ công để cải thiện độ chính xác cho nhãn đặc thù pháp luật.
