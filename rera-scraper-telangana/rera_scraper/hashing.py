"""Hash helpers for Telangana detail scraping."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def district_hash(district_id: str, district_name: str = "") -> str:
    raw = f"{district_id.strip()}|{district_name.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def district_worker_shard(district_id: str, num_workers: int) -> int:
    if num_workers <= 1:
        return 0
    try:
        return int(district_id or "0") % num_workers
    except ValueError:
        return hash(district_id) % num_workers


def project_identity_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    search = row.get("search") or {}
    return (
        str(row.get("project_name", "")).strip().lower(),
        str(row.get("promoter_name", "")).strip().lower(),
        str(search.get("district_id", "")),
        str(search.get("project_type_id", "")),
    )
