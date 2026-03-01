"""CLI entrypoint for running one sync cycle."""

from __future__ import annotations

import argparse
import sys

from simapwatch.fetcher import HttpHtmlFetcher
from simapwatch.repository import SqliteAwardRepository
from simapwatch.services import SyncInterruptedError, SyncProgress, SyncService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one SIMAP sync cycle.")
    parser.add_argument(
        "--overview-url",
        default="https://www.simap.ch/api/publications/v2/project/project-search?lang=de&newestPubTypes=award_tender",
        help="Overview source URL (API or HTML page).",
    )
    parser.add_argument(
        "--db-path",
        default="simapwatch.db",
        help="SQLite database path.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=20,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Number of concurrent detail-page fetch workers.",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Delete existing awards, sync runs and parse errors before the sync starts.",
    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="Fetch all overview pages instead of stopping at the first already known entry.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    repository = SqliteAwardRepository(args.db_path)
    repository.init_schema()
    if args.reset_db:
        repository.clear_all_data()

    fetcher = HttpHtmlFetcher(timeout_seconds=args.timeout_seconds)
    def print_progress(progress: SyncProgress) -> None:
        if progress.phase == "overview":
            print(
                f"overview pages={progress.overview_page_count} discovered={progress.discovered_count}",
                file=sys.stdout,
                flush=True,
            )
            return
        print(
            f"progress processed={progress.processed_count}/{progress.total_count} "
            f"new={progress.new_count} updated={progress.updated_count} errors={progress.error_count}",
            file=sys.stdout,
            flush=True,
        )

    print(
        f"starting overview_url={args.overview_url} db_path={args.db_path} "
        f"workers={args.max_workers} reset={args.reset_db} incremental={not args.full_sync}",
        file=sys.stdout,
        flush=True,
    )

    service = SyncService(
        fetcher=fetcher,
        repository=repository,
        max_workers=args.max_workers,
        progress_callback=print_progress,
        incremental=not args.full_sync,
    )
    try:
        stats = service.run_once(args.overview_url)
    except SyncInterruptedError as interrupted:
        stats = interrupted.stats
        print(
            f"status={stats.status} overview={stats.overview_count} "
            f"new={stats.new_count} updated={stats.updated_count} errors={stats.error_count}",
            file=sys.stdout,
            flush=True,
        )
        return 130

    print(
        f"status={stats.status} overview={stats.overview_count} "
        f"new={stats.new_count} updated={stats.updated_count} errors={stats.error_count}"
    )
    return 0 if stats.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
