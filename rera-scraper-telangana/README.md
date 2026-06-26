# Telangana RERA Scraper

Playwright scraper for [Telangana RERA Search](https://rerait.telangana.gov.in/SearchList/Search).

## Features

- Opens the search page **once** and reuses the same browser session
- Extracts `__RequestVerificationToken` automatically
- Solves captcha via OCR (`ddddocr`)
- Searches by project name (`#Project`) or promoter name (`#promoter_name`)
- Scrapes structured detail sections and downloads registration certificates
- Saves results to **MongoDB** (`RERA-DETAILS.DETAILS`) and optionally **CSV/Excel**

## Setup

```bash
cd rera-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

MongoDB must be running locally (default: `mongodb://localhost:27017`).

## Usage

Search by promoter (scrapes detail pages + certificates → MongoDB):

```bash
python main.py --promoter "VAJRAM CONSTRUCTIONS PVT LTD"
```

Search project, then auto re-search by promoter organization name:

```bash
python main.py "VAJRAM ASTER HOMES" -o output/vajram.csv
```

Optional CSV/Excel export alongside MongoDB:

```bash
python main.py --promoter "VAJRAM CONSTRUCTIONS PVT LTD" -o output/vajram.xlsx
```

Skip MongoDB (export only):

```bash
python main.py --promoter "VAJRAM CONSTRUCTIONS PVT LTD" -o output/vajram.csv --no-mongo
```

## Advanced Search — all projects (District × Project Type)

A separate scraper opens **Advanced Search**, loops every **District** and **Project Type**
combination, paginates through `#projectTable`, and saves each row as JSON in MongoDB:

- **Database:** `INFRA`
- **Collection:** `All_projects`
- **URI:** `mongodb://localhost:27017`

### Run full scrape (all districts × all project types)

```bash
python scrape_all_projects.py
```

This can take a long time (captcha per page × many pages per combo). Logs print in the terminal.

### Test with one district / type (first page only)

```bash
python scrape_all_projects.py --district 25 --project-type 13 --max-pages 1
```

### Options

| Flag | Description |
|------|-------------|
| `--district ID [ID ...]` | Only these district IDs (e.g. `25` = Hyderabad) |
| `--project-type ID [ID ...]` | `12` Commercial, `13` Residential, `15` Plotted, `33` Mixed |
| `--max-pages N` | Limit pages per combo (testing) |
| `--headed` | Show browser window |
| `--no-mongo` | Scrape without saving |

### Stored document shape

```json
{
  "detail_url": "https://rerait.telangana.gov.in/PrintPreview/PrintPreview?q=...",
  "sr_no": "1",
  "project_name": "SKV S ANANDA VILAS",
  "promoter_name": "KACHAM RAJESHWAR",
  "last_modified": "31/08/2018 00:00:00",
  "certificate_qstr": "...",
  "extension_certificate_qstr": null,
  "rera_registration_id": null,
  "directions": null,
  "search": {
    "district_id": "25",
    "district_name": "Hyderabad",
    "project_type_id": "13",
    "project_type_name": "Residential"
  }
}
```

Documents are upserted by `detail_url` (same project found in multiple searches updates one doc).


## Session flow

```
GET Search page (once)
      ↓
Read token + captcha
      ↓
POST Search (project 1)
      ↓
Scrape detail pages
      ↓
Read Promoter Organization Name
      ↓
POST Search (#promoter_name)   ← same session
      ↓
Scrape all promoter projects
      ↓
POST Search (project 2)
      ↓
Download certificates from search table
      ↓
Save to MongoDB RERA-DETAILS.DETAILS
```

The page is **not** reopened between searches unless the session is lost.

## MongoDB storage

By default, every scrape is saved to:

| Setting | Default |
|---------|---------|
| URI | `mongodb://localhost:27017` |
| Database | `RERA-DETAILS` |
| Collection | `DETAILS` |

Each document includes:

- **Search table fields** — project name, promoter name, last modified, RERA registration ID
- **certificate** — PDF (base64), download URL, decoded params
- **promoter_information** — organization name, GST, org type, etc.
- **member_information** — member name + designation list
- **project_information** — project name, status, completion dates, type
- **bank_details** — collection / separate / transaction accounts
- **land_details** — area, boundaries, building units
- **built_up_area_details** — approved and mortgage area
- **address_details** — state, district, street, pin code

## Extension integration (hi-extension)

When a user selects an entity and clicks **Place Report**, the extension calls:

```
POST http://localhost:8000/api/place-report
```

### Start the API server

```bash
cd rera-scraper
source .venv/bin/activate
python run_api.py
```

### One MongoDB document per report

Each place-report request saves **one JSON document** keyed by `report_id`
(same user email + entity name → same document, updated not duplicated).

The API responds **immediately** with `status: processing`. RERA scraping
runs in the background; when finished the document is updated to
`completed` or `failed`.

```json
{
  "report_id": "abc123...",
  "status": "processing|completed|failed",
  "user_details": { "name", "email", "mobile" },
  "report_request": { "entity_name", "cin", "source_page_url" },
  "vendor_discovery": { ... },
  "rera": {
    "entity_searched": "ORGANO ALOOR EXTENSION",
    "total_projects": 2,
    "projects": [ ... all scraped projects in one array ... ]
  }
}
```

Fetch a saved report:

```bash
curl http://localhost:8000/api/reports/{report_id}
```

### Search INFRA.All_projects (extension Enable Search)

Elasticsearch-style full-text search over scraped projects:

```bash
curl "http://localhost:8000/api/infra/search?q=prestige&page=1&page_size=20"
```

Query params: `q` (required), `page`, `page_size` (max 100). Results are ranked by MongoDB text score.

The **Enable Search** button in the extension opens a search modal that calls this API (no auto-select on page text).

### Scrape logs

Scrape progress is printed only in the terminal where you run the API:

```bash
cd rera-scraper && source .venv/bin/activate && python run_api.py
```

Example output:

```
12:34:56 INFO [rera.report] [971c1e88...] Report placed for entity='...' — scrape queued
12:34:56 INFO [rera.report] [971c1e88...] Starting RERA scrape in background
12:34:58 INFO [rera.report] [971c1e88...] Searching project: ...
12:35:01 INFO [rera.report] [971c1e88...]   Found 2 result(s)
12:35:10 INFO [rera.report] [971c1e88...] Scrape completed: 2 project(s) saved
```

## Notes

- Project names must be at least **4 characters** (portal validation).
- Captcha is solved automatically; if OCR fails repeatedly, run with `--headed` and inspect the captcha image.
- The portal uses a self-signed certificate chain; HTTPS errors are ignored in Playwright.
