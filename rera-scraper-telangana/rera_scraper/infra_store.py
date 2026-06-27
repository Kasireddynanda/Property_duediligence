"""MongoDB persistence for INFRA.All_projects and INFRA.Telangana_Detailed."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from .hashing import project_identity_key


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


class TelanganaProjectStore:
    """Reads listing rows from All_projects and writes detail docs to Telangana_Detailed."""

    def __init__(
        self,
        uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
        db_name: str = "INFRA",
        all_projects_col: str = "All_projects",
        detailed_col: str = "Telangana_Detailed",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.all_projects: Collection = self.db[all_projects_col]
        self.detailed: Collection = self.db[detailed_col]

    def ping(self) -> None:
        self.client.admin.command("ping")
        self.detailed.create_index("detail_url", unique=True)
        self.detailed.create_index("district_hash")
        self.detailed.create_index("search.district_id")

    def upsert_detailed(self, detail: dict[str, Any]) -> None:
        key = project_identity_key(detail)
        now = datetime.now(UTC)
        self.detailed.update_one(
            {
                "project_name": detail.get("project_name"),
                "promoter_name": detail.get("promoter_name"),
                "search.district_id": key[2],
                "search.project_type_id": key[3],
            },
            {
                "$set": {**detail, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    def upsert_detailed_many(self, details: list[dict[str, Any]]) -> int:
        for detail in details:
            self.upsert_detailed(detail)
        return len(details)

    def existing_detail_urls(self) -> set[str]:
        return set(self.detailed.distinct("detail_url"))

    def detailed_count(self) -> int:
        return self.detailed.count_documents({})

    def all_projects_count(self) -> int:
        return self.all_projects.count_documents({})

    def close(self) -> None:
        self.client.close()
