"""CLI: scrape all Tamil Nadu registered building projects and save them to MongoDB."""

from __future__ import annotations

import argparse
import asyncio
import logging

from rera_scraper.advanced_scraper import run_advanced_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Tamil Nadu RERA registered building projects."
    )
    parser.add_argument(
        "--district",
        nargs="+",
        metavar="ID",
        help="Filter district names/IDs (optional).",
    )
    parser.add_argument(
        "--project-type",
        nargs="+",
        metavar="ID",
        help="Filter project type IDs (optional).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        metavar="N",
        help="Limit page/year count (optional).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in visible mode (if applicable).",
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB URI. Default: mongodb://localhost:27017",
    )
    parser.add_argument(
        "--mongo-db",
        default="INFRA",
        help="MongoDB database. Default: INFRA",
    )
    parser.add_argument(
        "--mongo-collection",
        default="TN_allprojects",
        help="MongoDB collection. Default: TN_allprojects",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Skip saving to MongoDB.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = asyncio.run(
        run_advanced_scraper(
            headless=not args.headed,
            mongo_uri=args.mongo_uri,
            mongo_db=args.mongo_db,
            mongo_collection=args.mongo_collection,
            district_ids=args.district,
            project_type_ids=args.project_type,
            max_pages=args.max_pages,
            save_mongo=not args.no_mongo,
        )
    )
    print(f"Done. Scraped {len(rows)} table row(s).")


if __name__ == "__main__":
    main()
