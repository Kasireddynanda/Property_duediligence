"""MongoDB stores for Madhya Pradesh RERA projects and details."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


class MPProjectStore:
    """Manages two MongoDB collections:
    - MP_allprojects  : one doc per listing-table row (registration no, name, promoter, district…)
    - MP_Detailed     : one doc per project detail page (project info, location, promoter info)
    """

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "INFRA",
        all_projects_col: str = "MP_allprojects",
        detailed_col: str = "MP_detailed",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.all_projects: Collection = self.db[all_projects_col]
        self.detailed: Collection = self.db[detailed_col]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def upsert_project(self, project: dict[str, Any]) -> None:
        """Insert or update a listing-table row, keyed by registration_no."""
        reg_no = project.get("registration_no")
        now = datetime.now(UTC)

        if reg_no:
            query: dict[str, Any] = {"registration_no": reg_no}
        else:
            query = {"project_name": project.get("project_name")}

        self.all_projects.update_one(
            query,
            {
                "$set": {**project, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def upsert_detailed(self, detail: dict[str, Any]) -> None:
        """Insert or update a project detail record, keyed by registration_no."""
        reg_no = detail.get("registration_no")
        now = datetime.now(UTC)

        if reg_no:
            query: dict[str, Any] = {"registration_no": reg_no}
        else:
            query = {"project_name": detail.get("project_name")}

        self.detailed.update_one(
            query,
            {
                "$set": {**detail, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def close(self) -> None:
        self.client.close()
