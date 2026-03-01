"""Domain contracts for parsed SIMAP award data."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class OverviewEntry:
    """Represents one card entry from the award_tender overview page."""

    project_id: str
    project_url: str
    title: str
    procurement_office: str
    publication_type: str
    publication_date: str


@dataclass(frozen=True)
class AwardDetail:
    """Represents extracted fields from one award detail page."""

    publication_number: str
    publication_date: Optional[str]
    related_notice_number: Optional[str]
    winner_name: Optional[str]
    award_amount_chf: Optional[float]
    vat_percent: Optional[float]
    offers_count: Optional[int]
    winner_position: int = 1
    winner_address: Optional[str] = None
    procurement_office_address: Optional[str] = None
    cpv_codes: list[str] = field(default_factory=list)
    procurement_type: Optional[str] = None
    source_url: Optional[str] = None
