import pathlib
import json
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.parsers.detail_parser import parse_award_detail, parse_award_details


def load_fixture(name: str) -> str:
    return (ROOT / "Docs" / "Example" / name).read_text(encoding="utf-8")


class DetailParserTests(unittest.TestCase):
    def test_multiple_winners_create_multiple_detail_rows(self) -> None:
        html = (ROOT / "docs" / "example" / "example_multimple_accepts.txt").read_text(encoding="utf-8")

        details = parse_award_details(html)

        self.assertEqual(len(details), 7)
        self.assertEqual(details[0].publication_number, "#9869-02")
        self.assertEqual(details[0].winner_name, "ABC Taxis Cochet SA")
        self.assertEqual(details[0].winner_address, "Route de Divonne 66, 1260 Nyon, Schweiz")
        self.assertAlmostEqual(details[0].award_amount_chf or 0.0, 1432902.51, places=2)
        self.assertEqual(details[-1].winner_name, "Transports Taxis Dany SA")
        self.assertEqual(details[-1].winner_address, "Rue du Nord 26, 1180 Rolle, Schweiz")

    def test_first_example_extracts_winner_amount_offers(self) -> None:
        html = load_fixture("First_Example.txt")
        detail = parse_award_detail(html)

        self.assertEqual(detail.publication_number, "#17391-02")
        self.assertEqual(detail.related_notice_number, "#17391-01")
        self.assertEqual(detail.winner_name, "ATEGRA AG")
        self.assertEqual(detail.winner_address, "Kreuzstrasse 60, 8008 Zürich, Schweiz")
        self.assertEqual(detail.offers_count, 12)
        self.assertAlmostEqual(detail.award_amount_chf or 0.0, 593203.05, places=2)

    def test_second_example_extracts_publication_and_procurement_type(self) -> None:
        html = load_fixture("Second_Example.txt")
        detail = parse_award_detail(html)

        self.assertEqual(detail.publication_number, "#23385-02")
        self.assertEqual(detail.related_notice_number, "#23385-01")
        self.assertEqual(detail.publication_date, "25.02.2026")
        self.assertEqual(detail.procurement_type, "Bauleistung")
        self.assertEqual(detail.offers_count, 4)

    def test_third_example_extracts_cpv_codes(self) -> None:
        html = load_fixture("Third_Example.txt")
        detail = parse_award_detail(html)

        self.assertEqual(detail.publication_number, "#27702-02")
        self.assertEqual(detail.offers_count, 2)
        self.assertIn("45000000", detail.cpv_codes)
        self.assertIn("45112000", detail.cpv_codes)
        self.assertIn("45113000", detail.cpv_codes)
        self.assertIn("45200000", detail.cpv_codes)

    def test_missing_optional_fields_are_none(self) -> None:
        html = """
        <div id="zuschlag">
            <ul>
                <li><span>#99999-01</span></li>
                <li><span>01.01.2026</span></li>
            </ul>
        </div>
        """
        detail = parse_award_detail(html)
        self.assertEqual(detail.publication_number, "#99999-01")
        self.assertEqual(detail.publication_date, "01.01.2026")
        self.assertIsNone(detail.related_notice_number)
        self.assertIsNone(detail.winner_name)
        self.assertIsNone(detail.award_amount_chf)
        self.assertIsNone(detail.vat_percent)
        self.assertIsNone(detail.offers_count)
        self.assertEqual(detail.cpv_codes, [])

    def test_cpv_codes_are_unique_and_sorted(self) -> None:
        html = """
        <div id="zuschlag"><li><span>#11111-01</span></li></div>
        <div>CPV 45200000 text 45000000 text 45200000 text 45112000</div>
        """
        detail = parse_award_detail(html)
        self.assertEqual(detail.cpv_codes, ["45000000", "45112000", "45200000"])

    def test_parse_detail_supports_api_json(self) -> None:
        payload = {
            "procurement": {
                "orderType": "construction",
                "cpvCode": {"code": 45000000},
                "cpvCodes": [{"code": 45112000}],
            },
            "decision": {
                "vendors": [
                    {
                        "vendorName": "Vendor A",
                        "price": {"price": 123456.78},
                        "vendorAddress": {
                            "street": "Main Street",
                            "postalCode": "8000",
                            "city": "Zurich",
                            "cantonId": "ZH",
                            "countryId": "CH",
                        },
                    }
                ],
                "numberOfSubmissions": 5,
            },
            "referencingPub": {"publicationNumber": "10992-01"},
            "base": {"publicationNumber": "10992-02", "publicationDate": "2026-02-25"},
            "project-info": {
                "procOfficeAddress": {
                    "street": {"de": "Office Street"},
                    "postalCode": "3000",
                    "city": {"de": "Bern"},
                    "cantonId": "BE",
                    "countryId": "CH",
                }
            },
        }
        detail = parse_award_detail(json.dumps(payload))
        self.assertEqual(detail.publication_number, "10992-02")
        self.assertEqual(detail.publication_date, "25.02.2026")
        self.assertEqual(detail.related_notice_number, "10992-01")
        self.assertEqual(detail.winner_name, "Vendor A")
        self.assertEqual(detail.winner_address, "Main Street, 8000 Zurich, ZH, CH")
        self.assertEqual(detail.procurement_office_address, "Office Street, 3000 Bern, BE, CH")
        self.assertAlmostEqual(detail.award_amount_chf or 0.0, 123456.78, places=2)
        self.assertEqual(detail.offers_count, 5)
        self.assertEqual(detail.procurement_type, "Bauleistung")
        self.assertEqual(detail.cpv_codes, ["45000000", "45112000"])

    def test_parse_detail_supports_multiple_vendors_from_api_json(self) -> None:
        payload = {
            "procurement": {"orderType": "service", "cpvCode": {"code": 45000000}},
            "decision": {
                "vendors": [
                    {
                        "vendorName": "Vendor A",
                        "price": {"price": 100.0},
                        "vendorAddress": {
                            "street": "Alpha Street 1",
                            "postalCode": "8000",
                            "city": "Zurich",
                            "countryId": "CH",
                        },
                    },
                    {
                        "vendorName": "Vendor B",
                        "price": {"price": 200.0},
                        "vendorAddress": {
                            "street": "Beta Street 2",
                            "postalCode": "3000",
                            "city": "Bern",
                            "countryId": "CH",
                        },
                    },
                ],
                "numberOfSubmissions": 5,
            },
            "base": {"publicationNumber": "10993-02", "publicationDate": "2026-02-25"},
        }

        details = parse_award_details(json.dumps(payload))

        self.assertEqual(len(details), 2)
        self.assertEqual([detail.winner_name for detail in details], ["Vendor A", "Vendor B"])
        self.assertEqual([detail.award_amount_chf for detail in details], [100.0, 200.0])


if __name__ == "__main__":
    unittest.main()
