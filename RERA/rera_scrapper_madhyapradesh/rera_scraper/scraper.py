"""Playwright-based scraper for Madhya Pradesh RERA (rera.mp.gov.in).

Strategy
--------
The listing page at https://www.rera.mp.gov.in/projects-completed/ is a
server-rendered DataTable (jQuery DataTables).  All 1 039+ entries are already
present in the page HTML (hidden rows injected server-side) – the DataTable
just re-renders visible rows when the user changes the page or page-size.

We therefore:
1.  Load the page once.
2.  Inject a JS snippet to switch the DataTable to show 10 000 entries
    so every row is visible in the DOM simultaneously.
3.  Parse every <tr> in #example tbody using BeautifulSoup.
4.  For each row follow the "View" link in a new tab and parse the
    Project Information / Location / Promoter Information sections.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import Browser, Page, async_playwright

from .extractors import extract_project_detail_page

logger = logging.getLogger("rera.mp.scraper")

LISTING_URL = "https://www.rera.mp.gov.in/projects-completed/"
BASE_URL = "https://www.rera.mp.gov.in"


class MPReraScraper:
    """Async context-manager wrapping a Playwright browser session."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self.playwright = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> MPReraScraper:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-web-security", "--no-sandbox"],
        )
        context = await self.browser.new_context(
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
        )
        context.set_default_timeout(60_000)
        self.page = await context.new_page()

    async def stop(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # ------------------------------------------------------------------
    # Listing page
    # ------------------------------------------------------------------

    async def navigate_to_listing(self, max_retries: int = 3) -> bool:
        """Navigate to the completed-projects listing page."""
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Navigating to MP RERA listing (attempt %s/%s)…",
                    attempt,
                    max_retries,
                )
                response = await self.page.goto(
                    LISTING_URL,
                    wait_until="networkidle",
                    timeout=60_000,
                )
                if response and response.status == 200:
                    # Wait for DataTable to initialise
                    await self.page.wait_for_selector("#example tbody tr", timeout=20_000)
                    logger.info("Listing page loaded successfully.")
                    return True
                logger.warning("Listing page status: %s", response.status if response else "none")
            except Exception as exc:
                logger.error("Navigation attempt %s failed: %s", attempt, exc)
            await asyncio.sleep(4)
        return False

    async def _expand_all_rows(self) -> None:
        """
        Force the DataTable to show all rows by selecting the maximum page
        length.  We inject a large value (10000) directly because the dropdown
        only goes up to 100.
        """
        try:
            await self.page.evaluate("""() => {
                // Access the DataTable API
                const table = $('#example').DataTable();
                // Change page length to a very large number to show all rows
                table.page.len(10000).draw();
            }""")
            # Give DataTable time to re-render
            await asyncio.sleep(3)
            await self.page.wait_for_selector("#example tbody tr", timeout=15_000)
            row_count = await self.page.locator("#example tbody tr").count()
            logger.info("DataTable expanded: %s row(s) visible.", row_count)
        except Exception as exc:
            logger.warning("Could not expand DataTable via API: %s — trying select approach.", exc)
            try:
                # Fallback: set select to 100 (maximum available option)
                await self.page.select_option('select[name="example_length"]', value="100")
                await asyncio.sleep(2)
            except Exception as exc2:
                logger.warning("Fallback expand also failed: %s", exc2)

    async def get_listing_rows_html(self) -> str:
        """Return the full page HTML after expanding all rows."""
        await self._expand_all_rows()
        return await self.page.content()

    # ------------------------------------------------------------------
    # Detail page
    # ------------------------------------------------------------------

    async def fetch_detail_page(self, detail_url: str) -> str:
        """Open a detail URL in a new tab and return its HTML."""
        new_page: Page | None = None
        try:
            new_page = await self.browser.new_page()
            new_page.set_default_timeout(40_000)
            response = await new_page.goto(detail_url, wait_until="domcontentloaded", timeout=40_000)
            if response and response.status == 200:
                # Wait for the project-info container to appear
                try:
                    await new_page.wait_for_selector(".container .title", timeout=10_000)
                except Exception:
                    pass
                html = await new_page.content()
                return html
            logger.warning("Detail page returned status %s for URL: %s", response.status if response else "?", detail_url)
            return ""
        except Exception as exc:
            logger.error("Failed to fetch detail page %s: %s", detail_url, exc)
            return ""
        finally:
            if new_page:
                await new_page.close()
