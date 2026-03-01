"""Overview parser for SIMAP award list pages."""

from __future__ import annotations

import json
import re

from simapwatch.domain.contracts import OverviewEntry


_ENTRY_PATTERN = re.compile(
    r'<article[^>]*\sid="(?P<project_id>[^"]+)"[^>]*>.*?'
    r'aria-label="Projekttitel: (?P<title>[^"]+)".*?'
    r'aria-label="Beschaffungsstelle: (?P<procurement_office>[^"]+)".*?'
    r'aria-label="Publikationstyp: (?P<publication_type>[^"]+)".*?'
    r'aria-label="Publikationsdatum: (?P<publication_date>[^"]+)".*?'
    r'href="(?P<project_url>/de/project-detail/[^"]+)"',
    re.DOTALL,
)


def _pick_locale_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("de", "en", "fr", "it"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return ""


def _normalize_date(date_value: str) -> str:
    raw = date_value.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        year, month, day = raw.split("-")
        return f"{day}.{month}.{year}"
    return raw


def _map_publication_type(pub_type: str) -> str:
    mapping = {
        "award": "Zuschlag",
        "award_tender": "Zuschlag",
        "tender": "Ausschreibung",
    }
    return mapping.get(pub_type, pub_type)


def _to_absolute_url(url: str, base_url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{base_url.rstrip('/')}{url}"
    return f"{base_url.rstrip('/')}/{url}"


def _parse_json_overview(raw: str, base_url: str) -> list[OverviewEntry]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, dict):
        return []
    projects = payload.get("projects")
    if not isinstance(projects, list):
        return []

    entries: list[OverviewEntry] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_id = str(project.get("id") or "").strip()
        publication_id = str(project.get("publicationId") or "").strip()
        if not project_id or not publication_id:
            continue

        title = _pick_locale_value(project.get("title")) or "(ohne Titel)"
        procurement_office = _pick_locale_value(project.get("procOfficeName")) or "(ohne Beschaffungsstelle)"
        publication_type = _map_publication_type(str(project.get("pubType") or "").strip())
        publication_date = _normalize_date(str(project.get("publicationDate") or "").strip())
        detail_api_url = (
            f"{base_url.rstrip('/')}/api/publications/v1/project/"
            f"{project_id}/publication-details/{publication_id}?lang=de"
        )

        entries.append(
            OverviewEntry(
                project_id=project_id,
                project_url=detail_api_url,
                title=title,
                procurement_office=procurement_office,
                publication_type=publication_type,
                publication_date=publication_date,
            )
        )

    return entries


def extract_overview_pagination_last_item(raw: str) -> str | None:
    """Read pagination cursor (`lastItem`) from overview JSON payload."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    pagination = payload.get("pagination")
    if not isinstance(pagination, dict):
        return None
    last_item = pagination.get("lastItem")
    if not isinstance(last_item, str):
        return None
    stripped = last_item.strip()
    return stripped or None


def parse_overview(html: str, base_url: str = "https://www.simap.ch") -> list[OverviewEntry]:
    """Parse overview HTML into structured entries."""
    json_entries = _parse_json_overview(html, base_url=base_url)
    if json_entries:
        return json_entries

    entries: list[OverviewEntry] = []

    for match in _ENTRY_PATTERN.finditer(html):
        entries.append(
            OverviewEntry(
                project_id=match.group("project_id").strip(),
                project_url=_to_absolute_url(match.group("project_url").strip(), base_url),
                title=match.group("title").strip(),
                procurement_office=match.group("procurement_office").strip(),
                publication_type=match.group("publication_type").strip(),
                publication_date=match.group("publication_date").strip(),
            )
        )

    return entries
