"""Playwright scraper for Telangana RERA with session reuse."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from urllib.parse import urljoin

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .captcha import refresh_captcha, solve_captcha_from_page
from .certificates import (
    build_certificate_payload,
    parse_directions_onclick,
    parse_map_onclick,
)
from .extractors import extract_project_detail

SEARCH_URL = "https://rerait.telangana.gov.in/SearchList/Search"
BASE_URL = "https://rerait.telangana.gov.in"

SearchType = Literal["project", "promoter"]


@dataclass
class SearchResultRow:
    sr_no: str
    project_name: str
    promoter_name: str
    last_modified: str
    detail_url: str
    certificate_qstr: str | None = None
    extension_certificate_qstr: str | None = None
    rera_registration_id: str | None = None
    directions: dict[str, str] | None = None


@dataclass
class ReraScraper:
    headless: bool = True
    max_captcha_retries: int = 3
    search_delay_ms: int = 1500
    log_fn: Callable[[str, str], None] | None = None

    _playwright: Any = field(default=None, init=False, repr=False)
    _browser: Browser | None = field(default=None, init=False, repr=False)
    _context: BrowserContext | None = field(default=None, init=False, repr=False)
    _page: Page | None = field(default=None, init=False, repr=False)
    _session_ready: bool = field(default=False, init=False, repr=False)

    async def __aenter__(self) -> "ReraScraper":
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(ignore_https_errors=True)
        self._page = await self._context.new_page()
        await self.open_search_page()

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._session_ready = False

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Scraper not started. Call start() first.")
        return self._page

    @property
    def context(self) -> BrowserContext:
        if not self._context:
            raise RuntimeError("Scraper not started.")
        return self._context

    def _log(self, message: str, level: str = "info") -> None:
        if self.log_fn:
            self.log_fn(message, level)
        else:
            print(message)

    async def open_search_page(self) -> None:
        await self.page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
        await self.page.wait_for_selector("#frmSearchList")
        await self.page.check("#Promoter", force=True)
        self._session_ready = True

    async def _clear_search_fields(self) -> None:
        page = self.page
        await page.fill("#Project", "")
        await page.fill("#promoter_name", "")
        await page.fill("#CertiNo", "")
        await page.fill("#Captcha", "")

    async def _submit_search(
        self,
        *,
        project_name: str = "",
        promoter_name: str = "",
    ) -> None:
        page = self.page

        if not self._session_ready:
            await self.open_search_page()

        project_name = project_name.strip()
        promoter_name = promoter_name.strip()

        if not project_name and not promoter_name:
            raise ValueError("Provide a project name and/or promoter name.")

        if project_name and len(project_name) < 4:
            raise ValueError("Project name must be at least 4 characters.")

        await self._clear_search_fields()
        if project_name:
            await page.fill("#Project", project_name)
        if promoter_name:
            await page.fill("#promoter_name", promoter_name)

        captcha = ""
        for attempt in range(self.max_captcha_retries):
            if attempt > 0:
                await refresh_captcha(page)

            captcha = await solve_captcha_from_page(page)
            await page.fill("#Captcha", captcha)
            await page.click("#btnSearch")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(self.search_delay_ms)

            invalid_captcha = await page.locator(
                'span[data-valmsg-for="Captcha"]:not(.field-validation-valid)'
            ).count()
            if invalid_captcha == 0:
                return

        raise RuntimeError(
            f"Captcha verification failed after {self.max_captcha_retries} attempts "
            f"(last attempt: {captcha!r})"
        )

    async def _parse_search_results(self) -> list[SearchResultRow]:
        table = self.page.locator("#projectTable tbody tr")
        row_count = await table.count()
        if row_count == 0:
            return []

        results: list[SearchResultRow] = []
        for i in range(row_count):
            row = table.nth(i)
            cells = row.locator("td")
            detail_href = await row.locator("a.btn-primary").first.get_attribute("href")
            if not detail_href:
                continue

            cert_btn = row.locator('a.btn-success[title="View Certificate"]')
            cert_qstr = (
                await cert_btn.first.get_attribute("data-qstr")
                if await cert_btn.count()
                else None
            )

            ext_btn = row.locator('a[title="View Extension Certificate"]')
            ext_qstr = None
            if await ext_btn.count():
                ext_qstr = await ext_btn.first.get_attribute("data-qstr")

            map_btn = row.locator('a[title="View on Map"]')
            rera_id = None
            if await map_btn.count():
                rera_id = parse_map_onclick(await map_btn.first.get_attribute("onclick"))

            dir_btn = row.locator('a[title="View Directions"]')
            directions = None
            if await dir_btn.count():
                directions = parse_directions_onclick(
                    await dir_btn.first.get_attribute("onclick")
                )

            results.append(
                SearchResultRow(
                    sr_no=(await cells.nth(0).inner_text()).strip(),
                    project_name=(await cells.nth(1).inner_text()).strip(),
                    promoter_name=(await cells.nth(2).inner_text()).strip(),
                    last_modified=(await cells.nth(4).inner_text()).strip(),
                    detail_url=urljoin(BASE_URL, detail_href),
                    certificate_qstr=cert_qstr,
                    extension_certificate_qstr=ext_qstr,
                    rera_registration_id=rera_id,
                    directions=directions,
                )
            )

        return results

    async def search_by_project(self, project_name: str) -> list[SearchResultRow]:
        await self._submit_search(project_name=project_name)
        return await self._parse_search_results()

    async def search_by_promoter(self, promoter_name: str) -> list[SearchResultRow]:
        await self._submit_search(promoter_name=promoter_name)
        return await self._parse_search_results()

    async def scrape_project_detail(self, detail_url: str) -> dict[str, Any]:
        detail_page = await self.context.new_page()
        try:
            await detail_page.goto(detail_url, wait_until="networkidle", timeout=60000)
            await detail_page.wait_for_selector(".container-print", timeout=30000)
            return await extract_project_detail(detail_page)
        finally:
            await detail_page.close()

    async def _build_record(
        self,
        row: SearchResultRow,
        search_query: str,
        search_type: SearchType,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "search_type": search_type,
            "search_query": search_query,
            "sr_no": row.sr_no,
            "result_project_name": row.project_name,
            "result_promoter_name": row.promoter_name,
            "last_modified": row.last_modified,
            "detail_url": row.detail_url,
            "rera_registration_id": row.rera_registration_id,
            "directions": row.directions,
        }

        if row.certificate_qstr:
            self._log(f"  Downloading certificate: {row.project_name}")
            record["certificate"] = await build_certificate_payload(
                self.context, row.certificate_qstr
            )

        if row.extension_certificate_qstr:
            record["extension_certificate"] = await build_certificate_payload(
                self.context, row.extension_certificate_qstr
            )

        if detail:
            record.update(detail)

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
            if row.detail_url in scraped_urls:
                continue

            detail: dict[str, Any] | None = None
            if scrape_details:
                self._log(f"  Scraping detail: {row.project_name}")
                detail = await self.scrape_project_detail(row.detail_url)
                scraped_urls.add(row.detail_url)

            records.append(
                await self._build_record(row, search_query, search_type, detail)
            )

        return records

    async def scrape_promoter_portfolio(
        self,
        promoter_name: str,
        scrape_details: bool = True,
        scraped_urls: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        self._log(f"Searching promoter: {promoter_name}")
        rows = await self.search_by_promoter(promoter_name)
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
            rows = await self.search_by_project(query)
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
                promoter_org = (record.get("promoter_organization_name") or "").strip()
                if not promoter_org:
                    continue
                key = promoter_org.lower()
                if key in searched_promoters:
                    continue

                searched_promoters.add(key)
                self._log(f"  Re-searching by promoter organization: {promoter_org}")
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
    from .exporters import save_records
    from .mongodb import ReraMongoStore

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
        store.ping()
        ids = store.save_records(records)
        store.close()
        print(f"Saved {len(ids)} record(s) to MongoDB {mongo_db}.{mongo_collection}")

    if output_path:
        path = save_records(records, output_path)
        print(f"Exported {len(records)} record(s) to {path}")

    return records
