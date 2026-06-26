#!/usr/bin/env bash
# Resume full scrape from Khammam (district 8) through all remaining districts.
# Re-scrapes Khammam × all project types, then continues portal order after Khammam.
# Existing MongoDB docs are upserted by detail_url (no duplicates).

set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate

python scrape_all_projects.py \
  --from-district 8 \
  --max-pages 100 \
  2>&1 | tee -a logs_resume_khammam.log
