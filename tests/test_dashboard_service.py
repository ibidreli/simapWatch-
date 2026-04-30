import pathlib
import sys
import tempfile
import unittest
from datetime import date


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.dashboard.service import build_dashboard_payload
from simapwatch.domain.contracts import AwardDetail, OverviewEntry
from simapwatch.repository import SqliteAwardRepository


class DashboardServiceTests(unittest.TestCase):
    def _seed_dashboard_data(self, db_path: pathlib.Path) -> None:
        repository = SqliteAwardRepository(db_path)
        repository.init_schema()

        items = [
            (
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
                    cpv_codes=["45000000", "45200000"],
                    procurement_type="Bauleistung",
                    source_url="https://example.local/proj-1",
                ),
            ),
            (
                OverviewEntry(
                    project_id="proj-2",
                    project_url="https://example.local/proj-2",
                    title="School Transport Services",
                    procurement_office="Etat de Vaud",
                    publication_type="Zuschlag",
                    publication_date="20.02.2026",
                ),
                AwardDetail(
                    publication_number="PUB-101",
                    publication_date="20.02.2026",
                    related_notice_number="PUB-098",
                    winner_name="Transports Dany SA",
                    award_amount_chf=620_000.0,
                    vat_percent=None,
                    offers_count=12,
                    winner_position=1,
                    winner_address="Rue du Nord 26, 1180 Rolle, Schweiz",
                    procurement_office_address="Place du Chateau 1, 1014 Lausanne, VD, CH",
                    cpv_codes=["60100000"],
                    procurement_type="Dienstleistung",
                    source_url="https://example.local/proj-2",
                ),
            ),
            (
                OverviewEntry(
                    project_id="proj-3",
                    project_url="https://example.local/proj-3",
                    title="Medical Equipment Supply",
                    procurement_office="Universitat Zurich",
                    publication_type="Zuschlag",
                    publication_date="15.11.2025",
                ),
                AwardDetail(
                    publication_number="PUB-102",
                    publication_date="15.11.2025",
                    related_notice_number="PUB-097",
                    winner_name="MedTech Supply GmbH",
                    award_amount_chf=280_000.0,
                    vat_percent=None,
                    offers_count=4,
                    winner_position=1,
                    winner_address="Industriestrasse 5, 8005 Zurich, Schweiz",
                    procurement_office_address="Rämistrasse 71, 8006 Zurich, ZH, CH",
                    cpv_codes=["33100000"],
                    procurement_type="Lieferung",
                    source_url="https://example.local/proj-3",
                ),
            ),
        ]

        for entry, detail in items:
            repository.upsert_award(entry, detail)

        geocodes = {
            "PUB-100::1": {
                "winner": (46.948, 7.447, "Werkstrasse 10, 3000 Bern, Schweiz"),
                "procurement_office": (46.947, 7.444, "Bundesgasse 1, 3000 Bern, BE, CH"),
            },
            "PUB-101::1": {
                "winner": (46.458, 6.338, "Rue du Nord 26, 1180 Rolle, Schweiz"),
                "procurement_office": (46.523, 6.632, "Place du Chateau 1, 1014 Lausanne, VD, CH"),
            },
            "PUB-102::1": {
                "winner": (47.388, 8.515, "Industriestrasse 5, 8005 Zurich, Schweiz"),
                "procurement_office": (47.376, 8.548, "Rämistrasse 71, 8006 Zurich, ZH, CH"),
            },
        }
        for award_row_id, values in geocodes.items():
            repository.update_award_geocoding(
                award_row_id,
                side="winner",
                query=values["winner"][2],
                status="ok",
                lat=values["winner"][0],
                lon=values["winner"][1],
            )
            repository.update_award_geocoding(
                award_row_id,
                side="procurement_office",
                query=values["procurement_office"][2],
                status="ok",
                lat=values["procurement_office"][0],
                lon=values["procurement_office"][1],
            )

    def test_build_dashboard_payload_returns_expected_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            self._seed_dashboard_data(db_path)

            payload = build_dashboard_payload(db_path, today=date(2026, 3, 1))

            self.assertEqual(payload["summary"]["award_count"], 3)
            self.assertEqual(payload["summary"]["buyer_count"], 3)
            self.assertEqual(payload["summary"]["winner_count"], 3)
            self.assertEqual(payload["summary"]["recent_30d_count"], 2)
            self.assertAlmostEqual(payload["summary"]["total_volume_chf"], 2_400_000.0)
            self.assertEqual(len(payload["top_winners"]), 3)
            self.assertEqual(payload["top_winners"][0]["winner_name"], "Alpha Bau AG")
            self.assertEqual(payload["top_buyers"][0]["procurement_office"], "Kanton Bern")
            self.assertEqual(payload["cpv_breakdown"][0]["cpv_primary"], "45000000")
            self.assertEqual(payload["recent_awards"][0]["publication_number"], "PUB-100")
            self.assertEqual(payload["recent_awards"][1]["publication_number"], "PUB-101")
            self.assertEqual(len(payload["map_flows"]), 3)
            self.assertEqual(payload["map_flows"][0]["from"]["lat"], 46.947)
            self.assertEqual(payload["map_flows"][0]["to"]["lon"], 7.447)

    def test_build_dashboard_payload_generates_monthly_series(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            self._seed_dashboard_data(db_path)

            payload = build_dashboard_payload(db_path, today=date(2026, 3, 1))

            monthly = payload["monthly_series"]
            self.assertEqual(monthly[-1]["month"], "2026-02")
            self.assertEqual(monthly[-1]["award_count"], 2)
            self.assertAlmostEqual(monthly[-1]["total_volume_chf"], 2_120_000.0)
            self.assertEqual(monthly[0]["month"], "2025-03")


if __name__ == "__main__":
    unittest.main()
