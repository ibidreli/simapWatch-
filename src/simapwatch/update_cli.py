"""CLI entrypoint for incremental sync plus analysis export."""

from __future__ import annotations

import argparse
import sys

from simapwatch.services import SyncInterruptedError
from simapwatch.update_runner import default_progress_printer, run_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a SIMAP update cycle and refresh the analysis CSV.")
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
        "--csv-path",
        default="analysis.csv",
        help="Target CSV path.",
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
    parser.add_argument(
        "--skip-csv",
        action="store_true",
        help="Run the sync only and skip the CSV export step.",
    )
    return parser

def main() -> int:
    args = build_parser().parse_args()

    print(
        f"update starting db_path={args.db_path} csv_path={args.csv_path} "
        f"workers={args.max_workers} reset={args.reset_db} incremental={not args.full_sync}",
        file=sys.stdout,
        flush=True,
    )

    try:
        result = run_update(
            db_path=args.db_path,
            csv_path=args.csv_path,
            overview_url=args.overview_url,
            timeout_seconds=args.timeout_seconds,
            max_workers=args.max_workers,
            reset_db=args.reset_db,
            full_sync=args.full_sync,
            skip_csv=args.skip_csv,
            progress_callback=default_progress_printer,
        )
    except SyncInterruptedError as interrupted:
        stats = interrupted.stats
        print(
            f"status={stats.status} overview={stats.overview_count} "
            f"new={stats.new_count} updated={stats.updated_count} errors={stats.error_count}",
            file=sys.stdout,
            flush=True,
        )
        return 130

    stats = result.sync_stats
    print(
        f"sync status={stats.status} overview={stats.overview_count} "
        f"new={stats.new_count} updated={stats.updated_count} errors={stats.error_count}",
        file=sys.stdout,
        flush=True,
    )
    if stats.status != "success":
        return 1

    if result.geocoding_stats is not None:
        print(
            f"geocoding updated_rows={result.geocoding_stats.updated_rows} "
            f"queried_addresses={result.geocoding_stats.queried_addresses} "
            f"skipped_rows={result.geocoding_stats.skipped_rows}",
            file=sys.stdout,
            flush=True,
        )

    if result.csv_row_count is None:
        print("csv skipped", file=sys.stdout, flush=True)
        return 0

    print(f"csv rows={result.csv_row_count} csv_path={args.csv_path}", file=sys.stdout, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
