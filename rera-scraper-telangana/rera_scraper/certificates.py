"""Download RERA registration certificates."""

from __future__ import annotations

import base64
import re
from typing import Any
from urllib.parse import quote

from playwright.async_api import BrowserContext

BASE_URL = "https://rerait.telangana.gov.in"


def decode_qstr(qstr: str) -> dict[str, str]:
    try:
        decoded = base64.b64decode(qstr).decode("utf-8", errors="replace")
    except Exception:
        return {"raw": qstr}

    params: dict[str, str] = {}
    for part in decoded.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            params[key] = value
    return params


async def fetch_certificate_pdf(context: BrowserContext, qstr: str) -> bytes | None:
    url = (
        f"{BASE_URL}/SearchList/GetShowCertificateFileContent"
        f"?QueryStringID={quote(qstr, safe='')}"
    )
    response = await context.request.get(url)
    if not response.ok:
        return None

    body = await response.body()
    content_type = response.headers.get("content-type", "").lower()
    if body[:4] == b"%PDF" or "pdf" in content_type:
        return body
    return None


def parse_map_onclick(onclick: str | None) -> str | None:
    if not onclick:
        return None
    match = re.search(r"view_on_map\('([^']+)'\)", onclick)
    return match.group(1) if match else None


def parse_directions_onclick(onclick: str | None) -> dict[str, str] | None:
    if not onclick:
        return None
    match = re.search(r"direction_on_map\('([^']+)','([^']+)'\)", onclick)
    if not match:
        return None
    return {"latitude": match.group(1), "longitude": match.group(2)}


async def build_certificate_payload(
    context: BrowserContext,
    qstr: str | None,
) -> dict[str, Any] | None:
    if not qstr:
        return None

    pdf_bytes = await fetch_certificate_pdf(context, qstr)
    payload: dict[str, Any] = {
        "qstr": qstr,
        "params": decode_qstr(qstr),
        "download_url": (
            f"{BASE_URL}/SearchList/GetShowCertificateFileContent"
            f"?QueryStringID={quote(qstr, safe='')}"
        ),
    }

    if pdf_bytes:
        payload["pdf_size_bytes"] = len(pdf_bytes)
        payload["pdf_base64"] = base64.b64encode(pdf_bytes).decode("ascii")

    return payload
