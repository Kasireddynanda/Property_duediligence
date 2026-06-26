"""Search and map-point queries over INFRA.Map_telangana."""

from __future__ import annotations

import re
from typing import Any

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import OperationFailure

from .map_store import MapTelanganaStore

TEXT_INDEX_NAME = "map_telangana_text"
TEXT_SEARCH_FIELDS = (
    "Name_of_Project",
    "locality",
    "street",
    "Project_District",
    "Project_Taluka",
    "Project_State",
    "Application_No",
)
REGEX_SEARCH_FIELDS = TEXT_SEARCH_FIELDS + ("Registration No.",)

MAP_EXCLUDED_PROJECTS = ("HEARTLAND ONE",)

GEO_FILTER: dict[str, Any] = {
    "lat": {"$type": ["double", "int", "long", "decimal"]},
    "lng": {"$type": ["double", "int", "long", "decimal"]},
}


def ensure_text_index(collection: Collection) -> None:
    for index in collection.list_indexes():
        key = index.get("key", {})
        if any(spec == "text" for spec in key.values()):
            return

    collection.create_index(
        [(field, "text") for field in TEXT_SEARCH_FIELDS],
        name=TEXT_INDEX_NAME,
        default_language="english",
    )


def normalize_map_doc(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "mongo_id": str(doc.get("_id", "")),
        "id": doc.get("id"),
        "name": doc.get("Name_of_Project"),
        "lat": doc.get("lat"),
        "lng": doc.get("lng"),
        "locality": doc.get("locality"),
        "street": doc.get("street"),
        "district": doc.get("Project_District"),
        "taluka": doc.get("Project_Taluka"),
        "state": doc.get("Project_State"),
        "division": doc.get("Project_Division"),
        "pin_code": doc.get("PinCode"),
        "registration_no": doc.get("Registration No."),
        "application_no": doc.get("Application_No"),
        "plot_bearing": doc.get("PlotBearing"),
        "boundaries": {
            "east": doc.get("BoundriesE"),
            "west": doc.get("BoundriesW"),
            "north": doc.get("BoundriesN"),
            "south": doc.get("BoundriesS"),
        },
    }


def _map_exclusion_filter() -> dict[str, Any]:
    return {"Name_of_Project": {"$nin": list(MAP_EXCLUDED_PROJECTS)}}


def _regex_fallback_query(query: str) -> dict[str, Any]:
    tokens = [t for t in re.split(r"\s+", query.strip()) if t]
    if not tokens:
        return {}
    or_clauses: list[dict[str, Any]] = []
    for field in REGEX_SEARCH_FIELDS:
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
                str(doc.get("Name_of_Project", "")),
                str(doc.get("locality", "")),
                str(doc.get("street", "")),
                str(doc.get("Project_District", "")),
                str(doc.get("Registration No.", "")),
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


class MapTelanganaSearch:
    def __init__(
        self,
        uri: str = __import__("os").getenv("MONGO_URI", "mongodb://localhost:27017"),
        db_name: str = "INFRA",
        collection_name: str = "Map_telangana",
    ) -> None:
        self.store = MapTelanganaStore(uri, db_name, collection_name)
        self.collection = self.store.collection

    def ping(self) -> None:
        self.store.ping()
        ensure_text_index(self.collection)

    def _build_filter(
        self,
        query: str,
        *,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lng: float | None = None,
        max_lng: float | None = None,
    ) -> dict[str, Any]:
        filters: list[dict[str, Any]] = [GEO_FILTER, _map_exclusion_filter()]

        if min_lat is not None:
            filters.append({"lat": {"$gte": min_lat}})
        if max_lat is not None:
            filters.append({"lat": {"$lte": max_lat}})
        if min_lng is not None:
            filters.append({"lng": {"$gte": min_lng}})
        if max_lng is not None:
            filters.append({"lng": {"$lte": max_lng}})

        query = query.strip()
        if query:
            text_filter = {"$text": {"$search": query}}
            try:
                if self.collection.count_documents({**GEO_FILTER, **text_filter}, limit=1):
                    filters.append(text_filter)
                    return {"$and": filters}
            except OperationFailure:
                pass

            regex_filter = _regex_fallback_query(query)
            if regex_filter:
                filters.append(regex_filter)

        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}

    def search(
        self,
        query: str = "",
        *,
        page: int = 1,
        page_size: int = 20,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lng: float | None = None,
        max_lng: float | None = None,
    ) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size
        mongo_filter = self._build_filter(
            query,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )

        total = self.collection.count_documents(mongo_filter)
        cursor = self.collection.find(mongo_filter).sort("Name_of_Project", 1).skip(skip).limit(page_size)
        docs = list(cursor)
        if query.strip() and "$text" not in str(mongo_filter):
            docs = _attach_scores_regex(docs, query)

        return {
            "total_count": total,
            "page": page,
            "page_size": page_size,
            "results": [normalize_map_doc(doc) for doc in docs],
        }

    def list_points(
        self,
        query: str = "",
        *,
        limit: int = 2000,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lng: float | None = None,
        max_lng: float | None = None,
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), 5000)
        mongo_filter = self._build_filter(
            query,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )
        total = self.collection.count_documents(mongo_filter)
        cursor = (
            self.collection.find(mongo_filter)
            .sort("Name_of_Project", 1)
            .limit(limit)
        )
        docs = list(cursor)
        if query.strip() and "$text" not in str(mongo_filter):
            docs = _attach_scores_regex(docs, query)

        return {
            "total_count": total,
            "returned_count": len(docs),
            "results": [normalize_map_doc(doc) for doc in docs],
        }

    def get_by_id(self, project_id: str) -> dict[str, Any] | None:
        filters: list[dict[str, Any]] = []
        if project_id.isdigit():
            filters.append({"id": int(project_id)})
        try:
            filters.append({"_id": ObjectId(project_id)})
        except Exception:
            pass

        for filt in filters:
            doc = self.collection.find_one({**filt, **GEO_FILTER, **_map_exclusion_filter()})
            if doc:
                return normalize_map_doc(doc)
        return None

    def close(self) -> None:
        self.store.close()
