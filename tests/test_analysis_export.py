import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.analysis import ANALYSIS_COLUMNS, export_analysis_csv, load_analysis_dataframe, load_analysis_rows
from simapwatch.domain.contracts import AwardDetail, OverviewEntry
from simapwatch.repository import SqliteAwardRepository


class AnalysisExportTests(unittest.TestCase):
    def _seed_multi_award(self, db_path: pathlib.Path) -> None:
        repository = SqliteAwardRepository(db_path)
        repository.init_schema()

        entry = OverviewEntry(
            project_id="proj-1",
            project_url="https://www.simap.ch/api/publications/v1/project/proj-1/publication-details/pub-1?lang=de",
            title="Marché de services de transports scolaires spécialisés",
            procurement_office="Direction générale de l'enfance et de la jeunesse",
            publication_type="Zuschlag",
            publication_date="14.06.2025",
        )
        detail_1 = AwardDetail(
            publication_number="PUB-1",
            publication_date="14.06.2025",
            related_notice_number="PUB-0",
            winner_name="ABC Taxis Cochet SA",
            award_amount_chf=1432902.51,
            vat_percent=8.1,
            offers_count=52,
            winner_position=1,
            winner_address="Route de Divonne 66, 1260 Nyon, Schweiz",
            procurement_office_address="Office Street 1, 3000 Bern, BE, CH",
            cpv_codes=["60100000", "60130000"],
            procurement_type="Dienstleistung",
            source_url=entry.project_url,
        )
        detail_2 = AwardDetail(
            publication_number="PUB-1",
            publication_date="14.06.2025",
            related_notice_number="PUB-0",
            winner_name="ES Transport Sarl",
            award_amount_chf=250000.0,
            vat_percent=None,
            offers_count=52,
            winner_position=2,
            winner_address="Route de Crochy 1, 1024 Ecublens VD, Schweiz",
            procurement_office_address="Office Street 1, 3000 Bern, BE, CH",
            cpv_codes=["60100000", "60130000"],
            procurement_type="Dienstleistung",
            source_url=entry.project_url,
        )

        repository.upsert_award(entry, detail_1)
        repository.upsert_award(entry, detail_2)

    def test_load_analysis_rows_builds_expected_schema_and_derived_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            self._seed_multi_award(db_path)

            rows = load_analysis_rows(db_path)

            self.assertEqual(len(rows), 2)
            self.assertEqual(list(rows[0].keys()), ANALYSIS_COLUMNS)
            self.assertEqual(rows[0]["publication_year"], 2025)
            self.assertEqual(rows[0]["publication_month"], 6)
            self.assertEqual(rows[0]["cpv_primary"], "60100000")
            self.assertEqual(rows[0]["cpv_count"], 2)
            self.assertTrue(rows[0]["is_multi_award"])
            self.assertEqual(rows[0]["winner_street"], "Route de Divonne 66")
            self.assertEqual(rows[0]["winner_postal_code"], "1260")
            self.assertEqual(rows[0]["winner_city"], "Nyon")
            self.assertEqual(rows[0]["winner_region"], "Schweiz")
            self.assertEqual(rows[0]["procurement_office_street"], "Office Street 1")
            self.assertEqual(rows[0]["procurement_office_postal_code"], "3000")
            self.assertEqual(rows[0]["procurement_office_city"], "Bern")
            self.assertEqual(rows[0]["procurement_office_region"], "BE, CH")

    def test_load_analysis_dataframe_wraps_rows_in_pandas_dataframe(self) -> None:
        class FakeDataFrame:
            def __init__(self, rows, columns):
                self.rows = rows
                self.columns = columns

        fake_pandas = types.SimpleNamespace(DataFrame=FakeDataFrame)

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            self._seed_multi_award(db_path)

            with mock.patch("simapwatch.analysis.exporter.importlib.import_module", return_value=fake_pandas):
                frame = load_analysis_dataframe(db_path)

            self.assertEqual(frame.columns, ANALYSIS_COLUMNS)
            self.assertEqual(len(frame.rows), 2)

    def test_load_analysis_dataframe_raises_helpful_error_without_pandas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            self._seed_multi_award(db_path)

            with mock.patch(
                "simapwatch.analysis.exporter.importlib.import_module",
                side_effect=ModuleNotFoundError("No module named 'pandas'"),
            ):
                with self.assertRaisesRegex(RuntimeError, "pip install -r requirements.txt"):
                    load_analysis_dataframe(db_path)

    def test_export_analysis_csv_writes_expected_header_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            csv_path = pathlib.Path(tmp_dir) / "analysis.csv"
            self._seed_multi_award(db_path)

            row_count = export_analysis_csv(db_path, csv_path)

            content = csv_path.read_text(encoding="utf-8")
            self.assertEqual(row_count, 2)
            self.assertIn("award_row_id,publication_number,winner_position", content)
            self.assertIn("ABC Taxis Cochet SA", content)
            self.assertIn("ES Transport Sarl", content)


if __name__ == "__main__":
    unittest.main()
