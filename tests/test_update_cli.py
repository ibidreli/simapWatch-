import io
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.services import SyncInterruptedError, SyncStats
from simapwatch.update_cli import main
from simapwatch.update_runner import UpdateResult
from simapwatch.geocoding import GeocodingStats


class UpdateCliTests(unittest.TestCase):
    def test_update_cli_runs_update_runner_and_reports_csv(self) -> None:
        result = UpdateResult(
            sync_stats=SyncStats(
                overview_count=3,
                new_count=2,
                updated_count=0,
                error_count=0,
                status="success",
            ),
            geocoding_stats=GeocodingStats(updated_rows=2, queried_addresses=2, skipped_rows=4),
            csv_row_count=12,
            db_path="simapwatch.db",
            csv_path="analysis.csv",
        )

        with (
            mock.patch("simapwatch.update_cli.run_update", return_value=result) as run_update,
            mock.patch("sys.argv", ["update_cli", "--db-path", "simapwatch.db", "--csv-path", "analysis.csv"]),
            io.StringIO() as buffer,
            redirect_stdout(buffer),
        ):
            exit_code = main()
            output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        run_update.assert_called_once()
        self.assertIn("sync status=success", output)
        self.assertIn("geocoding updated_rows=2", output)
        self.assertIn("csv rows=12", output)

    def test_update_cli_skips_csv_when_runner_reports_none(self) -> None:
        result = UpdateResult(
            sync_stats=SyncStats(
                overview_count=1,
                new_count=1,
                updated_count=0,
                error_count=0,
                status="success",
            ),
            geocoding_stats=GeocodingStats(updated_rows=0, queried_addresses=0, skipped_rows=2),
            csv_row_count=None,
            db_path="simapwatch.db",
            csv_path="analysis.csv",
        )

        with (
            mock.patch("simapwatch.update_cli.run_update", return_value=result),
            mock.patch("sys.argv", ["update_cli", "--skip-csv"]),
            io.StringIO() as buffer,
            redirect_stdout(buffer),
        ):
            exit_code = main()
            output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("csv skipped", output)

    def test_update_cli_returns_130_on_interrupt(self) -> None:
        interrupted = SyncInterruptedError(
            SyncStats(
                overview_count=10,
                new_count=4,
                updated_count=0,
                error_count=0,
                status="interrupted",
            )
        )

        with (
            mock.patch("simapwatch.update_cli.run_update", side_effect=interrupted),
            mock.patch("sys.argv", ["update_cli"]),
        ):
            exit_code = main()

        self.assertEqual(exit_code, 130)


if __name__ == "__main__":
    unittest.main()
