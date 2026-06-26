"""Advanced search scraper for Tamil Nadu: Scrapes all projects across years and saves them to INFRA.TN_allprojects."""

from __future__ import annotations

import logging
from typing import Any

from .scraper import ReraScraper
from .infra_store import InfraProjectStore

logger = logging.getLogger("rera.advanced")


async def run_advanced_scraper(
    *,
    headless: bool = True,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "INFRA",
    mongo_collection: str = "TN_allprojects",
    district_ids: list[str] | None = None,
    project_type_ids: list[str] | None = None,
    from_district_id: str | None = None,
    from_project_type_id: str | None = None,
    max_pages: int | None = None,
    save_mongo: bool = True,
) -> list[dict[str, Any]]:
    """Tamil Nadu implementation: fetches all registered building projects across years and saves to MongoDB."""
    store: InfraProjectStore | None = None
    if save_mongo:
        store = InfraProjectStore(mongo_uri, mongo_db, mongo_collection)
        store.ping()
        logger.info("MongoDB %s.%s — existing docs: %s", mongo_db, mongo_collection, store.count())

    records: list[dict[str, Any]] = []

    async with ReraScraper(headless=headless) as scraper:
        # Fetch and parse all table rows (cache loads all years)
        rows = scraper._fetch_all_table_rows()

        # Filter by district names if district_ids/names are supplied (though usually we fetch all)
        # Note: since district_ids are not standard for TN, we keep them all or filter if needed.

        for row in rows:
            # Build basic project record (same as search table row format)
            record = {
                "detail_url": row.detail_url,
                "sr_no": row.sr_no,
                "project_name": row.project_name,
                "promoter_name": row.promoter_name,
                "last_modified": row.registration_date or row.completion_date,
                "registration_no": row.registration_no,
                "registration_date": row.registration_date,
                "promoter_address": row.promoter_address,
                "approval_details": row.approval_details,
                "completion_date": row.completion_date,
                "promoter_details_url": row.promoter_details_url,
                "form_c_url": row.form_c_url,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "status_text": row.status_text,
                "state": "TN",
                "search": {
                    "district_name": "", # populated on detail scrape or empty
                    "project_type_name": "Building",
                    "state": "TN"
                }
            }
            records.append(record)

    if store and records:
        saved = store.upsert_projects(records)
        logger.info("Saved %s project row(s) to %s.%s", saved, mongo_db, mongo_collection)
        store.close()

    return records
