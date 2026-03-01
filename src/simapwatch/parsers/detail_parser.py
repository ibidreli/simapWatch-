"""Detail parser for SIMAP award detail pages."""

from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any, Optional

from simapwatch.domain.contracts import AwardDetail


def _search(pattern: str, text: str, flags: int = re.DOTALL) -> Optional[str]:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return match.group(1).strip()


def _parse_chf_amount(raw_value: Optional[str]) -> Optional[float]:
    if not raw_value:
        return None

    numeric = raw_value
    numeric = numeric.replace("CHF", "")
    numeric = numeric.replace("'", "")
    numeric = numeric.replace("\u2019", "")
    numeric = numeric.replace("’", "")
    numeric = numeric.replace(" ", "")
    numeric = numeric.strip()
    try:
        return float(numeric)
    except ValueError:
        return None


def _parse_int(raw_value: Optional[str]) -> Optional[int]:
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _parse_vat(raw_value: Optional[str]) -> Optional[float]:
    if not raw_value:
        return None
    normalized = raw_value.replace(",", ".").strip()
    try:
        return float(normalized)
    except ValueError:
        return None


def _normalize_date(date_value: Optional[str]) -> Optional[str]:
    if not date_value:
        return None
    raw = date_value.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        year, month, day = raw.split("-")
        return f"{day}.{month}.{year}"
    return raw


def _order_type_to_procurement_type(order_type: Optional[str]) -> Optional[str]:
    if not order_type:
        return None
    mapping = {
        "construction": "Bauleistung",
        "supply": "Lieferung",
        "service": "Dienstleistung",
    }
    return mapping.get(order_type, order_type)


def _pick_locale_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("de", "en", "fr", "it"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return ""


def _format_address(address: object) -> Optional[str]:
    if not isinstance(address, dict):
        return None

    street = _pick_locale_value(address.get("street"))
    postal_code = str(address.get("postalCode") or "").strip()
    city = _pick_locale_value(address.get("city"))
    canton_id = str(address.get("cantonId") or "").strip()
    country_id = str(address.get("countryId") or "").strip()

    line1 = ", ".join(part for part in [street] if part)
    locality = " ".join(part for part in [postal_code, city] if part)
    region = ", ".join(part for part in [canton_id, country_id] if part)
    full = ", ".join(part for part in [line1, locality, region] if part)
    return full or None


def _build_award_detail(
    *,
    publication_number: str,
    publication_date: Optional[str],
    related_notice_number: Optional[str],
    winner_name: Optional[str],
    award_amount_chf: Optional[float],
    vat_percent: Optional[float],
    offers_count: Optional[int],
    winner_position: int,
    winner_address: Optional[str],
    procurement_office_address: Optional[str],
    cpv_codes: list[str],
    procurement_type: Optional[str],
    source_url: Optional[str],
) -> AwardDetail:
    return AwardDetail(
        publication_number=publication_number,
        publication_date=publication_date,
        related_notice_number=related_notice_number,
        winner_name=winner_name,
        award_amount_chf=award_amount_chf,
        vat_percent=vat_percent,
        offers_count=offers_count,
        winner_position=winner_position,
        winner_address=winner_address,
        procurement_office_address=procurement_office_address,
        cpv_codes=cpv_codes,
        procurement_type=procurement_type,
        source_url=source_url,
    )


def _parse_details_from_json(raw: str, source_url: Optional[str]) -> Optional[list[AwardDetail]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    if "base" not in payload and "decision" not in payload:
        return None

    base = payload.get("base") if isinstance(payload.get("base"), dict) else {}
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    referencing_pub = payload.get("referencingPub") if isinstance(payload.get("referencingPub"), dict) else {}
    procurement = payload.get("procurement") if isinstance(payload.get("procurement"), dict) else {}
    project_info = payload.get("project-info") if isinstance(payload.get("project-info"), dict) else {}

    vendors = decision.get("vendors") if isinstance(decision.get("vendors"), list) else []

    cpv_codes: list[str] = []
    cpv_code = procurement.get("cpvCode")
    if isinstance(cpv_code, dict):
        code = cpv_code.get("code")
        if code is not None:
            code_str = str(code).strip()
            if re.match(r"^\d{8}$", code_str):
                cpv_codes.append(code_str)

    cpv_codes_payload = procurement.get("cpvCodes")
    if isinstance(cpv_codes_payload, list):
        for item in cpv_codes_payload:
            if not isinstance(item, dict):
                continue
            code = item.get("code")
            if code is None:
                continue
            code_str = str(code).strip()
            if re.match(r"^\d{8}$", code_str):
                cpv_codes.append(code_str)

    publication_number = str(base.get("publicationNumber") or "").strip()
    publication_date = _normalize_date(str(base.get("publicationDate") or "").strip()) if base.get("publicationDate") else None
    related_notice_number = str(referencing_pub.get("publicationNumber") or "").strip() or None
    procurement_office_address = _format_address(project_info.get("procOfficeAddress"))

    offers_count = None
    number_of_submissions = decision.get("numberOfSubmissions")
    if isinstance(number_of_submissions, int):
        offers_count = number_of_submissions
    elif isinstance(number_of_submissions, str):
        offers_count = _parse_int(number_of_submissions)

    procurement_type = _order_type_to_procurement_type(str(procurement.get("orderType") or "").strip() or None)
    unique_cpv_codes = sorted(set(cpv_codes))

    details: list[AwardDetail] = []
    for index, vendor in enumerate(vendors, start=1):
        if not isinstance(vendor, dict):
            continue
        vendor_price = vendor.get("price") if isinstance(vendor.get("price"), dict) else {}
        award_amount_chf: Optional[float] = None
        price_value = vendor_price.get("price")
        if isinstance(price_value, (int, float)):
            award_amount_chf = float(price_value)
        elif isinstance(price_value, str):
            award_amount_chf = _parse_chf_amount(price_value)

        details.append(
            _build_award_detail(
                publication_number=publication_number,
                publication_date=publication_date,
                related_notice_number=related_notice_number,
                winner_name=str(vendor.get("vendorName") or "").strip() or None,
                award_amount_chf=award_amount_chf,
                vat_percent=None,
                offers_count=offers_count,
                winner_position=index,
                winner_address=_format_address(vendor.get("vendorAddress")),
                procurement_office_address=procurement_office_address,
                cpv_codes=unique_cpv_codes,
                procurement_type=procurement_type,
                source_url=source_url,
            )
        )

    if details:
        return details

    return [
        _build_award_detail(
            publication_number=publication_number,
            publication_date=publication_date,
            related_notice_number=related_notice_number,
            winner_name=None,
            award_amount_chf=None,
            vat_percent=None,
            offers_count=offers_count,
            winner_position=1,
            winner_address=None,
            procurement_office_address=procurement_office_address,
            cpv_codes=unique_cpv_codes,
            procurement_type=procurement_type,
            source_url=source_url,
        )
    ]


def _parse_winner_blocks_from_html(
    text: str,
    *,
    publication_number: str,
    publication_date: Optional[str],
    related_notice_number: Optional[str],
    offers_count: Optional[int],
    procurement_type: Optional[str],
    cpv_codes: list[str],
    source_url: Optional[str],
) -> list[AwardDetail]:
    details: list[AwardDetail] = []
    pattern = re.compile(
        r"<li[^>]*>.*?>Anbieter</h5>\s*<p[^>]*>([^<]+)</p>"
        r".*?>Preis des ber[^<]*Angebots</h5>\s*<p[^>]*>([^<]+)</p>"
        r"(?:\s*<p[^>]*>mit\s*([0-9]+,[0-9]+)\s*%\s*MWST</p>)?"
        r".*?</li>",
        re.DOTALL,
    )

    for index, match in enumerate(pattern.finditer(text), start=1):
        winner_raw = match.group(1).strip()
        parts = [part.strip() for part in winner_raw.split(",")]
        winner_name = parts[0] if parts else None
        winner_address = ", ".join(parts[1:]).strip() or None if len(parts) > 1 else None
        details.append(
            _build_award_detail(
                publication_number=publication_number,
                publication_date=publication_date,
                related_notice_number=related_notice_number,
                winner_name=winner_name,
                award_amount_chf=_parse_chf_amount(match.group(2)),
                vat_percent=_parse_vat(match.group(3)),
                offers_count=offers_count,
                winner_position=index,
                winner_address=winner_address,
                procurement_office_address=None,
                cpv_codes=cpv_codes,
                procurement_type=procurement_type,
                source_url=source_url,
            )
        )
    return details


def parse_award_details(html: str, source_url: Optional[str] = None) -> list[AwardDetail]:
    """Parse award detail HTML/JSON into one or more structured winner rows."""
    parsed_json = _parse_details_from_json(html, source_url=source_url)
    if parsed_json is not None:
        return parsed_json

    text = html_lib.unescape(html)

    publication_number = _search(
        r'id="zuschlag".*?<li[^>]*>\s*<span[^>]*>(#[0-9]+-[0-9]+)</span>',
        text,
    ) or ""

    publication_date = _search(
        r'id="zuschlag".*?<li[^>]*>\s*<span[^>]*>#[0-9]+-[0-9]+</span>\s*</li>\s*'
        r'<li[^>]*>\s*<span[^>]*>([0-9]{2}\.[0-9]{2}\.[0-9]{4})</span>',
        text,
    )

    related_notice_number = _search(
        r'>Meldungsnummer</h5>\s*<p[^>]*>(#[0-9]+-[0-9]+)</p>',
        text,
    )
    if related_notice_number is None:
        related_notice_number = _search(
            r'id="vergangenePublikationen".*?<span[^>]*>(#[0-9]+-[0-9]+)</span>',
            text,
        )

    offers_count = _parse_int(
        _search(r'>Anzahl eingegangener Angebote</h5>\s*<p[^>]*>([0-9]+)</p>', text)
    )

    procurement_type = _search(r'>Auftragsart</h5>\s*<p[^>]*>([^<]+)</p>', text)
    cpv_codes = sorted(set(re.findall(r"\b[0-9]{8}\b", text)))

    details = _parse_winner_blocks_from_html(
        text,
        publication_number=publication_number,
        publication_date=publication_date,
        related_notice_number=related_notice_number,
        offers_count=offers_count,
        procurement_type=procurement_type,
        cpv_codes=cpv_codes,
        source_url=source_url,
    )
    if details:
        return details

    return [
        _build_award_detail(
            publication_number=publication_number,
            publication_date=publication_date,
            related_notice_number=related_notice_number,
            winner_name=None,
            award_amount_chf=None,
            vat_percent=None,
            offers_count=offers_count,
            winner_position=1,
            winner_address=None,
            procurement_office_address=None,
            cpv_codes=cpv_codes,
            procurement_type=procurement_type,
            source_url=source_url,
        )
    ]


def parse_award_detail(html: str, source_url: Optional[str] = None) -> AwardDetail:
    """Parse award detail HTML into the first structured winner row."""
    return parse_award_details(html, source_url=source_url)[0]
