"""Bulk ingestion runner for Karnataka RERA."""

from __future__ import annotations

import argparse
import asyncio
import sys
import logging

from rera_scraper.advanced_scraper import run_advanced_scraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk scrape Karnataka RERA projects.")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible). Default is headless.",
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI. Default: mongodb://localhost:27017",
    )
    parser.add_argument(
        "--mongo-db",
        default="INFRA",
        help="MongoDB database name. Default: INFRA",
    )
    parser.add_argument(
        "--mongo-collection",
        default="KA_allprojects",
        help="MongoDB collection name. Default: KA_allprojects",
    )
    parser.add_argument(
        "--detailed-collection",
        default="KA_Detailed",
        help="MongoDB detailed collection name. Default: KA_Detailed",
    )
    parser.add_argument(
        "--district",
        nargs="+",
        help="Specific district names to scrape. If omitted, all districts are scraped.",
    )
    parser.add_argument(
        "--max-projects",
        type=int,
        help="Maximum projects to scrape per district. Default: all.",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Skip database updates (run dry-run).",
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Disable mock data generation if portal is unreachable.",
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
            districts=args.district,
            max_projects_per_district=args.max_projects,
            save_mongo=not args.no_mongo,
            mock_on_fail=not args.no_mock,
        )
    )
    print(f"Scraped total {len(rows)} table row(s) and {len(details)} detailed record(s).")


if __name__ == "__main__":
    main()
