"""MongoDB access for INFRA.Map_telangana (RERA project map pins)."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.collection import Collection


class MapTelanganaStore:
    def __init__(
        self,
        uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
        db_name: str = "INFRA",
        collection_name: str = "Map_telangana",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.collection: Collection = self.client[db_name][collection_name]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def count(self, query: dict | None = None) -> int:
        return self.collection.count_documents(query or {})

    def close(self) -> None:
        self.client.close()
