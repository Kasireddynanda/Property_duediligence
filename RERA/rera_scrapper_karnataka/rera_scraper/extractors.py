"""BeautifulSoup extractors for Karnataka RERA project/promoter detail tabs."""

from __future__ import annotations

import logging
from typing import Any
from bs4 import BeautifulSoup

logger = logging.getLogger("rera.extractors")


def parse_container_key_values(container) -> dict[str, Any]:
    """Extracts key-value pairs from .row layouts inside the container."""
    data = {}
    if not container:
        return data

    rows = container.find_all("div", class_="row")
    for row in rows:
        cols = row.find_all("div", recursive=False)
        i = 0
        while i < len(cols) - 1:
            lbl_el = cols[i]
            val_el = cols[i + 1]
            lbl_p = lbl_el.find("p")
            val_p = val_el.find("p")
            if lbl_p and val_p:
                lbl_text = lbl_p.text.replace(":", "").strip()
                lbl_text = " ".join(lbl_text.split())

                # Check for link/document
                a_tag = val_p.find("a")
                if a_tag:
                    val_text = a_tag.get("href", "").strip()
                else:
                    val_text = " ".join(val_p.text.split())

                if lbl_text:
                    data[lbl_text] = val_text
                    i += 2
                    continue
            i += 1
    return data


def extract_detailed_tabs(html: str) -> dict[str, Any]:
    """Parses #home (Promoter Details) and #menu1 (Project Details) from the modal/page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract Promoter Details
    promoter_section = soup.find(id="home")
    promoter_data = parse_container_key_values(promoter_section)

    # Extract Project Details
    project_section = soup.find(id="menu1")
    project_data = parse_container_key_values(project_section)

    return {
        "promoter_details": promoter_data,
        "project_details": project_data,
    }
