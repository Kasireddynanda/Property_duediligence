# Karnataka RERA Scraper (`rera_scrapper_karnataka`)

This module provides a robust, session-persistent Playwright python scraper for the Karnataka RERA (KRERA) registered buildings portal.

## Features

- **Automated Dropdown Search & Scraping:** Automatically iterates through all districts (or specified district targets), selects them from the RERA dropdown, and triggers searches to scrape the results table.
- **Deep Modal Detail Extraction:** Automatically triggers the "View Project Details" modal (by executing `showFileApplicationPreview`) and extracts both Promoter Details (`#home`) and Project Details (`#menu1`) sections.
- **Fail-safe Mock Fallback:** If the government portal is unreachable or times out, the scraper automatically falls back to generating standard mock records to ensure developer and test server continuity.
- **FastAPI Search & Reporting API:** Includes a fully compatible API server matching the Telangana/Tamil Nadu endpoint structure (`/api/infra/search`, `/api/place-report`, etc.) running by default on port `8002`.
- **MongoDB Storage:**
  - Saves table row details to `INFRA.KA_allprojects` for search autocomplete.
  - Saves detailed modal/tab details to `INFRA.KA_Detailed`.
  - Saves unified reports to `RERA-DETAILS.DETAILS`.

---

## Directory Structure

```text
rera_scrapper_karnataka/
├── api/
│   └── server.py             # FastAPI App & Endpoints (Port 8002)
├── rera_scraper/
│   ├── __init__.py
│   ├── advanced_scraper.py   # Bulk scraper coordinator & mock generator
│   ├── extractors.py         # BeautifulSoup HTML parsers for Promoter/Project tabs
│   ├── infra_search.py       # Full-text and regex-fallback search index
│   ├── infra_store.py        # MongoDB database store logic (KA_allprojects & KA_Detailed)
│   ├── mongodb.py            # MongoDB store for unified reports (RERA-DETAILS.DETAILS)
│   ├── report_service.py     # Background scraper orchestration for report placement
│   └── scraper.py            # Playwright page actions & modal scraping
├── main.py                   # CLI entry point to search projects
├── run_api.py                # API server runner
├── scrape_all_projects.py    # Bulk scrape CLI tool
└── requirements.txt          # Python dependencies
```

---

## Installation & Setup

1. **Activate Environment & Install Dependencies:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Playwright Browsers:**

   ```bash
   playwright install chromium
   ```

3. **Ensure MongoDB is Active:**
   The store expects a MongoDB instance running locally at `mongodb://localhost:27017`.

---

## Usage

### 1. Run the Bulk Scraper

To populate the local MongoDB autocomplete search database (`INFRA.KA_allprojects`):

```bash
python3 scrape_all_projects.py
```

- To see the browser running: `--headed`
- To run without MongoDB updates (dry-run): `--no-mongo`
- To disable offline fallback mock data: `--no-mock`
- To limit projects for quick testing: `--max-projects 5`

### 2. Run the API Server

Start the Karnataka API server on port `8002`:

```bash
python3 run_api.py --port 8002
```

### 3. Search via CLI

```bash
python3 main.py "Slum Development"
```
