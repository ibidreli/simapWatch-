import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.services import SyncStats
from simapwatch.update_runner import run_update


class UpdateRunnerTests(unittest.TestCase):
    def test_run_update_runs_sync_then_exports_csv(self) -> None:
        fake_repository = mock.Mock()
        fake_service = mock.Mock()
        fake_service.run_once.return_value = SyncStats(
            overview_count=3,
            new_count=2,
            updated_count=0,
            error_count=0,
            status="success",
        )

        with (
            mock.patch("simapwatch.update_runner.SqliteAwardRepository", return_value=fake_repository),
            mock.patch("simapwatch.update_runner.HttpHtmlFetcher"),
            mock.patch("simapwatch.update_runner.SyncService", return_value=fake_service),
            mock.patch("simapwatch.update_runner.export_analysis_csv", return_value=12) as export_csv,
        ):
            result = run_update(db_path="simapwatch.db", csv_path="analysis.csv")

        fake_repository.init_schema.assert_called_once()
        fake_service.run_once.assert_called_once()
        export_csv.assert_called_once_with("simapwatch.db", "analysis.csv")
        self.assertEqual(result.sync_stats.status, "success")
        self.assertEqual(result.csv_row_count, 12)

    def test_run_update_skips_csv_when_requested(self) -> None:
        fake_repository = mock.Mock()
        fake_service = mock.Mock()
        fake_service.run_once.return_value = SyncStats(
            overview_count=1,
            new_count=1,
            updated_count=0,
            error_count=0,
            status="success",
        )

        with (
            mock.patch("simapwatch.update_runner.SqliteAwardRepository", return_value=fake_repository),
            mock.patch("simapwatch.update_runner.HttpHtmlFetcher"),
            mock.patch("simapwatch.update_runner.SyncService", return_value=fake_service),
            mock.patch("simapwatch.update_runner.export_analysis_csv") as export_csv,
        ):
            result = run_update(skip_csv=True)

        export_csv.assert_not_called()
        self.assertIsNone(result.csv_row_count)

    def test_run_update_does_not_export_csv_when_sync_failed(self) -> None:
        fake_repository = mock.Mock()
        fake_service = mock.Mock()
        fake_service.run_once.return_value = SyncStats(
            overview_count=1,
            new_count=0,
            updated_count=0,
            error_count=1,
            status="failed",
        )

        with (
            mock.patch("simapwatch.update_runner.SqliteAwardRepository", return_value=fake_repository),
            mock.patch("simapwatch.update_runner.HttpHtmlFetcher"),
            mock.patch("simapwatch.update_runner.SyncService", return_value=fake_service),
            mock.patch("simapwatch.update_runner.export_analysis_csv") as export_csv,
        ):
            result = run_update()

        export_csv.assert_not_called()
        self.assertIsNone(result.csv_row_count)
        self.assertEqual(result.sync_stats.status, "failed")


if __name__ == "__main__":
    unittest.main()
