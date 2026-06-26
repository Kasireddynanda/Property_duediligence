"""FastAPI server for extension Place Report + RERA scrape."""

from __future__ import annotations

from typing import Any

# pyrefly: ignore [missing-import]
from fastapi import BackgroundTasks, FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr, Field
from rera_scraper.mongodb import ReraMongoStore
from rera_scraper.report_service import create_pending_report, run_background_scrape

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
    name: str = Field(min_length=2)
    email: EmailStr
    mobile: str = Field(min_length=8, max_length=15)


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
