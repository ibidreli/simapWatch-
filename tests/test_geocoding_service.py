import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.domain.contracts import AwardDetail, OverviewEntry
from simapwatch.geocoding.service import GeocodingResult, geocode_missing_awards
from simapwatch.repository import SqliteAwardRepository


class FakeGeocoder:
    def __init__(self, mapping: dict[str, GeocodingResult]):
        self.mapping = mapping
        self.calls: list[str] = []

    def geocode(self, query: str) -> GeocodingResult:
        self.calls.append(query)
        return self.mapping[query]


class GeocodingServiceTests(unittest.TestCase):
    def _seed_award(self, db_path: pathlib.Path) -> SqliteAwardRepository:
        repository = SqliteAwardRepository(db_path)
        repository.init_schema()
        repository.upsert_award(
            OverviewEntry(
                project_id="proj-1",
                project_url="https://example.local/proj-1",
                title="Bridge Renovation",
                procurement_office="Kanton Bern",
                publication_type="Zuschlag",
                publication_date="28.02.2026",
            ),
            AwardDetail(
                publication_number="PUB-100",
                publication_date="28.02.2026",
                related_notice_number="PUB-099",
                winner_name="Alpha Bau AG",
                award_amount_chf=1_500_000.0,
                vat_percent=8.1,
                offers_count=6,
                winner_position=1,
                winner_address="Werkstrasse 10, 3000 Bern, Schweiz",
                procurement_office_address="Bundesgasse 1, 3000 Bern, BE, CH",
                cpv_codes=["45000000"],
                procurement_type="Bauleistung",
                source_url="https://example.local/proj-1",
            ),
        )
        return repository

    def test_geocode_missing_awards_updates_both_coordinate_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = self._seed_award(db_path)
            geocoder = FakeGeocoder(
                {
                    "Werkstrasse 10, 3000 Bern, Schweiz": GeocodingResult("ok", 46.948, 7.447),
                    "Bundesgasse 1, 3000 Bern, BE, CH": GeocodingResult("ok", 46.947, 7.444),
                }
            )

            stats = geocode_missing_awards(repository, geocoder)

            self.assertEqual(stats.updated_rows, 2)
            row = repository.get_award("PUB-100")
            self.assertEqual(row["winner_geocode_status"], "ok")
            self.assertEqual(row["procurement_office_geocode_status"], "ok")
            self.assertAlmostEqual(row["winner_lat"], 46.948)
            self.assertAlmostEqual(row["winner_lon"], 7.447)
            self.assertAlmostEqual(row["procurement_office_lat"], 46.947)
            self.assertAlmostEqual(row["procurement_office_lon"], 7.444)

    def test_geocode_missing_awards_skips_cached_queries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = self._seed_award(db_path)
            geocoder = FakeGeocoder(
                {
                    "Werkstrasse 10, 3000 Bern, Schweiz": GeocodingResult("ok", 46.948, 7.447),
                    "Bundesgasse 1, 3000 Bern, BE, CH": GeocodingResult("ok", 46.947, 7.444),
                }
            )

            geocode_missing_awards(repository, geocoder)
            geocoder.calls.clear()
            stats = geocode_missing_awards(repository, geocoder)

            self.assertEqual(stats.updated_rows, 0)
            self.assertEqual(geocoder.calls, [])


if __name__ == "__main__":
    unittest.main()
