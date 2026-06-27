"""Thread-pool bulk detail scraper for Telangana RERA projects."""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from .advanced_scraper import (
    AdvancedSearchScraper,
    DropdownOption,
    _filter_from_option,
)
from .hashing import district_worker_shard, project_identity_key
from .infra_store import TelanganaProjectStore

logger = logging.getLogger("rera.telangana.details")


@dataclass
class DetailBatchWriter:
    """Buffer detail records and flush to MongoDB every N saves."""

    store: TelanganaProjectStore
    batch_size: int = 100
    enabled: bool = True
    _buffer: list[dict[str, Any]] = field(default_factory=list)
    total_saved: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def pending_count(self) -> int:
        return self.total_saved + len(self._buffer)

    def add(self, record: dict[str, Any]) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._buffer.append(record)
            if len(self._buffer) >= self.batch_size:
                self._flush_unlocked()

    def flush(self) -> int:
        with self._lock:
            return self._flush_unlocked()

    def _flush_unlocked(self) -> int:
        if not self._buffer:
            return 0
        count = self.store.upsert_detailed_many(self._buffer)
        self.total_saved += count
        logger.info(
            "Flushed %s record(s) to MongoDB (shard total saved: %s, db total: %s)",
            count,
            self.total_saved,
            self.store.detailed_count(),
        )
        self._buffer.clear()
        return count


def load_existing_identity_keys(store: TelanganaProjectStore) -> set[tuple[str, str, str, str]]:
    keys: set[tuple[str, str, str, str]] = set()
    projection = {
        "project_name": 1,
        "promoter_name": 1,
        "search.district_id": 1,
        "search.project_type_id": 1,
    }
    for doc in store.detailed.find({}, projection):
        keys.add(project_identity_key(doc))
    return keys


async def _scrape_district_shard(
    districts: list[DropdownOption],
    project_types: list[DropdownOption],
    *,
    headless: bool,
    max_pages: int | None,
    skip_keys: set[tuple[str, str, str, str]],
    writer: DetailBatchWriter,
    limit: int | None,
) -> int:
    async with AdvancedSearchScraper(headless=headless) as scraper:
        for district in districts:
            for project_type in project_types:
                if limit is not None and writer.pending_count >= limit:
                    writer.flush()
                    return writer.total_saved

                try:
                    await scraper.scrape_combination_with_details(
                        district,
                        project_type,
                        max_pages=max_pages,
                        skip_keys=skip_keys,
                        on_record=writer.add,
                    )
                    if limit is not None and writer.pending_count >= limit:
                        writer.flush()
                        return writer.total_saved
                except Exception as exc:
                    logger.error(
                        "Failed %s / %s: %s",
                        district.label,
                        project_type.label,
                        exc,
                    )
                    writer.flush()
                    try:
                        await scraper.open_search_page()
                        await scraper._dismiss_blocking_overlays()
                    except Exception:
                        pass

    writer.flush()
    return writer.total_saved


def _run_shard_in_thread(
    districts: list[DropdownOption],
    project_types: list[DropdownOption],
    *,
    mongo_uri: str,
    mongo_db: str,
    all_projects_col: str,
    detailed_col: str,
    headless: bool,
    max_pages: int | None,
    skip_keys: set[tuple[str, str, str, str]],
    batch_size: int,
    save_to_mongo: bool,
    limit: int | None,
) -> dict[str, Any]:
    store = TelanganaProjectStore(
        mongo_uri,
        mongo_db,
        all_projects_col,
        detailed_col,
    )
    store.ping()
    writer = DetailBatchWriter(
        store,
        batch_size=batch_size,
        enabled=save_to_mongo,
    )

    try:
        total = asyncio.run(
            _scrape_district_shard(
                districts,
                project_types,
                headless=headless,
                max_pages=max_pages,
                skip_keys=set(skip_keys),
                writer=writer,
                limit=limit,
            )
        )
        return {"saved": total, "shard": ", ".join(d.label for d in districts[:3])}
    except Exception as exc:
        writer.flush()
        raise exc
    finally:
        store.close()


def _build_district_shards(
    districts: list[DropdownOption],
    threads: int,
    district_ids: list[str] | None,
    worker_index: int | None,
    num_workers: int,
) -> list[list[DropdownOption]]:
    filtered = districts
    if district_ids:
        wanted = {str(d) for d in district_ids}
        filtered = [d for d in districts if d.value in wanted]

    if worker_index is not None and num_workers > 1:
        filtered = [
            d
            for d in filtered
            if district_worker_shard(d.value, num_workers) == worker_index
        ]

    shards: list[list[DropdownOption]] = [[] for _ in range(max(threads, 1))]
    for district in filtered:
        shard_index = district_worker_shard(district.value, len(shards))
        shards[shard_index].append(district)

    return [shard for shard in shards if shard]


def run_detail_scraper(
    *,
    mongo_uri: str = "mongodb://localhost:27017",
    mongo_db: str = "INFRA",
    all_projects_col: str = "All_projects",
    detailed_col: str = "Telangana_Detailed",
    threads: int = 8,
    batch_size: int = 100,
    headless: bool = True,
    district_ids: list[str] | None = None,
    worker_index: int | None = None,
    num_workers: int = 1,
    skip_existing: bool = True,
    force: bool = False,
    limit: int | None = None,
    max_pages: int | None = None,
    project_type_ids: list[str] | None = None,
    from_district_id: str | None = None,
    from_project_type_id: str | None = None,
    save_to_mongo: bool = True,
) -> dict[str, Any]:
    if threads < 1:
        raise ValueError("threads must be >= 1")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    store = TelanganaProjectStore(
        mongo_uri,
        mongo_db,
        all_projects_col,
        detailed_col,
    )
    store.ping()

    skip_keys: set[tuple[str, str, str, str]] = set()
    if skip_existing and not force:
        skip_keys = load_existing_identity_keys(store)
        logger.info(
            "Resume mode: skipping %s project(s) already in %s.%s",
            len(skip_keys),
            mongo_db,
            detailed_col,
        )

    existing_count = store.detailed_count()
    store.close()

    bootstrap = AdvancedSearchScraper(headless=headless)

    async def _load_options() -> tuple[list[DropdownOption], list[DropdownOption]]:
        async with bootstrap:
            districts = await bootstrap.get_districts()
            project_types = await bootstrap.get_project_types()
            return districts, project_types

    all_districts, all_project_types = asyncio.run(_load_options())
    districts = _filter_from_option(all_districts, from_district_id)
    project_types = _filter_from_option(all_project_types, from_project_type_id)

    if project_type_ids:
        wanted = {str(t) for t in project_type_ids}
        project_types = [t for t in project_types if t.value in wanted]

    shards = _build_district_shards(
        districts,
        threads,
        district_ids,
        worker_index,
        num_workers,
    )

    logger.info(
        "Starting detail scrape: %s thread shard(s), %s district(s), "
        "%s project type(s), batch_size=%s, already_in_db=%s",
        len(shards),
        sum(len(s) for s in shards),
        len(project_types),
        batch_size,
        existing_count,
    )

    saved = 0
    errors: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=len(shards)) as executor:
        futures = {
            executor.submit(
                _run_shard_in_thread,
                shard,
                project_types,
                mongo_uri=mongo_uri,
                mongo_db=mongo_db,
                all_projects_col=all_projects_col,
                detailed_col=detailed_col,
                headless=headless,
                max_pages=max_pages,
                skip_keys=skip_keys,
                batch_size=batch_size,
                save_to_mongo=save_to_mongo,
                limit=limit,
            ): shard
            for shard in shards
        }

        for future in as_completed(futures):
            shard = futures[future]
            shard_label = ", ".join(d.label for d in shard[:3])
            try:
                result = future.result()
                saved += result.get("saved", 0)
                logger.info("Shard complete (%s...): saved %s", shard_label, result.get("saved"))
            except Exception as exc:
                logger.error("Shard failed (%s...): %s", shard_label, exc)
                errors.append({"shard": shard_label, "error": str(exc)})

    summary_store = TelanganaProjectStore(
        mongo_uri,
        mongo_db,
        all_projects_col,
        detailed_col,
    )
    summary_store.ping()
    total_detailed = summary_store.detailed_count()
    total_listing = summary_store.all_projects_count()
    summary_store.close()

    return {
        "thread_shards": len(shards),
        "saved_count": saved,
        "skipped_existing": len(skip_keys),
        "error_count": len(errors),
        "mongo_detailed_total": total_detailed,
        "mongo_listing_total": total_listing,
        "batch_size": batch_size,
        "errors": errors,
    }
