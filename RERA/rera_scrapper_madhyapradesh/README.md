# Madhya Pradesh RERA Scraper

Scrapes **completed projects** from [rera.mp.gov.in/projects-completed/](https://www.rera.mp.gov.in/projects-completed/) and stores the data in MongoDB (`INFRA` database).

## Architecture

```
rera_scrapper_madhyapradesh/
├── scrape_all_projects.py     # Bulk ingestion CLI
├── main.py                    # Search CLI
├── run_api.py                 # FastAPI server runner (port 8003)
├── requirements.txt
├── api/
│   └── server.py              # FastAPI endpoints
└── rera_scraper/
    ├── __init__.py
    ├── scraper.py             # Playwright browser wrapper
    ├── extractors.py          # BeautifulSoup HTML parsers
    ├── advanced_scraper.py    # Orchestration: listing + detail pages
    ├── infra_store.py         # MongoDB upsert (MP_allprojects / MP_Detailed)
    ├── infra_search.py        # Full-text search over MP_allprojects
    ├── mongodb.py             # Unified report store (RERA-DETAILS.DETAILS)
    └── report_service.py      # Report placement + background scrape
```

## Data scraped

### Listing table (`MP_allprojects`)
| Field | Source |
|---|---|
| `registration_no` | Project Registration No. column |
| `project_name` | Project Name column |
| `promoter_name` | Promoter Name column |
| `district` | District part of "District – Planning Area" |
| `planning_area` | Planning Area part of "District – Planning Area" |
| `detail_url` | href of the "View" button |
| `state` | hardcoded `"MP"` |

### Detail page (`MP_Detailed`)
Parsed from the individual project page (`view_project_details.php`):

- **`project_info`** — Project Name, Registration Number, Project Type, Application Status, Contact Email, Agency for External Development, Land Ownership, Actual Start Date, Proposed End Date, Estimated Cost of Construction, Estimated Cost of Land, Is Project on Schedule?, Construction Status
- **`project_location`** — State, District, Tehsil, Project Address, Project Planning Area
- **`promoter_info`** — Name, Applicant Type, Address, Email, Is it a New Entity?, Company Reg. Document

## Setup

```bash
cd rera_scrapper_madhyapradesh

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Usage

### 1. Bulk scrape all projects
```bash
# Headless (default) – all 1039+ projects + detail pages
python scrape_all_projects.py

# Limit to first 50 projects only
python scrape_all_projects.py --max-projects 50

# Visible browser (good for debugging)
python scrape_all_projects.py --headed

# Skip detail-page fetching (fast listing-only mode)
python scrape_all_projects.py --no-details

# Dry-run (no MongoDB writes)
python scrape_all_projects.py --no-mongo

# Custom MongoDB URI
python scrape_all_projects.py --mongo-uri mongodb://user:pass@host:27017
```

### 2. Search stored data
```bash
python main.py "Indore"
python main.py "Gravity Infrastructures"
python main.py "Apollo Creations" --page-size 5
```

### 3. Run the FastAPI server (port 8003)
```bash
python run_api.py
# or with auto-reload:
python run_api.py --reload
```

#### API endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/place-report` | Place a report request (background scrape) |
| GET | `/api/reports/{report_id}` | Poll report status/results |
| GET | `/api/infra/search?q=...` | Search MP_allprojects |

## MongoDB collections

| Collection | Database | Description |
|---|---|---|
| `MP_allprojects` | `INFRA` | One doc per listing-table row |
| `MP_Detailed` | `INFRA` | One doc per project detail page |
| `DETAILS` | `RERA-DETAILS` | Unified report documents |
