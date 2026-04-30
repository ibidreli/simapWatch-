"""Aggregate and filter analysis rows for the dashboard."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
import os
from pathlib import Path
import re
from statistics import median
from typing import Mapping, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from simapwatch.analysis import load_analysis_rows


@dataclass(frozen=True)
class DashboardFilters:
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    buyer: Optional[str] = None
    winner: Optional[str] = None
    cpv: Optional[str] = None
    procurement_type: Optional[str] = None
    text: Optional[str] = None
    min_amount_chf: Optional[float] = None
    max_amount_chf: Optional[float] = None


_CPV_DIVISION_LABELS_DE: dict[str, str] = {
    "03": "Landwirtschaft, Forst, Fischerei und verwandte Erzeugnisse",
    "09": "Mineralöl, Brennstoff, Strom und andere Energiequellen",
    "14": "Bergbau, Basismetalle und verwandte Erzeugnisse",
    "15": "Nahrungsmittel, Getränke, Tabak und verwandte Erzeugnisse",
    "16": "Landwirtschaftsmaschinen",
    "18": "Kleidung, Schuhe, Gepäck und Zubehör",
    "19": "Leder-, Textil-, Kunststoff- und Gummierzeugnisse",
    "22": "Drucksachen und verwandte Erzeugnisse",
    "24": "Chemische Erzeugnisse",
    "30": "Büro- und Computerausrüstung (ohne Möbel und Software)",
    "31": "Elektrische Maschinen, Geräte und Verbrauchsartikel",
    "32": "Rundfunk-, TV-, Kommunikations- und Fernmeldeanlagen",
    "33": "Medizinische Ausrüstung, Pharma und Körperpflegeprodukte",
    "34": "Transportmittel und Verkehrszubehör",
    "35": "Sicherheits-, Feuerwehr-, Polizei- und Verteidigungsausrüstung",
    "37": "Musik, Sport, Spiele, Spielwaren und Kunstbedarf",
    "38": "Labor-, Optik- und Präzisionsgeräte",
    "39": "Möbel, Haushaltsgeräte und Reinigungsmittel",
    "41": "Rohwasser und aufbereitetes Wasser",
    "42": "Industrielle Maschinen",
    "43": "Bergbau-, Bau- und Steinbruchmaschinen",
    "44": "Baukonstruktionen, Baustoffe und Bauhilfsprodukte",
    "45": "Bauarbeiten",
    "48": "Softwarepakete und Informationssysteme",
    "50": "Reparatur- und Wartungsdienste",
    "51": "Installationsdienste (ohne Software)",
    "55": "Hotel-, Gastronomie- und Einzelhandelsdienste",
    "60": "Transport- und Beförderungsdienste (ohne Abfalltransport)",
    "63": "Hilfsdienste Verkehr und Reisebürodienste",
    "64": "Post- und Fernmeldedienste",
    "65": "Versorgungsunternehmen",
    "66": "Finanz- und Versicherungsdienstleistungen",
    "70": "Immobiliendienste",
    "71": "Architektur-, Ingenieur- und Prüfdienste",
    "72": "IT-Dienste: Beratung, Software, Internet und Support",
    "73": "Forschung, Entwicklung und zugehörige Beratung",
    "75": "Öffentliche Verwaltung, Verteidigung und Sozialversicherung",
    "76": "Dienstleistungen rund um Öl- und Gasgewinnung",
    "77": "Dienstleistungen für Landwirtschaft, Forst und Gartenbau",
    "79": "Unternehmensdienste: Recht, Marketing, Beratung, Druck, Sicherheit",
    "80": "Bildungs- und Ausbildungsdienstleistungen",
    "85": "Gesundheits- und Sozialdienste",
    "90": "Abwasser, Abfall, Reinigung und Umweltdienste",
    "92": "Erholung, Kultur und Sport",
    "98": "Sonstige gemeinschaftliche, soziale und persönliche Dienste",
}
_CPV_CODE_TOKEN_RE = re.compile(r"^\d{8}-\d$")
_CPV_LABEL_CACHE: dict[str, str] = {}
_CPV_FETCHED_DIVISIONS: set[str] = set()
_CPV_REMOTE_LOOKUP_ENABLED = os.environ.get("SIMAPWATCH_CPV_REMOTE_LOOKUP", "0") == "1"
_SWISS_CANTONS = {
    "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU", "LU", "NE", "NW",
    "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR", "VD", "VS", "ZG", "ZH",
}
_CANTON_POPULATION = {
    "AG": 706_000,
    "AI": 16_500,
    "AR": 55_300,
    "BE": 1_059_000,
    "BL": 296_000,
    "BS": 201_000,
    "FR": 343_600,
    "GE": 517_000,
    "GL": 41_300,
    "GR": 206_000,
    "JU": 74_100,
    "LU": 424_000,
    "NE": 177_000,
    "NW": 43_600,
    "OW": 38_800,
    "SG": 520_000,
    "SH": 84_900,
    "SO": 281_700,
    "SZ": 167_000,
    "TG": 291_000,
    "TI": 354_000,
    "UR": 37_200,
    "VD": 838_000,
    "VS": 357_000,
    "ZG": 132_600,
    "ZH": 1_619_000,
}
_AMOUNT_BUCKET_ORDER = [
    "<100k",
    "100k-500k",
    "500k-1m",
    "1m-5m",
    "5m-20m",
    ">20m",
    "unknown",
]
_OFFERS_BUCKET_ORDER = ["1", "2", "3-5", "6-10", "11+", "unknown"]


class _HtmlTextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        token = data.strip()
        if token:
            self.tokens.append(token)


def _normalize_cpv_code(value: object) -> str:
    raw = str(value or "")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 8:
        return digits[:8]
    return digits


def _collect_cpv_labels_from_html(html_text: str) -> dict[str, str]:
    parser = _HtmlTextCollector()
    parser.feed(html_text)
    parser.close()

    mapping: dict[str, str] = {}
    tokens = parser.tokens
    for index, token in enumerate(tokens[:-1]):
        if not _CPV_CODE_TOKEN_RE.match(token):
            continue
        label = tokens[index + 1].strip()
        if not label or _CPV_CODE_TOKEN_RE.match(label):
            continue
        mapping[token[:8]] = label
    return mapping


def _fetch_cpv_labels_for_division(division: str) -> None:
    if not _CPV_REMOTE_LOOKUP_ENABLED:
        return
    if division in _CPV_FETCHED_DIVISIONS:
        return
    _CPV_FETCHED_DIVISIONS.add(division)

    url = f"https://cpv.pm/divisions/{division}/?hl=de"
    request = Request(url, headers={"User-Agent": "simapWatch/1.0"})
    try:
        with urlopen(request, timeout=2.0) as response:
            html_text = response.read().decode("utf-8", errors="ignore")
    except (OSError, TimeoutError, URLError):
        return

    _CPV_LABEL_CACHE.update(_collect_cpv_labels_from_html(html_text))


def _resolve_cpv_label(code: object) -> Optional[str]:
    normalized = _normalize_cpv_code(code)
    if len(normalized) < 2:
        return None

    if normalized in _CPV_LABEL_CACHE:
        return _CPV_LABEL_CACHE[normalized]

    division = normalized[:2]
    _fetch_cpv_labels_for_division(division)

    if normalized in _CPV_LABEL_CACHE:
        return _CPV_LABEL_CACHE[normalized]
    return _CPV_DIVISION_LABELS_DE.get(division)


def _cpv_display(code: object) -> str:
    normalized = _normalize_cpv_code(code)
    if not normalized:
        return "-"
    label = _resolve_cpv_label(normalized)
    if label:
        return f"{normalized} - {label}"
    return normalized


def _extract_canton_from_text(value: object) -> Optional[str]:
    if value is None:
        return None
    tokens = re.findall(r"[A-Z]{2}", str(value).upper())
    for token in reversed(tokens):
        if token in _SWISS_CANTONS:
            return token
    return None


def _row_canton(row: Mapping[str, object], prefix: str) -> Optional[str]:
    region = _extract_canton_from_text(row.get(f"{prefix}_region"))
    if region:
        return region
    return _extract_canton_from_text(row.get(f"{prefix}_address"))


def _pct(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def _amount_bucket(amount: float) -> str:
    if amount <= 0:
        return "unknown"
    if amount < 100_000:
        return "<100k"
    if amount < 500_000:
        return "100k-500k"
    if amount < 1_000_000:
        return "500k-1m"
    if amount < 5_000_000:
        return "1m-5m"
    if amount < 20_000_000:
        return "5m-20m"
    return ">20m"


def _offers_bucket(offers_count: object) -> str:
    value = _safe_int(offers_count)
    if value <= 0:
        return "unknown"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    if value <= 5:
        return "3-5"
    if value <= 10:
        return "6-10"
    return "11+"


def _parse_date(value: object) -> Optional[date]:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def _parse_iso_date(value: object) -> Optional[date]:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _to_optional_text(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_optional_float(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip().replace("'", "").replace("_", "")
        if not text:
            return None
        return float(text)
    except ValueError:
        return None


def _coerce_filters(filters: DashboardFilters | Mapping[str, object] | None) -> DashboardFilters:
    if isinstance(filters, DashboardFilters):
        return filters
    if filters is None:
        return DashboardFilters()

    date_from = filters.get("from")
    if isinstance(date_from, date):
        parsed_from = date_from
    else:
        parsed_from = _parse_iso_date(date_from) or _parse_date(date_from)

    date_to = filters.get("to")
    if isinstance(date_to, date):
        parsed_to = date_to
    else:
        parsed_to = _parse_iso_date(date_to) or _parse_date(date_to)

    return DashboardFilters(
        date_from=parsed_from,
        date_to=parsed_to,
        buyer=_to_optional_text(filters.get("buyer")),
        winner=_to_optional_text(filters.get("winner")),
        cpv=_to_optional_text(filters.get("cpv")),
        procurement_type=_to_optional_text(filters.get("procurement_type")),
        text=_to_optional_text(filters.get("text")),
        min_amount_chf=_to_optional_float(filters.get("min_amount")),
        max_amount_chf=_to_optional_float(filters.get("max_amount")),
    )


def _month_key(value: Optional[date]) -> Optional[str]:
    if value is None:
        return None
    return value.strftime("%Y-%m")


def _round_amount(value: object) -> float:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return 0.0


def _build_month_range(today: date, months: int) -> list[str]:
    if months <= 0:
        return []

    result: list[str] = []
    year = today.year
    month = today.month - 1
    if month == 0:
        month = 12
        year -= 1

    for _ in range(months):
        result.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    result.reverse()
    return result


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _trend_bucket_for_range(day_count: int) -> str:
    if day_count <= 45:
        return "day"
    if day_count <= 180:
        return "week"
    return "month"


def _trend_key(value: date, bucket: str) -> str:
    if bucket == "day":
        return value.isoformat()
    if bucket == "week":
        return _week_start(value).isoformat()
    return value.strftime("%Y-%m")


def _trend_label(period_key: str, bucket: str) -> str:
    if bucket == "day":
        d = date.fromisoformat(period_key)
        return d.strftime("%d.%m")
    if bucket == "week":
        d = date.fromisoformat(period_key)
        end = d + timedelta(days=6)
        return f"{d.strftime('%d.%m')}-{end.strftime('%d.%m')}"
    return period_key[2:]


def _build_trend_range(date_from: date, date_to: date, bucket: str) -> list[str]:
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    if bucket == "day":
        keys: list[str] = []
        current = date_from
        while current <= date_to:
            keys.append(current.isoformat())
            current += timedelta(days=1)
        return keys

    if bucket == "week":
        keys = []
        current = _week_start(date_from)
        last = _week_start(date_to)
        while current <= last:
            keys.append(current.isoformat())
            current += timedelta(days=7)
        return keys

    keys = []
    current = _month_start(date_from)
    last = _month_start(date_to)
    while current <= last:
        keys.append(current.strftime("%Y-%m"))
        current = _next_month(current)
    return keys


def _published_at(row: Mapping[str, object]) -> Optional[date]:
    return _parse_date(row.get("publication_date")) or _parse_date(row.get("overview_publication_date"))


def _safe_int(value: object) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _contains_casefold(source: object, needle: str) -> bool:
    if not needle:
        return True
    return needle in str(source or "").casefold()


def _matches_filter(row: Mapping[str, object], filters: DashboardFilters) -> bool:
    published_at = _published_at(row)
    amount = _round_amount(row.get("award_amount_chf"))

    if filters.date_from and (published_at is None or published_at < filters.date_from):
        return False
    if filters.date_to and (published_at is None or published_at > filters.date_to):
        return False
    if filters.min_amount_chf is not None and amount < filters.min_amount_chf:
        return False
    if filters.max_amount_chf is not None and amount > filters.max_amount_chf:
        return False

    if filters.buyer and not _contains_casefold(row.get("procurement_office"), filters.buyer.casefold()):
        return False
    if filters.winner and not _contains_casefold(row.get("winner_name"), filters.winner.casefold()):
        return False

    cpv_primary = str(row.get("cpv_primary") or "").strip().casefold()
    if filters.cpv and not cpv_primary.startswith(filters.cpv.casefold()):
        return False

    procurement_type = str(row.get("procurement_type") or "").strip().casefold()
    if filters.procurement_type and filters.procurement_type.casefold() not in procurement_type:
        return False

    if filters.text:
        text_needle = filters.text.casefold()
        haystack = " ".join(
            [
                str(row.get("title") or ""),
                str(row.get("publication_number") or ""),
                str(row.get("procurement_office") or ""),
                str(row.get("winner_name") or ""),
                str(row.get("cpv_primary") or ""),
            ]
        ).casefold()
        if text_needle not in haystack:
            return False

    return True


def _filter_rows(rows: list[dict[str, object]], filters: DashboardFilters) -> list[dict[str, object]]:
    return [row for row in rows if _matches_filter(row, filters)]


def _rank_counter(counter: Mapping[str, int], limit: int) -> list[dict[str, object]]:
    return [
        {"name": key, "count": value}
        for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold()))[:limit]
    ]


def build_dashboard_filter_options(db_path: str | Path, limit: int = 250) -> dict[str, object]:
    rows = load_analysis_rows(db_path)

    buyer_counter: Counter[str] = Counter()
    winner_counter: Counter[str] = Counter()
    cpv_counter: Counter[str] = Counter()
    procurement_type_counter: Counter[str] = Counter()
    publication_dates: list[date] = []
    amounts: list[float] = []

    for row in rows:
        buyer_name = _to_optional_text(row.get("procurement_office"))
        if buyer_name:
            buyer_counter[buyer_name] += 1

        winner_name = _to_optional_text(row.get("winner_name"))
        if winner_name:
            winner_counter[winner_name] += 1

        cpv_primary = _to_optional_text(row.get("cpv_primary"))
        if cpv_primary:
            cpv_counter[cpv_primary] += 1

        procurement_type = _to_optional_text(row.get("procurement_type"))
        if procurement_type:
            procurement_type_counter[procurement_type] += 1

        published_at = _published_at(row)
        if published_at:
            publication_dates.append(published_at)

        amount = _round_amount(row.get("award_amount_chf"))
        if amount > 0:
            amounts.append(amount)

    min_date = min(publication_dates).isoformat() if publication_dates else None
    max_date = max(publication_dates).isoformat() if publication_dates else None

    cpv_ranked = _rank_counter(cpv_counter, limit)
    cpv_codes = [
        {
            "name": item["name"],
            "count": item["count"],
            "label": _resolve_cpv_label(item["name"]),
            "display": _cpv_display(item["name"]),
        }
        for item in cpv_ranked
    ]

    return {
        "buyers": _rank_counter(buyer_counter, limit),
        "winners": _rank_counter(winner_counter, limit),
        "cpv_codes": cpv_codes,
        "procurement_types": _rank_counter(procurement_type_counter, limit),
        "date_min": min_date,
        "date_max": max_date,
        "amount_min_chf": round(min(amounts), 2) if amounts else 0.0,
        "amount_max_chf": round(max(amounts), 2) if amounts else 0.0,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def build_dashboard_payload(
    db_path: str | Path,
    today: Optional[date] = None,
    filters: DashboardFilters | Mapping[str, object] | None = None,
    top_n: int = 8,
    recent_limit: int = 12,
    map_limit: int = 150,
    months: int = 12,
) -> dict[str, object]:
    current_day = today or date.today()
    parsed_filters = _coerce_filters(filters)
    rows_all = load_analysis_rows(db_path)
    rows = _filter_rows(rows_all, parsed_filters)

    total_volume = sum(_round_amount(row.get("award_amount_chf")) for row in rows)
    award_amounts = [
        _round_amount(row.get("award_amount_chf")) for row in rows if _round_amount(row.get("award_amount_chf")) > 0
    ]
    offer_counts = [_safe_int(row.get("offers_count")) for row in rows if _safe_int(row.get("offers_count")) > 0]
    winner_names = {str(row.get("winner_name")).strip() for row in rows if row.get("winner_name")}
    buyer_names = {str(row.get("procurement_office")).strip() for row in rows if row.get("procurement_office")}

    recent_cutoff = current_day - timedelta(days=30)
    recent_rows: list[dict[str, object]] = []

    trend_counts: dict[str, int] = defaultdict(int)
    trend_volume: dict[str, float] = defaultdict(float)
    top_winner_volume: dict[str, float] = defaultdict(float)
    top_buyer_volume: dict[str, float] = defaultdict(float)
    winner_award_counts: dict[str, int] = defaultdict(int)
    buyer_award_counts: dict[str, int] = defaultdict(int)
    winner_offer_totals: dict[str, int] = defaultdict(int)
    winner_offer_known_counts: dict[str, int] = defaultdict(int)
    winner_primary_cpv_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    winner_canton_by_name: defaultdict[str, Counter[str]] = defaultdict(Counter)
    cpv_counts: dict[str, int] = defaultdict(int)
    cpv_category_counts: dict[str, int] = defaultdict(int)
    cpv_category_codes: defaultdict[str, set[str]] = defaultdict(set)
    procurement_type_counts: dict[str, int] = defaultdict(int)
    procurement_type_single_bid_counts: dict[str, int] = defaultdict(int)
    procurement_type_offer_totals: dict[str, int] = defaultdict(int)
    procurement_type_offer_known_counts: dict[str, int] = defaultdict(int)
    winner_canton_counts: dict[str, int] = defaultdict(int)
    winner_canton_volume: dict[str, float] = defaultdict(float)
    buyer_canton_counts: dict[str, int] = defaultdict(int)
    buyer_canton_volume: dict[str, float] = defaultdict(float)
    canton_flow_counts: dict[tuple[str, str], int] = defaultdict(int)
    canton_flow_volume: dict[tuple[str, str], float] = defaultdict(float)
    amount_bucket_counts: dict[str, int] = defaultdict(int)
    amount_bucket_volume: dict[str, float] = defaultdict(float)
    offers_bucket_counts: dict[str, int] = defaultdict(int)
    offers_bucket_volume: dict[str, float] = defaultdict(float)
    period_known_canton_counts: dict[str, int] = defaultdict(int)
    period_inter_canton_counts: dict[str, int] = defaultdict(int)
    map_flow_aggregates: dict[tuple[str, str], dict[str, float]] = {}
    known_canton_awards = 0
    known_canton_volume = 0.0
    inter_canton_awards = 0
    inter_canton_volume = 0.0

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            _published_at(row) or date.min,
            str(row.get("publication_number") or ""),
            _safe_int(row.get("winner_position")),
        ),
        reverse=True,
    )

    published_dates = [_published_at(row) for row in sorted_rows]
    known_dates = [published_at for published_at in published_dates if published_at is not None]
    data_min_date = min(known_dates) if known_dates else None
    data_max_date = max(known_dates) if known_dates else None

    has_explicit_date_filter = parsed_filters.date_from is not None or parsed_filters.date_to is not None
    if has_explicit_date_filter:
        trend_from = parsed_filters.date_from or data_min_date or current_day
        trend_to = parsed_filters.date_to or data_max_date or current_day
        if trend_from > trend_to:
            trend_from, trend_to = trend_to, trend_from
        trend_day_count = (trend_to - trend_from).days + 1
        time_bucket = _trend_bucket_for_range(trend_day_count)
        trend_keys = _build_trend_range(trend_from, trend_to, time_bucket)
    else:
        time_bucket = "month"
        trend_from = None
        trend_to = None
        trend_keys = _build_month_range(current_day, months=months)

    for row in sorted_rows:
        published_at = _published_at(row)
        amount = _round_amount(row.get("award_amount_chf"))
        offers_count = _safe_int(row.get("offers_count"))
        winner_canton = _row_canton(row, "winner") or "unknown"
        buyer_canton = _row_canton(row, "procurement_office") or "unknown"

        if published_at and published_at >= recent_cutoff:
            recent_rows.append(row)

        if published_at:
            period_key = _trend_key(published_at, time_bucket)
            trend_counts[period_key] += 1
            trend_volume[period_key] += amount

        winner_name = str(row.get("winner_name") or "").strip()
        if winner_name:
            top_winner_volume[winner_name] += amount
            winner_award_counts[winner_name] += 1
            if offers_count > 0:
                winner_offer_totals[winner_name] += offers_count
                winner_offer_known_counts[winner_name] += 1
            winner_canton_by_name[winner_name][winner_canton] += 1

        buyer_name = str(row.get("procurement_office") or "").strip()
        if buyer_name:
            top_buyer_volume[buyer_name] += amount
            buyer_award_counts[buyer_name] += 1

        cpv_primary = str(row.get("cpv_primary") or "").strip()
        if cpv_primary:
            cpv_counts[cpv_primary] += 1
            cpv_label = _resolve_cpv_label(cpv_primary) or cpv_primary
            cpv_category_counts[cpv_label] += 1
            cpv_category_codes[cpv_label].add(cpv_primary)
            if winner_name:
                winner_primary_cpv_counts[winner_name][cpv_primary] += 1

        procurement_type = str(row.get("procurement_type") or "").strip()
        if procurement_type:
            procurement_type_counts[procurement_type] += 1
            if offers_count > 0:
                procurement_type_offer_totals[procurement_type] += offers_count
                procurement_type_offer_known_counts[procurement_type] += 1
            if offers_count == 1:
                procurement_type_single_bid_counts[procurement_type] += 1

        winner_canton_counts[winner_canton] += 1
        winner_canton_volume[winner_canton] += amount
        buyer_canton_counts[buyer_canton] += 1
        buyer_canton_volume[buyer_canton] += amount

        if winner_canton != "unknown" and buyer_canton != "unknown":
            flow_key = (buyer_canton, winner_canton)
            canton_flow_counts[flow_key] += 1
            canton_flow_volume[flow_key] += amount
            known_canton_awards += 1
            known_canton_volume += amount
            if published_at:
                period_key = _trend_key(published_at, time_bucket)
                period_known_canton_counts[period_key] += 1
            if buyer_canton != winner_canton:
                inter_canton_awards += 1
                inter_canton_volume += amount
                if published_at:
                    period_inter_canton_counts[period_key] += 1

            from_lat = row.get("procurement_office_lat")
            from_lon = row.get("procurement_office_lon")
            to_lat = row.get("winner_lat")
            to_lon = row.get("winner_lon")
            if all(isinstance(value, (int, float)) for value in [from_lat, from_lon, to_lat, to_lon]):
                aggregate = map_flow_aggregates.setdefault(
                    flow_key,
                    {
                        "award_count": 0.0,
                        "total_volume_chf": 0.0,
                        "from_lat_sum": 0.0,
                        "from_lon_sum": 0.0,
                        "to_lat_sum": 0.0,
                        "to_lon_sum": 0.0,
                    },
                )
                aggregate["award_count"] += 1.0
                aggregate["total_volume_chf"] += amount
                aggregate["from_lat_sum"] += float(from_lat)
                aggregate["from_lon_sum"] += float(from_lon)
                aggregate["to_lat_sum"] += float(to_lat)
                aggregate["to_lon_sum"] += float(to_lon)

        amount_bucket = _amount_bucket(amount)
        amount_bucket_counts[amount_bucket] += 1
        amount_bucket_volume[amount_bucket] += amount

        offers_bucket = _offers_bucket(row.get("offers_count"))
        offers_bucket_counts[offers_bucket] += 1
        offers_bucket_volume[offers_bucket] += amount

    time_series = []
    for period_key in trend_keys:
        time_series.append(
            {
                "period_key": period_key,
                "month": period_key,
                "label": _trend_label(period_key, time_bucket),
                "award_count": trend_counts.get(period_key, 0),
                "total_volume_chf": round(trend_volume.get(period_key, 0.0), 2),
            }
        )
    monthly_series = list(time_series)

    sorted_winners = sorted(top_winner_volume.items(), key=lambda item: (-item[1], item[0].casefold()))
    top_winners = [
        {
            "winner_name": name,
            "total_volume_chf": round(amount, 2),
            "award_count": winner_award_counts.get(name, 0),
            "share_of_volume_pct": _pct(amount, total_volume),
        }
        for name, amount in sorted_winners[:top_n]
    ]
    sorted_buyers = sorted(top_buyer_volume.items(), key=lambda item: (-item[1], item[0].casefold()))
    top_buyers = [
        {
            "procurement_office": name,
            "total_volume_chf": round(amount, 2),
            "award_count": buyer_award_counts.get(name, 0),
            "share_of_volume_pct": _pct(amount, total_volume),
        }
        for name, amount in sorted_buyers[:top_n]
    ]
    cpv_breakdown = []
    for code, count in sorted(cpv_counts.items(), key=lambda item: item[1], reverse=True)[:top_n]:
        cpv_breakdown.append(
            {
                "cpv_primary": code,
                "cpv_label": _resolve_cpv_label(code),
                "cpv_display": _cpv_display(code),
                "award_count": count,
                "share_of_awards_pct": _pct(count, len(rows)),
            }
        )
    cpv_category_breakdown = []
    for category, count in sorted(cpv_category_counts.items(), key=lambda item: (-item[1], item[0].casefold()))[:top_n]:
        category_codes = sorted(cpv_category_codes.get(category, set()))
        cpv_category_breakdown.append(
            {
                "cpv_category": category,
                "award_count": count,
                "share_of_awards_pct": _pct(count, len(rows)),
                "code_count": len(category_codes),
                "codes": category_codes,
                "codes_preview": category_codes[:4],
            }
        )
    top_procurement_types = [
        {
            "procurement_type": name,
            "award_count": count,
            "share_of_awards_pct": _pct(count, len(rows)),
        }
        for name, count in sorted(procurement_type_counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
    ]
    competition_by_procurement_type = []
    for name, count in sorted(procurement_type_counts.items(), key=lambda item: (-item[1], item[0]))[: max(top_n, 12)]:
        known_offer_count = procurement_type_offer_known_counts.get(name, 0)
        single_bid_count = procurement_type_single_bid_counts.get(name, 0)
        competition_by_procurement_type.append(
            {
                "procurement_type": name,
                "award_count": count,
                "single_bid_count": single_bid_count,
                "single_bid_share_pct": _pct(single_bid_count, known_offer_count),
                "known_offers_award_count": known_offer_count,
                "average_offers_count": (
                    round(procurement_type_offer_totals.get(name, 0) / known_offer_count, 2) if known_offer_count else None
                ),
            }
        )

    winner_canton_breakdown = []
    for canton, count in sorted(winner_canton_counts.items(), key=lambda item: (-item[1], item[0]))[: max(top_n, 12)]:
        volume = winner_canton_volume.get(canton, 0.0)
        population = _CANTON_POPULATION.get(canton)
        awards_per_100k = round((count / population) * 100_000, 2) if population else None
        volume_per_100k = round((volume / population) * 100_000, 2) if population else None
        winner_canton_breakdown.append(
            {
                "canton": "Unbekannt" if canton == "unknown" else canton,
                "canton_code": canton,
                "population": population,
                "award_count": count,
                "total_volume_chf": round(volume, 2),
                "awards_per_100k": awards_per_100k,
                "volume_per_100k_chf": volume_per_100k,
                "average_award_chf": round(volume / count, 2) if count else 0.0,
                "share_of_awards_pct": _pct(count, len(rows)),
                "share_of_volume_pct": _pct(volume, total_volume),
            }
        )

    buyer_canton_breakdown = []
    for canton, count in sorted(buyer_canton_counts.items(), key=lambda item: (-item[1], item[0]))[: max(top_n, 12)]:
        volume = buyer_canton_volume.get(canton, 0.0)
        buyer_canton_breakdown.append(
            {
                "canton": "Unbekannt" if canton == "unknown" else canton,
                "canton_code": canton,
                "award_count": count,
                "total_volume_chf": round(volume, 2),
                "average_award_chf": round(volume / count, 2) if count else 0.0,
                "share_of_awards_pct": _pct(count, len(rows)),
                "share_of_volume_pct": _pct(volume, total_volume),
            }
        )

    canton_flow_total = sum(canton_flow_counts.values())
    canton_flow_breakdown = []
    for flow_key, count in sorted(canton_flow_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))[
        : max(top_n * 2, 16)
    ]:
        from_canton, to_canton = flow_key
        volume = canton_flow_volume.get(flow_key, 0.0)
        canton_flow_breakdown.append(
            {
                "from_canton": from_canton,
                "to_canton": to_canton,
                "flow_label": f"{from_canton} -> {to_canton}",
                "award_count": count,
                "total_volume_chf": round(volume, 2),
                "average_award_chf": round(volume / count, 2) if count else 0.0,
                "share_of_canton_awards_pct": _pct(count, canton_flow_total),
                "intra_canton": from_canton == to_canton,
            }
        )

    award_size_breakdown = [
        {
            "bucket": bucket,
            "award_count": amount_bucket_counts.get(bucket, 0),
            "total_volume_chf": round(amount_bucket_volume.get(bucket, 0.0), 2),
            "share_of_awards_pct": _pct(amount_bucket_counts.get(bucket, 0), len(rows)),
            "share_of_volume_pct": _pct(amount_bucket_volume.get(bucket, 0.0), total_volume),
        }
        for bucket in _AMOUNT_BUCKET_ORDER
    ]

    competition_breakdown = [
        {
            "offers_bucket": bucket,
            "award_count": offers_bucket_counts.get(bucket, 0),
            "total_volume_chf": round(offers_bucket_volume.get(bucket, 0.0), 2),
            "share_of_awards_pct": _pct(offers_bucket_counts.get(bucket, 0), len(rows)),
            "share_of_volume_pct": _pct(offers_bucket_volume.get(bucket, 0.0), total_volume),
        }
        for bucket in _OFFERS_BUCKET_ORDER
    ]
    inter_canton_trend = []
    for period_key in trend_keys:
        known_count = period_known_canton_counts.get(period_key, 0)
        inter_count = period_inter_canton_counts.get(period_key, 0)
        inter_canton_trend.append(
            {
                "period_key": period_key,
                "label": _trend_label(period_key, time_bucket),
                "known_canton_award_count": known_count,
                "inter_canton_award_count": inter_count,
                "inter_canton_share_pct": _pct(inter_count, known_count),
            }
        )

    winner_profiles = []
    for winner_name, winner_volume in sorted_winners[: max(top_n * 2, 16)]:
        award_count = winner_award_counts.get(winner_name, 0)
        winner_canton_counter = winner_canton_by_name.get(winner_name, Counter())
        winner_canton_ranked = [canton for canton, _ in winner_canton_counter.most_common() if canton != "unknown"]
        winner_canton = winner_canton_ranked[0] if winner_canton_ranked else "unknown"
        cpv_counter = winner_primary_cpv_counts.get(winner_name, Counter())
        primary_cpv = cpv_counter.most_common(1)[0][0] if cpv_counter else None
        offers_known_count = winner_offer_known_counts.get(winner_name, 0)
        winner_profiles.append(
            {
                "winner_name": winner_name,
                "winner_canton": "Unbekannt" if winner_canton == "unknown" else winner_canton,
                "award_count": award_count,
                "total_volume_chf": round(winner_volume, 2),
                "average_award_chf": round(winner_volume / award_count, 2) if award_count else 0.0,
                "average_offers_count": (
                    round(winner_offer_totals.get(winner_name, 0) / offers_known_count, 2) if offers_known_count else None
                ),
                "primary_cpv": primary_cpv,
                "primary_cpv_display": _cpv_display(primary_cpv) if primary_cpv else None,
                "share_of_volume_pct": _pct(winner_volume, total_volume),
            }
        )

    winner_volumes = [amount for _, amount in sorted_winners if amount > 0]
    concentration_curve = []
    cumulative_volume = 0.0
    for index, winner_volume in enumerate(winner_volumes[: max(top_n * 3, 24)], start=1):
        cumulative_volume += winner_volume
        concentration_curve.append(
            {
                "rank": index,
                "winner_volume_chf": round(winner_volume, 2),
                "cumulative_volume_share_pct": _pct(cumulative_volume, total_volume),
            }
        )

    winner_count_total = len(winner_volumes)
    top_1_volume = winner_volumes[0] if winner_volumes else 0.0
    top_3_volume = sum(winner_volumes[:3])
    top_10_volume = sum(winner_volumes[:10])
    hhi_winner_volume = 0.0
    if total_volume > 0:
        hhi_winner_volume = round(sum(((amount / total_volume) * 100.0) ** 2 for amount in winner_volumes), 2)
    known_offers_rows = sum(count for bucket, count in offers_bucket_counts.items() if bucket != "unknown")
    single_offer_count = offers_bucket_counts.get("1", 0)
    large_award_volume = amount_bucket_volume.get("5m-20m", 0.0) + amount_bucket_volume.get(">20m", 0.0)

    insights = [
        {
            "id": "top_1_share",
            "title": "Top-1 Gewinneranteil",
            "value": f"{_pct(top_1_volume, total_volume):.2f}%",
            "description": "Volumenanteil des größten Gewinners.",
        },
        {
            "id": "top_3_share",
            "title": "Top-3 Gewinneranteil",
            "value": f"{_pct(top_3_volume, total_volume):.2f}%",
            "description": "Konzentration auf die drei größten Gewinner.",
        },
        {
            "id": "top_10_share",
            "title": "Top-10 Gewinneranteil",
            "value": f"{_pct(top_10_volume, total_volume):.2f}%",
            "description": "Wie viel Volumen bei den Top-10 Gewinnern landet.",
        },
        {
            "id": "winner_hhi",
            "title": "HHI Gewinner",
            "value": f"{hhi_winner_volume:.2f}",
            "description": "Je höher, desto stärker konzentriert der Gewinner-Markt.",
        },
        {
            "id": "inter_canton_share",
            "title": "Interkantonale Flüsse",
            "value": f"{_pct(inter_canton_awards, known_canton_awards):.2f}%",
            "description": "Anteil Zuschläge mit anderem Winner-Kanton als Buyer-Kanton.",
        },
        {
            "id": "single_bid_share",
            "title": "Single-Bid Anteil",
            "value": f"{_pct(single_offer_count, known_offers_rows):.2f}%",
            "description": "Anteil Zuschläge mit nur einem Angebot.",
        },
        {
            "id": "large_award_volume_share",
            "title": "Großauftragsanteil",
            "value": f"{_pct(large_award_volume, total_volume):.2f}%",
            "description": "Volumenanteil Zuschläge >= 5 Mio. CHF.",
        },
        {
            "id": "median_offers",
            "title": "Median Angebote",
            "value": str(round(median(offer_counts), 1)) if offer_counts else "-",
            "description": "Median der Anzahl Angebote (ohne unbekannte Werte).",
        },
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
        for row in sorted_rows[:recent_limit]
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

    map_flows_aggregated = []
    for flow_key, aggregate in sorted(
        map_flow_aggregates.items(),
        key=lambda item: (-item[1]["total_volume_chf"], -item[1]["award_count"], item[0][0], item[0][1]),
    )[:map_limit]:
        from_canton, to_canton = flow_key
        award_count = int(aggregate["award_count"])
        total_volume_flow = aggregate["total_volume_chf"]
        map_flows_aggregated.append(
            {
                "from_canton": from_canton,
                "to_canton": to_canton,
                "flow_label": f"{from_canton} -> {to_canton}",
                "award_count": award_count,
                "total_volume_chf": round(total_volume_flow, 2),
                "average_award_chf": round(total_volume_flow / award_count, 2) if award_count else 0.0,
                "share_of_known_canton_volume_pct": _pct(total_volume_flow, known_canton_volume),
                "intra_canton": from_canton == to_canton,
                "from": {
                    "lat": round(aggregate["from_lat_sum"] / award_count, 6) if award_count else 0.0,
                    "lon": round(aggregate["from_lon_sum"] / award_count, 6) if award_count else 0.0,
                },
                "to": {
                    "lat": round(aggregate["to_lat_sum"] / award_count, 6) if award_count else 0.0,
                    "lon": round(aggregate["to_lon_sum"] / award_count, 6) if award_count else 0.0,
                },
            }
        )

    return {
        "summary": {
            "award_count": len(rows),
            "winner_count": len(winner_names),
            "buyer_count": len(buyer_names),
            "recent_30d_count": len(recent_rows),
            "total_volume_chf": round(total_volume, 2),
            "average_award_chf": round(total_volume / len(rows), 2) if rows else 0.0,
            "median_award_chf": round(median(award_amounts), 2) if award_amounts else 0.0,
        },
        "meta": {
            "source_award_count": len(rows_all),
            "filtered_award_count": len(rows),
            "filters": {
                "from": parsed_filters.date_from.isoformat() if parsed_filters.date_from else None,
                "to": parsed_filters.date_to.isoformat() if parsed_filters.date_to else None,
                "buyer": parsed_filters.buyer,
                "winner": parsed_filters.winner,
                "cpv": parsed_filters.cpv,
                "procurement_type": parsed_filters.procurement_type,
                "text": parsed_filters.text,
                "min_amount": parsed_filters.min_amount_chf,
                "max_amount": parsed_filters.max_amount_chf,
            },
            "time_bucket": time_bucket,
            "trend_from": trend_from.isoformat() if trend_from else None,
            "trend_to": trend_to.isoformat() if trend_to else None,
        },
        "time_series": time_series,
        "monthly_series": monthly_series,
        "top_winners": top_winners,
        "top_buyers": top_buyers,
        "top_procurement_types": top_procurement_types,
        "competition_by_procurement_type": competition_by_procurement_type,
        "cpv_breakdown": cpv_breakdown,
        "cpv_category_breakdown": cpv_category_breakdown,
        "winner_canton_breakdown": winner_canton_breakdown,
        "buyer_canton_breakdown": buyer_canton_breakdown,
        "canton_flow_breakdown": canton_flow_breakdown,
        "award_size_breakdown": award_size_breakdown,
        "competition_breakdown": competition_breakdown,
        "inter_canton_trend": inter_canton_trend,
        "winner_profiles": winner_profiles,
        "winner_concentration_curve": concentration_curve,
        "insights": insights,
        "coverage": {
            "known_canton_award_count": known_canton_awards,
            "known_canton_volume_chf": round(known_canton_volume, 2),
            "inter_canton_award_count": inter_canton_awards,
            "inter_canton_volume_chf": round(inter_canton_volume, 2),
            "known_offers_award_count": known_offers_rows,
        },
        "recent_awards": recent_awards,
        "map_flows": map_flows[:map_limit],
        "map_flows_aggregated": map_flows_aggregated[:map_limit],
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
