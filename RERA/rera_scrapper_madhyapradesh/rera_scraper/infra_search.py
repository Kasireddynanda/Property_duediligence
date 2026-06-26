"""Elasticsearch-style full-text search over INFRA.MP_allprojects."""

from __future__ import annotations

import re
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure

TEXT_INDEX_NAME = "mp_infra_projects_text"
SEARCH_FIELDS = (
    "project_name",
    "promoter_name",
    "search.district",
    "search.planning_area",
)


def ensure_text_index(collection: Collection) -> None:
    for index in collection.list_indexes():
        key = index.get("key", {})
        if any(spec == "text" for spec in key.values()):
            return
    collection.create_index(
        [(field, "text") for field in SEARCH_FIELDS],
        name=TEXT_INDEX_NAME,
        default_language="english",
    )


def _regex_fallback_query(query: str) -> dict[str, Any]:
    tokens = [t for t in re.split(r"\s+", query.strip()) if t]
    if not tokens:
        return {}
    or_clauses: list[dict[str, Any]] = []
    for field in SEARCH_FIELDS:
        for token in tokens:
            or_clauses.append({field: {"$regex": re.escape(token), "$options": "i"}})
    return {"$or": or_clauses}


def _attach_scores_regex(
    docs: list[dict[str, Any]], query: str
) -> list[dict[str, Any]]:
    tokens = [t.lower() for t in re.split(r"\s+", query.strip()) if t]
    if not tokens:
        return docs

    def score_doc(doc: dict[str, Any]) -> float:
        haystack = " ".join(
            [
                str(doc.get("project_name", "")),
                str(doc.get("promoter_name", "")),
                str(doc.get("search", {}).get("district", "")),
                str(doc.get("search", {}).get("planning_area", "")),
            ]
        ).lower()
        score = 0.0
        for token in tokens:
            if token in haystack:
                score += 2.0
            if haystack.startswith(token):
                score += 1.0
        return score

    for doc in docs:
        doc["score"] = score_doc(doc)
    docs.sort(key=lambda d: d.get("score", 0), reverse=True)
    return docs


class InfraProjectSearch:
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "INFRA",
        collection_name: str = "MP_allprojects",
    ) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection: Collection = self.db[collection_name]

    def ping(self) -> None:
        self.client.admin.command("ping")
        ensure_text_index(self.collection)

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        query = query.strip()
        if not query:
            return {"total_count": 0, "page": page, "page_size": page_size, "results": []}

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size

        text_filter = {"$text": {"$search": query}}
        try:
            total = self.collection.count_documents(text_filter)
            if total > 0:
                cursor = (
                    self.collection.find(
                        text_filter,
                        {"_id": 0, "score": {"$meta": "textScore"}},
                    )
                    .sort([("score", {"$meta": "textScore"})])
                    .skip(skip)
                    .limit(page_size)
                )
                results = list(cursor)
                return {
                    "total_count": total,
                    "page": page,
                    "page_size": page_size,
                    "results": results,
                }
        except OperationFailure:
            pass

        regex_filter = _regex_fallback_query(query)
        if not regex_filter:
            return {"total_count": 0, "page": page, "page_size": page_size, "results": []}

        total = self.collection.count_documents(regex_filter)
        results = list(
            self.collection.find(regex_filter, {"_id": 0}).skip(skip).limit(page_size)
        )
        results = _attach_scores_regex(results, query)

        return {
            "total_count": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        }

    def close(self) -> None:
        self.client.close()
