"""MongoDB persistence for INFRA.Delhi_allprojects_detailed."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


class DelhiProjectStore:
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "INFRA",
        collection_name: str = "Delhi_allprojects_detailed",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.collection: Collection = self.client[db_name][collection_name]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def upsert_project(self, project: dict[str, Any]) -> None:
        reg_no = project.get("registration_no")
        project_id = project.get("project_id")
        now = datetime.now(UTC)

        if reg_no:
            query: dict[str, Any] = {"registration_no": reg_no}
        elif project_id is not None:
            query = {"project_id": project_id}
        else:
            query = {"project_name": project.get("project_name")}

        self.collection.update_one(
            query,
            {
                "$set": {**project, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def count(self) -> int:
        return self.collection.count_documents({})

    def close(self) -> None:
        self.client.close()
