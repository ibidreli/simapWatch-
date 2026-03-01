import pathlib
import json
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import dataclass


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simapwatch.repository import SqliteAwardRepository
from simapwatch.domain.contracts import AwardDetail, OverviewEntry
from simapwatch.services import SyncInterruptedError, SyncProgress, SyncService


def load_fixture(name: str) -> str:
    return (ROOT / "Docs" / "Example" / name).read_text(encoding="utf-8")


class DictFetcher:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping
        self.calls: list[str] = []

    def fetch_text(self, url: str) -> str:
        self.calls.append(url)
        return self.mapping[url]


class SlowConcurrentFetcher(DictFetcher):
    def __init__(self, mapping: dict[str, str], delay_seconds: float):
        super().__init__(mapping)
        self.delay_seconds = delay_seconds
        self._lock = threading.Lock()
        self.active_calls = 0
        self.max_active_calls = 0

    def fetch_text(self, url: str) -> str:
        if url == "https://example.local/overview":
            return super().fetch_text(url)

        with self._lock:
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)

        try:
            time.sleep(self.delay_seconds)
            return super().fetch_text(url)
        finally:
            with self._lock:
                self.active_calls -= 1


@dataclass(eq=False)
class FakeFuture:
    value: object

    def result(self):
        return self.value


class RecordingExecutor:
    def __init__(self):
        self.futures = []
        self.shutdown_calls = []

    def submit(self, fn, *args, **kwargs):
        future = FakeFuture(fn(*args, **kwargs))
        self.futures.append(future)
        return future

    def shutdown(self, wait=True, cancel_futures=False):
        self.shutdown_calls.append((wait, cancel_futures))


class InterruptingSyncService(SyncService):
    def __init__(self, *, fetcher, repository, executor):
        super().__init__(fetcher=fetcher, repository=repository, max_workers=2)
        self._test_executor = executor

    def _make_executor(self):
        return self._test_executor

    def _iter_completed_futures(self, future_map):
        raise KeyboardInterrupt()


class SyncIntegrationTests(unittest.TestCase):
    def _overview_html(self) -> str:
        return """
        <article id="proj-a">
            <h6 aria-label="Projekttitel: Project A"></h6>
            <p aria-label="Beschaffungsstelle: Office A"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 25.02.2026"></span>
            <a href="/de/project-detail/proj-a"></a>
        </article>
        <article id="proj-b">
            <h6 aria-label="Projekttitel: Project B"></h6>
            <p aria-label="Beschaffungsstelle: Office B"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 25.02.2026"></span>
            <a href="/de/project-detail/proj-b"></a>
        </article>
        """

    def test_sync_is_idempotent_and_updates_changed_detail(self) -> None:
        overview_url = "https://example.local/overview"
        detail_url_a = "https://www.simap.ch/de/project-detail/proj-a"
        detail_url_b = "https://www.simap.ch/de/project-detail/proj-b"

        detail_a = load_fixture("First_Example.txt")
        detail_b = load_fixture("Second_Example.txt")

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher(
                {
                    overview_url: self._overview_html(),
                    detail_url_a: detail_a,
                    detail_url_b: detail_b,
                }
            )
            service = SyncService(fetcher=fetcher, repository=repository)

            run1 = service.run_once(overview_url)
            self.assertEqual(run1.status, "success")
            self.assertEqual(run1.overview_count, 2)
            self.assertEqual(run1.new_count, 2)
            self.assertEqual(run1.updated_count, 0)
            self.assertEqual(run1.error_count, 0)
            self.assertEqual(repository.count_awards(), 2)

            run2 = service.run_once(overview_url)
            self.assertEqual(run2.status, "success")
            self.assertEqual(run2.new_count, 0)
            self.assertEqual(run2.updated_count, 0)
            self.assertEqual(run2.error_count, 0)
            self.assertEqual(repository.count_awards(), 2)

            changed_detail_a = detail_a.replace("ATEGRA AG,", "UPDATED AG,", 1)
            fetcher.mapping[detail_url_a] = changed_detail_a

            full_sync_service = SyncService(fetcher=fetcher, repository=repository, incremental=False)
            run3 = full_sync_service.run_once(overview_url)
            self.assertEqual(run3.status, "success")
            self.assertEqual(run3.new_count, 0)
            self.assertEqual(run3.updated_count, 1)
            self.assertEqual(run3.error_count, 0)

            updated = repository.get_award("#17391-02")
            self.assertIsNotNone(updated)
            self.assertEqual(updated["winner_name"], "UPDATED AG")

            latest = repository.latest_sync_run()
            self.assertIsNotNone(latest)
            self.assertEqual(latest.status, "success")
            self.assertEqual(latest.overview_count, 2)
            self.assertEqual(latest.updated_count, 1)

    def test_sync_counts_entry_errors_without_failing_whole_run(self) -> None:
        overview_url = "https://example.local/overview"
        detail_url_a = "https://www.simap.ch/de/project-detail/proj-a"
        detail_url_b = "https://www.simap.ch/de/project-detail/proj-b"

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher(
                {
                    overview_url: self._overview_html(),
                    detail_url_a: "<html><body>broken detail</body></html>",
                    detail_url_b: load_fixture("Second_Example.txt"),
                }
            )
            service = SyncService(fetcher=fetcher, repository=repository)

            run = service.run_once(overview_url)
            self.assertEqual(run.status, "success")
            self.assertEqual(run.overview_count, 2)
            self.assertEqual(run.new_count, 1)
            self.assertEqual(run.updated_count, 0)
            self.assertEqual(run.error_count, 1)
            self.assertEqual(repository.count_awards(), 1)

    def test_sync_follows_api_pagination_last_item(self) -> None:
        overview_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender"
        )
        page2_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender&lastItem=cursor-1"
        )
        detail_url_1 = "https://www.simap.ch/api/publications/v1/project/proj-1/publication-details/pub-1?lang=de"
        detail_url_2 = "https://www.simap.ch/api/publications/v1/project/proj-2/publication-details/pub-2?lang=de"

        page1 = {
            "projects": [
                {
                    "id": "proj-1",
                    "publicationId": "pub-1",
                    "title": {"de": "Projekt 1"},
                    "procOfficeName": {"de": "Amt 1"},
                    "pubType": "award",
                    "publicationDate": "2026-02-25",
                }
            ],
            "pagination": {"lastItem": "cursor-1", "itemsPerPage": 20},
        }
        page2 = {
            "projects": [
                {
                    "id": "proj-2",
                    "publicationId": "pub-2",
                    "title": {"de": "Projekt 2"},
                    "procOfficeName": {"de": "Amt 2"},
                    "pubType": "award",
                    "publicationDate": "2026-02-24",
                }
            ],
            "pagination": {"itemsPerPage": 20},
        }

        detail_1 = {
            "procurement": {"orderType": "construction", "cpvCode": {"code": 45000000}},
            "decision": {"vendors": [{"vendorName": "Vendor 1", "price": {"price": 10.0}}], "numberOfSubmissions": 1},
            "referencingPub": {"publicationNumber": "X-01"},
            "base": {"publicationNumber": "X-02", "publicationDate": "2026-02-25"},
            "project-info": {
                "procOfficeAddress": {
                    "street": {"de": "Street 1"},
                    "postalCode": "8000",
                    "city": {"de": "Zurich"},
                    "cantonId": "ZH",
                    "countryId": "CH",
                }
            },
        }
        detail_2 = {
            "procurement": {"orderType": "supply", "cpvCode": {"code": 45112000}},
            "decision": {"vendors": [{"vendorName": "Vendor 2", "price": {"price": 20.0}}], "numberOfSubmissions": 2},
            "referencingPub": {"publicationNumber": "Y-01"},
            "base": {"publicationNumber": "Y-02", "publicationDate": "2026-02-24"},
            "project-info": {
                "procOfficeAddress": {
                    "street": {"de": "Street 2"},
                    "postalCode": "3000",
                    "city": {"de": "Bern"},
                    "cantonId": "BE",
                    "countryId": "CH",
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher(
                {
                    overview_url: json.dumps(page1),
                    page2_url: json.dumps(page2),
                    detail_url_1: json.dumps(detail_1),
                    detail_url_2: json.dumps(detail_2),
                }
            )
            service = SyncService(fetcher=fetcher, repository=repository)

            run = service.run_once(overview_url)
            self.assertEqual(run.status, "success")
            self.assertEqual(run.overview_count, 2)
            self.assertEqual(run.new_count, 2)
            self.assertEqual(run.error_count, 0)
            self.assertEqual(repository.count_awards(), 2)

    def test_sync_stores_multiple_rows_for_multiple_winners(self) -> None:
        overview_url = "https://example.local/overview"
        detail_url = "https://www.simap.ch/de/project-detail/proj-multi"

        overview_html = """
        <article id="proj-multi">
            <h6 aria-label="Projekttitel: Project Multi"></h6>
            <p aria-label="Beschaffungsstelle: Office Multi"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 14.06.2025"></span>
            <a href="/de/project-detail/proj-multi"></a>
        </article>
        """
        detail_html = (ROOT / "docs" / "example" / "example_multimple_accepts.txt").read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher({overview_url: overview_html, detail_url: detail_html})
            service = SyncService(fetcher=fetcher, repository=repository)

            run = service.run_once(overview_url)

            self.assertEqual(run.status, "success")
            self.assertEqual(run.overview_count, 1)
            self.assertEqual(run.new_count, 7)
            self.assertEqual(run.error_count, 0)
            self.assertEqual(repository.count_awards(), 7)

            winners = repository.get_awards_by_publication_number("#9869-02")
            self.assertEqual(len(winners), 7)
            self.assertEqual(winners[0]["winner_name"], "ABC Taxis Cochet SA")
            self.assertEqual(winners[-1]["winner_name"], "Transports Taxis Dany SA")

    def test_repository_reset_clears_existing_awards(self) -> None:
        overview_url = "https://example.local/overview"
        detail_url_a = "https://www.simap.ch/de/project-detail/proj-a"

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher(
                {
                    overview_url: """
                    <article id="proj-a">
                        <h6 aria-label="Projekttitel: Project A"></h6>
                        <p aria-label="Beschaffungsstelle: Office A"></p>
                        <p aria-label="Publikationstyp: Zuschlag"></p>
                        <span aria-label="Publikationsdatum: 25.02.2026"></span>
                        <a href="/de/project-detail/proj-a"></a>
                    </article>
                    """,
                    detail_url_a: load_fixture("First_Example.txt"),
                }
            )
            service = SyncService(fetcher=fetcher, repository=repository)
            service.run_once(overview_url)
            self.assertEqual(repository.count_awards(), 1)

            repository.clear_all_data()
            self.assertEqual(repository.count_awards(), 0)

    def test_sync_fetches_detail_pages_concurrently(self) -> None:
        overview_url = "https://example.local/overview"
        overview_html = """
        <article id="proj-a">
            <h6 aria-label="Projekttitel: Project A"></h6>
            <p aria-label="Beschaffungsstelle: Office A"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 25.02.2026"></span>
            <a href="/de/project-detail/proj-a"></a>
        </article>
        <article id="proj-b">
            <h6 aria-label="Projekttitel: Project B"></h6>
            <p aria-label="Beschaffungsstelle: Office B"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 25.02.2026"></span>
            <a href="/de/project-detail/proj-b"></a>
        </article>
        <article id="proj-c">
            <h6 aria-label="Projekttitel: Project C"></h6>
            <p aria-label="Beschaffungsstelle: Office C"></p>
            <p aria-label="Publikationstyp: Zuschlag"></p>
            <span aria-label="Publikationsdatum: 25.02.2026"></span>
            <a href="/de/project-detail/proj-c"></a>
        </article>
        """

        detail_payload = json.dumps(
            {
                "procurement": {"orderType": "construction"},
                "decision": {"vendors": [{"vendorName": "Vendor", "price": {"price": 10.0}}]},
                "base": {"publicationNumber": "PUB-02", "publicationDate": "2026-02-25"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = SlowConcurrentFetcher(
                {
                    overview_url: overview_html,
                    "https://www.simap.ch/de/project-detail/proj-a": detail_payload.replace("PUB-02", "PUB-A"),
                    "https://www.simap.ch/de/project-detail/proj-b": detail_payload.replace("PUB-02", "PUB-B"),
                    "https://www.simap.ch/de/project-detail/proj-c": detail_payload.replace("PUB-02", "PUB-C"),
                },
                delay_seconds=0.05,
            )
            service = SyncService(fetcher=fetcher, repository=repository, max_workers=3)

            run = service.run_once(overview_url)

            self.assertEqual(run.status, "success")
            self.assertEqual(run.new_count, 3)
            self.assertGreater(fetcher.max_active_calls, 1)

    def test_sync_reports_progress_updates(self) -> None:
        overview_url = "https://example.local/overview"
        detail_url_a = "https://www.simap.ch/de/project-detail/proj-a"
        detail_url_b = "https://www.simap.ch/de/project-detail/proj-b"
        progress_updates: list[SyncProgress] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher(
                {
                    overview_url: self._overview_html(),
                    detail_url_a: load_fixture("First_Example.txt"),
                    detail_url_b: load_fixture("Second_Example.txt"),
                }
            )
            service = SyncService(
                fetcher=fetcher,
                repository=repository,
                progress_callback=progress_updates.append,
            )

            run = service.run_once(overview_url)

            self.assertEqual(run.status, "success")
            self.assertGreaterEqual(len(progress_updates), 3)
            self.assertEqual(progress_updates[0].total_count, 2)
            self.assertEqual(progress_updates[0].processed_count, 0)
            self.assertEqual(progress_updates[-1].processed_count, 2)
            self.assertEqual(progress_updates[-1].new_count, 2)

    def test_sync_reports_overview_progress_during_pagination(self) -> None:
        overview_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender"
        )
        page2_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender&lastItem=cursor-1"
        )
        progress_updates: list[SyncProgress] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher(
                {
                    overview_url: json.dumps(
                        {
                            "projects": [
                                {
                                    "id": "proj-1",
                                    "publicationId": "pub-1",
                                    "title": {"de": "Projekt 1"},
                                    "procOfficeName": {"de": "Amt 1"},
                                    "pubType": "award",
                                    "publicationDate": "2026-02-25",
                                }
                            ],
                            "pagination": {"lastItem": "cursor-1", "itemsPerPage": 20},
                        }
                    ),
                    page2_url: json.dumps(
                        {
                            "projects": [
                                {
                                    "id": "proj-2",
                                    "publicationId": "pub-2",
                                    "title": {"de": "Projekt 2"},
                                    "procOfficeName": {"de": "Amt 2"},
                                    "pubType": "award",
                                    "publicationDate": "2026-02-24",
                                }
                            ],
                            "pagination": {"itemsPerPage": 20},
                        }
                    ),
                    "https://www.simap.ch/api/publications/v1/project/proj-1/publication-details/pub-1?lang=de": json.dumps(
                        {
                            "procurement": {"orderType": "construction"},
                            "decision": {"vendors": [{"vendorName": "Vendor 1", "price": {"price": 10.0}}]},
                            "base": {"publicationNumber": "PUB-1", "publicationDate": "2026-02-25"},
                        }
                    ),
                    "https://www.simap.ch/api/publications/v1/project/proj-2/publication-details/pub-2?lang=de": json.dumps(
                        {
                            "procurement": {"orderType": "construction"},
                            "decision": {"vendors": [{"vendorName": "Vendor 2", "price": {"price": 20.0}}]},
                            "base": {"publicationNumber": "PUB-2", "publicationDate": "2026-02-24"},
                        }
                    ),
                }
            )
            service = SyncService(
                fetcher=fetcher,
                repository=repository,
                progress_callback=progress_updates.append,
            )

            run = service.run_once(overview_url)

            self.assertEqual(run.status, "success")
            overview_updates = [update for update in progress_updates if update.phase == "overview"]
            self.assertGreaterEqual(len(overview_updates), 2)
            self.assertEqual(overview_updates[0].discovered_count, 1)
            self.assertEqual(overview_updates[-1].discovered_count, 2)

    def test_incremental_sync_stops_when_first_known_entry_is_reached(self) -> None:
        overview_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender"
        )
        page2_url = (
            "https://www.simap.ch/api/publications/v2/project/project-search"
            "?lang=de&newestPubTypes=award_tender&lastItem=cursor-1"
        )
        detail_url_new_1 = "https://www.simap.ch/api/publications/v1/project/proj-new-1/publication-details/pub-new-1?lang=de"
        detail_url_new_2 = "https://www.simap.ch/api/publications/v1/project/proj-new-2/publication-details/pub-new-2?lang=de"
        detail_url_known = "https://www.simap.ch/api/publications/v1/project/proj-known/publication-details/pub-known?lang=de"

        first_page = {
            "projects": [
                {
                    "id": "proj-new-1",
                    "publicationId": "pub-new-1",
                    "title": {"de": "Projekt Neu 1"},
                    "procOfficeName": {"de": "Amt 1"},
                    "pubType": "award",
                    "publicationDate": "2026-02-26",
                },
                {
                    "id": "proj-new-2",
                    "publicationId": "pub-new-2",
                    "title": {"de": "Projekt Neu 2"},
                    "procOfficeName": {"de": "Amt 2"},
                    "pubType": "award",
                    "publicationDate": "2026-02-25",
                },
                {
                    "id": "proj-known",
                    "publicationId": "pub-known",
                    "title": {"de": "Projekt Bekannt"},
                    "procOfficeName": {"de": "Amt 3"},
                    "pubType": "award",
                    "publicationDate": "2026-02-24",
                },
            ],
            "pagination": {"lastItem": "cursor-1", "itemsPerPage": 20},
        }
        second_page = {
            "projects": [
                {
                    "id": "proj-old",
                    "publicationId": "pub-old",
                    "title": {"de": "Projekt Alt"},
                    "procOfficeName": {"de": "Amt 4"},
                    "pubType": "award",
                    "publicationDate": "2026-02-23",
                }
            ],
            "pagination": {"itemsPerPage": 20},
        }

        detail_payload = lambda number, name: json.dumps(
            {
                "procurement": {"orderType": "construction"},
                "decision": {"vendors": [{"vendorName": name, "price": {"price": 10.0}}]},
                "base": {"publicationNumber": number, "publicationDate": "2026-02-25"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()
            repository.upsert_award(
                OverviewEntry(
                    project_id="proj-known",
                    project_url=detail_url_known,
                    title="Projekt Bekannt",
                    procurement_office="Amt 3",
                    publication_type="Zuschlag",
                    publication_date="24.02.2026",
                ),
                AwardDetail(
                    publication_number="PUB-KNOWN",
                    publication_date="24.02.2026",
                    related_notice_number=None,
                    winner_name="Known Vendor",
                    award_amount_chf=10.0,
                    vat_percent=None,
                    offers_count=None,
                    winner_position=1,
                    winner_address=None,
                    procurement_office_address=None,
                    cpv_codes=[],
                    procurement_type="Bauleistung",
                    source_url=detail_url_known,
                ),
            )

            fetcher = DictFetcher(
                {
                    overview_url: json.dumps(first_page),
                    page2_url: json.dumps(second_page),
                    detail_url_new_1: detail_payload("PUB-NEW-1", "Vendor 1"),
                    detail_url_new_2: detail_payload("PUB-NEW-2", "Vendor 2"),
                    detail_url_known: detail_payload("PUB-KNOWN", "Known Vendor"),
                }
            )

            run = SyncService(fetcher=fetcher, repository=repository).run_once(overview_url)

            self.assertEqual(run.status, "success")
            self.assertEqual(run.overview_count, 2)
            self.assertEqual(run.new_count, 2)
            self.assertNotIn(page2_url, fetcher.calls)
            self.assertNotIn(detail_url_known, fetcher.calls)

    def test_sync_interrupt_shuts_down_executor_without_waiting(self) -> None:
        overview_url = "https://example.local/overview"
        executor = RecordingExecutor()

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = pathlib.Path(tmp_dir) / "simapwatch.db"
            repository = SqliteAwardRepository(db_path)
            repository.init_schema()

            fetcher = DictFetcher(
                {
                    overview_url: self._overview_html(),
                    "https://www.simap.ch/de/project-detail/proj-a": load_fixture("First_Example.txt"),
                    "https://www.simap.ch/de/project-detail/proj-b": load_fixture("Second_Example.txt"),
                }
            )
            service = InterruptingSyncService(fetcher=fetcher, repository=repository, executor=executor)

            raised = None
            try:
                service.run_once(overview_url)
            except SyncInterruptedError as error:
                raised = error

            self.assertIsNotNone(raised)
            self.assertEqual(raised.stats.status, "interrupted")
            self.assertIn((False, True), executor.shutdown_calls)


if __name__ == "__main__":
    unittest.main()
