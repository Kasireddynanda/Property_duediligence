"""CLI entry point for Tamil Nadu RERA scraper."""

from __future__ import annotations

import argparse
import asyncio

from rera_scraper.scraper import run_scraper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Tamil Nadu RERA project data."
    )
    parser.add_argument(
        "projects",
        nargs="*",
        help="Project name(s) to search.",
    )
    parser.add_argument(
        "--promoter",
        nargs="+",
        metavar="NAME",
        help="Search by promoter name.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional CSV/Excel export path.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run in headed mode (if applicable).",
    )
    parser.add_argument(
        "--no-follow-promoter",
        action="store_true",
        help="Do not re-search using Promoter Name from scraped details.",
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI. Default: mongodb://localhost:27017",
    )
    parser.add_argument(
        "--mongo-db",
        default="RERA-DETAILS",
        help="MongoDB database name. Default: RERA-DETAILS",
    )
    parser.add_argument(
        "--mongo-collection",
        default="DETAILS",
        help="MongoDB collection name. Default: DETAILS",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Skip saving to MongoDB.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.projects and not args.promoter:
        raise SystemExit("Provide at least one project name or --promoter NAME")

    asyncio.run(
        run_scraper(
            project_names=args.projects or None,
            promoter_names=args.promoter,
            output_path=args.output,
            headless=not args.headed,
            follow_promoter_search=not args.no_follow_promoter,
            mongo_uri=args.mongo_uri,
            mongo_db=args.mongo_db,
            mongo_collection=args.mongo_collection,
            save_mongo=not args.no_mongo,
        )
    )


if __name__ == "__main__":
    main()
