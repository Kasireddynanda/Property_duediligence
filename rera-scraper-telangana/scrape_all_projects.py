"""CLI: scrape all projects via Advanced Search (District × Project Type)."""

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
        description=(
            "Scrape Telangana RERA project table via Advanced Search "
            "(every District × Project Type combination)."
        )
    )
    parser.add_argument(
        "--district",
        nargs="+",
        metavar="ID",
        help="Only these district IDs (e.g. 25 for Hyderabad). Default: all.",
    )
    parser.add_argument(
        "--project-type",
        nargs="+",
        metavar="ID",
        help="Only these project type IDs (12=Commercial, 13=Residential, etc.). Default: all.",
    )
    parser.add_argument(
        "--from-district",
        metavar="ID",
        help="Resume from this district ID onward (portal dropdown order). E.g. 8 = Khammam.",
    )
    parser.add_argument(
        "--from-project-type",
        metavar="ID",
        help="Resume from this project type ID onward. E.g. 15 = Plotted Development.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        metavar="N",
        help="Limit pages per district/type combo (useful for testing).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in visible mode.",
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
        default="All_projects",
        help="MongoDB collection. Default: All_projects",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Skip saving to MongoDB (scrape only, print counts).",
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
            from_district_id=args.from_district,
            from_project_type_id=args.from_project_type,
            max_pages=args.max_pages,
            save_mongo=not args.no_mongo,
        )
    )
    print(f"Done. Scraped {len(rows)} table row(s).")


if __name__ == "__main__":
    main()
