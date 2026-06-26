"""Playwright-based scraper for Karnataka RERA."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import async_playwright, Page, Browser, Locator
from .extractors import extract_detailed_tabs
from .infra_store import KAProjectStore

logger = logging.getLogger("rera.scraper")


class KAReraScraper:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self.playwright = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> KAReraScraper:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-web-security", "--no-sandbox"],
        )
        # Create context with longer timeouts
        context = await self.browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        context.set_default_timeout(30000)
        self.page = await context.new_page()

    async def stop(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def navigate_to_portal(self, max_retries: int = 3) -> bool:
        """Navigates to the projectViewDetails page with retry logic."""
        url = "https://rera.karnataka.gov.in/projectViewDetails"
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Navigating to Karnataka RERA portal (attempt %s/%s)...", attempt, max_retries)
                # Use wait_until domcontentloaded or commit to handle slow servers
                response = await self.page.goto(url, wait_until="domcontentloaded", timeout=35000)
                if response and response.status == 200:
                    logger.info("Successfully navigated to portal.")
                    return True
                else:
                    logger.warning("Portal responded with status: %s", response.status if response else "No response")
            except Exception as e:
                logger.error("Navigation failed: %s", e)
            await asyncio.sleep(3)
        return False

    async def get_districts(self) -> list[str]:
        """Reads all option values from the district dropdown."""
        try:
            # First, click the Applied For Registration tab
            tab_selector = 'a[data-toggle="tab"][href="#1"]'
            if await self.page.locator(tab_selector).count() > 0:
                await self.page.locator(tab_selector).click()
                await asyncio.sleep(1)

            # Wait for district dropdown
            await self.page.wait_for_selector("select#projectDist", timeout=5000)
            options = await self.page.locator("select#projectDist option").all()
            districts = []
            for opt in options:
                val = await opt.get_attribute("value")
                text = await opt.inner_text()
                if val and val != "0" and val != "":
                    districts.append(val.strip())
            logger.info("Found %s district(s) in dropdown: %s", len(districts), districts)
            return districts
        except Exception as e:
            logger.error("Failed to retrieve districts: %s", e)
            return []

    async def select_district_and_search(self, district: str) -> bool:
        """Selects a district and triggers the search."""
        try:
            logger.info("Selecting district: %s", district)
            await self.page.select_option("select#projectDist", value=district)
            await asyncio.sleep(1)

            # Click search button (btn1)
            search_btn = self.page.locator("input[type='submit'][value='Search'], #loginFormID input[name='btn1']")
            if await search_btn.count() > 0:
                await search_btn.click()
            else:
                # Fallback form submit
                await self.page.evaluate("document.getElementById('loginFormID').submit()")

            # Wait for search results table to load or refresh
            logger.info("Waiting for table results...")
            await self.page.wait_for_selector("#approvedTable", timeout=15000)
            await asyncio.sleep(2)

            # Try to force 500 page size
            await self.page.evaluate("""() => {
                const select = document.querySelector('select[name="approvedTable_length"]');
                if (select) {
                    const opt = document.createElement('option');
                    opt.value = '500';
                    opt.innerHTML = '500';
                    select.appendChild(opt);
                    select.value = '500';
                    select.dispatchEvent(new Event('change'));
                }
            }""")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error("Failed search for district %s: %s", district, e)
            return False

    async def scrape_project_details_modal(self, anchor: Locator) -> dict[str, Any]:
        """Clicks the project details anchor and extracts Promoter and Project tabs."""
        detail_html = ""
        popup_page = None
        try:
            # We try to expect a new tab/popup
            async with self.page.context.expect_page(timeout=4000) as page_info:
                await anchor.click()
            popup_page = await page_info.value
            await popup_page.wait_for_load_state()
            detail_html = await popup_page.content()
            await popup_page.close()
        except Exception:
            # Assume it opened an inline modal on the same page
            try:
                await self.page.wait_for_selector("#home", timeout=2000)
                detail_html = await self.page.content()
                # Close the modal
                close_btn = self.page.locator(".modal-header button.close, #closeModalBtn, .close, button[data-dismiss='modal']")
                if await close_btn.count() > 0:
                    await close_btn.first.click()
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug("Failed to extract inline modal details: %s", e)

        if not detail_html:
            return {}

        try:
            return extract_detailed_tabs(detail_html)
        except Exception as e:
            logger.error("Error parsing detailed tabs: %s", e)
            return {}
