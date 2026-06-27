"""Extract structured fields from RERA detail pages."""

from __future__ import annotations

import re
from typing import Any

from playwright.async_api import Locator, Page


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


async def _cell_value(col: Locator) -> str:
    clone = col
    for span in ["span.field-validation-valid"]:
        for i in range(await clone.locator(span).count()):
            pass
    text = await col.inner_text()
    return _clean(text)


async def _extract_panel_pairs(panel: Locator, prefix: str = "") -> dict[str, str]:
    data: dict[str, str] = {}
    rows = panel.locator(":scope > .x_content .row, :scope .x_content.label-block .row")
    row_count = await rows.count()

    for i in range(row_count):
        row = rows.nth(i)
        cols = row.locator(":scope > .form-group > .col-md-3, :scope > .col-md-3")
        col_count = await cols.count()

        j = 0
        while j < col_count:
            col = cols.nth(j)
            label_el = col.locator("label")
            if await label_el.count() == 0:
                j += 1
                continue

            key = _clean(await label_el.first.inner_text()).rstrip(":")
            if not key:
                j += 1
                continue

            value = ""
            if j + 1 < col_count:
                value_col = cols.nth(j + 1)
                if await value_col.locator("label").count() == 0:
                    value = await _cell_value(value_col)
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


async def _extract_panel_by_title(page: Page, title: str) -> dict[str, str]:
    panel = page.locator(f'.x_panel:has(.x_title h2:text-is("{title}"))')
    if await panel.count() == 0:
        return {}
    return await _extract_panel_pairs(panel.first)


async def extract_bank_details(page: Page) -> dict[str, str]:
    panel = page.locator('.x_panel:has(.x_title h2:text-is("Bank Details"))')
    if await panel.count() == 0:
        return {}

    data: dict[str, str] = {}
    blocks = panel.first.locator(".x_content.label-block")
    block_count = await blocks.count()

    for i in range(block_count):
        block = blocks.nth(i)
        heading = block.locator("h4")
        prefix = ""
        if await heading.count() > 0:
            prefix = _clean(await heading.first.inner_text()) + " - "

        rows = block.locator(".row")
        for r in range(await rows.count()):
            row = rows.nth(r)
            cols = row.locator(".col-md-3")
            col_count = await cols.count()
            j = 0
            while j < col_count:
                col = cols.nth(j)
                label_el = col.locator("label")
                if await label_el.count() == 0:
                    j += 1
                    continue
                key = _clean(await label_el.first.inner_text()).rstrip(":")
                value = ""
                if j + 1 < col_count:
                    value = await _cell_value(cols.nth(j + 1))
                    j += 2
                else:
                    j += 1
                if key and value:
                    data[f"{prefix}{key}"] = value

    return data


async def extract_members(page: Page) -> list[dict[str, str]]:
    table = page.locator('table:has(th:text("Member Name"))')
    if await table.count() == 0:
        return []

    members: list[dict[str, str]] = []
    rows = table.first.locator("tbody tr")
    for i in range(await rows.count()):
        row = rows.nth(i)
        cells = row.locator("td")
        if await cells.count() < 2:
            continue
        members.append(
            {
                "member_name": _clean(await cells.nth(0).inner_text()),
                "designation": _clean(await cells.nth(1).inner_text()),
            }
        )
    return members


async def extract_promoter_organization_name(page: Page) -> str | None:
    panel = page.locator(
        '.x_panel:has(.x_title h2:text-is("Promoter Information - Organization"))'
    )
    if await panel.count() == 0:
        return None

    value_col = panel.locator(
        'label[for="PersonalInfoModel_CompanyName"]'
    ).locator("xpath=../following-sibling::div[contains(@class, 'col-md-3')]")
    if await value_col.count() == 0:
        return None

    name = _clean(await value_col.first.inner_text())
    return name or None


async def _extract_table(table: Locator) -> list[dict[str, str]]:
    rows_data: list[dict[str, str]] = []
    header_cells = table.locator("thead th, tr th")
    headers: list[str] = []
    header_count = await header_cells.count()
    for i in range(header_count):
        text = _clean(await header_cells.nth(i).inner_text())
        if text:
            headers.append(text)

    body_rows = table.locator("tbody tr")
    body_count = await body_rows.count()
    if body_count == 0:
        body_rows = table.locator("tr").filter(has=table.locator("td"))
        body_count = await body_rows.count()

    for i in range(body_count):
        row = body_rows.nth(i)
        cells = row.locator("td")
        cell_count = await cells.count()
        if cell_count == 0:
            continue
        if not headers:
            headers = [f"column_{j + 1}" for j in range(cell_count)]
        item: dict[str, str] = {}
        for j in range(min(cell_count, len(headers))):
            value = _clean(await cells.nth(j).inner_text())
            if value:
                item[headers[j]] = value
        if item:
            rows_data.append(item)
    return rows_data


async def _extract_h3_panels(scope: Locator) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    panels = scope.locator(":scope > .x_panel, :scope .x_panel .x_panel")
    count = await panels.count()
    for i in range(count):
        panel = panels.nth(i)
        h3 = panel.locator(".x_title h3")
        if await h3.count() == 0:
            continue
        title = _clean(await h3.first.inner_text())
        pairs = await _extract_panel_pairs(panel)
        if pairs:
            sections[title] = pairs
    return sections


async def extract_uploaded_documents(page: Page) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    doc_panel = page.locator('.x_panel:has(.x_title h2:text-is("Uploaded Documents"))')
    if await doc_panel.count() == 0:
        return documents

    rows = doc_panel.first.locator("table tbody tr")
    for i in range(await rows.count()):
        row = rows.nth(i)
        cells = row.locator("td")
        if await cells.count() < 2:
            continue
        name_cell = cells.nth(0)
        doc_name = _clean(await name_cell.locator("span[title]").first.inner_text()) if await name_cell.locator("span[title]").count() else _clean(await name_cell.inner_text())
        if not doc_name or doc_name.lower() == "document name":
            continue

        upload_id = await row.locator('input[name^="ID_"]').first.get_attribute("value") if await row.locator('input[name^="ID_"]').count() else None
        doc_type = await row.locator('input[name^="DocType_"]').first.get_attribute("value") if await row.locator('input[name^="DocType_"]').count() else None
        file_type = await row.locator('input[name^="FileType_"]').first.get_attribute("value") if await row.locator('input[name^="FileType_"]').count() else None
        seen_flag = await row.locator('input[name^="SeenFlag_"]').first.get_attribute("value") if await row.locator('input[name^="SeenFlag_"]').count() else None

        btn = row.locator('button[id^="btnShow1_"]')
        btn_id = await btn.first.get_attribute("id") if await btn.count() else None
        status = "uploaded" if btn_id else _clean(await cells.nth(1).inner_text())

        entry: dict[str, Any] = {
            "document_name": doc_name,
            "status": status,
        }
        if upload_id and upload_id != "-1":
            entry["upload_id"] = upload_id
        if doc_type:
            entry["doc_type"] = doc_type
        if file_type:
            entry["file_type"] = file_type
        if seen_flag:
            entry["seen_flag"] = seen_flag
        if btn_id:
            entry["button_id"] = btn_id
        documents.append(entry)
    return documents


async def extract_all_sections(page: Page) -> dict[str, Any]:
    """Extract every x_panel section as key-value fields or table rows."""
    sections: dict[str, Any] = {}
    panels = page.locator(".container-print .x_panel")
    panel_count = await panels.count()

    for i in range(panel_count):
        panel = panels.nth(i)
        title = ""
        h2 = panel.locator(":scope > .x_title h2, :scope > .x_title > h2")
        h3 = panel.locator(":scope > .x_title h3, :scope > .x_title > h3")
        if await h2.count() > 0:
            title = _clean(await h2.first.inner_text())
        elif await h3.count() > 0:
            title = _clean(await h3.first.inner_text())
        if not title:
            continue

        table = panel.locator(":scope > .x_content table.table, :scope table.table").first
        if await panel.locator("table.table").count() > 0:
            table_rows = await _extract_table(panel.locator("table.table").first)
            if table_rows:
                sections[title] = table_rows
                continue

        pairs = await _extract_panel_pairs(panel)
        if pairs:
            sections[title] = pairs

    return sections


async def extract_project_meta(page: Page) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for selector, key in (
        ("#ProjectID", "project_id"),
        ("input[name='ProjectID']", "project_id"),
    ):
        if await page.locator(selector).count():
            value = await page.locator(selector).first.input_value()
            if value:
                meta[key] = value
                break
    return meta


async def extract_plot_details(page: Page) -> list[dict[str, str]]:
    block = page.locator("#DivBuilding")
    if await block.count() == 0:
        return []
    table = block.locator("table.table")
    if await table.count() == 0:
        return []
    return await _extract_table(table.first)


async def extract_project_detail(page: Page) -> dict[str, Any]:
    promoter = await _extract_panel_by_title(page, "Promoter Information - Organization")
    project = await _extract_panel_by_title(page, "Project Information")
    land = await _extract_panel_by_title(page, "Land Details")
    built_up = await _extract_panel_by_title(page, "Built-Up Area Details")
    address = await _extract_panel_by_title(page, "Address Details")
    bank = await extract_bank_details(page)
    members = await extract_members(page)
    general = await _extract_panel_by_title(page, "General Information")
    uploaded_documents = await extract_uploaded_documents(page)
    all_sections = await extract_all_sections(page)
    plot_details = all_sections.get("Plot Details") or await extract_plot_details(page)

    promoter_org = await extract_promoter_organization_name(page)

    promoter_scope = page.locator("#fldFirm")
    promoter_subpanels: dict[str, dict[str, str]] = {}
    if await promoter_scope.count():
        promoter_subpanels = await _extract_h3_panels(promoter_scope.first)

    detail: dict[str, Any] = {
        "detail_url": page.url,
        "project_name": project.get("Project Name") or project.get("  Project Name"),
        "promoter_organization_name": promoter_org,
        "promoter_information": promoter,
        "promoter_address_details": promoter_subpanels.get("Address Details", {}),
        "promoter_contact_details": promoter_subpanels.get("Organization Contact Details", {}),
        "general_information": general,
        "member_information": members,
        "other_organization_members": all_sections.get(
            "Other Organization Type Member Information", []
        ),
        "project_information": project,
        "bank_details": bank,
        "land_details": land,
        "built_up_area_details": built_up,
        "address_details": address,
        "project_details": all_sections.get("Project Details", []),
        "development_work": all_sections.get("Development Work", []),
        "plot_details": plot_details,
        "project_professionals": all_sections.get("Project Professional Information", []),
        "uploaded_documents": uploaded_documents,
        "sections": all_sections,
    }
    detail.update(await extract_project_meta(page))
    return detail
