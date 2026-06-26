"""CLI search tool for Madhya Pradesh RERA project data stored in MongoDB.

Usage:
    python main.py "Gravity Infrastructures"
    python main.py "Indore" --mongo-collection MP_allprojects
"""

from __future__ import annotations

import argparse
import logging
import sys

from rera_scraper.infra_search import InfraProjectSearch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search Madhya Pradesh RERA project data in MongoDB.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query (e.g. project name, promoter name, district).",
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
        help="MongoDB collection name.",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Result page number.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="Results per page.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.query:
        print("Please provide a search query.")
        sys.exit(1)

    print(f"Searching for: {args.query!r}")
    search = InfraProjectSearch(
        uri=args.mongo_uri,
        db_name=args.mongo_db,
        collection_name=args.mongo_collection,
    )
    try:
        search.ping()
        res = search.search(args.query, page=args.page, page_size=args.page_size)
        total = res.get("total_count", 0)
        results = res.get("results", [])
        print(f"Found {total} matching project(s) (showing page {args.page}):")
        for i, doc in enumerate(results, start=1):
            print(
                f"  {i:3}. [{doc.get('registration_no', '—')}] "
                f"{doc.get('project_name', '—')} | "
                f"{doc.get('promoter_name', '—')} | "
                f"{doc.get('district', '—')}"
            )
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    finally:
        search.close()


if __name__ == "__main__":
    main()
