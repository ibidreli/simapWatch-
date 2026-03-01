import pathlib
import json
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.parsers.overview_parser import parse_overview


def load_fixture(name: str) -> str:
    return (ROOT / "Docs" / "Example" / name).read_text(encoding="utf-8")


class OverviewParserTests(unittest.TestCase):
    def test_parse_overview_returns_20_entries(self) -> None:
        html = load_fixture("Overview.txt")
        entries = parse_overview(html)
        self.assertEqual(len(entries), 20)

    def test_first_entry_has_expected_core_fields(self) -> None:
        html = load_fixture("Overview.txt")
        entry = parse_overview(html)[0]

        self.assertEqual(entry.project_id, "3702a8fd-f579-4dd1-9b3b-ee94be5288f9")
        self.assertTrue(entry.project_url.endswith("/de/project-detail/3702a8fd-f579-4dd1-9b3b-ee94be5288f9"))
        self.assertTrue(entry.title.startswith("PL20240025"))
        self.assertEqual(entry.procurement_office, "Azienda Elettrica Ticinese")
        self.assertEqual(entry.publication_type, "Zuschlag")
        self.assertEqual(entry.publication_date, "25.02.2026")

    def test_parse_overview_builds_absolute_url(self) -> None:
        html = """
        <article id="abc">
            <h6 aria-label="Projekttitel: Demo Titel"></h6>
            <p aria-label="Beschaffungsstelle: Demo Amt"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 01.01.2026"></span>
            <a href="/de/project-detail/abc"></a>
        </article>
        """
        entries = parse_overview(html, base_url="https://example.org")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].project_url, "https://example.org/de/project-detail/abc")

    def test_parse_overview_skips_incomplete_entries(self) -> None:
        html = """
        <article id="ok">
            <h6 aria-label="Projekttitel: Vollständig"></h6>
            <p aria-label="Beschaffungsstelle: Amt A"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 02.01.2026"></span>
            <a href="/de/project-detail/ok"></a>
        </article>
        <article id="bad">
            <h6 aria-label="Projekttitel: Unvollständig"></h6>
            <a href="/de/project-detail/bad"></a>
        </article>
        """
        entries = parse_overview(html)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].project_id, "ok")

    def test_parse_overview_supports_api_json(self) -> None:
        payload = {
            "projects": [
                {
                    "id": "proj-1",
                    "publicationId": "pub-1",
                    "title": {"de": "Titel 1"},
                    "procOfficeName": {"de": "Amt 1"},
                    "pubType": "award",
                    "publicationDate": "2026-02-25",
                }
            ],
            "pagination": {"hasNext": False},
        }
        entries = parse_overview(json.dumps(payload), base_url="https://www.simap.ch")
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0].project_url,
            "https://www.simap.ch/api/publications/v1/project/proj-1/publication-details/pub-1?lang=de",
        )
        self.assertEqual(entries[0].publication_type, "Zuschlag")
        self.assertEqual(entries[0].publication_date, "25.02.2026")


if __name__ == "__main__":
    unittest.main()
