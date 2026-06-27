"""Advanced search scraper: District × Project Type → project table rows."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urljoin

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .captcha import refresh_captcha, solve_captcha_from_page
from .certificates import parse_directions_onclick, parse_map_onclick
from .infra_store import InfraProjectStore

SEARCH_URL = "https://rerait.telangana.gov.in/SearchList/Search"
BASE_URL = "https://rerait.telangana.gov.in"

logger = logging.getLogger("rera.advanced")


def _filter_from_option(
    options: list["DropdownOption"],
    from_id: str | None,
) -> list["DropdownOption"]:
    if not from_id:
        return options
    for index, option in enumerate(options):
        if option.value == from_id:
            return options[index:]
    raise ValueError(f"Start id {from_id!r} not found in dropdown options")


def _project_identity_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    from .hashing import project_identity_key

    return project_identity_key(row)


def _merge_listing_and_detail(
    listing: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, Any]:
    from .hashing import content_hash, district_hash

    search = listing.get("search") or {}
    district_id = str(search.get("district_id", ""))
    district_name = str(search.get("district_name", ""))
    detail_body = {k: v for k, v in detail.items() if k != "detail_url"}

    return {
        **listing,
        **detail,
        "district_hash": district_hash(district_id, district_name),
        "content_hash": content_hash(detail_body),
        "state": "Telangana",
    }


@dataclass
class DropdownOption:
    value: str
    label: str


@dataclass
class AdvancedSearchScraper:
    headless: bool = True
    max_captcha_retries: int = 3
    search_delay_ms: int = 1500
    log_fn: Callable[[str, str], None] | None = None

    _playwright: Any = field(default=None, init=False, repr=False)
    _browser: Browser | None = field(default=None, init=False, repr=False)
    _context: BrowserContext | None = field(default=None, init=False, repr=False)
    _page: Page | None = field(default=None, init=False, repr=False)

    async def __aenter__(self) -> "AdvancedSearchScraper":
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Scraper not started.")
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
            getattr(logger, level, logger.info)(message)

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

    async def open_search_page(self) -> None:
        await self.page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
        await self.page.wait_for_selector("#frmSearchList")
        await self._show_advanced_search()

    async def _show_advanced_search(self) -> None:
        if not await self.page.locator("#District").is_visible():
            await self._safe_click("#btnAdvance")
            await self.page.wait_for_selector("#District", state="visible")

    async def _dismiss_blocking_overlays(self) -> None:
        page = self.page
        for _ in range(3):
            visible_confirm = page.locator(
                ".sweet-alert.showSweetAlert button.confirm, "
                ".sweet-alert.visible button.confirm"
            )
            if await visible_confirm.count():
                try:
                    await visible_confirm.first.click(timeout=2000)
                    await page.wait_for_timeout(300)
                except Exception:
                    pass

            await page.evaluate(
                """() => {
                    document.querySelectorAll(
                        '.sweet-overlay, .sweet-container, .sweet-alert'
                    ).forEach((el) => el.remove());
                }"""
            )
            if await page.locator(".sweet-overlay").count() == 0:
                break
            await page.wait_for_timeout(200)

    async def _safe_click(self, selector: str) -> None:
        await self._dismiss_blocking_overlays()
        try:
            await self.page.click(selector, timeout=10000)
            return
        except Exception:
            await self._dismiss_blocking_overlays()
            await self.page.click(selector, force=True, timeout=10000)

    async def _get_select_options(self, selector: str) -> list[DropdownOption]:
        options = await self.page.eval_on_selector_all(
            f"{selector} option",
            """els => els.map(o => ({ value: o.value, label: (o.textContent || '').trim() }))""",
        )
        return [
            DropdownOption(value=item["value"], label=item["label"])
            for item in options
            if item["value"]
        ]

    async def get_districts(self) -> list[DropdownOption]:
        await self._show_advanced_search()
        return await self._get_select_options("#District")

    async def get_project_types(self) -> list[DropdownOption]:
        await self._show_advanced_search()
        return await self._get_select_options("#PType")

    async def _solve_captcha_and_retry(self, click_selector: str) -> None:
        page = self.page
        captcha = ""
        for attempt in range(self.max_captcha_retries):
            if attempt > 0:
                await refresh_captcha(page)

            captcha = await solve_captcha_from_page(page)
            await page.fill("#Captcha", captcha)
            await self._safe_click(click_selector)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(self.search_delay_ms)
            await self._dismiss_blocking_overlays()

            invalid = await page.locator(
                'span[data-valmsg-for="Captcha"]:not(.field-validation-valid)'
            ).count()
            if invalid == 0:
                return

        raise RuntimeError(
            f"Captcha failed after {self.max_captcha_retries} attempts "
            f"(last: {captcha!r})"
        )

    async def _submit_advanced_search(
        self,
        district: DropdownOption,
        project_type: DropdownOption,
    ) -> None:
        await self._show_advanced_search()
        await self.page.select_option("#District", district.value)
        await self.page.wait_for_timeout(400)
        await self.page.select_option("#PType", project_type.value)
        await self.page.evaluate(
            """([district, ptype]) => {
                const hdnDistrict = document.querySelector('#hdnDistrict');
                const hdnPType = document.querySelector('#hdnPType');
                if (hdnDistrict) hdnDistrict.value = district;
                if (hdnPType) hdnPType.value = ptype;
            }""",
            [district.value, project_type.value],
        )
        await self.page.fill("#Project", "")
        await self.page.fill("#promoter_name", "")
        await self.page.fill("#CertiNo", "")
        await self.page.fill("#Captcha", "")
        await self._solve_captcha_and_retry("#btnSearch")

    async def _has_results(self) -> bool:
        if await self.page.locator("#CurrentPage").count():
            return True
        return await self.page.locator("#projectTable tbody tr").count() > 0

    async def _pagination_info(self) -> tuple[int, int, int]:
        if not await self.page.locator("#CurrentPage").count():
            return 1, 1, 0

        page = self.page
        current = int(await page.input_value("#CurrentPage") or "1")
        total_pages = int(await page.input_value("#TotalPages") or "1")
        total_records = int(await page.input_value("#TotalRecords") or "0")
        return current, total_pages, total_records

    async def _has_next_page(self) -> bool:
        if not await self.page.locator("#btnNext").count():
            return False
        disabled = await self.page.locator("#btnNext").get_attribute("disabled")
        return disabled is None

    async def _prefill_captcha_if_empty(self) -> None:
        captcha_input = self.page.locator("#Captcha")
        if not await captcha_input.count() or not await captcha_input.is_visible():
            return
        if (await captcha_input.input_value()).strip():
            return
        captcha = await solve_captcha_from_page(self.page)
        await captcha_input.fill(captcha)

    async def _go_next_page(self) -> None:
        current_before, _, _ = await self._pagination_info()
        await self._prefill_captcha_if_empty()
        await self._safe_click("#btnNext")
        await self.page.wait_for_load_state("networkidle")
        await self._wait_for_page_change(current_before)

    async def _wait_for_page_change(self, previous_page: int) -> None:
        await self.page.wait_for_timeout(self.search_delay_ms)
        current_after, _, _ = await self._pagination_info()
        if current_after > previous_page:
            await self._prefill_captcha_if_empty()
            return

        if await self.page.locator("#Captcha").is_visible():
            await self._solve_captcha_and_retry("#btnNext")
            current_after, _, _ = await self._pagination_info()
            if current_after > previous_page:
                await self._prefill_captcha_if_empty()
                return

        raise RuntimeError(
            f"Pagination stuck on page {previous_page} (still {current_after})"
        )

    async def _parse_table_rows(
        self,
        district: DropdownOption,
        project_type: DropdownOption,
    ) -> list[dict[str, Any]]:
        table = self.page.locator("#projectTable tbody tr")
        row_count = await table.count()
        if row_count == 0:
            return []

        rows: list[dict[str, Any]] = []
        for i in range(row_count):
            row = table.nth(i)
            try:
                view_link = row.locator("a.btn-primary")
                if await view_link.count() == 0:
                    self._log(
                        f"  Skipping table row {i + 1}: no View Details link",
                        level="warning",
                    )
                    continue

                detail_href = await view_link.first.get_attribute("href")
                if not detail_href:
                    continue

                cells = row.locator("td")

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
                    rera_id = parse_map_onclick(
                        await map_btn.first.get_attribute("onclick")
                    )

                dir_btn = row.locator('a[title="View Directions"]')
                directions = None
                if await dir_btn.count():
                    directions = parse_directions_onclick(
                        await dir_btn.first.get_attribute("onclick")
                    )

                rows.append(
                    {
                        "sr_no": (await cells.nth(0).inner_text()).strip(),
                        "project_name": (await cells.nth(1).inner_text()).strip(),
                        "promoter_name": (await cells.nth(2).inner_text()).strip(),
                        "detail_url": urljoin(BASE_URL, detail_href),
                        "last_modified": (await cells.nth(4).inner_text()).strip(),
                        "certificate_qstr": cert_qstr,
                        "extension_certificate_qstr": ext_qstr,
                        "rera_registration_id": rera_id,
                        "directions": directions,
                        "search": {
                            "district_id": district.value,
                            "district_name": district.label,
                            "project_type_id": project_type.value,
                            "project_type_name": project_type.label,
                        },
                    }
                )
            except Exception as exc:
                self._log(
                    f"  Skipping table row {i + 1}: {exc}",
                    level="warning",
                )

        return rows

    async def scrape_project_detail(self, detail_url: str) -> dict[str, Any]:
        from .extractors import extract_project_detail

        detail_page = await self.context.new_page()
        try:
            await detail_page.goto(detail_url, wait_until="networkidle", timeout=90000)
            await detail_page.wait_for_selector(".container-print", timeout=45000)
            return await extract_project_detail(detail_page)
        finally:
            await detail_page.close()

    async def scrape_combination_with_details(
        self,
        district: DropdownOption,
        project_type: DropdownOption,
        *,
        max_pages: int | None = None,
        skip_keys: set[tuple[str, str, str, str]] | None = None,
        on_record: Callable[[dict[str, Any]], None] | None = None,
    ) -> int:
        label = f"{district.label} / {project_type.label}"
        self._log(f"Advanced search + details: {label}")
        await self.open_search_page()
        await self._dismiss_blocking_overlays()
        await self._submit_advanced_search(district, project_type)
        await self._dismiss_blocking_overlays()

        if not await self._has_results():
            self._log(f"  No results for {label}")
            return 0

        skip_keys = skip_keys or set()
        saved_count = 0

        while True:
            current, total_pages, total_records = await self._pagination_info()
            page_rows = await self._parse_table_rows(district, project_type)
            self._log(
                f"  Page {current}/{total_pages}: {len(page_rows)} row(s) "
                f"(total records: {total_records})"
            )

            for row in page_rows:
                key = _project_identity_key(row)
                if key in skip_keys:
                    self._log(f"  Skipping existing detail: {row['project_name']}")
                    continue

                try:
                    self._log(f"  Scraping detail: {row['project_name']}")
                    detail = await self.scrape_project_detail(row["detail_url"])
                    record = _merge_listing_and_detail(row, detail)
                    skip_keys.add(key)
                    saved_count += 1
                    if on_record:
                        on_record(record)
                except Exception as exc:
                    self._log(
                        f"  Detail scrape failed for {row['project_name']}: {exc}",
                        level="error",
                    )

            if max_pages is not None and current >= max_pages:
                break
            if not await self._has_next_page():
                break

            await self._go_next_page()

        self._log(f"  Saved {saved_count} detailed record(s) for {label}")
        await self._dismiss_blocking_overlays()
        return saved_count

    async def scrape_combination(
        self,
        district: DropdownOption,
        project_type: DropdownOption,
        *,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        label = f"{district.label} / {project_type.label}"
        self._log(f"Advanced search: {label}")
        await self.open_search_page()
        await self._dismiss_blocking_overlays()
        await self._submit_advanced_search(district, project_type)
        await self._dismiss_blocking_overlays()

        if not await self._has_results():
            self._log(f"  No results for {label}")
            return []

        all_rows: list[dict[str, Any]] = []
        while True:
            current, total_pages, total_records = await self._pagination_info()
            page_rows = await self._parse_table_rows(district, project_type)
            all_rows.extend(page_rows)
            self._log(
                f"  Page {current}/{total_pages}: {len(page_rows)} row(s) "
                f"(total records: {total_records})"
            )

            if max_pages is not None and current >= max_pages:
                break
            if not await self._has_next_page():
                break

            await self._go_next_page()

        self._log(f"  Collected {len(all_rows)} row(s) for {label}")
        await self._dismiss_blocking_overlays()
        return all_rows

    async def scrape_all(
        self,
        *,
        districts: list[DropdownOption] | None = None,
        project_types: list[DropdownOption] | None = None,
        max_pages: int | None = None,
        store: InfraProjectStore | None = None,
    ) -> list[dict[str, Any]]:
        districts = districts or await self.get_districts()
        project_types = project_types or await self.get_project_types()

        self._log(
            f"Starting advanced scrape: {len(districts)} district(s) × "
            f"{len(project_types)} project type(s)"
        )

        all_rows: list[dict[str, Any]] = []
        for district in districts:
            for project_type in project_types:
                try:
                    rows = await self.scrape_combination(
                        district,
                        project_type,
                        max_pages=max_pages,
                    )
                except Exception as exc:
                    self._log(
                        f"  Failed {district.label} / {project_type.label}: {exc}",
                        level="error",
                    )
                    try:
                        await self.open_search_page()
                        await self._dismiss_blocking_overlays()
                    except Exception:
                        pass
                    continue
                all_rows.extend(rows)
                if store and rows:
                    saved = store.upsert_projects(rows)
                    self._log(f"  Saved {saved} row(s) to INFRA.All_projects")

        self._log(f"Advanced scrape finished: {len(all_rows)} total row(s)")
        return all_rows


async def run_advanced_scraper(
    *,
    headless: bool = True,
    mongo_uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
    mongo_db: str = "INFRA",
    mongo_collection: str = "All_projects",
    district_ids: list[str] | None = None,
    project_type_ids: list[str] | None = None,
    from_district_id: str | None = None,
    from_project_type_id: str | None = None,
    max_pages: int | None = None,
    save_mongo: bool = True,
) -> list[dict[str, Any]]:
    store: InfraProjectStore | None = None
    if save_mongo:
        store = InfraProjectStore(mongo_uri, mongo_db, mongo_collection)
        store.ping()
        logger.info("MongoDB %s.%s — existing docs: %s", mongo_db, mongo_collection, store.count())

    async with AdvancedSearchScraper(headless=headless) as scraper:
        all_districts = await scraper.get_districts()
        all_types = await scraper.get_project_types()

        districts = (
            [d for d in all_districts if d.value in district_ids]
            if district_ids
            else all_districts
        )
        project_types = (
            [t for t in all_types if t.value in project_type_ids]
            if project_type_ids
            else all_types
        )
        districts = _filter_from_option(districts, from_district_id)
        project_types = _filter_from_option(project_types, from_project_type_id)

        if from_district_id and not districts:
            raise ValueError(f"--from-district {from_district_id} not in selected districts")
        if from_project_type_id and not project_types:
            raise ValueError(
                f"--from-project-type {from_project_type_id} not in selected project types"
            )

        if district_ids and not districts:
            raise ValueError(f"No matching districts for ids: {district_ids}")
        if project_type_ids and not project_types:
            raise ValueError(f"No matching project types for ids: {project_type_ids}")

        rows = await scraper.scrape_all(
            districts=districts,
            project_types=project_types,
            max_pages=max_pages,
            store=store,
        )

    if store:
        logger.info(
            "MongoDB %s.%s — total docs after scrape: %s",
            mongo_db,
            mongo_collection,
            store.count(),
        )
        store.close()

    return rows
