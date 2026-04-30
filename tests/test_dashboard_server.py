import json
import pathlib
import socket
import sys
import tempfile
import threading
import time
import unittest
from urllib.request import urlopen


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.dashboard.server import make_handler
from simapwatch.domain.contracts import AwardDetail, OverviewEntry
from simapwatch.repository import SqliteAwardRepository
from http.server import ThreadingHTTPServer


class DashboardServerTests(unittest.TestCase):
    def _seed(self, db_path: pathlib.Path) -> None:
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
        repository.update_award_geocoding(
            "PUB-100::1",
            side="winner",
            query="Werkstrasse 10, 3000 Bern, Schweiz",
            status="ok",
            lat=46.948,
            lon=7.447,
        )
        repository.update_award_geocoding(
            "PUB-100::1",
            side="procurement_office",
            query="Bundesgasse 1, 3000 Bern, BE, CH",
            status="ok",
            lat=46.947,
            lon=7.444,
        )

    def test_api_dashboard_returns_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            self._seed(db_path)

            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                host, port = probe.getsockname()

            server = ThreadingHTTPServer((host, port), make_handler(str(db_path)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            time.sleep(0.1)

            try:
                with urlopen(f"http://{host}:{port}/api/dashboard") as response:
                    payload = json.loads(response.read().decode("utf-8"))
                with urlopen(f"http://{host}:{port}/") as response:
                    html = response.read().decode("utf-8")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            self.assertEqual(payload["summary"]["award_count"], 1)
            self.assertIn("simapWatch Dashboard", html)


if __name__ == "__main__":
    unittest.main()
