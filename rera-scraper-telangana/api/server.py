"""FastAPI server for extension Place Report + RERA scrape."""

from __future__ import annotations

from typing import Any

# pyrefly: ignore [missing-import]
from fastapi import BackgroundTasks, FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr, Field, field_validator
from rera_scraper.mongodb import ReraMongoStore
from rera_scraper.report_service import (
    create_discovery_report,
    create_pending_report,
    run_background_scrape,
    run_discovery_background_scrape,
)

import os
import re
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "INFRA")

print("DEBUG => MONGO_URI =", repr(MONGO_URI))
print("DEBUG => DB_NAME =", repr(DB_NAME))

app = FastAPI(title="RERA Report API", version="1.0.0")

ALLOWED_ORIGINS = [
    "https://housing.com",
    "https://www.housing.com",
    "https://99acres.com",
    "https://www.99acres.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_private_network=True,
    max_age=600,
)


class UserDetails(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    mobile: str = Field(min_length=10, max_length=15)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not re.fullmatch(r"[A-Za-z][A-Za-z\s'.-]{1,99}", cleaned):
            raise ValueError("Name must be at least 2 characters and contain only letters")
        return cleaned

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str) -> str:
        cleaned = re.sub(r"[\s\-()]", "", value.strip())
        if cleaned.startswith("+91"):
            cleaned = cleaned[3:]
        elif cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        elif cleaned.startswith("0") and len(cleaned) == 11:
            cleaned = cleaned[1:]
        if not re.fullmatch(r"[6-9]\d{9}", cleaned):
            raise ValueError("Mobile must be a valid 10-digit Indian number")
        return cleaned


class DiscoveryPlaceReportRequest(BaseModel):
    entity_name: str = Field(min_length=2)
    user: UserDetails
    report_type: str = Field(pattern=r"^(project|proprietor|none)$")
    state: str | None = None
    rera_id: str | None = None
    promoter_name: str | None = None
    promoter_gst: str | None = None
    promoter_pan: str | None = None
    report_includes: list[str] = Field(default_factory=list)


class PlaceReportRequest(BaseModel):
    entity_name: str = Field(min_length=2)
    user: UserDetails
    cin: str | None = None
    vendor_data: dict[str, Any] | None = None
    source_page_url: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/place-report")
async def api_place_report(
    body: PlaceReportRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    try:
        report = create_pending_report(
            entity_name=body.entity_name,
            user_name=body.user.name,
            user_email=body.user.email,
            user_mobile=body.user.mobile,
            cin=body.cin,
            vendor_data=body.vendor_data,
            source_page_url=body.source_page_url,
        )
        background_tasks.add_task(
            run_background_scrape,
            report["report_id"],
            body.entity_name,
        )
        return {
            "report_id": report["report_id"],
            "status": "processing",
            "total_rera_projects": 0,
            "message": (
                "Report placed. RERA scraping runs in the background — "
                "watch the terminal where run_api.py is running for logs."
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/discovery/place-report")
async def api_discovery_place_report(
    body: DiscoveryPlaceReportRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    try:
        report = create_discovery_report(
            entity_name=body.entity_name,
            user_name=body.user.name,
            user_email=str(body.user.email),
            user_mobile=body.user.mobile,
            report_type=body.report_type,
            state=body.state,
            rera_id=body.rera_id,
            promoter_name=body.promoter_name,
            promoter_gst=body.promoter_gst,
            promoter_pan=body.promoter_pan,
            report_includes=body.report_includes,
            mongo_uri=MONGO_URI,
        )
        background_tasks.add_task(
            run_discovery_background_scrape,
            report["report_id"],
            body.entity_name,
            report_type=body.report_type,
            state=body.state,
            rera_id=body.rera_id,
            promoter_name=body.promoter_name,
            promoter_gst=body.promoter_gst,
            promoter_pan=body.promoter_pan,
            mongo_uri=MONGO_URI,
            infra_db=DB_NAME,
        )
        message = (
            "Report saved. Promoter portfolio is being loaded from INFRA.Telangana_Detailed."
        )
        if body.report_type == "proprietor":
            message += " RiskMaster wishlist will be created in the background."
        return {
            "report_id": report["report_id"],
            "status": report["status"],
            "report_name": report["report_request"]["report_name"],
            "message": message,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/reports/{report_id}")
def get_report(report_id: str) -> dict[str, Any]:
    store = ReraMongoStore()
    store.ping()
    report = store.get_report(report_id)
    store.close()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/infra/search")
def search_infra_projects(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    from rera_scraper.infra_search import InfraProjectSearch

    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    search = InfraProjectSearch()
    try:
        search.ping()
        return search.search(q, page=page, page_size=page_size)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        search.close()


@app.get("/api/map/telangana/points")
def list_telangana_map_points(
    q: str = "",
    limit: int = 2000,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lng: float | None = None,
    max_lng: float | None = None,
) -> dict[str, Any]:
    from rera_scraper.map_search import MapTelanganaSearch

    search = MapTelanganaSearch()
    try:
        search.ping()
        return search.list_points(
            q,
            limit=limit,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        search.close()


@app.get("/api/map/telangana/search")
def search_telangana_map_projects(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lng: float | None = None,
    max_lng: float | None = None,
) -> dict[str, Any]:
    from rera_scraper.map_search import MapTelanganaSearch

    search = MapTelanganaSearch()
    try:
        search.ping()
        return search.search(
            q,
            page=page,
            page_size=page_size,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        search.close()


@app.get("/api/map/telangana/{project_id}")
def get_telangana_map_project(project_id: str) -> dict[str, Any]:
    from rera_scraper.map_search import MapTelanganaSearch

    search = MapTelanganaSearch()
    try:
        search.ping()
        project = search.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Map project not found")
        return project
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        search.close()

class LiveCrawlRequest(BaseModel):
    entity_name: str

@app.post("/api/crawl/live")
async def crawl_live(body: LiveCrawlRequest) -> dict[str, Any]:
    from rera_scraper.scraper import run_scraper
    try:
        records = await run_scraper(
            project_names=[body.entity_name],
            headless=True,
            follow_promoter_search=False,
            save_mongo=False
        )
        if not records:
            return {"status": "error", "message": "No records found", "data": None}
        return {"status": "success", "data": records[0]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.get("/api/generic/search")
def generic_search(q: str, collection: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    from pymongo import MongoClient
    import re
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    coll = db[collection]
    
    tokens = [t for t in re.split(r"\s+", q.strip()) if t]
    search_fields = ["project_name", "promoter_name"]
    if collection == "Telangana_Detailed":
        search_fields.extend(
            [
                "promoter_organization_name",
                "rera_registration_id",
                "search.district_name",
            ]
        )
    or_clauses = []
    for field in search_fields:
        for token in tokens:
            or_clauses.append({field: {"$regex": re.escape(token), "$options": "i"}})
            
    query = {"$or": or_clauses} if or_clauses else {}
    
    skip = (page - 1) * page_size
    cursor = coll.find(query, {"_id": 0}).skip(skip).limit(page_size)
    results = list(cursor)
    if collection == "Telangana_Detailed":
        results = [_enrich_telangana_certificate_urls(doc) for doc in results]
    total = coll.count_documents(query)
    client.close()
    
    return {
        "total_count": total,
        "page": page,
        "page_size": page_size,
        "results": results
    }

def _enrich_telangana_certificate_urls(doc: dict[str, Any]) -> dict[str, Any]:
    from rera_scraper.certificates import build_certificate_metadata

    if not doc.get("certificate"):
        cert = build_certificate_metadata(doc.get("certificate_qstr"))
        if cert:
            doc["certificate"] = cert

    if not doc.get("extension_certificate"):
        ext = build_certificate_metadata(doc.get("extension_certificate_qstr"))
        if ext:
            doc["extension_certificate"] = ext

    return doc


@app.get("/api/generic/details")
def generic_details(
    project_name: str,
    collection: str,
    rera_id: str | None = None,
) -> dict[str, Any]:
    from pymongo import MongoClient
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    coll = db[collection]
    query: dict[str, Any] = {"project_name": project_name}
    if rera_id:
        query["rera_registration_id"] = rera_id
    doc = coll.find_one(query, {"_id": 0})
    client.close()
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if collection == "Telangana_Detailed":
        doc = _enrich_telangana_certificate_urls(doc)
    return {"status": "success", "data": doc}

class RecentSearch(BaseModel):
    query: str
    state: str
    property_name: str | None = None
    rera_id: str | None = None

@app.post("/api/recent-searches")
def store_recent_search(search: RecentSearch) -> dict[str, Any]:
    from pymongo import MongoClient
    from datetime import datetime
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    coll = db["Recent_searches"]
    
    doc = search.model_dump()
    doc["timestamp"] = datetime.utcnow().isoformat()
    
    coll.insert_one(doc)
    client.close()
    return {"status": "success", "message": "Recent search stored"}

@app.get("/api/recent-searches")
def get_recent_searches(limit: int = 6) -> dict[str, Any]:
    from pymongo import MongoClient
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    coll = db["Recent_searches"]
    
    cursor = coll.find({}, {"_id": 0}).sort("timestamp", -1).limit(50)
    results = list(cursor)
    
    unique_queries = []
    seen = set()
    for r in results:
        prop_name = r.get("property_name") or ""
        q = prop_name.strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            unique_queries.append(q)
            if len(unique_queries) >= limit:
                break
                
    client.close()
    return {"status": "success", "data": unique_queries}
