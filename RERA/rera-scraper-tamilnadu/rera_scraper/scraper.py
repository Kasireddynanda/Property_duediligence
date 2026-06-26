"""Requests-based scraper for Tamil Nadu RERA with cache-based fast search."""

from __future__ import annotations

import logging
import re
import urllib3
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .extractors import extract_project_detail, extract_promoter_detail
from .exporters import save_records
from .mongodb import ReraMongoStore

# Disable insecure request warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://rera.tn.gov.in"
REGISTERED_BUILDING_URL = "https://rera.tn.gov.in/registered-building/tn"

SearchType = Literal["project", "promoter"]

logger = logging.getLogger("rera.scraper")


@dataclass
class SearchResultRow:
    sr_no: str
    registration_no: str
    registration_date: str
    promoter_name: str
    promoter_address: str
    project_name: str
    project_address: str
    approval_details: str
    completion_date: str
    promoter_details_url: str
    detail_url: str
    latitude: str
    longitude: str
    form_c_url: str
    status_text: str
    year: str


@dataclass
class ReraScraper:
    headless: bool = True
    max_captcha_retries: int = 3
    search_delay_ms: int = 1500
    log_fn: Callable[[str, str], None] | None = None

    _session: requests.Session = field(default_factory=requests.Session, init=False, repr=False)
    _cached_rows: list[SearchResultRow] | None = field(default=None, init=False, repr=False)

    async def __aenter__(self) -> "ReraScraper":
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def start(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self._log("Tamil Nadu RERA Scraper initialized.")

    async def close(self) -> None:
        self._session.close()

    def _log(self, message: str, level: str = "info") -> None:
        if self.log_fn:
            self.log_fn(message, level)
        else:
            print(f"[{level.upper()}] {message}")

    def _fetch_all_table_rows(self) -> list[SearchResultRow]:
        if self._cached_rows is not None:
            return self._cached_rows

        self._log("Fetching all registered building projects from Tamil Nadu RERA portal...")
        all_rows: list[SearchResultRow] = []

        try:
            # 1. Perform GET to retrieve initial cookies and CSRF token
            resp = self._session.get(REGISTERED_BUILDING_URL, verify=False, timeout=30)
            if resp.status_code != 200:
                self._log(f"Failed to fetch TN RERA index page: HTTP {resp.status_code}", "error")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract years from the select dropdown
            select_year = soup.find("select", {"id": "year"})
            years = ["2026", "2025", "2024", "2023"]
            if select_year:
                parsed_years = [opt.get("value") for opt in select_year.find_all("option") if opt.get("value")]
                if parsed_years:
                    years = parsed_years

            self._log(f"Identified registered project years: {years}")

            # Extract CSRF token
            token_input = soup.find("input", {"name": "_token"})
            token = token_input["value"] if token_input else ""

            # Fetch table rows for each year
            for year in years:
                self._log(f"Fetching table rows for year: {year}")
                data = {"_token": token, "year": year}
                
                # Fetch via POST
                post_resp = self._session.post(REGISTERED_BUILDING_URL, data=data, verify=False, timeout=30)
                if post_resp.status_code != 200:
                    self._log(f"Failed to fetch projects for year {year}: HTTP {post_resp.status_code}", "warning")
                    continue

                year_soup = BeautifulSoup(post_resp.text, "html.parser")
                table = year_soup.find("table", {"id": "example1"}) or year_soup.find("table")
                if not table:
                    self._log(f"No table found for year {year}", "warning")
                    continue

                tr_elements = table.find_all("tr")[1:] # Skip header row
                self._log(f"Found {len(tr_elements)} projects in year {year}")

                clean = lambda text: re.sub(r"\s+", " ", text).strip() if text else ""

                for tr in tr_elements:
                    cells = tr.find_all("td")
                    if len(cells) < 9:
                        continue

                    sr_no = clean(cells[0].get_text())

                    # Parse Reg No & Date
                    reg_text = clean(cells[1].get_text(separator=" "))
                    reg_match = re.search(r"(TNRERA/\S+)\s*(?:dated\s*(.*))?", reg_text, re.IGNORECASE)
                    reg_no = reg_match.group(1) if reg_match else reg_text
                    reg_date = reg_match.group(2) if reg_match and reg_match.group(2) else ""

                    # Promoter Name & Address
                    promoter_text = clean(cells[2].get_text())
                    promoter_parts = [p.strip() for p in promoter_text.split(",") if p.strip()]
                    promoter_name = promoter_parts[0] if promoter_parts else "Unknown Promoter"
                    promoter_address = ", ".join(promoter_parts[1:]) if len(promoter_parts) > 1 else promoter_text

                    # Project Details & Address
                    project_text = clean(cells[3].get_text())
                    proj_name_match = re.search(r"Project Name:\s*(.*?)(?:Registration of|Registration for|$)", project_text, re.IGNORECASE)
                    project_name = proj_name_match.group(1).strip() if proj_name_match else "Unknown Project"
                    project_address = project_text

                    approval_details = clean(cells[4].get_text())
                    completion_date = clean(cells[5].get_text())

                    # Other details (Links & Location)
                    other_td = cells[6]
                    promoter_link_el = other_td.find("a", href=lambda h: h and "public-view1" in h)
                    promoter_details_url = urljoin(BASE_URL, promoter_link_el["href"]) if promoter_link_el else ""

                    project_link_el = other_td.find("a", href=lambda h: h and "public-view2" in h)
                    project_details_url = urljoin(BASE_URL, project_link_el["href"]) if project_link_el else ""

                    lat_lon_text = other_td.get_text()
                    lat_match = re.search(r"Latitude-?\s*([0-9.]+)", lat_lon_text, re.IGNORECASE)
                    lon_match = re.search(r"Longitude-?\s*([0-9.]+)", lat_lon_text, re.IGNORECASE)
                    latitude = lat_match.group(1) if lat_match else ""
                    longitude = lon_match.group(1) if lon_match else ""

                    # Form C link
                    form_c_td = cells[7]
                    form_c_link_el = form_c_td.find("a", href=True)
                    form_c_url = urljoin(BASE_URL, form_c_link_el["href"]) if form_c_link_el else ""

                    status_text = clean(cells[8].get_text())

                    all_rows.append(
                        SearchResultRow(
                            sr_no=sr_no,
                            registration_no=reg_no,
                            registration_date=reg_date,
                            promoter_name=promoter_name,
                            promoter_address=promoter_address,
                            project_name=project_name,
                            project_address=project_address,
                            approval_details=approval_details,
                            completion_date=completion_date,
                            promoter_details_url=promoter_details_url,
                            detail_url=project_details_url,
                            latitude=latitude,
                            longitude=longitude,
                            form_c_url=form_c_url,
                            status_text=status_text,
                            year=year,
                        )
                    )

        except Exception as e:
            self._log(f"Error during fetching table rows: {e}", "error")

        self._cached_rows = all_rows
        self._log(f"Successfully cached {len(all_rows)} registered projects in total.")
        return all_rows

    def search_by_project(self, project_name: str) -> list[SearchResultRow]:
        rows = self._fetch_all_table_rows()
        q = project_name.strip().lower()
        if not q:
            return []
        return [r for r in rows if q in r.project_name.lower()]

    def search_by_promoter(self, promoter_name: str) -> list[SearchResultRow]:
        rows = self._fetch_all_table_rows()
        q = promoter_name.strip().lower()
        if not q:
            return []
        return [r for r in rows if q in r.promoter_name.lower()]

    def scrape_project_detail(self, detail_url: str) -> dict[str, Any]:
        """Fetch and extract project details page."""
        if not detail_url:
            return {}
        try:
            resp = self._session.get(detail_url, verify=False, timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                return extract_project_detail(soup)
        except Exception as e:
            self._log(f"Error scraping project details at {detail_url}: {e}", "warning")
        return {}

    def scrape_promoter_detail(self, promoter_url: str) -> dict[str, Any]:
        """Fetch and extract promoter details page."""
        if not promoter_url:
            return {}
        try:
            resp = self._session.get(promoter_url, verify=False, timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                return extract_promoter_detail(soup)
        except Exception as e:
            self._log(f"Error scraping promoter details at {promoter_url}: {e}", "warning")
        return {}

    async def _build_record(
        self,
        row: SearchResultRow,
        search_query: str,
        search_type: SearchType,
        scrape_details: bool = True,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "search_type": search_type,
            "search_query": search_query,
            "sr_no": row.sr_no,
            "result_project_name": row.project_name,
            "result_promoter_name": row.promoter_name,
            "project_name": row.project_name,
            "promoter_name": row.promoter_name,
            "last_modified": row.registration_date or row.completion_date,
            "detail_url": row.detail_url,
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
                "district_name": "",
                "project_type_name": "Building",
                "state": "TN"
            }
        }

        if scrape_details:
            if row.detail_url:
                self._log(f"  Scraping project detail: {row.project_name}")
                proj_detail = self.scrape_project_detail(row.detail_url)
                if proj_detail:
                    record.update(proj_detail)
                    # Update search info from detail page
                    if "project_information" in proj_detail:
                        district = proj_detail.get("raw_project_details", {}).get("District", "")
                        usage = proj_detail.get("raw_project_details", {}).get("Usage", "")
                        record["search"]["district_name"] = district
                        record["search"]["project_type_name"] = usage

            if row.promoter_details_url:
                self._log(f"  Scraping promoter detail: {row.promoter_name}")
                prom_detail = self.scrape_promoter_detail(row.promoter_details_url)
                if prom_detail:
                    record.update(prom_detail)

        return record

    async def _scrape_result_rows(
        self,
        rows: list[SearchResultRow],
        search_query: str,
        search_type: SearchType,
        scrape_details: bool,
        scraped_urls: set[str],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for row in rows:
            url_key = row.detail_url or f"{row.project_name}::{row.promoter_name}"
            if url_key in scraped_urls:
                continue

            record = await self._build_record(
                row,
                search_query=search_query,
                search_type=search_type,
                scrape_details=scrape_details
            )
            records.append(record)
            if row.detail_url:
                scraped_urls.add(row.detail_url)

        return records

    async def scrape_promoter_portfolio(
        self,
        promoter_name: str,
        scrape_details: bool = True,
        scraped_urls: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        self._log(f"Searching promoter: {promoter_name}")
        rows = self.search_by_promoter(promoter_name)
        self._log(f"  Found {len(rows)} result(s) for promoter")

        return await self._scrape_result_rows(
            rows,
            search_query=promoter_name,
            search_type="promoter",
            scrape_details=scrape_details,
            scraped_urls=scraped_urls or set(),
        )

    async def scrape_projects(
        self,
        project_names: list[str],
        scrape_details: bool = True,
        follow_promoter_search: bool = True,
    ) -> list[dict[str, Any]]:
        all_records: list[dict[str, Any]] = []
        scraped_urls: set[str] = set()
        searched_promoters: set[str] = set()

        for query in project_names:
            self._log(f"Searching project: {query}")
            rows = self.search_by_project(query)
            self._log(f"  Found {len(rows)} result(s)")

            project_records = await self._scrape_result_rows(
                rows,
                search_query=query,
                search_type="project",
                scrape_details=scrape_details,
                scraped_urls=scraped_urls,
            )
            all_records.extend(project_records)

            if not follow_promoter_search:
                continue

            for record in project_records:
                promoter_org = record.get("result_promoter_name") or record.get("promoter_name")
                if not promoter_org:
                    continue
                key = promoter_org.strip().lower()
                if key in searched_promoters:
                    continue

                searched_promoters.add(key)
                self._log(f"  Re-searching by promoter: {promoter_org}")
                promoter_records = await self.scrape_promoter_portfolio(
                    promoter_org,
                    scrape_details=scrape_details,
                    scraped_urls=scraped_urls,
                )
                all_records.extend(promoter_records)

        return all_records

    async def scrape_promoters(
        self,
        promoter_names: list[str],
        scrape_details: bool = True,
    ) -> list[dict[str, Any]]:
        all_records: list[dict[str, Any]] = []
        scraped_urls: set[str] = set()

        for promoter in promoter_names:
            records = await self.scrape_promoter_portfolio(
                promoter,
                scrape_details=scrape_details,
                scraped_urls=scraped_urls,
            )
            all_records.extend(records)

        return all_records


async def run_scraper(
    project_names: list[str] | None = None,
    promoter_names: list[str] | None = None,
    output_path: str | None = None,
    headless: bool = True,
    follow_promoter_search: bool = True,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "RERA-DETAILS",
    mongo_collection: str = "DETAILS",
    save_mongo: bool = True,
) -> list[dict[str, Any]]:
    async with ReraScraper(headless=headless) as scraper:
        records: list[dict[str, Any]] = []

        if project_names:
            records.extend(
                await scraper.scrape_projects(
                    project_names,
                    follow_promoter_search=follow_promoter_search,
                )
            )

        if promoter_names:
            records.extend(await scraper.scrape_promoters(promoter_names))

    if save_mongo:
        store = ReraMongoStore(mongo_uri, mongo_db, mongo_collection)
        try:
            store.ping()
            ids = store.save_records(records)
            print(f"Saved {len(ids)} record(s) to MongoDB {mongo_db}.{mongo_collection}")
        except Exception as e:
            print(f"MongoDB connection/save failed: {e}")
        finally:
            store.close()

    if output_path:
        path = save_records(records, output_path)
        print(f"Exported {len(records)} record(s) to {path}")

    return records
