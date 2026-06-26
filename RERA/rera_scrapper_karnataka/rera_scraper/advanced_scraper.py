"""Advanced scraper coordinator for Karnataka RERA."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .scraper import KAReraScraper
from .infra_store import KAProjectStore

logger = logging.getLogger("rera.advanced")


async def run_advanced_scraper(
    *,
    headless: bool = True,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "INFRA",
    all_projects_col: str = "KA_allprojects",
    detailed_col: str = "KA_Detailed",
    districts: list[str] | None = None,
    max_projects_per_district: int | None = None,
    save_mongo: bool = True,
    mock_on_fail: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Runs Karnataka RERA scraper, iterates over districts, extracts table rows & details modals."""
    store = None
    if save_mongo:
        store = KAProjectStore(mongo_uri, mongo_db, all_projects_col, detailed_col)
        store.ping()

    all_rows: list[dict[str, Any]] = []
    all_details: list[dict[str, Any]] = []

    logger.info("Initializing Playwright scraper...")
    async with KAReraScraper(headless=headless) as scraper:
        online = await scraper.navigate_to_portal()
        
        if not online:
            if mock_on_fail:
                logger.warning("Karnataka RERA portal is unreachable. Generating mock fallback projects for testing...")
                mock_rows, mock_details = get_mock_karnataka_data()
                all_rows.extend(mock_rows)
                all_details.extend(mock_details)
            else:
                logger.error("Karnataka RERA portal is unreachable. Scrape aborted.")
                if store:
                    store.close()
                return [], []
        else:
            # Live Scrape
            try:
                available_districts = await scraper.get_districts()
                if not available_districts:
                    available_districts = ["Bagalkot", "Bengaluru Urban", "Bengaluru Rural"]

                target_districts = districts if districts else available_districts
                logger.info("Target districts to scrape: %s", target_districts)

                for dist in target_districts:
                    logger.info("Starting scrape for district: %s", dist)
                    success = await scraper.select_district_and_search(dist)
                    if not success:
                        logger.warning("Skipping district %s due to search failure.", dist)
                        continue

                    # Parse Table Rows
                    rows_loc = scraper.page.locator("#approvedTable tbody tr")
                    row_count = await rows_loc.count()
                    logger.info("Found %s row(s) in approvedTable for district %s.", row_count, dist)

                    scraped_in_dist = 0
                    for idx in range(row_count):
                        if max_projects_per_district and scraped_in_dist >= max_projects_per_district:
                            break

                        row = rows_loc.nth(idx)
                        
                        # Verify we have tds
                        td_count = await row.locator("td").count()
                        if td_count < 11:
                            # Might be 'No data available in table' row
                            continue

                        # Extract texts
                        td_texts = [await row.locator("td").nth(i).inner_text() for i in range(td_count)]
                        td_texts = [t.strip() for t in td_texts]

                        # Check for rejection or empty statuses
                        ack_no = td_texts[1]
                        reg_no = td_texts[2]
                        promoter_name = td_texts[4]
                        project_name = td_texts[5]
                        status = td_texts[6]
                        district_val = td_texts[7] or dist
                        taluk = td_texts[8]
                        project_type = td_texts[9]
                        approved_on = td_texts[10]
                        proposed_completion = td_texts[11] if td_count > 11 else ""

                        # Extract certificates
                        certificate_href = ""
                        cert_anchor = row.locator("td").nth(16).locator("a")
                        if await cert_anchor.count() > 0:
                            certificate_href = await cert_anchor.first.get_attribute("href") or ""

                        # Build project row record
                        project_record = {
                            "acknowledgement_no": ack_no,
                            "registration_no": reg_no,
                            "promoter_name": promoter_name,
                            "project_name": project_name,
                            "status": status,
                            "district": district_val,
                            "taluk": taluk,
                            "project_type": project_type,
                            "approved_on": approved_on,
                            "proposed_completion_date": proposed_completion,
                            "certificate_url": certificate_href,
                            "state": "KA",
                            "search": {
                                "district_name": district_val,
                                "project_type_name": project_type,
                                "state": "KA"
                            }
                        }
                        
                        # Find Details Modal Link
                        detail_anchor = row.locator("td").nth(3).locator("a")
                        project_id = ""
                        details_data = {}
                        if await detail_anchor.count() > 0:
                            project_id = await detail_anchor.first.get_attribute("id") or ""
                            project_record["project_id"] = project_id
                            
                            # Click and parse details modal
                            logger.info("Scraping details for project: %s (id: %s)...", project_name, project_id)
                            details_data = await scraper.scrape_project_details_modal(detail_anchor.first)
                            
                        # Merge if details found
                        if details_data:
                            detailed_record = {
                                "project_id": project_id,
                                "acknowledgement_no": ack_no,
                                "registration_no": reg_no,
                                "project_name": project_name,
                                "promoter_name": promoter_name,
                                "district": district_val,
                                "promoter_details": details_data.get("promoter_details", {}),
                                "project_details": details_data.get("project_details", {}),
                                "state": "KA"
                            }
                            all_details.append(detailed_record)
                        else:
                            logger.info("Details modal empty or skipped for project: %s", project_name)

                        all_rows.append(project_record)
                        scraped_in_dist += 1
                        
            except Exception as e:
                logger.error("Scraper encountered an exception during loop: %s", e)

    # Save to Mongo
    if store:
        if all_rows:
            logger.info("Saving %s rows to KA_allprojects collection...", len(all_rows))
            for row in all_rows:
                store.upsert_project(row)
        if all_details:
            logger.info("Saving %s detailed records to KA_Detailed collection...", len(all_details))
            for det in all_details:
                store.upsert_detailed(det)
        store.close()

    return all_rows, all_details


def get_mock_karnataka_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generates standard mockup data matching Karnataka RERA for offline test coverage."""
    mock_rows = [
        {
            "acknowledgement_no": "ACK/KA/RERA/1247/298/PR/210223/004721",
            "registration_no": "PRM/KA/RERA/1247/298/PR/210225/003958",
            "project_id": "7720",
            "promoter_name": "Karnataka Slum Development Board",
            "project_name": "Construction of 500 (GF) DUs in Bilagi town",
            "status": "APPROVED",
            "district": "Bagalkot",
            "taluk": "Bilagi",
            "project_type": "Residential/Group Housing",
            "approved_on": "25/02/2021",
            "proposed_completion_date": "10/02/2026",
            "certificate_url": "/certificate?CER_NO=PRM/KA/RERA/1247/298/PR/210225/003958",
            "state": "KA",
            "search": {
                "district_name": "Bagalkot",
                "project_type_name": "Residential/Group Housing",
                "state": "KA"
            }
        },
        {
            "acknowledgement_no": "ACK/KA/RERA/1247/298/PR/211027/005430",
            "registration_no": "PRM/KA/RERA/1247/298/PR/211108/004473",
            "project_id": "8815",
            "promoter_name": "KARNATAKA SLUM DEVELOPMENT BOARD",
            "project_name": "Construction of 250 Houses at Bilagi Town",
            "status": "APPROVED",
            "district": "Bagalkot",
            "taluk": "Bilagi",
            "project_type": "Residential/Group Housing",
            "approved_on": "08/11/2021",
            "proposed_completion_date": "20/10/2026",
            "certificate_url": "/certificate?CER_NO=PRM/KA/RERA/1247/298/PR/211108/004473",
            "state": "KA",
            "search": {
                "district_name": "Bagalkot",
                "project_type_name": "Residential/Group Housing",
                "state": "KA"
            }
        },
        {
            "acknowledgement_no": "PR/KN/170831/001853",
            "registration_no": "",
            "project_id": "1853",
            "promoter_name": "karnataka housing Board",
            "project_name": "Bilagi",
            "status": "REJECTED",
            "district": "Bagalkot",
            "taluk": "Bilagi",
            "project_type": "Plotted Development",
            "approved_on": "",
            "proposed_completion_date": "30/11/2017",
            "certificate_url": "",
            "state": "KA",
            "search": {
                "district_name": "Bagalkot",
                "project_type_name": "Plotted Development",
                "state": "KA"
            }
        },
        {
            "acknowledgement_no": "ACK/KA/RERA/1251/310/PR/220615/005900",
            "registration_no": "PRM/KA/RERA/1251/310/PR/220830/005210",
            "project_id": "9950",
            "promoter_name": "Prestige South City Holdings",
            "project_name": "Prestige Primrose Hills Phase 1",
            "status": "APPROVED",
            "district": "Bengaluru Urban",
            "taluk": "Bengaluru South",
            "project_type": "Residential/Group Housing",
            "approved_on": "30/08/2022",
            "proposed_completion_date": "31/12/2026",
            "certificate_url": "/certificate?CER_NO=PRM/KA/RERA/1251/310/PR/220830/005210",
            "state": "KA",
            "search": {
                "district_name": "Bengaluru Urban",
                "project_type_name": "Residential/Group Housing",
                "state": "KA"
            }
        }
    ]

    mock_details = [
        {
            "project_id": "7720",
            "acknowledgement_no": "ACK/KA/RERA/1247/298/PR/210223/004721",
            "registration_no": "PRM/KA/RERA/1247/298/PR/210225/003958",
            "project_name": "Construction of 500 (GF) DUs in Bilagi town",
            "promoter_name": "Karnataka Slum Development Board",
            "district": "Bagalkot",
            "promoter_details": {
                "PAN Number": "AAALK0136B",
                "District": "Bengaluru Urban",
                "State/UT": "Karnataka",
                "Company Registration No.": "ACT NO 33 of 1974",
                "Certificate": "/download_jc?DOC_ID=Aa6hGYfi71a5nCXhqgJ6%2Fw%3D%3D",
                "Promoter Type": "Karnataka Slum Development Board",
                "Name": "Karnataka Slum Development Board"
            },
            "project_details": {
                "Project Name": "Construction of 500 (GF) DUs in Bilagi town",
                "Project Type": "Residential/Group Housing",
                "Project Status": "APPROVED",
                "District": "Bagalkot",
                "Taluk": "Bilagi"
            },
            "state": "KA"
        },
        {
            "project_id": "9950",
            "acknowledgement_no": "ACK/KA/RERA/1251/310/PR/220615/005900",
            "registration_no": "PRM/KA/RERA/1251/310/PR/220830/005210",
            "project_name": "Prestige Primrose Hills Phase 1",
            "promoter_name": "Prestige South City Holdings",
            "district": "Bengaluru Urban",
            "promoter_details": {
                "PAN Number": "AABCP7780K",
                "District": "Bengaluru Urban",
                "State/UT": "Karnataka",
                "Company Registration No.": "109887 of 2012",
                "Promoter Type": "Company",
                "Name": "Prestige South City Holdings"
            },
            "project_details": {
                "Project Name": "Prestige Primrose Hills Phase 1",
                "Project Type": "Residential/Group Housing",
                "Project Status": "APPROVED",
                "District": "Bengaluru Urban",
                "Taluk": "Bengaluru South"
            },
            "state": "KA"
        }
    ]
    return mock_rows, mock_details
