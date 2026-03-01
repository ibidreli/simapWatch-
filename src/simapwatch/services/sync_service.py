"""Orchestrates one full SIMAP sync run."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import urllib.parse
from typing import Callable, Optional

from simapwatch.fetcher import HtmlFetcher
from simapwatch.parsers import (
    extract_overview_pagination_last_item,
    parse_award_details,
    parse_overview,
)
from simapwatch.repository import SaveOutcome, SqliteAwardRepository, SyncRunStatus


@dataclass(frozen=True)
class SyncStats:
    """Summary of one sync execution."""

    overview_count: int
    new_count: int
    updated_count: int
    error_count: int
    status: str


@dataclass(frozen=True)
class SyncProgress:
    """Progress update for a running sync."""

    total_count: int
    processed_count: int
    new_count: int
    updated_count: int
    error_count: int
    phase: str = "details"
    discovered_count: int = 0
    overview_page_count: int = 0


class SyncInterruptedError(KeyboardInterrupt):
    """Raised when the sync is interrupted by the user."""

    def __init__(self, stats: SyncStats):
        super().__init__("sync interrupted by user")
        self.stats = stats


class SyncService:
    """Runs overview fetch, detail fetch, parse and persistence."""

    def __init__(
        self,
        *,
        fetcher: HtmlFetcher,
        repository: SqliteAwardRepository,
        max_workers: int = 8,
        progress_callback: Optional[Callable[[SyncProgress], None]] = None,
        incremental: bool = True,
    ):
        self._fetcher = fetcher
        self._repository = repository
        self._max_workers = max(1, max_workers)
        self._progress_callback = progress_callback
        self._incremental = incremental

    @staticmethod
    def _is_project_search_api(url: str) -> bool:
        return "/api/publications/v2/project/project-search" in url

    @staticmethod
    def _with_last_item(url: str, last_item: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        query["lastItem"] = [last_item]
        encoded = urllib.parse.urlencode(query, doseq=True)
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, encoded, parsed.fragment))

    def _make_executor(self):
        return ThreadPoolExecutor(max_workers=self._max_workers)

    @staticmethod
    def _iter_completed_futures(future_map):
        return as_completed(future_map)

    def _report_progress(
        self,
        *,
        total_count: int,
        processed_count: int,
        new_count: int,
        updated_count: int,
        error_count: int,
        phase: str = "details",
        discovered_count: int = 0,
        overview_page_count: int = 0,
    ) -> None:
        if self._progress_callback is None:
            return
        self._progress_callback(
            SyncProgress(
                total_count=total_count,
                processed_count=processed_count,
                new_count=new_count,
                updated_count=updated_count,
                error_count=error_count,
                phase=phase,
                discovered_count=discovered_count,
                overview_page_count=overview_page_count,
            )
        )

    def _fetch_overview_entries(self, overview_url: str) -> list:
        incremental_boundary_active = self._incremental and self._repository.count_awards() > 0
        if not self._is_project_search_api(overview_url):
            raw = self._fetcher.fetch_text(overview_url)
            parsed_entries = parse_overview(raw)
            if parsed_entries:
                return self._filter_incremental_entries(parsed_entries, incremental_boundary_active)
            fallback_url = (
                "https://www.simap.ch/api/publications/v2/project/project-search"
                "?lang=de&newestPubTypes=award_tender"
            )
            return self._fetch_overview_entries(fallback_url)

        all_entries = []
        seen_urls: set[str] = set()
        current_url = overview_url
        seen_last_items: set[str] = set()
        max_pages = 2000

        for page_index in range(1, max_pages + 1):
            raw = self._fetcher.fetch_text(current_url)
            page_entries = parse_overview(raw)
            should_stop = False
            for entry in page_entries:
                if entry.project_url in seen_urls:
                    continue
                if self._should_stop_at_known_entry(entry.project_url, incremental_boundary_active):
                    should_stop = True
                    break
                seen_urls.add(entry.project_url)
                all_entries.append(entry)

            self._report_progress(
                total_count=0,
                processed_count=0,
                new_count=0,
                updated_count=0,
                error_count=0,
                phase="overview",
                discovered_count=len(all_entries),
                overview_page_count=page_index,
            )

            if should_stop:
                break

            last_item = extract_overview_pagination_last_item(raw)
            if not last_item:
                break
            if last_item in seen_last_items:
                break
            seen_last_items.add(last_item)
            current_url = self._with_last_item(overview_url, last_item)

        return all_entries

    def _filter_incremental_entries(self, entries: list, incremental_boundary_active: bool) -> list:
        filtered = []
        for entry in entries:
            if self._should_stop_at_known_entry(entry.project_url, incremental_boundary_active):
                break
            filtered.append(entry)
        return filtered

    def _should_stop_at_known_entry(self, project_url: str, incremental_boundary_active: bool) -> bool:
        if not incremental_boundary_active:
            return False
        return self._repository.has_project_url(project_url)

    def _fetch_and_parse_entry(self, entry) -> tuple[object, list]:
        detail_html = self._fetcher.fetch_text(entry.project_url)
        details = parse_award_details(detail_html, source_url=entry.project_url)
        if not details:
            raise ValueError("no award detail rows parsed")
        for detail in details:
            if not detail.publication_number:
                raise ValueError("publication_number missing")
        return entry, details

    def run_once(self, overview_url: str) -> SyncStats:
        run_id = self._repository.start_sync_run()
        overview_count = 0
        new_count = 0
        updated_count = 0
        error_count = 0
        processed_count = 0
        executor = None

        try:
            entries = self._fetch_overview_entries(overview_url)
            overview_count = len(entries)
            self._report_progress(
                total_count=overview_count,
                processed_count=processed_count,
                new_count=new_count,
                updated_count=updated_count,
                error_count=error_count,
                phase="details",
                discovered_count=overview_count,
            )

            executor = self._make_executor()
            future_map = {
                executor.submit(self._fetch_and_parse_entry, entry): entry for entry in entries
            }
            try:
                for future in self._iter_completed_futures(future_map):
                    entry = future_map[future]
                    try:
                        resolved_entry, details = future.result()
                        for detail in details:
                            outcome = self._repository.upsert_award(resolved_entry, detail)
                            if outcome == SaveOutcome.INSERTED:
                                new_count += 1
                            elif outcome == SaveOutcome.UPDATED:
                                updated_count += 1
                    except Exception as error:  # pragma: no cover - covered in integration
                        error_count += 1
                        self._repository.log_parse_error(run_id, entry.project_url, str(error))
                    finally:
                        processed_count += 1
                        self._report_progress(
                            total_count=overview_count,
                            processed_count=processed_count,
                            new_count=new_count,
                            updated_count=updated_count,
                            error_count=error_count,
                            phase="details",
                            discovered_count=overview_count,
                        )
            except KeyboardInterrupt:
                executor.shutdown(wait=False, cancel_futures=True)
                executor = None
                interrupted_stats = SyncStats(
                    overview_count=overview_count,
                    new_count=new_count,
                    updated_count=updated_count,
                    error_count=error_count,
                    status="interrupted",
                )
                self._repository.finish_sync_run(
                    run_id,
                    status=SyncRunStatus.FAILED,
                    overview_count=overview_count,
                    new_count=new_count,
                    updated_count=updated_count,
                    error_count=error_count,
                    error_message="interrupted by user",
                )
                raise SyncInterruptedError(interrupted_stats)
            finally:
                if executor is not None:
                    executor.shutdown(wait=True, cancel_futures=False)
                    executor = None

            self._repository.finish_sync_run(
                run_id,
                status=SyncRunStatus.SUCCESS,
                overview_count=overview_count,
                new_count=new_count,
                updated_count=updated_count,
                error_count=error_count,
            )
            return SyncStats(
                overview_count=overview_count,
                new_count=new_count,
                updated_count=updated_count,
                error_count=error_count,
                status=SyncRunStatus.SUCCESS.value,
            )
        except SyncInterruptedError:
            raise
        except Exception as error:
            self._repository.finish_sync_run(
                run_id,
                status=SyncRunStatus.FAILED,
                overview_count=overview_count,
                new_count=new_count,
                updated_count=updated_count,
                error_count=error_count + 1,
                error_message=str(error),
            )
            return SyncStats(
                overview_count=overview_count,
                new_count=new_count,
                updated_count=updated_count,
                error_count=error_count + 1,
                status=SyncRunStatus.FAILED.value,
            )
