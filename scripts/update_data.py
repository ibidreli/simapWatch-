from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from simapwatch.services import SyncInterruptedError
from simapwatch.update_runner import default_progress_printer, run_update


DB_PATH = SRC_ROOT / "simapwatch.db"
CSV_PATH = SRC_ROOT / "analysis.csv"
MAX_WORKERS = 12
TIMEOUT_SECONDS = 20
RESET_DB = False
FULL_SYNC = False
SKIP_CSV = False
GEOCODE_MISSING = True


def main() -> int:
    print(
        f"update starting db_path={DB_PATH} csv_path={CSV_PATH} "
        f"workers={MAX_WORKERS} reset={RESET_DB} incremental={not FULL_SYNC}",
        flush=True,
    )
    try:
        result = run_update(
            db_path=str(DB_PATH),
            csv_path=str(CSV_PATH),
            timeout_seconds=TIMEOUT_SECONDS,
            max_workers=MAX_WORKERS,
            reset_db=RESET_DB,
            full_sync=FULL_SYNC,
            skip_csv=SKIP_CSV,
            geocode_missing=GEOCODE_MISSING,
            progress_callback=default_progress_printer,
        )
    except SyncInterruptedError as interrupted:
        stats = interrupted.stats
        print(
            f"status={stats.status} overview={stats.overview_count} "
            f"new={stats.new_count} updated={stats.updated_count} errors={stats.error_count}",
            flush=True,
        )
        return 130

    stats = result.sync_stats
    print(
        f"sync status={stats.status} overview={stats.overview_count} "
        f"new={stats.new_count} updated={stats.updated_count} errors={stats.error_count}",
        flush=True,
    )
    if result.geocoding_stats is not None:
        print(
            f"geocoding updated_rows={result.geocoding_stats.updated_rows} "
            f"queried_addresses={result.geocoding_stats.queried_addresses} "
            f"skipped_rows={result.geocoding_stats.skipped_rows}",
            flush=True,
        )
    if result.csv_row_count is None:
        print("csv skipped", flush=True)
        return 0
    print(f"csv rows={result.csv_row_count} csv_path={result.csv_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
