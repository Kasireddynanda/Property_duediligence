"""MongoDB stores for Karnataka RERA projects and details."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


class KAProjectStore:
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "INFRA",
        all_projects_col: str = "KA_allprojects",
        detailed_col: str = "KA_Detailed",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.all_projects: Collection = self.db[all_projects_col]
        self.detailed: Collection = self.db[detailed_col]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def upsert_project(self, project: dict[str, Any]) -> None:
        ack_no = project.get("acknowledgement_no")
        reg_no = project.get("registration_no")
        now = datetime.now(UTC)
        # Match by acknowledgement_no or registration_no
        query = {}
        if ack_no:
            query["acknowledgement_no"] = ack_no
        elif reg_no:
            query["registration_no"] = reg_no
        else:
            query["project_name"] = project.get("project_name")

        self.all_projects.update_one(
            query,
            {
                "$set": {**project, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def upsert_detailed(self, detail: dict[str, Any]) -> None:
        # Match by project identifier
        project_id = detail.get("project_id")
        ack_no = detail.get("acknowledgement_no")
        reg_no = detail.get("registration_no")
        now = datetime.now(UTC)

        query = {}
        if project_id:
            query["project_id"] = project_id
        elif ack_no:
            query["acknowledgement_no"] = ack_no
        elif reg_no:
            query["registration_no"] = reg_no
        else:
            query["project_name"] = detail.get("project_name")

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
