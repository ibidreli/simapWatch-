"""Build analysis rows and DataFrames from SQLite awards."""

from __future__ import annotations

import csv
import importlib
from collections import Counter
from pathlib import Path
from typing import Optional

from simapwatch.repository import SqliteAwardRepository


ANALYSIS_COLUMNS = [
    "award_row_id",
    "publication_number",
    "winner_position",
    "publication_date",
    "overview_publication_date",
    "publication_year",
    "publication_month",
    "publication_type",
    "related_notice_number",
    "project_id",
    "project_url",
    "source_url",
    "title",
    "procurement_type",
    "procurement_office",
    "procurement_office_address",
    "procurement_office_lat",
    "procurement_office_lon",
    "procurement_office_geocode_status",
    "procurement_office_street",
    "procurement_office_postal_code",
    "procurement_office_city",
    "procurement_office_region",
    "winner_name",
    "winner_address",
    "winner_lat",
    "winner_lon",
    "winner_geocode_status",
    "winner_street",
    "winner_postal_code",
    "winner_city",
    "winner_region",
    "award_amount_chf",
    "vat_percent",
    "offers_count",
    "cpv_codes",
    "cpv_primary",
    "cpv_count",
    "is_multi_award",
    "has_winner_address",
    "has_procurement_office_address",
    "has_award_amount",
    "has_vat_percent",
    "created_at",
    "updated_at",
]


def _split_address(address: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not address:
        return None, None, None, None

    parts = [part.strip() for part in address.split(",") if part.strip()]
    street = parts[0] if parts else None
    postal_code = None
    city = None
    region = None

    if len(parts) >= 2:
        locality_tokens = parts[1].split()
        if locality_tokens and locality_tokens[0].isdigit():
            postal_code = locality_tokens[0]
            city = " ".join(locality_tokens[1:]) or None
        else:
            city = parts[1] or None
    if len(parts) >= 3:
        region = ", ".join(parts[2:])

    return street, postal_code, city, region


def _extract_year_month(date_value: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    if not date_value or len(date_value) != 10:
        return None, None
    try:
        day, month, year = date_value.split(".")
        return int(year), int(month)
    except ValueError:
        return None, None


def _cpv_primary(cpv_codes: str) -> Optional[str]:
    codes = [code.strip() for code in cpv_codes.split(",") if code.strip()]
    return codes[0] if codes else None


def _cpv_count(cpv_codes: str) -> int:
    return len([code.strip() for code in cpv_codes.split(",") if code.strip()])


def load_analysis_rows(db_path: str | Path) -> list[dict[str, object]]:
    repository = SqliteAwardRepository(db_path)
    repository.init_schema()
    awards = repository.list_awards()
    publication_counts = Counter(str(row["publication_number"]) for row in awards)

    rows: list[dict[str, object]] = []
    for award in awards:
        publication_date = award.get("publication_date") or award.get("overview_publication_date")
        publication_year, publication_month = _extract_year_month(str(publication_date) if publication_date else None)
        procurement_office_street, procurement_office_postal_code, procurement_office_city, procurement_office_region = _split_address(
            award.get("procurement_office_address") if isinstance(award.get("procurement_office_address"), str) else None
        )
        winner_street, winner_postal_code, winner_city, winner_region = _split_address(
            award.get("winner_address") if isinstance(award.get("winner_address"), str) else None
        )
        cpv_codes = str(award.get("cpv_codes") or "")

        row = {
            "award_row_id": award.get("award_row_id"),
            "publication_number": award.get("publication_number"),
            "winner_position": award.get("winner_position"),
            "publication_date": award.get("publication_date"),
            "overview_publication_date": award.get("overview_publication_date"),
            "publication_year": publication_year,
            "publication_month": publication_month,
            "publication_type": award.get("publication_type"),
            "related_notice_number": award.get("related_notice_number"),
            "project_id": award.get("project_id"),
            "project_url": award.get("project_url"),
            "source_url": award.get("source_url"),
            "title": award.get("title"),
            "procurement_type": award.get("procurement_type"),
            "procurement_office": award.get("procurement_office"),
            "procurement_office_address": award.get("procurement_office_address"),
            "procurement_office_lat": award.get("procurement_office_lat"),
            "procurement_office_lon": award.get("procurement_office_lon"),
            "procurement_office_geocode_status": award.get("procurement_office_geocode_status"),
            "procurement_office_street": procurement_office_street,
            "procurement_office_postal_code": procurement_office_postal_code,
            "procurement_office_city": procurement_office_city,
            "procurement_office_region": procurement_office_region,
            "winner_name": award.get("winner_name"),
            "winner_address": award.get("winner_address"),
            "winner_lat": award.get("winner_lat"),
            "winner_lon": award.get("winner_lon"),
            "winner_geocode_status": award.get("winner_geocode_status"),
            "winner_street": winner_street,
            "winner_postal_code": winner_postal_code,
            "winner_city": winner_city,
            "winner_region": winner_region,
            "award_amount_chf": award.get("award_amount_chf"),
            "vat_percent": award.get("vat_percent"),
            "offers_count": award.get("offers_count"),
            "cpv_codes": cpv_codes,
            "cpv_primary": _cpv_primary(cpv_codes),
            "cpv_count": _cpv_count(cpv_codes),
            "is_multi_award": publication_counts[str(award.get("publication_number"))] > 1,
            "has_winner_address": bool(award.get("winner_address")),
            "has_procurement_office_address": bool(award.get("procurement_office_address")),
            "has_award_amount": award.get("award_amount_chf") is not None,
            "has_vat_percent": award.get("vat_percent") is not None,
            "created_at": award.get("created_at"),
            "updated_at": award.get("updated_at"),
        }
        rows.append(row)

    return rows


def load_analysis_dataframe(db_path: str | Path):
    try:
        pandas = importlib.import_module("pandas")
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "pandas is required for DataFrame export. Install it with `pip install -r requirements.txt`."
        ) from error

    rows = load_analysis_rows(db_path)
    return pandas.DataFrame(rows, columns=ANALYSIS_COLUMNS)


def export_analysis_csv(db_path: str | Path, csv_path: str | Path) -> int:
    rows = load_analysis_rows(db_path)
    target = Path(csv_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANALYSIS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
