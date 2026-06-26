"""Unified report document persistence (one MongoDB doc per report)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


class ReraMongoStore:
    def __init__(
        self,
        uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
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

    def upsert_record(self, record: dict[str, Any]) -> str:
        """Legacy per-project save (CLI). Prefer save_unified_report for reports."""
        doc = {**record, "updated_at": datetime.now(UTC)}
        detail_url = record.get("detail_url")
        if detail_url:
            filter_doc = {"detail_url": detail_url}
        else:
            filter_doc = {
                "search_query": record.get("search_query"),
                "result_project_name": record.get("result_project_name"),
                "sr_no": record.get("sr_no"),
            }

        result = self.collection.update_one(
            filter_doc,
            {"$set": doc, "$setOnInsert": {"created_at": datetime.now(UTC)}},
            upsert=True,
        )
        if result.upserted_id:
            return str(result.upserted_id)
        existing = self.collection.find_one(filter_doc, {"_id": 1})
        return str(existing["_id"]) if existing else ""

    def save_records(self, records: list[dict[str, Any]]) -> list[str]:
        return [self.upsert_record(record) for record in records]

    def close(self) -> None:
        self.client.close()
