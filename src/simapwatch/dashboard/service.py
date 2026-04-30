"""Aggregate analysis rows for the dashboard."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Optional

from simapwatch.analysis import load_analysis_rows


def _parse_date(value: object) -> Optional[date]:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def _month_key(value: Optional[date]) -> Optional[str]:
    if value is None:
        return None
    return value.strftime("%Y-%m")


def _round_amount(value: object) -> float:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return 0.0


def _build_month_range(today: date) -> list[str]:
    months: list[str] = []
    year = today.year
    month = today.month - 1
    if month == 0:
        month = 12
        year -= 1
    for _ in range(12):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()
    return months


def build_dashboard_payload(db_path: str | Path, today: Optional[date] = None) -> dict[str, object]:
    current_day = today or date.today()
    rows = load_analysis_rows(db_path)

    total_volume = sum(_round_amount(row.get("award_amount_chf")) for row in rows)
    winner_names = {str(row.get("winner_name")).strip() for row in rows if row.get("winner_name")}
    buyer_names = {str(row.get("procurement_office")).strip() for row in rows if row.get("procurement_office")}
    recent_cutoff = current_day - timedelta(days=30)
    recent_rows = []
    monthly_counts: dict[str, int] = defaultdict(int)
    monthly_volume: dict[str, float] = defaultdict(float)
    top_winner_volume: dict[str, float] = defaultdict(float)
    top_buyer_volume: dict[str, float] = defaultdict(float)
    cpv_counts: dict[str, int] = defaultdict(int)

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _parse_date(row.get("publication_date")) or date.min,
            str(row.get("publication_number") or ""),
            int(row.get("winner_position") or 0),
        ),
        reverse=True,
    )

    for row in sorted_rows:
        published_at = _parse_date(row.get("publication_date")) or _parse_date(row.get("overview_publication_date"))
        if published_at and published_at >= recent_cutoff:
            recent_rows.append(row)

        month = _month_key(published_at)
        if month:
            monthly_counts[month] += 1
            monthly_volume[month] += _round_amount(row.get("award_amount_chf"))

        winner_name = str(row.get("winner_name") or "").strip()
        if winner_name:
            top_winner_volume[winner_name] += _round_amount(row.get("award_amount_chf"))

        buyer_name = str(row.get("procurement_office") or "").strip()
        if buyer_name:
            top_buyer_volume[buyer_name] += _round_amount(row.get("award_amount_chf"))

        cpv_primary = str(row.get("cpv_primary") or "").strip()
        if cpv_primary:
            cpv_counts[cpv_primary] += 1

    monthly_series = []
    for month in _build_month_range(current_day):
        monthly_series.append(
            {
                "month": month,
                "award_count": monthly_counts.get(month, 0),
                "total_volume_chf": round(monthly_volume.get(month, 0.0), 2),
            }
        )

    top_winners = [
        {"winner_name": name, "total_volume_chf": round(amount, 2)}
        for name, amount in sorted(top_winner_volume.items(), key=lambda item: item[1], reverse=True)[:8]
    ]
    top_buyers = [
        {"procurement_office": name, "total_volume_chf": round(amount, 2)}
        for name, amount in sorted(top_buyer_volume.items(), key=lambda item: item[1], reverse=True)[:8]
    ]
    cpv_breakdown = [
        {"cpv_primary": code, "award_count": count}
        for code, count in sorted(cpv_counts.items(), key=lambda item: item[1], reverse=True)[:8]
    ]
    recent_awards = [
        {
            "publication_number": row.get("publication_number"),
            "publication_date": row.get("publication_date"),
            "title": row.get("title"),
            "winner_name": row.get("winner_name"),
            "procurement_office": row.get("procurement_office"),
            "award_amount_chf": _round_amount(row.get("award_amount_chf")),
            "project_url": row.get("project_url"),
        }
        for row in sorted_rows[:12]
    ]
    map_flows = []
    for row in sorted_rows:
        from_lat = row.get("procurement_office_lat")
        from_lon = row.get("procurement_office_lon")
        to_lat = row.get("winner_lat")
        to_lon = row.get("winner_lon")
        if not all(isinstance(value, (int, float)) for value in [from_lat, from_lon, to_lat, to_lon]):
            continue
        map_flows.append(
            {
                "award_row_id": row.get("award_row_id"),
                "publication_number": row.get("publication_number"),
                "title": row.get("title"),
                "procurement_office": row.get("procurement_office"),
                "winner_name": row.get("winner_name"),
                "award_amount_chf": _round_amount(row.get("award_amount_chf")),
                "from": {"lat": float(from_lat), "lon": float(from_lon)},
                "to": {"lat": float(to_lat), "lon": float(to_lon)},
            }
        )

    return {
        "summary": {
            "award_count": len(rows),
            "winner_count": len(winner_names),
            "buyer_count": len(buyer_names),
            "recent_30d_count": len(recent_rows),
            "total_volume_chf": round(total_volume, 2),
        },
        "monthly_series": monthly_series,
        "top_winners": top_winners,
        "top_buyers": top_buyers,
        "cpv_breakdown": cpv_breakdown,
        "recent_awards": recent_awards,
        "map_flows": map_flows[:150],
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
