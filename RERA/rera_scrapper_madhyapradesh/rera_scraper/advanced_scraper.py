"""Advanced scraper coordinator for Madhya Pradesh RERA.

Workflow
--------
1.  Navigate to https://www.rera.mp.gov.in/projects-completed/
2.  Expand the DataTable to show all rows (or paginate in batches of 100).
3.  Parse every listing row → build MP_allprojects records.
4.  For each listing row, fetch the detail page → parse project info /
    location / promoter info → build MP_Detailed records.
5.  Upsert everything to MongoDB.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .extractors import extract_project_detail_page
from .infra_store import MPProjectStore
from .scraper import MPReraScraper, BASE_URL

logger = logging.getLogger("rera.mp.advanced")

# How long to sleep between detail-page requests (be polite to the server)
DETAIL_DELAY_SECONDS = 1.5


def _parse_listing_html(html: str) -> list[dict[str, Any]]:
    """
    Parse all <tr> rows from the #example DataTable and return list of dicts.

    Columns (0-indexed):
      0 – S.No.
      1 – Project Registration No.
      2 – Project Name
      3 – Promoter Name
      4 – District – Planning Area
      5 – Details (contains <a href="..."> View link)
    """
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.select_one("#example tbody")
    if not tbody:
        logger.warning("Could not find #example tbody in listing HTML.")
        return []

    rows = []
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue  # skip empty / header rows

        # Serial number
        sno = tds[0].get_text(strip=True)

        # Registration number
        reg_no = tds[1].get_text(strip=True)

        # Project name
        project_name = tds[2].get_text(strip=True)

        # Promoter name
        promoter_name = tds[3].get_text(" ", strip=True)

        # District – Planning Area (contains &nbsp; separators)
        raw_district = tds[4].get_text(" ", strip=True)
        # Normalise "Gwalior   -   Gwalior" → "Gwalior - Gwalior"
        district_raw = " ".join(raw_district.split())

        # Split into district and planning area if " - " is present
        if " - " in district_raw:
            parts = [p.strip() for p in district_raw.split(" - ", 1)]
            district = parts[0]
            planning_area = parts[1]
        else:
            district = district_raw
            planning_area = ""

        # Detail page URL (5th column)
        detail_url = ""
        if len(tds) >= 6:
            a_tag = tds[5].find("a")
            if a_tag and a_tag.get("href"):
                href = a_tag["href"].strip()
                detail_url = href if href.startswith("http") else urljoin(BASE_URL, href)

        rows.append(
            {
                "sno": sno,
                "registration_no": reg_no,
                "project_name": project_name,
                "promoter_name": promoter_name,
                "district": district,
                "planning_area": planning_area,
                "detail_url": detail_url,
                "state": "MP",
                "search": {
                    "district": district,
                    "planning_area": planning_area,
                    "state": "MP",
                },
            }
        )

    logger.info("Parsed %s rows from listing HTML.", len(rows))
    return rows


async def _scrape_with_pagination(
    scraper: MPReraScraper,
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    """
    If the DataTable API call to show all rows fails, fall back to clicking
    through pages 1…N (each shows 100 rows) and accumulating.
    """
    all_rows: list[dict[str, Any]] = []

    # First try the all-at-once approach
    try:
        html = await scraper.get_listing_rows_html()
        rows = _parse_listing_html(html)
        if rows:
            return rows
    except Exception as exc:
        logger.warning("All-rows approach failed: %s — falling back to pagination.", exc)

    # Pagination fallback: select 100 per page and click Next repeatedly
    page_num = 0
    while True:
        page_num += 1
        if max_pages and page_num > max_pages:
            break

        html = await scraper.page.content()
        rows = _parse_listing_html(html)
        all_rows.extend(rows)
        logger.info("Page %s: accumulated %s rows total.", page_num, len(all_rows))

        # Try clicking "Next"
        next_btn = scraper.page.locator("#example_next:not(.disabled)")
        if await next_btn.count() == 0:
            logger.info("No more pages – pagination complete.")
            break

        await next_btn.click()
        try:
            await scraper.page.wait_for_selector("#example tbody tr", timeout=10_000)
        except Exception:
            pass
        await asyncio.sleep(1.5)

    return all_rows


async def run_advanced_scraper(
    *,
    headless: bool = True,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "INFRA",
    all_projects_col: str = "MP_allprojects",
    detailed_col: str = "MP_detailed",
    max_projects: int | None = None,
    save_mongo: bool = True,
    scrape_details: bool = True,
    mock_on_fail: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Main entry point.

    Returns (all_rows, all_details).
    """
    store: MPProjectStore | None = None
    if save_mongo:
        store = MPProjectStore(mongo_uri, mongo_db, all_projects_col, detailed_col)
        store.ping()

    all_rows: list[dict[str, Any]] = []
    all_details: list[dict[str, Any]] = []

    logger.info("Starting Playwright browser for MP RERA…")
    async with MPReraScraper(headless=headless) as scraper:
        online = await scraper.navigate_to_listing()

        if not online:
            if mock_on_fail:
                logger.warning(
                    "MP RERA portal unreachable – generating mock fallback data for testing."
                )
                mock_rows, mock_details = _get_mock_mp_data()
                all_rows.extend(mock_rows)
                all_details.extend(mock_details)
            else:
                logger.error("MP RERA portal unreachable. Aborting.")
                if store:
                    store.close()
                return [], []
        else:
            # ---- Parse listing rows ----
            try:
                all_rows = await _scrape_with_pagination(scraper)
            except Exception as exc:
                logger.error("Listing scrape failed: %s", exc)

            # Apply global limit
            if max_projects:
                all_rows = all_rows[:max_projects]
                logger.info("Limiting to %s project(s) as requested.", max_projects)

            logger.info("Total listing rows collected: %s", len(all_rows))

            # ---- Fetch detail pages ----
            if scrape_details:
                for idx, row in enumerate(all_rows):
                    url = row.get("detail_url", "")
                    if not url:
                        logger.debug("No detail URL for row %s (%s) – skipping.", idx + 1, row.get("project_name"))
                        continue

                    logger.info(
                        "[%s/%s] Fetching detail for %s …",
                        idx + 1,
                        len(all_rows),
                        row.get("project_name"),
                    )
                    try:
                        detail_html = await scraper.fetch_detail_page(url)
                    except Exception as exc:
                        logger.error("Detail fetch error for %s: %s", url, exc)
                        detail_html = ""

                    if detail_html:
                        parsed = extract_project_detail_page(detail_html)
                        detail_record = {
                            "registration_no": row.get("registration_no"),
                            "project_name": row.get("project_name"),
                            "promoter_name": row.get("promoter_name"),
                            "district": row.get("district"),
                            "planning_area": row.get("planning_area"),
                            "detail_url": url,
                            "project_info": parsed.get("project_info", {}),
                            "project_location": parsed.get("project_location", {}),
                            "promoter_info": parsed.get("promoter_info", {}),
                            "state": "MP",
                        }
                        all_details.append(detail_record)
                    else:
                        logger.warning("Empty detail page for project: %s", row.get("project_name"))

                    await asyncio.sleep(DETAIL_DELAY_SECONDS)

    # ---- Persist to MongoDB ----
    if store:
        if all_rows:
            logger.info("Saving %s listing rows to %s…", len(all_rows), all_projects_col)
            for row in all_rows:
                store.upsert_project(row)

        if all_details:
            logger.info("Saving %s detailed records to %s…", len(all_details), detailed_col)
            for det in all_details:
                store.upsert_detailed(det)

        store.close()

    return all_rows, all_details


# ---------------------------------------------------------------------------
# Mock data (used when the portal is unreachable during development/testing)
# ---------------------------------------------------------------------------

def _get_mock_mp_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return sample MP RERA records matching the live portal structure."""
    mock_rows = [
        {
            "sno": "1",
            "registration_no": "P-GWL-17-004",
            "project_name": "GARDEN PALACE",
            "promoter_name": "GRAVITY INFRASTRUCTURES PVT LTD",
            "district": "Gwalior",
            "planning_area": "Gwalior",
            "detail_url": "https://www.rera.mp.gov.in/view_project_details.php?id=NEo3Vm1qOUlOajNSdEdxS0R4c3A0QT09",
            "state": "MP",
            "search": {"district": "Gwalior", "planning_area": "Gwalior", "state": "MP"},
        },
        {
            "sno": "2",
            "registration_no": "P-GWL-17-005",
            "project_name": "NG GRANDE",
            "promoter_name": "GLR REAL ESTATE PVT LTD",
            "district": "Gwalior",
            "planning_area": "Gwalior",
            "detail_url": "https://www.rera.mp.gov.in/view_project_details.php?id=M1psdmdFRWo5Z2VJWnBtU0RxVC9VUT09",
            "state": "MP",
            "search": {"district": "Gwalior", "planning_area": "Gwalior", "state": "MP"},
        },
        {
            "sno": "3",
            "registration_no": "P-IND-17-002",
            "project_name": "APOLLO PREMIER",
            "promoter_name": "APOLLO CREATIONS PVT LTD",
            "district": "Indore",
            "planning_area": "Indore",
            "detail_url": "https://www.rera.mp.gov.in/view_project_details.php?id=bVZhTVozWmFKSHNjMW94WVBIa1VjZz09",
            "state": "MP",
            "search": {"district": "Indore", "planning_area": "Indore", "state": "MP"},
        },
        {
            "sno": "4",
            "registration_no": "P-IND-17-003",
            "project_name": "SECTOR E GOLF LINKS",
            "promoter_name": "APOLLO CREATIONS PVT LTD",
            "district": "Indore",
            "planning_area": "Indore",
            "detail_url": "https://www.rera.mp.gov.in/view_project_details.php?id=WklXUnE1T3Z6SHUzYktHcUJmOThDdz09",
            "state": "MP",
            "search": {"district": "Indore", "planning_area": "Indore", "state": "MP"},
        },
        {
            "sno": "5",
            "registration_no": "P-JBP-17-452",
            "project_name": "RELIABLE ESTATE",
            "promoter_name": "RELIABLE DEVELOPERS",
            "district": "Jabalpur",
            "planning_area": "Jabalpur",
            "detail_url": "https://www.rera.mp.gov.in/view_project_details.php?id=TXh2VDlQMndXdWFsTERjQUcrWUMxQT09",
            "state": "MP",
            "search": {"district": "Jabalpur", "planning_area": "Jabalpur", "state": "MP"},
        },
    ]

    mock_details = [
        {
            "registration_no": "P-GWL-17-004",
            "project_name": "GARDEN PALACE",
            "promoter_name": "GRAVITY INFRASTRUCTURES PVT LTD",
            "district": "Gwalior",
            "planning_area": "Gwalior",
            "detail_url": "https://www.rera.mp.gov.in/view_project_details.php?id=NEo3Vm1qOUlOajNSdEdxS0R4c3A0QT09",
            "project_info": {
                "Project Name": "GARDEN PALACE",
                "Registration Number": "P-GWL-17-004",
                "Project Type": "Ongoing",
                "Application Status": "Completed",
                "Contact Email": "neoteric_gwl@yahoo.co.in",
                "Agency for External Development": "Local Authority",
                "Land Ownership": "Gravity Infrastructures Pvt Ltd",
                "Actual Start Date": "15-11-2015",
                "Proposed End Date": "31-07-2018",
                "Estimated Cost of Construction(in lacs)": "250000000.00",
                "Estimated Cost of Land(in lacs)": "7117000.00",
                "Is Project on Schedule?": "Yes",
                "Construction Status": "Ongoing",
            },
            "project_location": {
                "State": "Madhya Pradesh",
                "District": "Gwalior",
                "Tehsil": "Gwalior (Gird)",
                "Project Address": "Next to Gems School Gulmohar City Road Behind New Collectorate New City Center Gwalior Madhya Pradesh",
                "Project Planning Area": "Gwalior",
            },
            "promoter_info": {
                "Name": "GRAVITY INFRASTRUCTURES PVT LTD",
                "Applicant Type": "Company",
                "Address": "60 Silver Shopping Gallery Silver Estate University Road Gwalior",
                "Email": "neoteric_gwl@yahoo.co.in",
                "Is it a New Entity ?": "NO",
            },
            "state": "MP",
        },
    ]

    return mock_rows, mock_details
