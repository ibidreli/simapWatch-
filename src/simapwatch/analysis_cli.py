"""CLI entrypoint for analysis exports."""

from __future__ import annotations

import argparse

from simapwatch.analysis import export_analysis_csv, load_analysis_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export analysis rows from the SIMAP SQLite database.")
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    row_count = export_analysis_csv(args.db_path, args.csv_path)
    print(f"rows={row_count} csv_path={args.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
