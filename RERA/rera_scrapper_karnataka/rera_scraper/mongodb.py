"""Unified report document persistence (one MongoDB doc per report) for Karnataka."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


class ReraMongoStore:
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "RERA-DETAILS",
        collection_name: str = "DETAILS",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.collection: Collection = self.client[db_name][collection_name]

    def ping(self) -> None:
        self.client.admin.command("ping")

    @staticmethod
    def make_report_id(entity_name: str, email: str) -> str:
        """Stable id so the same user + entity updates one document."""
        raw = f"{email.strip().lower()}::{entity_name.strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def save_unified_report(self, report: dict[str, Any]) -> str:
        """Save or update a single report document keyed by report_id."""
        report_id = report["report_id"]
        now = datetime.now(UTC)

        self.collection.update_one(
            {"report_id": report_id},
            {
                "$set": {**report, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return report_id

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({"report_id": report_id}, {"_id": 0})

    def update_report_scrape_result(
        self,
        report_id: str,
        *,
        status: str,
        entity_name: str,
        projects: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(UTC),
        }
        if projects is not None:
            update["rera"] = {
                "entity_searched": entity_name,
                "total_projects": len(projects),
                "projects": projects,
            }
        if error is not None:
            update["error"] = error
        self.collection.update_one({"report_id": report_id}, {"$set": update})

    def close(self) -> None:
        self.client.close()
