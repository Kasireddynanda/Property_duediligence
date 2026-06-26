"""BeautifulSoup extractors for Madhya Pradesh RERA project detail pages."""

from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger("rera.mp.extractors")


def _clean(text: str) -> str:
    """Strip whitespace and non-breaking spaces."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _extract_key_value_container(container) -> dict[str, Any]:
    """
    Extract key-value pairs from a Bootstrap .row container.
    Handles 2-col rows (col-md-4 label / col-md-8 value) and
    4-col rows (col-md-3 label / col-md-3 value / col-md-3 label / col-md-3 value).
    """
    data: dict[str, Any] = {}
    if not container:
        return data

    for row in container.find_all("div", class_="row"):
        cols = [c for c in row.children if getattr(c, "name", None) == "div"]
        i = 0
        while i < len(cols) - 1:
            lbl_el = cols[i]
            val_el = cols[i + 1]

            # Label must contain a <b> tag
            b_tag = lbl_el.find("b")
            if not b_tag:
                i += 1
                continue

            lbl_text = _clean(b_tag.get_text()).rstrip(":").strip()
            if not lbl_text:
                i += 1
                continue

            # Value may contain anchor links (e.g. PDF downloads)
            a_tags = val_el.find_all("a")
            if a_tags:
                hrefs = [a.get("href", "").strip() for a in a_tags if a.get("href")]
                val_text = "; ".join(hrefs) if hrefs else _clean(val_el.get_text())
            else:
                # Check for button-style status
                btn = val_el.find("a", class_="btn")
                if btn:
                    val_text = _clean(btn.get_text())
                else:
                    val_text = _clean(val_el.get_text())

            data[lbl_text] = val_text
            i += 2

    return data


def extract_project_detail_page(html: str) -> dict[str, Any]:
    """
    Parse the MP RERA project detail page (view_project_details.php).

    Returns a dict with keys:
      - project_info: dict  (Project Information section)
      - project_location: dict  (Project Location section)
      - promoter_info: dict  (Promoter Information section)
    """
    soup = BeautifulSoup(html, "html.parser")

    result: dict[str, Any] = {
        "project_info": {},
        "project_location": {},
        "promoter_info": {},
    }

    # Find all top-level containers with a .title heading
    containers = soup.find_all("div", class_="container")

    for container in containers:
        title_el = container.find(class_="title")
        if not title_el:
            continue
        title = _clean(title_el.get_text()).lower()

        # Find the .box wrapper inside
        box = container.find("div", class_="box")
        target = box if box else container

        if "project information" in title:
            result["project_info"] = _extract_key_value_container(target)
        elif "project location" in title:
            result["project_location"] = _extract_key_value_container(target)
        elif "promoter information" in title:
            result["promoter_info"] = _extract_key_value_container(target)

    return result
