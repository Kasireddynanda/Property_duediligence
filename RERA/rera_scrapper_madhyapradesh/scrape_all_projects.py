"""Bulk ingestion runner for Madhya Pradesh RERA.

Usage examples
--------------
# Scrape ALL completed projects (headless, store to MongoDB):
python scrape_all_projects.py

# Headed mode (see browser), limit to 50 projects:
python scrape_all_projects.py --headed --max-projects 50

# Dry-run (no MongoDB writes):
python scrape_all_projects.py --no-mongo

# Skip detail-page fetching (listing rows only):
python scrape_all_projects.py --no-details

# Use a custom MongoDB URI:
python scrape_all_projects.py --mongo-uri mongodb://user:pass@host:27017
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from rera_scraper.advanced_scraper import run_advanced_scraper

# ---------------------------------------------------------------------------
# Logging — writes to BOTH stdout (live) and scrape.log (tail -f)
# ---------------------------------------------------------------------------
LOG_FILE = "scrape.log"

_fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

_stdout_handler = logging.StreamHandler(sys.stdout)
_stdout_handler.setFormatter(_fmt)

_file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
_file_handler.setFormatter(_fmt)

logging.basicConfig(
    level=logging.INFO,
    handlers=[_stdout_handler, _file_handler],
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk scrape Madhya Pradesh RERA completed projects.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed (visible) mode.",
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI.",
    )
    parser.add_argument(
        "--mongo-db",
        default="INFRA",
        help="MongoDB database name.",
    )
    parser.add_argument(
        "--mongo-collection",
        default="MP_allprojects",
        help="MongoDB collection for listing rows.",
    )
    parser.add_argument(
        "--detailed-collection",
        default="MP_detailed",
        help="MongoDB collection for detail-page records.",
    )
    parser.add_argument(
        "--max-projects",
        type=int,
        default=None,
        help="Maximum number of projects to scrape. Default: all.",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Skip MongoDB writes (dry-run).",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip fetching individual project detail pages.",
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Disable mock fallback data when portal is unreachable.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    rows, details = asyncio.run(
        run_advanced_scraper(
            headless=not args.headed,
            mongo_uri=args.mongo_uri,
            mongo_db=args.mongo_db,
            all_projects_col=args.mongo_collection,
            detailed_col=args.detailed_collection,
            max_projects=args.max_projects,
            save_mongo=not args.no_mongo,
            scrape_details=not args.no_details,
            mock_on_fail=not args.no_mock,
        )
    )

    print(
        f"\n✅  Done – scraped {len(rows)} listing row(s) "
        f"and {len(details)} detailed record(s)."
    )


if __name__ == "__main__":
    main()
