"""BeautifulSoup extractors for Delhi RERA listing and detail pages."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

BASE_URL = "https://erera.co.in/reradelhiindex/"
LIST_URL = urljoin(BASE_URL, "PublicView/RegisteredProjectDetail")
DETAIL_URL = urljoin(BASE_URL, "PublicView/ProjectViewDetails")

TAB_IDS = (
    "Promoter",
    "Projects",
    "Project-plan-facilities",
    "Project-documents",
    "Project-professionals",
    "Project-quarterly-updates",
)

TAB_KEYS = {
    "Promoter": "promoter_details",
    "Projects": "project_details",
    "Project-plan-facilities": "project_plan_facilities",
    "Project-documents": "project_documents",
    "Project-professionals": "project_professionals",
    "Project-quarterly-updates": "quarterly_updates",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _abs_url(href: str) -> str:
    href = href.strip().replace("\\", "/")
    if href.startswith("http"):
        url = href
    else:
        url = urljoin("https://erera.co.in/", href.lstrip("/"))
    return re.sub(r"(?<!:)/{2,}", "/", url)


def _cell_text(cell: Tag) -> str:
    links = cell.find_all("a", href=True)
    if links:
        parts = []
        for link in links:
            href = _abs_url(link["href"])
            label = _clean(link.get_text())
            parts.append(f"{label} ({href})" if label else href)
        return "; ".join(parts)
    return _clean(cell.get_text(" ", strip=True))


def _extract_key_value_table(table: Tag) -> dict[str, str]:
    data: dict[str, str] = {}
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if len(tds) == 2:
            key = _clean(tds[0].get_text())
            if key:
                data[key] = _cell_text(tds[1])
        elif len(tds) == 4:
            k1, v1, k2, v2 = tds
            key1 = _clean(k1.get_text())
            key2 = _clean(k2.get_text())
            if key1:
                data[key1] = _cell_text(v1)
            if key2:
                data[key2] = _cell_text(v2)
        elif len(tds) == 1 and tds[0].has_attr("colspan"):
            continue
    return data


def _extract_data_table(table: Tag) -> list[dict[str, str]]:
    thead = table.find("thead")
    if not thead:
        return []

    headers = [_clean(th.get_text()) for th in thead.find_all("th")]
    headers = [h for h in headers if h]
    if not headers:
        return []

    rows: list[dict[str, str]] = []
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue
        row: dict[str, str] = {}
        for idx, td in enumerate(tds):
            header = headers[idx] if idx < len(headers) else f"column_{idx + 1}"
            row[header] = _cell_text(td)
        if any(v and v != "--" for v in row.values()):
            rows.append(row)
    return rows


def _extract_section(section: Tag) -> dict[str, Any]:
    heading_el = section.select_one(".view-detail-heading1")
    heading = _clean(heading_el.get_text()) if heading_el else "Section"

    tables = section.select("table.table-properties")
    key_values: dict[str, str] = {}
    table_rows: list[dict[str, str]] = []
    pdf_links: list[dict[str, str]] = []

    for table in tables:
        if table.find("thead"):
            table_rows.extend(_extract_data_table(table))
        else:
            key_values.update(_extract_key_value_table(table))

        for link in table.select("a[href]"):
            href = _abs_url(link["href"])
            if href.lower().endswith(".pdf") or "pdf" in href.lower():
                pdf_links.append(
                    {
                        "title": link.get("title") or _clean(link.get_text()) or heading,
                        "url": href,
                    }
                )

    for img in section.select("img[src]"):
        src = _abs_url(img["src"])
        if src.lower().endswith((".jpg", ".jpeg", ".png")):
            pdf_links.append({"title": heading, "url": src, "type": "image"})

    section_data: dict[str, Any] = {"heading": heading}
    if key_values:
        section_data["fields"] = key_values
    if table_rows:
        section_data["rows"] = table_rows
    if pdf_links:
        section_data["links"] = pdf_links
    return section_data


def _extract_tab_pane(soup: BeautifulSoup, pane_id: str) -> dict[str, Any]:
    pane = soup.select_one(f"#{pane_id}")
    if not pane:
        return {"sections": []}

    sections = [_extract_section(sec) for sec in pane.select(".each-table-space")]
    return {"sections": sections}


def extract_list_rows(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []

    for tr in soup.select("#dataTableSearchProject tbody tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 8:
            continue

        project_cell = tds[2]
        project_name = project_cell.get("data-project-name") or _clean(
            project_cell.get_text(" ", strip=True)
        )
        project_id = tr.select_one("input.hdnProjectID")
        promoter_id = tr.select_one("input.hdnPromoterID")
        promoter_type = tr.select_one("input.hdnPromoterType")
        diary_cell = tds[4]
        registration_no = diary_cell.get("data-diary-no") or _clean(diary_cell.get_text())

        cert_link = tr.select_one('a[href*="PRJcert"], a[href*="readwritePRJCert"]')
        certificate_url = _abs_url(cert_link["href"]) if cert_link else ""

        pid = int(project_id["value"]) if project_id and project_id.get("value") else None
        prom_id = int(promoter_id["value"]) if promoter_id and promoter_id.get("value") else None
        prom_type = int(promoter_type["value"]) if promoter_type and promoter_type.get("value") else None

        detail_url = ""
        if pid is not None and prom_id is not None and prom_type is not None:
            detail_url = (
                f"{DETAIL_URL}?inProject_ID={pid}"
                f"&inPromoter_ID={prom_id}&inPromoterType={prom_type}"
            )

        rows.append(
            {
                "sno": _clean(tds[0].get_text()),
                "district": _clean(tds[1].get_text()),
                "project_name": _clean(project_name),
                "promoter_name": _clean(tds[3].get_text()),
                "registration_no": _clean(registration_no),
                "registration_valid_upto": _clean(tds[5].get_text()),
                "project_type": _clean(tds[6].get_text()),
                "project_id": pid,
                "promoter_id": prom_id,
                "promoter_type": prom_type,
                "certificate_url": certificate_url,
                "detail_url": detail_url,
                "state": "Delhi",
            }
        )

    return rows


def extract_detail_page(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    tabs: dict[str, Any] = {}
    all_links: list[dict[str, str]] = []

    for pane_id in TAB_IDS:
        tab_data = _extract_tab_pane(soup, pane_id)
        tabs[TAB_KEYS[pane_id]] = tab_data
        for section in tab_data.get("sections", []):
            for link in section.get("links", []):
                all_links.append(
                    {
                        "tab": TAB_KEYS[pane_id],
                        "section": section.get("heading", ""),
                        **link,
                    }
                )

    return {"tabs": tabs, "document_links": all_links}
