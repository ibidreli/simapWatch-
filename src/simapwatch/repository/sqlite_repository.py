"""SQLite persistence for scraped awards and sync runs."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional

from simapwatch.domain.contracts import AwardDetail, OverviewEntry


class SaveOutcome(str, Enum):
    """Outcome of upsert operation."""

    INSERTED = "inserted"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class SyncRunStatus(str, Enum):
    """Status values for sync runs."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class SyncRunRecord:
    id: int
    status: str
    overview_count: int
    new_count: int
    updated_count: int
    error_count: int


class SqliteAwardRepository:
    """Repository for writing and reading scraper data."""

    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _awards_table_sql() -> str:
        return """
            CREATE TABLE IF NOT EXISTS awards (
                award_row_id TEXT PRIMARY KEY,
                publication_number TEXT NOT NULL,
                winner_position INTEGER NOT NULL DEFAULT 1,
                related_notice_number TEXT,
                publication_date TEXT,
                project_id TEXT NOT NULL,
                project_url TEXT NOT NULL,
                title TEXT NOT NULL,
                procurement_office TEXT NOT NULL,
                publication_type TEXT NOT NULL,
                overview_publication_date TEXT NOT NULL,
                winner_name TEXT,
                winner_address TEXT,
                procurement_office_address TEXT,
                award_amount_chf REAL,
                vat_percent REAL,
                offers_count INTEGER,
                procurement_type TEXT,
                cpv_codes TEXT NOT NULL DEFAULT '',
                source_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(publication_number, winner_position)
            );
        """

    def init_schema(self) -> None:
        with self._connection() as conn:
            self._ensure_awards_table(conn)
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    overview_count INTEGER NOT NULL DEFAULT 0,
                    new_count INTEGER NOT NULL DEFAULT 0,
                    updated_count INTEGER NOT NULL DEFAULT 0,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS parse_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    source_url TEXT,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES sync_runs(id)
                );
                """
            )

    def _ensure_awards_table(self, conn: sqlite3.Connection) -> None:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'awards'"
        ).fetchone()
        if table_exists is None:
            conn.executescript(self._awards_table_sql())
            return

        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(awards)").fetchall()
        }
        required_columns = {"award_row_id", "winner_position", "winner_address", "procurement_office_address"}
        if required_columns.issubset(columns):
            return

        legacy_columns = columns
        conn.execute("ALTER TABLE awards RENAME TO awards_legacy")
        conn.executescript(self._awards_table_sql())

        winner_address_expr = "winner_address" if "winner_address" in legacy_columns else "NULL"
        procurement_office_address_expr = (
            "procurement_office_address" if "procurement_office_address" in legacy_columns else "NULL"
        )

        conn.execute(
            f"""
            INSERT INTO awards(
                award_row_id, publication_number, winner_position,
                related_notice_number, publication_date,
                project_id, project_url, title, procurement_office, publication_type,
                overview_publication_date, winner_name, winner_address, procurement_office_address,
                award_amount_chf, vat_percent, offers_count, procurement_type,
                cpv_codes, source_url, created_at, updated_at
            )
            SELECT
                publication_number || '::1',
                publication_number,
                1,
                related_notice_number,
                publication_date,
                project_id,
                project_url,
                title,
                procurement_office,
                publication_type,
                overview_publication_date,
                winner_name,
                {winner_address_expr},
                {procurement_office_address_expr},
                award_amount_chf,
                vat_percent,
                offers_count,
                procurement_type,
                cpv_codes,
                source_url,
                created_at,
                updated_at
            FROM awards_legacy
            """
        )
        conn.execute("DROP TABLE awards_legacy")

    def clear_all_data(self) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM awards")
            conn.execute("DELETE FROM parse_errors")
            conn.execute("DELETE FROM sync_runs")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('sync_runs', 'parse_errors')")

    def start_sync_run(self) -> int:
        now = self._now_iso()
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT INTO sync_runs(started_at, status) VALUES(?, ?)",
                (now, SyncRunStatus.RUNNING.value),
            )
            return int(cursor.lastrowid)

    def finish_sync_run(
        self,
        run_id: int,
        *,
        status: SyncRunStatus,
        overview_count: int,
        new_count: int,
        updated_count: int,
        error_count: int,
        error_message: Optional[str] = None,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE sync_runs
                SET finished_at = ?,
                    status = ?,
                    overview_count = ?,
                    new_count = ?,
                    updated_count = ?,
                    error_count = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    self._now_iso(),
                    status.value,
                    overview_count,
                    new_count,
                    updated_count,
                    error_count,
                    error_message,
                    run_id,
                ),
            )

    def log_parse_error(self, run_id: Optional[int], source_url: str, message: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO parse_errors(run_id, source_url, message, created_at) VALUES(?, ?, ?, ?)",
                (run_id, source_url, message, self._now_iso()),
            )

    @staticmethod
    def _cpv_csv(detail: AwardDetail) -> str:
        return ",".join(sorted(set(detail.cpv_codes)))

    @staticmethod
    def _award_row_id(detail: AwardDetail) -> str:
        return f"{detail.publication_number}::{detail.winner_position}"

    def upsert_award(self, entry: OverviewEntry, detail: AwardDetail) -> SaveOutcome:
        award_row_id = self._award_row_id(detail)
        existing = self.get_award_by_row_id(award_row_id)
        if existing is None:
            with self._connection() as conn:
                now = self._now_iso()
                conn.execute(
                    """
                    INSERT INTO awards(
                        award_row_id, publication_number, winner_position,
                        related_notice_number, publication_date,
                        project_id, project_url, title, procurement_office, publication_type,
                        overview_publication_date, winner_name, winner_address, procurement_office_address,
                        award_amount_chf, vat_percent,
                        offers_count, procurement_type, cpv_codes, source_url, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        award_row_id,
                        detail.publication_number,
                        detail.winner_position,
                        detail.related_notice_number,
                        detail.publication_date,
                        entry.project_id,
                        entry.project_url,
                        entry.title,
                        entry.procurement_office,
                        entry.publication_type,
                        entry.publication_date,
                        detail.winner_name,
                        detail.winner_address,
                        detail.procurement_office_address,
                        detail.award_amount_chf,
                        detail.vat_percent,
                        detail.offers_count,
                        detail.procurement_type,
                        self._cpv_csv(detail),
                        detail.source_url,
                        now,
                        now,
                    ),
                )
            return SaveOutcome.INSERTED

        new_payload = {
            "publication_number": detail.publication_number,
            "winner_position": detail.winner_position,
            "related_notice_number": detail.related_notice_number,
            "publication_date": detail.publication_date,
            "project_id": entry.project_id,
            "project_url": entry.project_url,
            "title": entry.title,
            "procurement_office": entry.procurement_office,
            "publication_type": entry.publication_type,
            "overview_publication_date": entry.publication_date,
            "winner_name": detail.winner_name,
            "winner_address": detail.winner_address,
            "procurement_office_address": detail.procurement_office_address,
            "award_amount_chf": detail.award_amount_chf,
            "vat_percent": detail.vat_percent,
            "offers_count": detail.offers_count,
            "procurement_type": detail.procurement_type,
            "cpv_codes": self._cpv_csv(detail),
            "source_url": detail.source_url,
        }

        unchanged = all(existing[key] == value for key, value in new_payload.items())
        if unchanged:
            return SaveOutcome.UNCHANGED

        with self._connection() as conn:
            conn.execute(
                """
                UPDATE awards
                SET publication_number = ?,
                    winner_position = ?,
                    related_notice_number = ?,
                    publication_date = ?,
                    project_id = ?,
                    project_url = ?,
                    title = ?,
                    procurement_office = ?,
                    publication_type = ?,
                    overview_publication_date = ?,
                    winner_name = ?,
                    winner_address = ?,
                    procurement_office_address = ?,
                    award_amount_chf = ?,
                    vat_percent = ?,
                    offers_count = ?,
                    procurement_type = ?,
                    cpv_codes = ?,
                    source_url = ?,
                    updated_at = ?
                WHERE award_row_id = ?
                """,
                (
                    new_payload["publication_number"],
                    new_payload["winner_position"],
                    new_payload["related_notice_number"],
                    new_payload["publication_date"],
                    new_payload["project_id"],
                    new_payload["project_url"],
                    new_payload["title"],
                    new_payload["procurement_office"],
                    new_payload["publication_type"],
                    new_payload["overview_publication_date"],
                    new_payload["winner_name"],
                    new_payload["winner_address"],
                    new_payload["procurement_office_address"],
                    new_payload["award_amount_chf"],
                    new_payload["vat_percent"],
                    new_payload["offers_count"],
                    new_payload["procurement_type"],
                    new_payload["cpv_codes"],
                    new_payload["source_url"],
                    self._now_iso(),
                    award_row_id,
                ),
            )
        return SaveOutcome.UPDATED

    def count_awards(self) -> int:
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM awards").fetchone()
            return int(row["c"])

    def has_project_url(self, project_url: str) -> bool:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM awards WHERE project_url = ? LIMIT 1",
                (project_url,),
            ).fetchone()
            return row is not None

    def get_award_by_row_id(self, award_row_id: str) -> Optional[dict[str, object]]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM awards WHERE award_row_id = ?",
                (award_row_id,),
            ).fetchone()
            if row is None:
                return None
            return {key: row[key] for key in row.keys()}

    def get_award(self, publication_number: str) -> Optional[dict[str, object]]:
        awards = self.get_awards_by_publication_number(publication_number)
        if not awards:
            return None
        return awards[0]

    def get_awards_by_publication_number(self, publication_number: str) -> list[dict[str, object]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM awards WHERE publication_number = ? ORDER BY winner_position ASC",
                (publication_number,),
            ).fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]

    def list_awards(self) -> list[dict[str, object]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM awards
                ORDER BY
                    substr(overview_publication_date, 7, 4) DESC,
                    substr(overview_publication_date, 4, 2) DESC,
                    substr(overview_publication_date, 1, 2) DESC,
                    publication_number DESC,
                    winner_position ASC
                """
            ).fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]

    def latest_sync_run(self) -> Optional[SyncRunRecord]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, status, overview_count, new_count, updated_count, error_count
                FROM sync_runs
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            return SyncRunRecord(
                id=int(row["id"]),
                status=str(row["status"]),
                overview_count=int(row["overview_count"]),
                new_count=int(row["new_count"]),
                updated_count=int(row["updated_count"]),
                error_count=int(row["error_count"]),
            )
