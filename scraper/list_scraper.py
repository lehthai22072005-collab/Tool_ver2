import json
import math
import re
import time
import unicodedata
from pathlib import Path

import requests
from loguru import logger

from config import (
    API_HEADERS,
    API_LIST_URL,
    ALL_DOC_TYPE_API_IDS,
    BASE_URL,
    DEFAULT_PAGE_SIZE,
    DOC_TYPE_ALIASES,
    DOC_TYPE_API_IDS,
    MAX_RETRIES,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    TYPE_ID_NAME_MAP,
)


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


def _canonical_type_id(type_id: str) -> str:
    raw = str(type_id or "")
    return DOC_TYPE_ALIASES.get(raw, raw)


def _post(session: requests.Session, url: str, payload: dict) -> dict | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning(f"API request failed {attempt}/{MAX_RETRIES}: {exc}")
            time.sleep(REQUEST_DELAY * attempt)
    return None


def _slugify(text: str) -> str:
    try:
        import unicodedata

        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = text.replace("đ", "d").replace("Đ", "D")
    except Exception:
        pass
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or "van-ban"


def _detail_url(item: dict) -> str:
    title = item.get("title") or item.get("docNum") or "van-ban"
    return f"{BASE_URL}/van-ban/chi-tiet/{_slugify(title)}--{item.get('id', '')}"


def _name(value) -> str:
    if isinstance(value, dict):
        return value.get("name") or value.get("title") or value.get("code") or ""
    return str(value or "")


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _starts_with_form(text: str, form: str) -> bool:
    text = _normalize_text(text)
    form = _normalize_text(form)
    return text == form or text.startswith(f"{form} ") or text.startswith(f"{form}-")


def _matches_type(item: dict, type_id: str) -> bool:
    type_id = _canonical_type_id(type_id)
    if not type_id:
        return True
    names = TYPE_ID_NAME_MAP.get(str(type_id), ())
    if not names:
        return True
    selected_names = tuple(names)
    excluded_names = [
        name
        for current_id, current_names in TYPE_ID_NAME_MAP.items()
        if str(current_id) != str(type_id)
        for name in current_names
        if any(_normalize_text(name).startswith(f"{_normalize_text(selected)} ") for selected in selected_names)
    ]
    doc_type = _name(item.get("docType"))
    title = item.get("title") or ""

    if any(_starts_with_form(doc_type, name) or _starts_with_form(title, name) for name in excluded_names):
        return False
    return any(_starts_with_form(doc_type, name) or _starts_with_form(title, name) for name in names)


def _document_type_filter(type_id: str) -> list[str]:
    type_id = _canonical_type_id(type_id)
    if not type_id:
        return ALL_DOC_TYPE_API_IDS
    return DOC_TYPE_API_IDS.get(str(type_id), [])


def _list_payload(type_id: str, keyword: str, page: int, page_size: int) -> dict:
    payload = {
        "pageNumber": page,
        "pageSize": page_size,
        "keyword": keyword or "",
        "sortBy": "issueDate",
        "sortDirection": "desc",
        "groupVbpl": True,
        "score": False,
        "agencyLevel": "TRUNG_UONG",
        "searchIn": "title",
        "matchMode": "all_words",
    }
    doc_type_filter = _document_type_filter(type_id)
    if doc_type_filter:
        payload["docType"] = doc_type_filter
    return payload


def get_total_pages(type_id: str = "", keyword: str = "", page_size: int = DEFAULT_PAGE_SIZE) -> tuple[int, int]:
    session = requests.Session()
    session.headers.update(API_HEADERS)
    response = _post(session, API_LIST_URL, _list_payload(type_id, keyword, 1, page_size))
    if response is None:
        return 0, 0
    data = response.get("data") or response
    total = int(data.get("total") or 0)
    total_pages = math.ceil(total / page_size) if total else 0
    return total, total_pages


def _normalize_item(item: dict, page: int, type_id: str, keyword: str) -> dict:
    item_id = item.get("id") or ""
    return {
        "item_id": item_id,
        "url": _detail_url(item),
        "url_toanvan": _detail_url(item),
        "api_detail_url": f"{API_LIST_URL.rsplit('/all', 1)[0]}/{item_id}",
        "title": item.get("title") or "",
        "doc_number": item.get("docNum") or "",
        "doc_type": _name(item.get("docType")),
        "issue_date": item.get("issueDate") or "",
        "effective_date": item.get("effFrom") or "",
        "issuer": item.get("agencyName") or _name(item.get("organization")),
        "status": _name(item.get("effStatus")) or item.get("status") or "",
        "summary": item.get("docAbs") or "",
        "list_page": page,
        "type_id": type_id,
        "keyword": keyword,
    }


def _load_cached_items(checkpoint_path: Path) -> list[dict]:
    if not checkpoint_path.exists():
        return []

    items = []
    with checkpoint_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Cannot parse cached line in {checkpoint_path}")
    return items


def _append_cached_items(checkpoint_path: Path, items: list[dict]) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint_path.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def scrape_all_pages(
    type_id: str = "",
    keyword: str = "",
    max_pages: int = 0,
    checkpoint_path: str | Path | None = None,
    resume: bool = True,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[dict]:
    session = requests.Session()
    session.headers.update(API_HEADERS)

    checkpoint = Path(checkpoint_path) if checkpoint_path else None
    all_items = _load_cached_items(checkpoint) if checkpoint and resume else []
    cached_pages = {int(item.get("list_page", 0)) for item in all_items if item.get("list_page")}
    page = max(cached_pages, default=0) + 1
    total_pages = None

    if all_items:
        logger.info(f"Loaded {len(all_items)} cached list item(s) from {checkpoint}")
        logger.info(f"Resuming API list scrape at page {page}")

    while True:
        if max_pages and page > max_pages:
            break

        payload = _list_payload(type_id, keyword, page, page_size)

        logger.info(f"Scraping API list page {page}{f'/{total_pages}' if total_pages else ''}: {API_LIST_URL}")
        response = _post(session, API_LIST_URL, payload)
        if response is None:
            logger.error(f"Cannot fetch API list page {page}; stopping")
            break

        data = response.get("data") or response
        raw_items = data.get("items") or []
        items = [
            _normalize_item(item, page, type_id, keyword)
            for item in raw_items
            if _matches_type(item, type_id)
        ]

        if total_pages is None:
            total = int(data.get("total") or 0)
            total_pages = math.ceil(total / page_size) if total else 1
            logger.info(f"Detected total API page(s): {total_pages} | total item(s): {total}")

        if not raw_items:
            logger.info("No API item found on this page; ending pagination")
            break

        all_items.extend(items)
        if checkpoint and items:
            _append_cached_items(checkpoint, items)
            logger.info(f"Cached {len(items)} item(s) from page {page} to {checkpoint}")

        logger.info(f"Found {len(items)}/{len(raw_items)} matching item(s) on page {page}; accumulated {len(all_items)}")

        if total_pages and page >= total_pages:
            break
        if max_pages and page >= max_pages:
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    logger.info(f"Total list item(s): {len(all_items)}")
    return all_items
