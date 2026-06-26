"""BeautifulSoup extractors for Tamil Nadu RERA detail pages."""

from __future__ import annotations

import logging
from typing import Any
from bs4 import BeautifulSoup

logger = logging.getLogger("rera.extractors")


def extract_key_values(soup: BeautifulSoup) -> dict[str, str]:
    """Extract standard label-value pairs from .form-group containers."""
    details: dict[str, str] = {}
    for group in soup.find_all(class_="form-group"):
        p1 = group.find("p1")
        p = group.find("p")
        if p1 and p:
            label = p1.get_text(strip=True).rstrip(":").strip()
            value = p.get_text(strip=True)
            if label:
                details[label] = value
    return details


def extract_project_detail(soup: BeautifulSoup) -> dict[str, Any]:
    """Parse the project detail page and structure it into standard fields."""
    raw_details = extract_key_values(soup)

    # Structure the extracted fields into standard sections
    project_info = {
        "project_name": raw_details.get("Project Name", ""),
        "project_details": raw_details.get("Project Details", ""),
        "building_type": raw_details.get("Type of Building", ""),
        "usage": raw_details.get("Usage", ""),
        "site_extent": raw_details.get("Site Extent(Sq.m)", ""),
        "total_dwellings": raw_details.get("Total No. of Dwelling Units including all Phases/Villas", ""),
        "stage_of_construction": raw_details.get("Stage of Construction", ""),
        "completion_date": raw_details.get("Project Completion Date", ""),
        "category": raw_details.get("Category", ""),
        "blocks_applied_now": raw_details.get("No.of Blocks Applied Now", ""),
        "total_blocks": raw_details.get("Total No.of Blocks in the Project", ""),
    }

    bank_details = {
        "bank_name": raw_details.get("Bank Name", ""),
        "bank_email": raw_details.get("Bank Email ID", ""),
        "branch_name": raw_details.get("Branch Name", ""),
        "account_holder": raw_details.get("Bank A/C Opened in favour of", ""),
        "account_no": raw_details.get("Separate Account No for the Project", ""),
    }

    structural_engineer = {
        "name": raw_details.get("Engineer Name", ""),
        "email": raw_details.get("Email ID", ""),  # Note: might clash, but we'll store raw too
        "mobile": raw_details.get("Mobile No. 1", ""),
        "license_no": raw_details.get("Registration No. / License No.", ""),
        "license_valid_upto": raw_details.get("License Valid Upto", ""),
    }

    architect = {
        "name": raw_details.get("Architect Name", ""),
        "registration_year": raw_details.get("Year of Registration as Architect", ""),
        "mca_no": raw_details.get("MCA No.", ""),
    }

    contractor = {
        "name": raw_details.get("Contractor Name", ""),
        "pan": raw_details.get("PAN Card No", ""),
    }

    # Extract coordinates if present
    lat = raw_details.get("Latitude", "")
    lon = raw_details.get("Longitude", "")

    return {
        "project_information": project_info,
        "bank_details": bank_details,
        "structural_engineer": structural_engineer,
        "architect": architect,
        "contractor": contractor,
        "latitude": lat,
        "longitude": lon,
        "raw_project_details": raw_details,
    }


def extract_promoter_detail(soup: BeautifulSoup) -> dict[str, Any]:
    """Parse the promoter detail page and structure it into standard fields."""
    raw_details = extract_key_values(soup)

    promoter_info = {
        "developed_projects": raw_details.get("Project Developed by", ""),
        "promoter_type": raw_details.get("Type of Promoter", ""),
        "promoter_name": raw_details.get("Firm Name", "") or raw_details.get("Promoter Name", ""),
        "email": raw_details.get("Email ID", ""),
        "mobile_1": raw_details.get("Mobile No. 1", ""),
        "mobile_2": raw_details.get("Mobile No. 2", ""),
        "pan": raw_details.get("PAN Card No", ""),
        "address": raw_details.get("Address", ""),
        "registration_no": raw_details.get("Company Registration No", ""),
        "net_worth": raw_details.get("Net Worth(Total Assets Less Liabilities)", ""),
    }

    return {
        "promoter_information": promoter_info,
        "raw_promoter_details": raw_details,
    }
