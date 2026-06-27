"""Sync Playwright extractors for threaded detail scraping."""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Locator, Page


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _cell_value(col: Locator) -> str:
    return _clean(col.inner_text())


def _extract_panel_pairs(panel: Locator, prefix: str = "") -> dict[str, str]:
    data: dict[str, str] = {}
    rows = panel.locator(":scope > .x_content .row, :scope .x_content.label-block .row")
    row_count = rows.count()

    for i in range(row_count):
        row = rows.nth(i)
        cols = row.locator(":scope > .form-group > .col-md-3, :scope > .col-md-3")
        col_count = cols.count()

        j = 0
        while j < col_count:
            col = cols.nth(j)
            label_el = col.locator("label")
            if label_el.count() == 0:
                j += 1
                continue

            key = _clean(label_el.first.inner_text()).rstrip(":")
            if not key:
                j += 1
                continue

            value = ""
            if j + 1 < col_count:
                value_col = cols.nth(j + 1)
                if value_col.locator("label").count() == 0:
                    value = _cell_value(value_col)
                    j += 2
                else:
                    j += 1
            else:
                j += 1

            if not value:
                continue

            field_key = f"{prefix}{key}" if prefix else key
            if field_key not in data:
                data[field_key] = value

    return data


def _extract_panel_by_title(page: Page, title: str) -> dict[str, str]:
    panel = page.locator(f'.x_panel:has(.x_title h2:text-is("{title}"))')
    if panel.count() == 0:
        return {}
    return _extract_panel_pairs(panel.first)


def extract_bank_details(page: Page) -> dict[str, str]:
    panel = page.locator('.x_panel:has(.x_title h2:text-is("Bank Details"))')
    if panel.count() == 0:
        return {}

    data: dict[str, str] = {}
    blocks = panel.first.locator(".x_content.label-block")
    block_count = blocks.count()

    for i in range(block_count):
        block = blocks.nth(i)
        heading = block.locator("h4")
        prefix = ""
        if heading.count() > 0:
            prefix = _clean(heading.first.inner_text()) + " - "

        rows = block.locator(".row")
        for r in range(rows.count()):
            row = rows.nth(r)
            cols = row.locator(".col-md-3")
            col_count = cols.count()
            j = 0
            while j < col_count:
                col = cols.nth(j)
                label_el = col.locator("label")
                if label_el.count() == 0:
                    j += 1
                    continue
                key = _clean(label_el.first.inner_text()).rstrip(":")
                value = ""
                if j + 1 < col_count:
                    value = _cell_value(cols.nth(j + 1))
                    j += 2
                else:
                    j += 1
                if key and value:
                    data[f"{prefix}{key}"] = value

    return data


def extract_members(page: Page) -> list[dict[str, str]]:
    table = page.locator('table:has(th:text("Member Name"))')
    if table.count() == 0:
        return []

    members: list[dict[str, str]] = []
    rows = table.first.locator("tbody tr")
    for i in range(rows.count()):
        row = rows.nth(i)
        cells = row.locator("td")
        if cells.count() < 2:
            continue
        members.append(
            {
                "member_name": _clean(cells.nth(0).inner_text()),
                "designation": _clean(cells.nth(1).inner_text()),
            }
        )
    return members


def extract_promoter_organization_name(page: Page) -> str | None:
    panel = page.locator(
        '.x_panel:has(.x_title h2:text-is("Promoter Information - Organization"))'
    )
    if panel.count() == 0:
        return None

    value_col = panel.locator(
        'label[for="PersonalInfoModel_CompanyName"]'
    ).locator("xpath=../following-sibling::div[contains(@class, 'col-md-3')]")
    if value_col.count() == 0:
        return None

    name = _clean(value_col.first.inner_text())
    return name or None


def extract_project_detail(page: Page) -> dict[str, Any]:
    promoter = _extract_panel_by_title(page, "Promoter Information - Organization")
    project = _extract_panel_by_title(page, "Project Information")
    land = _extract_panel_by_title(page, "Land Details")
    built_up = _extract_panel_by_title(page, "Built-Up Area Details")
    address = _extract_panel_by_title(page, "Address Details")
    bank = extract_bank_details(page)
    members = extract_members(page)
    promoter_org = extract_promoter_organization_name(page)

    return {
        "detail_url": page.url,
        "promoter_organization_name": promoter_org,
        "promoter_information": promoter,
        "member_information": members,
        "project_information": project,
        "bank_details": bank,
        "land_details": land,
        "built_up_area_details": built_up,
        "address_details": address,
    }
