"""Orchestrate extension report + RERA scrape into one MongoDB document."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .mongodb import ReraMongoStore
from .scraper import ReraScraper, SearchResultRow

logger = logging.getLogger("rera.report")

REPORT_TYPE_LABELS = {
    "project": "Project Report",
    "proprietor": "Promoter Report",
    "none": "Web Only",
}


def _make_log_fn(report_id: str) -> Callable[[str, str], None]:
    def log(message: str, level: str = "info") -> None:
        prefixed = f"[{report_id}] {message}"
        log_method = getattr(logger, level, logger.info)
        log_method(prefixed)

    return log


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def _pick_search_row(
    rows: list[SearchResultRow],
    entity_name: str,
    rera_id: str | None,
) -> SearchResultRow | None:
    if not rows:
        return None

    target = _normalize(entity_name)
    rera_target = _normalize(rera_id)

    for row in rows:
        if _normalize(row.project_name) == target:
            return row

    for row in rows:
        project = _normalize(row.project_name)
        if target and (target in project or project in target):
            return row

    if rera_target:
        for row in rows:
            registration = _normalize(row.rera_registration_id)
            if registration and (rera_target in registration or registration in rera_target):
                return row

    return rows[0]


async def scrape_single_project_live(
    entity_name: str,
    rera_id: str | None = None,
    *,
    headless: bool = True,
    log_fn: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    """Search Telangana RERA portal and scrape one project's PrintPreview page."""
    entity_name = entity_name.strip()
    if not entity_name:
        raise ValueError("entity_name is required")

    async with ReraScraper(headless=headless, log_fn=log_fn) as scraper:
        rows = await scraper.search_by_project(entity_name)
        if not rows:
            if log_fn:
                log_fn("No project search results; trying promoter search")
            rows = await scraper.search_by_promoter(entity_name)

        row = _pick_search_row(rows, entity_name, rera_id)
        if not row:
            raise ValueError(f"No matching project found for {entity_name!r}")

        if log_fn:
            log_fn(f"Matched project: {row.project_name}")

        detail = await scraper.scrape_project_detail(row.detail_url)
        record = await scraper._build_record(row, entity_name, "project", detail)

        return {
            "listing": {
                "sr_no": row.sr_no,
                "project_name": row.project_name,
                "promoter_name": row.promoter_name,
                "last_modified": row.last_modified,
                "detail_url": row.detail_url,
                "rera_registration_id": row.rera_registration_id,
                "directions": row.directions,
            },
            "live_details": detail,
            "record": record,
        }


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
    mongo_uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
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


def create_discovery_report(
    *,
    entity_name: str,
    user_name: str,
    user_email: str,
    user_mobile: str,
    report_type: str,
    state: str | None = None,
    rera_id: str | None = None,
    promoter_name: str | None = None,
    promoter_gst: str | None = None,
    promoter_pan: str | None = None,
    report_includes: list[str] | None = None,
    mongo_uri: str | None = None,
    mongo_db: str = "RERA-DETAILS",
    mongo_collection: str = "DETAILS",
) -> dict[str, Any]:
    """Save a Property Discovery report request to RERA-DETAILS.DETAILS."""
    uri = mongo_uri or __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017")
    store = ReraMongoStore(uri, mongo_db, mongo_collection)
    store.ping()

    report_id = store.make_report_id(entity_name, user_email)
    report_name = REPORT_TYPE_LABELS.get(report_type, report_type.title())

    report: dict[str, Any] = {
        "report_id": report_id,
        "status": "processing",
        "source": "property_discovery",
        "user_details": {
            "name": user_name.strip(),
            "email": user_email.strip().lower(),
            "mobile": user_mobile.strip(),
        },
        "report_request": {
            "entity_name": entity_name.strip(),
            "report_type": report_type,
            "report_name": report_name,
            "state": state,
            "rera_id": rera_id,
            "promoter_name": (promoter_name or "").strip() or None,
            "promoter_gst": (promoter_gst or "").strip().upper() or None,
            "promoter_pan": (promoter_pan or "").strip().upper() or None,
            "report_includes": report_includes or [],
        },
        "rera": {
            "entity_searched": entity_name.strip(),
            "total_projects": 0,
            "projects": [],
        },
    }

    store.save_unified_report(report)
    store.close()

    logger.info(
        "[%s] Discovery report placed for entity=%r report=%r",
        report_id,
        entity_name,
        report_name,
    )
    return report


async def run_discovery_background_scrape(
    report_id: str,
    entity_name: str,
    *,
    report_type: str = "project",
    state: str | None = None,
    rera_id: str | None = None,
    promoter_name: str | None = None,
    promoter_gst: str | None = None,
    promoter_pan: str | None = None,
    mongo_uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
    infra_db: str = __import__("os").getenv("DB_NAME", "INFRA"),
    mongo_db: str = "RERA-DETAILS",
    mongo_collection: str = "DETAILS",
) -> None:
    """Load promoter portfolio from INFRA and optionally create RiskMaster wishlist."""
    from .promoter_portfolio import (
        extract_promoter_identifiers,
        load_promoter_portfolio_for_report,
        resolve_promoter_details,
    )
    from .riskmaster_client import (
        RiskMasterError,
        create_promoter_wishlist,
        normalize_gstin,
        normalize_pan,
    )

    store = ReraMongoStore(mongo_uri, mongo_db, mongo_collection)
    log = _make_log_fn(report_id)

    state_code = (state or "TS").upper()
    if state_code not in ("TS", "TELANGANA"):
        store.update_discovery_scrape_result(
            report_id,
            status="completed",
            entity_name=entity_name,
            error=f"Promoter portfolio lookup is only supported for Telangana (state={state})",
        )
        store.close()
        log(f"Skipped promoter portfolio load for state={state}")
        return

    riskmaster_result: dict[str, Any] | None = None
    riskmaster_error: str | None = None

    try:
        store.update_discovery_scrape_result(
            report_id,
            status="loading",
            entity_name=entity_name,
        )

        if report_type == "proprietor":
            log("Resolving promoter details for RiskMaster wishlist")
            details = resolve_promoter_details(
                entity_name=entity_name,
                promoter_name=promoter_name,
                promoter_gst=promoter_gst,
                promoter_pan=promoter_pan,
                rera_id=rera_id,
                mongo_uri=mongo_uri,
                infra_db=infra_db,
            )
            resolved_promoter = details["promoter_name"]
            gstin = details["gstin"]
            pan = details["pan"]

            if not resolved_promoter:
                raise ValueError(
                    f"Could not resolve promoter name for project {entity_name!r}"
                )

            log(
                f"Promoter identifiers resolved: name={resolved_promoter!r} "
                f"gst={gstin or 'N/A'} pan={pan or 'N/A'}"
            )

            log("Authenticating with RiskMaster (Login -> OTP) and creating wishlist")
            if not pan:
                riskmaster_error = (
                    "PAN is required for promoter report. "
                    "Ensure GST Number is available in promoter details."
                )
                log(riskmaster_error, level="error")
            else:
                try:
                    riskmaster_result = create_promoter_wishlist(
                        promoter_name=resolved_promoter,
                        pan=pan,
                        gstin=gstin or None,
                    )
                    wishlist_id = riskmaster_result.get("wishlist", {}).get("id")
                    log(f"RiskMaster wishlist created: id={wishlist_id}")

                    if wishlist_id:
                        from .riskmaster_client import create_multiple_signalx_report
                        log("Triggering RiskMaster SignalX Report generation...")
                        report_result = create_multiple_signalx_report(
                            entity_name=resolved_promoter,
                            pan=pan,
                            wishlist_id=wishlist_id,
                        )
                        riskmaster_result["report_creation"] = report_result
                        log("RiskMaster SignalX Report triggered successfully.")
                except RiskMasterError as exc:
                    riskmaster_error = str(exc)
                    riskmaster_result = {
                        "success": False,
                        "error": riskmaster_error,
                        "debug_trace": exc.debug_trace,
                    }
                    log(f"RiskMaster wishlist failed: {exc}", level="error")
                except Exception as exc:
                    riskmaster_error = str(exc)
                    if "not configured" in riskmaster_error.lower():
                        log(f"RiskMaster not configured (skipping wishlist for {resolved_promoter})", level="info")
                    else:
                        log(f"RiskMaster wishlist failed: {exc}", level="error")
                        logger.exception("[%s] RiskMaster wishlist failed", report_id)

        log("Loading promoter portfolio from INFRA.Telangana_Detailed")
        payload = load_promoter_portfolio_for_report(
            entity_name=entity_name,
            promoter_name=promoter_name,
            rera_id=rera_id,
            mongo_uri=mongo_uri,
            infra_db=infra_db,
        )

        primary = payload.get("primary_project")
        resolved_promoter = payload["promoter_name"]
        db_gst, db_pan = extract_promoter_identifiers(primary)
        gstin = normalize_gstin(promoter_gst or db_gst)
        pan = normalize_pan(promoter_pan or db_pan, gstin)

        update_kwargs: dict[str, Any] = {
            "report_id": report_id,
            "status": "completed",
            "entity_name": entity_name,
            "promoter_name": resolved_promoter,
            "live_details": primary,
            "listing": {
                "project_name": entity_name,
                "promoter_name": resolved_promoter,
                "promoter_gst": gstin or None,
                "promoter_pan": pan or None,
                "source_collection": payload["source_collection"],
                "loaded_at": payload["loaded_at"],
            },
            "projects": payload["projects"],
        }
        if report_type == "proprietor":
            update_kwargs["riskmaster"] = {
                **(riskmaster_result or {}),
                "success": bool(riskmaster_result and not riskmaster_error),
                "error": riskmaster_error,
            }
            if riskmaster_error:
                update_kwargs["error"] = riskmaster_error

        store.update_discovery_scrape_result(**update_kwargs)
        log(
            f"Promoter portfolio saved: {len(payload['projects'])} project(s) "
            f"for {resolved_promoter!r}"
        )
    except Exception as exc:
        log(f"Promoter portfolio load failed: {exc}", level="error")
        store.update_discovery_scrape_result(
            report_id,
            status="failed",
            entity_name=entity_name,
            error=str(exc),
        )
        logger.exception("[%s] Discovery promoter portfolio load failed", report_id)
    finally:
        store.close()


async def run_background_scrape(
    report_id: str,
    entity_name: str,
    *,
    mongo_uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
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
    mongo_uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
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
