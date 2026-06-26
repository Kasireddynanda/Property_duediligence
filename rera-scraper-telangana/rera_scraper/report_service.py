"""Orchestrate extension report + RERA scrape into one MongoDB document."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .mongodb import ReraMongoStore
from .scraper import ReraScraper

logger = logging.getLogger("rera.report")


def _make_log_fn(report_id: str) -> Callable[[str, str], None]:
    def log(message: str, level: str = "info") -> None:
        prefixed = f"[{report_id}] {message}"
        log_method = getattr(logger, level, logger.info)
        log_method(prefixed)

    return log


async def scrape_entity_for_report(
    entity_name: str,
    *,
    headless: bool = True,
    follow_promoter_search: bool = True,
    log_fn: Callable[[str, str], None] | None = None,
) -> list[dict[str, Any]]:
    entity_name = entity_name.strip()
    if not entity_name:
        return []

    def emit(msg: str, level: str = "info") -> None:
        if log_fn:
            log_fn(msg, level)
        else:
            logger.info("[%s] %s", entity_name, msg)

    async with ReraScraper(headless=headless, log_fn=emit) as scraper:
        records = await scraper.scrape_projects(
            [entity_name],
            follow_promoter_search=follow_promoter_search,
        )

        if not records:
            emit("No project results; trying promoter search")
            records = await scraper.scrape_promoters([entity_name])

    return records


def create_pending_report(
    *,
    entity_name: str,
    user_name: str,
    user_email: str,
    user_mobile: str,
    cin: str | None = None,
    vendor_data: dict[str, Any] | None = None,
    source_page_url: str | None = None,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "RERA-DETAILS",
    mongo_collection: str = "DETAILS",
) -> dict[str, Any]:
    """Save report immediately with status=processing; scrape runs separately."""
    store = ReraMongoStore(mongo_uri, mongo_db, mongo_collection)
    store.ping()

    report_id = store.make_report_id(entity_name, user_email)

    report: dict[str, Any] = {
        "report_id": report_id,
        "status": "processing",
        "user_details": {
            "name": user_name,
            "email": user_email,
            "mobile": user_mobile,
        },
        "report_request": {
            "entity_name": entity_name,
            "cin": cin,
            "source_page_url": source_page_url,
        },
        "vendor_discovery": vendor_data,
        "rera": {
            "entity_searched": entity_name,
            "total_projects": 0,
            "projects": [],
        },
    }
    store.save_unified_report(report)
    store.close()

    logger.info("[%s] Report placed for entity=%r — scrape queued", report_id, entity_name)
    return report


async def run_background_scrape(
    report_id: str,
    entity_name: str,
    *,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "RERA-DETAILS",
    mongo_collection: str = "DETAILS",
    headless: bool = True,
) -> None:
    """Run RERA scrape after the API has already responded to the client."""
    store = ReraMongoStore(mongo_uri, mongo_db, mongo_collection)
    log = _make_log_fn(report_id)

    try:
        log("Starting RERA scrape in background")
        projects = await scrape_entity_for_report(
            entity_name,
            headless=headless,
            log_fn=log,
        )
        store.update_report_scrape_result(
            report_id,
            status="completed",
            entity_name=entity_name,
            projects=projects,
        )
        log(f"Scrape completed: {len(projects)} project(s) saved")
    except Exception as exc:
        log(f"Scrape failed: {exc}", level="error")
        store.update_report_scrape_result(
            report_id,
            status="failed",
            entity_name=entity_name,
            projects=[],
            error=str(exc),
        )
        logger.exception("[%s] Background scrape failed", report_id)
    finally:
        store.close()


async def place_report(
    *,
    entity_name: str,
    user_name: str,
    user_email: str,
    user_mobile: str,
    cin: str | None = None,
    vendor_data: dict[str, Any] | None = None,
    source_page_url: str | None = None,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "RERA-DETAILS",
    mongo_collection: str = "DETAILS",
    headless: bool = True,
) -> dict[str, Any]:
    """Synchronous flow: place report and wait for scrape (CLI / tests)."""
    report = create_pending_report(
        entity_name=entity_name,
        user_name=user_name,
        user_email=user_email,
        user_mobile=user_mobile,
        cin=cin,
        vendor_data=vendor_data,
        source_page_url=source_page_url,
        mongo_uri=mongo_uri,
        mongo_db=mongo_db,
        mongo_collection=mongo_collection,
    )
    await run_background_scrape(
        report["report_id"],
        entity_name,
        mongo_uri=mongo_uri,
        mongo_db=mongo_db,
        mongo_collection=mongo_collection,
        headless=headless,
    )

    store = ReraMongoStore(mongo_uri, mongo_db, mongo_collection)
    updated = store.get_report(report["report_id"])
    store.close()
    return updated or report
