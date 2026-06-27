"""CLI: scrape Telangana project detail pages from INFRA.All_projects in parallel."""

from __future__ import annotations

import argparse
import logging

from rera_scraper.detail_scraper import run_detail_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape Telangana RERA PrintPreview detail pages for rows already stored "
            "in INFRA.All_projects, using a thread pool and district-based sharding."
        )
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=8,
        help="Number of parallel browser workers. Default: 8",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        metavar="N",
        help="Flush to MongoDB after every N scraped projects. Default: 100",
    )
    parser.add_argument(
        "--district",
        nargs="+",
        metavar="ID",
        help="Only scrape projects from these district IDs (e.g. 25 for Hyderabad).",
    )
    parser.add_argument(
        "--worker-index",
        type=int,
        metavar="N",
        help="Shard index for multi-process runs (0..num-workers-1).",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=1,
        metavar="N",
        help="Total shard count when using --worker-index. Default: 1",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Stop after saving N detailed projects (for testing).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        metavar="N",
        help="Limit listing pages per district/type combo (useful for testing).",
    )
    parser.add_argument(
        "--project-type",
        nargs="+",
        metavar="ID",
        help="Only these project type IDs (12=Commercial, 13=Residential, etc.).",
    )
    parser.add_argument(
        "--from-district",
        metavar="ID",
        help="Resume from this district ID onward.",
    )
    parser.add_argument(
        "--from-project-type",
        metavar="ID",
        help="Resume from this project type ID onward.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape even if detail_url already exists in Telangana_Detailed.",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Do not skip URLs already present in Telangana_Detailed.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browsers in visible mode.",
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
        "--all-projects-collection",
        default="All_projects",
        help="Source listing collection. Default: All_projects",
    )
    parser.add_argument(
        "--detailed-collection",
        default="Telangana_Detailed",
        help="Target detail collection. Default: Telangana_Detailed",
    )
    parser.add_argument(
        "--no-mongo",
        action="store_true",
        help="Parse only; do not write to MongoDB.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.worker_index is not None and (
        args.worker_index < 0 or args.worker_index >= args.num_workers
    ):
        raise SystemExit("--worker-index must be between 0 and num-workers - 1")

    result = run_detail_scraper(
        mongo_uri=args.mongo_uri,
        mongo_db=args.mongo_db,
        all_projects_col=args.all_projects_collection,
        detailed_col=args.detailed_collection,
        threads=args.threads,
        batch_size=args.batch_size,
        headless=not args.headed,
        district_ids=args.district,
        worker_index=args.worker_index,
        num_workers=args.num_workers,
        skip_existing=not args.no_skip_existing,
        force=args.force,
        limit=args.limit,
        max_pages=args.max_pages,
        project_type_ids=args.project_type,
        from_district_id=args.from_district,
        from_project_type_id=args.from_project_type,
        save_to_mongo=not args.no_mongo,
    )

    print(
        "Done. "
        f"shards={result['thread_shards']} "
        f"saved={result['saved_count']} "
        f"skipped_existing={result['skipped_existing']} "
        f"errors={result['error_count']} "
        f"detailed_total={result['mongo_detailed_total']}/{result['mongo_listing_total']} "
        f"batch_size={result['batch_size']}"
    )
    for err in result["errors"][:10]:
        label = err.get("project_name") or err.get("shard", "?")
        print(f"  error: {label}: {err['error']}")


if __name__ == "__main__":
    main()
