"""CLI: scrape Delhi RERA registered projects with full tab details."""

from __future__ import annotations

import argparse
import logging

from rera_scraper.delhi_scraper import scrape_delhi_projects

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape Delhi RERA registered projects from erera.co.in "
            "and store list rows + all detail tabs in MongoDB."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Scrape only the first N projects (for testing).",
    )
    parser.add_argument(
        "--registration-no",
        metavar="NO",
        help="Scrape a single project by registration number (e.g. DLRERA2026P0008).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.75,
        help="Seconds between detail-page requests. Default: 0.75",
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
        default="Delhi_allprojects_detailed",
        help="MongoDB collection. Default: Delhi_allprojects_detailed",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Parse only; do not write to MongoDB.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = scrape_delhi_projects(
        mongo_uri=args.mongo_uri,
        mongo_db=args.mongo_db,
        mongo_collection=args.mongo_collection,
        limit=args.limit,
        delay_seconds=args.delay,
        save_to_mongo=not args.no_mongo,
        registration_no=args.registration_no,
    )
    print(
        f"Done. listing={result['listing_count']} saved={result['saved_count']} "
        f"mongo_total={result['mongo_total']} errors={len(result['errors'])}"
    )
    for err in result["errors"][:10]:
        print(f"  error: {err['registration_no']}: {err['error']}")


if __name__ == "__main__":
    main()
