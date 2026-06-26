"""CLI entry point for Karnataka RERA scraper and search."""

from __future__ import annotations

import argparse
import asyncio
import sys
import logging

from rera_scraper.infra_search import InfraProjectSearch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search Karnataka RERA project data."
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query term (e.g. project name, promoter name, district).",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.query:
        print("Please provide a search query.")
        sys.exit(1)

    print(f"Searching for query: {args.query!r}")
    search = InfraProjectSearch(
        uri=args.mongo_uri,
        db_name=args.mongo_db,
        collection_name=args.mongo_collection,
    )
    try:
        search.ping()
        res = search.search(args.query)
        total = res.get("total_count", 0)
        results = res.get("results", [])
        print(f"Found {total} matching project(s):")
        for i, doc in enumerate(results):
            print(f"{i+1}. Project: {doc.get('project_name')} | Promoter: {doc.get('promoter_name')} | Status: {doc.get('status')} | District: {doc.get('district')}")
    except Exception as exc:
        print(f"Error during search: {exc}")
        sys.exit(1)
    finally:
        search.close()


if __name__ == "__main__":
    main()
