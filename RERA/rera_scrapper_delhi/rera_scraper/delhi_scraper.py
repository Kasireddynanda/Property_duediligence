"""HTTP scraper for Delhi RERA registered projects."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .delhi_store import DelhiProjectStore
from .extractors import DETAIL_URL, LIST_URL, extract_detail_page, extract_list_rows

logger = logging.getLogger("rera.delhi")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _build_detail_url(project_id: int, promoter_id: int, promoter_type: int) -> str:
    return (
        f"{DETAIL_URL}?inProject_ID={project_id}"
        f"&inPromoter_ID={promoter_id}&inPromoterType={promoter_type}"
    )


def scrape_delhi_projects(
    *,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "INFRA",
    mongo_collection: str = "Delhi_allprojects_detailed",
    limit: int | None = None,
    delay_seconds: float = 0.75,
    save_to_mongo: bool = True,
    registration_no: str | None = None,
) -> dict[str, Any]:
    store: DelhiProjectStore | None = None
    if save_to_mongo:
        store = DelhiProjectStore(mongo_uri, mongo_db, mongo_collection)
        store.ping()

    saved = 0
    errors: list[dict[str, str]] = []

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=60.0, follow_redirects=True) as client:
        logger.info("Fetching listing page: %s", LIST_URL)
        list_resp = client.get(LIST_URL)
        list_resp.raise_for_status()
        rows = extract_list_rows(list_resp.text)
        logger.info("Parsed %s projects from listing table.", len(rows))

        if registration_no:
            needle = registration_no.strip().upper()
            rows = [r for r in rows if r.get("registration_no", "").upper() == needle]
            logger.info("Filtered to registration_no=%s (%s rows).", registration_no, len(rows))

        if limit is not None:
            rows = rows[:limit]

        for idx, row in enumerate(rows, start=1):
            project_name = row.get("project_name", "Unknown")
            reg_no = row.get("registration_no", "")
            logger.info("[%s/%s] Scraping %s (%s)", idx, len(rows), project_name, reg_no)

            detail_url = row.get("detail_url")
            if not detail_url:
                errors.append(
                    {
                        "registration_no": reg_no,
                        "error": "Missing project/promoter IDs for detail URL",
                    }
                )
                continue

            try:
                detail_resp = client.get(detail_url)
                detail_resp.raise_for_status()
                detail_data = extract_detail_page(detail_resp.text)
            except Exception as exc:
                logger.exception("Failed detail scrape for %s", reg_no)
                errors.append({"registration_no": reg_no, "error": str(exc)})
                continue

            document: dict[str, Any] = {
                **row,
                "list_row": row,
                "detail_url": detail_url,
                "certificate_url": row.get("certificate_url", ""),
                "tabs": detail_data["tabs"],
                "document_links": detail_data["document_links"],
                "source": {
                    "list_url": LIST_URL,
                    "portal": "erera.co.in",
                    "state": "Delhi",
                },
            }

            if store:
                store.upsert_project(document)
            saved += 1

            if delay_seconds > 0 and idx < len(rows):
                time.sleep(delay_seconds)

    if store:
        total = store.count()
        store.close()
    else:
        total = saved

    return {
        "listing_count": len(rows),
        "saved_count": saved,
        "mongo_total": total,
        "errors": errors,
    }
