"""Captcha solving for Telangana RERA portal."""

from __future__ import annotations

import ddddocr
from playwright.async_api import Page

_ocr = ddddocr.DdddOcr(show_ad=False)


async def solve_captcha_from_page(page: Page) -> str:
    image = await page.locator("#captchaImage").screenshot()
    return _ocr.classification(image)


async def refresh_captcha(page: Page) -> None:
    await page.click('button:has-text("Try another")')
    await page.wait_for_timeout(500)
