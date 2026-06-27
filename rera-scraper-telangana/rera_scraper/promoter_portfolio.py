"""Load all Telangana_Detailed projects for a promoter from INFRA MongoDB."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from .certificates import build_certificate_metadata


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def _enrich_telangana_doc(doc: dict[str, Any]) -> dict[str, Any]:
    if not doc.get("certificate"):
        cert = build_certificate_metadata(doc.get("certificate_qstr"))
        if cert:
            doc["certificate"] = cert

    if not doc.get("extension_certificate"):
        ext = build_certificate_metadata(doc.get("extension_certificate_qstr"))
        if ext:
            doc["extension_certificate"] = ext

    return doc


def extract_promoter_label(doc: dict[str, Any]) -> str:
    info = doc.get("promoter_information") or {}
    return (
        doc.get("promoter_organization_name")
        or info.get("Name")
        or info.get("Organization Name")
        or doc.get("promoter_name")
        or ""
    ).strip()


def extract_promoter_identifiers(doc: dict[str, Any] | None) -> tuple[str, str]:
    """Return (gstin, pan) from a Telangana_Detailed project document."""
    if not doc:
        return "", ""

    info = doc.get("promoter_information") or {}
    gstin = (
        info.get("GST Number")
        or info.get("CompanyGSTIN")
        or doc.get("company_gstin")
        or ""
    ).strip().upper()

    pan = (
        info.get("CompanyPanNo")
        or info.get("Pan No.")
        or info.get("PAN Number")
        or info.get("Pan No")
        or ""
    ).strip().upper()

    if not pan and gstin and len(gstin) >= 12:
        pan = gstin[2:12]

    return gstin, pan


def find_seed_project(
    coll: Collection,
    entity_name: str,
    rera_id: str | None = None,
) -> dict[str, Any] | None:
    entity_name = entity_name.strip()
    if not entity_name:
        return None

    if rera_id:
        doc = coll.find_one({"rera_registration_id": rera_id}, {"_id": 0})
        if doc:
            return doc

    doc = coll.find_one({"project_name": entity_name}, {"_id": 0})
    if doc:
        return doc

    return coll.find_one(
        {"project_name": {"$regex": f"^{re.escape(entity_name)}$", "$options": "i"}},
        {"_id": 0},
    )


def _promoter_match_clauses(promoter_label: str) -> list[dict[str, Any]]:
    escaped = re.escape(promoter_label.strip())
    return [
        {"promoter_organization_name": {"$regex": f"^{escaped}$", "$options": "i"}},
        {"promoter_name": {"$regex": f"^{escaped}$", "$options": "i"}},
        {"promoter_information.Name": {"$regex": f"^{escaped}$", "$options": "i"}},
        {"promoter_information.Organization Name": {"$regex": f"^{escaped}$", "$options": "i"}},
    ]


def query_projects_by_promoter(coll: Collection, promoter_label: str) -> list[dict[str, Any]]:
    promoter_label = promoter_label.strip()
    if not promoter_label:
        return []

    exact_query = {"$or": _promoter_match_clauses(promoter_label)}
    projects = list(coll.find(exact_query, {"_id": 0}))
    if projects:
        return projects

    tokens = [t for t in re.split(r"\s+", promoter_label) if len(t) > 2]
    if not tokens:
        return []

    loose_clauses: list[dict[str, Any]] = []
    for field in (
        "promoter_organization_name",
        "promoter_name",
        "promoter_information.Name",
        "promoter_information.Organization Name",
    ):
        for token in tokens:
            loose_clauses.append({field: {"$regex": re.escape(token), "$options": "i"}})

    return list(coll.find({"$or": loose_clauses}, {"_id": 0}))


def _pick_primary_project(
    projects: list[dict[str, Any]],
    entity_name: str,
    seed: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if seed:
        seed_url = seed.get("detail_url")
        if seed_url:
            for project in projects:
                if project.get("detail_url") == seed_url:
                    return project
        target = _normalize(entity_name)
        for project in projects:
            if _normalize(project.get("project_name")) == target:
                return project
        return seed

    target = _normalize(entity_name)
    for project in projects:
        if _normalize(project.get("project_name")) == target:
            return project
    return projects[0] if projects else None


def resolve_promoter_details(
    *,
    entity_name: str,
    promoter_name: str | None = None,
    promoter_gst: str | None = None,
    promoter_pan: str | None = None,
    rera_id: str | None = None,
    mongo_uri: str = "mongodb://localhost:27017",
    infra_db: str = "INFRA",
    detailed_collection: str = "Telangana_Detailed",
) -> dict[str, Any]:
    """Resolve promoter name, GSTIN, PAN, and seed project without loading full portfolio."""
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    coll = client[infra_db][detailed_collection]

    seed = find_seed_project(coll, entity_name, rera_id)
    client.close()

    resolved_promoter = (promoter_name or "").strip()
    if not resolved_promoter and seed:
        resolved_promoter = extract_promoter_label(seed)

    db_gst, db_pan = extract_promoter_identifiers(seed)
    gstin = (promoter_gst or db_gst or "").strip().upper()
    pan = (promoter_pan or db_pan or "").strip().upper()
    if not pan and gstin and len(gstin) >= 12:
        pan = gstin[2:12]

    return {
        "promoter_name": resolved_promoter,
        "gstin": gstin,
        "pan": pan,
        "seed_project": seed,
    }


def load_promoter_portfolio_for_report(
    *,
    entity_name: str,
    promoter_name: str | None = None,
    rera_id: str | None = None,
    mongo_uri: str = "mongodb://localhost:27017",
    infra_db: str = "INFRA",
    detailed_collection: str = "Telangana_Detailed",
) -> dict[str, Any]:
    """Resolve promoter and return all matching detailed project documents."""
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    coll = client[infra_db][detailed_collection]

    seed = find_seed_project(coll, entity_name, rera_id)
    resolved_promoter = (promoter_name or "").strip()
    if not resolved_promoter and seed:
        resolved_promoter = extract_promoter_label(seed)

    if not resolved_promoter:
        client.close()
        raise ValueError(
            f"Could not resolve promoter name for project {entity_name!r}. "
            "Provide promoter_name or ensure the project exists in Telangana_Detailed."
        )

    raw_projects = query_projects_by_promoter(coll, resolved_promoter)
    projects = [_enrich_telangana_doc(doc) for doc in raw_projects]
    projects.sort(key=lambda item: (item.get("project_name") or "").lower())

    primary = _pick_primary_project(projects, entity_name, seed)
    if primary:
        primary = _enrich_telangana_doc(dict(primary))

    client.close()

    now = datetime.now(UTC).isoformat()
    return {
        "promoter_name": resolved_promoter,
        "primary_project": (
            {**primary, "loaded_at": now} if primary else None
        ),
        "projects": projects,
        "loaded_at": now,
        "source_collection": f"{infra_db}.{detailed_collection}",
    }
