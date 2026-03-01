"""Reusable Python update runner for sync plus analysis export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from simapwatch.analysis import export_analysis_csv
from simapwatch.fetcher import HttpHtmlFetcher
from simapwatch.repository import SqliteAwardRepository
from simapwatch.services import SyncProgress, SyncService, SyncStats


DEFAULT_OVERVIEW_URL = (
    "https://www.simap.ch/api/publications/v2/project/project-search"
    "?lang=de&newestPubTypes=award_tender"
)


@dataclass(frozen=True)
class UpdateResult:
    sync_stats: SyncStats
    csv_row_count: Optional[int]
    db_path: str
    csv_path: str


def default_progress_printer(progress: SyncProgress) -> None:
    if progress.phase == "overview":
        print(f"overview pages={progress.overview_page_count} discovered={progress.discovered_count}", flush=True)
        return
    print(
        f"progress processed={progress.processed_count}/{progress.total_count} "
        f"new={progress.new_count} updated={progress.updated_count} errors={progress.error_count}",
        flush=True,
    )


def run_update(
    *,
    db_path: str = "simapwatch.db",
    csv_path: str = "analysis.csv",
    overview_url: str = DEFAULT_OVERVIEW_URL,
    timeout_seconds: int = 20,
    max_workers: int = 8,
    reset_db: bool = False,
    full_sync: bool = False,
    skip_csv: bool = False,
    progress_callback: Optional[Callable[[SyncProgress], None]] = None,
) -> UpdateResult:
    repository = SqliteAwardRepository(db_path)
    repository.init_schema()
    if reset_db:
        repository.clear_all_data()

    fetcher = HttpHtmlFetcher(timeout_seconds=timeout_seconds)
    service = SyncService(
        fetcher=fetcher,
        repository=repository,
        max_workers=max_workers,
        progress_callback=progress_callback,
        incremental=not full_sync,
    )
    stats = service.run_once(overview_url)

    csv_row_count: Optional[int] = None
    if stats.status == "success" and not skip_csv:
        csv_row_count = export_analysis_csv(db_path, csv_path)

    return UpdateResult(
        sync_stats=stats,
        csv_row_count=csv_row_count,
        db_path=db_path,
        csv_path=csv_path,
    )
