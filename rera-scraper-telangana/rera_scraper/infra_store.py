"""MongoDB persistence for INFRA.All_projects (advanced search table rows)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


class InfraProjectStore:
    def __init__(
        self,
        uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
        db_name: str = "INFRA",
        collection_name: str = "All_projects",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.collection: Collection = self.client[db_name][collection_name]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def upsert_project(self, project: dict[str, Any]) -> None:
        detail_url = project["detail_url"]
        now = datetime.now(UTC)
        self.collection.update_one(
            {"detail_url": detail_url},
            {
                "$set": {**project, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def upsert_projects(self, projects: list[dict[str, Any]]) -> int:
        for project in projects:
            self.upsert_project(project)
        return len(projects)

    def count(self) -> int:
        return self.collection.count_documents({})

    def close(self) -> None:
        self.client.close()
