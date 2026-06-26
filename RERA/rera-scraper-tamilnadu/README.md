# Tamil Nadu RERA Scraper (`rera-scraper-tamilnadu`)

This module provides a fast, robust, and session-persistent python scraper for the Tamil Nadu RERA (TNRERA) registered buildings portal.

Unlike the Telangana scraper, the Tamil Nadu registered buildings page does not enforce a captcha, allowing this scraper to run entirely via HTTP `requests` and `BeautifulSoup4`. It operates at up to 100x speed and requires no headless browser initialization.

## Features

- **In-Memory Search Index:** Fetches all registered buildings for all years (2023-2026) dynamically in a single session, enabling instant case-insensitive fuzzy searches.
- **Deep Scraping:** Resolves promoter details pages (`public-view1`) and project details pages (`public-view2`) to extract comprehensive metadata, including bank accounts, structural engineers, architects, and coordinates.
- **FastAPI Search & Reporting API:** Includes a fully compatible API server matching the Telangana endpoint structure (`/api/infra/search`, `/api/place-report`, etc.) running by default on port `8001`.
- **MongoDB Storage:** Upserts scraped records to the `RERA-DETAILS.DETAILS` collection for reports and `INFRA.TN_allprojects` for search autocomplete.

---

## Directory Structure

```text
rera-scraper-tamilnadu/
├── api/
│   └── server.py             # FastAPI Server definitions
├── rera_scraper/
│   ├── __init__.py
│   ├── scraper.py            # Core requests-based TNRERA scraper
│   ├── advanced_scraper.py   # Bulk scraper (saves all projects to Mongo)
│   ├── extractors.py         # BeautifulSoup HTML element extractors
│   ├── mongodb.py            # MongoDB Client integration (reports/CLI)
│   ├── infra_store.py        # MongoDB Client integration (search index)
│   ├── infra_search.py       # Full-text / Regex fallback project search
│   └── exporters.py          # CSV/Excel flatten & export utilities
├── requirements.txt          # Python dependencies
├── main.py                   # CLI tool to search & scrape details
├── scrape_all_projects.py    # CLI tool to run a bulk scrape of all projects
└── run_api.py                # Server runner
```

---

## Getting Started

### 1. Set Up Environment & Install Dependencies

Ensure you have a Python 3 environment active, and install the required libraries:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Populate the Autocomplete Search Index (Bulk Scrape)

To populate your local MongoDB with all 950+ registered projects across Tamil Nadu:

```bash
python3 scrape_all_projects.py
```

This will run in ~20-30 seconds, saving all TN projects into `INFRA.TN_allprojects`.

### 3. Run the API Server

Start the TN API server on port `8001`:

```bash
python3 run_api.py --port 8001
```

The property discovery frontend (`Property_Discovery/src/App.tsx`) is configured to dynamically route search requests to port `8001` when the state is set to `TN` (Tamil Nadu), and port `8000` when set to `TS` (Telangana).

---

## CLI Usage

### Search & Scrape Project Details (with Excel Export)

```bash
python3 main.py "Thiruvottiyur Scheme" -o output/thiruvottiyur.xlsx
```

This commands searches for "Thiruvottiyur Scheme", scrapes its project details, promoter information, bank account numbers, coordinates, and exports the full flattened dataset to an Excel spreadsheet.

### Search by Promoter Name

```bash
python3 main.py --promoter "TNUHDB"
```
