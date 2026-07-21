"""Mapping from raw I14Y DCAT-AP-CH payloads to flat, LLM-friendly models.

Design note: I14Y payloads are deeply nested and heavily multilingual. A single
dataset record can exceed 20 kB of JSON, most of it repeated translations. These
mappers collapse the structure to one requested language, which is what keeps
the model context usable at scale.
"""

from __future__ import annotations

from typing import Any

from .models import (
    CatalogSummary,
    CodeListEntry,
    ConceptSummary,
    DataServiceSummary,
    DatasetDetail,
    DatasetSummary,
    Distribution,
    PublicServiceSummary,
    Publisher,
    SearchHit,
    pick_lang,
    vocab_label,
)

PORTAL = "https://www.i14y.admin.ch"


def _uris(items: Any) -> list[str]:
    """Extract URIs from a list of I14Y link objects.

    Field shape is inconsistent: some entries carry `uri`, others carry only a
    `label` multilanguage object with no URI at all (verified 2026-07-21 on
    `/api/dataservices`, e.g. entries labelled «OpenAPI Spezifikation»). Both
    shapes are handled; label-only entries surface as their label text so the
    information is not silently dropped.
    """
    out: list[str] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            uri = item.get("uri") or item.get("url")
            if uri:
                out.append(uri)
            else:
                label = pick_lang(item.get("label"))
                if label:
                    out.append(f"(no URI) {label}")
    return out


def _first_uri(items: Any) -> str | None:
    found = _uris(items)
    return found[0] if found else None


def _identifier(raw: dict[str, Any]) -> str | None:
    ids = raw.get("identifiers")
    if isinstance(ids, list) and ids:
        first = ids[0]
        return first if isinstance(first, str) else first.get("identifier")
    return raw.get("identifier")


def _labels(items: Any, language: str) -> list[str]:
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        label = vocab_label(item, language) if isinstance(item, dict) else str(item)
        if label:
            out.append(label)
    return out


def _keywords(raw: dict[str, Any], language: str) -> list[str]:
    kw = raw.get("keywords")
    out: list[str] = []
    if isinstance(kw, list):
        for item in kw:
            text = pick_lang(item, language) if isinstance(item, dict) else item
            if isinstance(text, str) and text:
                out.append(text)
    return out


def _publisher_name(raw: dict[str, Any], language: str) -> str | None:
    pub = raw.get("publisher")
    if not isinstance(pub, dict):
        return None
    return pick_lang(pub.get("name"), language) or pub.get("identifier")


def _portal_link(kind: str, raw: dict[str, Any]) -> str | None:
    """Build a permalink into the I14Y web portal for human follow-up."""
    ident = raw.get("id")
    return f"{PORTAL}/en/catalog/{kind}/{ident}" if ident else None


def map_search_hit(raw: dict[str, Any], language: str) -> SearchHit:
    return SearchHit(
        id=raw.get("id"),
        identifier=_identifier(raw),
        type=raw.get("type"),
        title=pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        publisher=_publisher_name(raw, language),
        themes=_labels(raw.get("themes"), language),
        access_rights=vocab_label(raw.get("accessRights"), language),
        registration_status=raw.get("registrationStatus"),
        landing_page=_portal_link("datasets", raw),
    )


def map_distribution(raw: dict[str, Any], language: str) -> Distribution:
    return Distribution(
        id=raw.get("id"),
        title=pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        format=vocab_label(raw.get("format"), language),
        media_type=vocab_label(raw.get("mediaType"), language),
        download_url=_first_uri([raw.get("downloadUrl")] if raw.get("downloadUrl") else []),
        access_url=_first_uri([raw.get("accessUrl")] if raw.get("accessUrl") else []),
        licence=vocab_label(raw.get("license"), language),
        rights=pick_lang(raw.get("rights"), language),
        byte_size=raw.get("byteSize"),
        issued=raw.get("issued"),
        modified=raw.get("modified"),
    )


def map_dataset_summary(raw: dict[str, Any], language: str) -> DatasetSummary:
    return DatasetSummary(
        id=raw.get("id"),
        identifier=_identifier(raw),
        title=pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        publisher=_publisher_name(raw, language),
        themes=_labels(raw.get("themes"), language),
        keywords=_keywords(raw, language),
        access_rights=vocab_label(raw.get("accessRights"), language),
        registration_status=raw.get("registrationStatus"),
        frequency=vocab_label(raw.get("frequency"), language),
        landing_page=_first_uri(raw.get("landingPages")) or _portal_link("datasets", raw),
        distribution_count=len(raw.get("distributions") or []),
    )


def map_dataset_detail(raw: dict[str, Any], language: str) -> DatasetDetail:
    base = map_dataset_summary(raw, language).model_dump()
    contacts = raw.get("contactPoints") or []
    contact = contacts[0] if contacts else {}
    temporal = raw.get("temporalCoverage")
    temporal_text = None
    if isinstance(temporal, list) and temporal:
        first = temporal[0]
        if isinstance(first, dict):
            temporal_text = f"{first.get('start', '?')} – {first.get('end', '?')}"
    return DatasetDetail(
        **base,
        contact_email=contact.get("hasEmail") if isinstance(contact, dict) else None,
        contact_name=pick_lang(contact.get("fn"), language) if isinstance(contact, dict) else None,
        languages=_labels(raw.get("languages"), language),
        temporal_coverage=temporal_text,
        spatial=_labels(raw.get("spatial"), language),
        documentation=_uris(raw.get("documentation")),
        distributions=[map_distribution(d, language) for d in (raw.get("distributions") or [])],
    )


def map_data_service(raw: dict[str, Any], language: str) -> DataServiceSummary:
    serves = raw.get("servesDatasets")
    serves_ids: list[str] = []
    if isinstance(serves, list):
        for item in serves:
            if isinstance(item, str):
                serves_ids.append(item)
            elif isinstance(item, dict):
                found = item.get("id") or item.get("identifier") or item.get("uri")
                if found:
                    serves_ids.append(found)
    return DataServiceSummary(
        id=raw.get("id"),
        identifier=_identifier(raw),
        title=pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        publisher=_publisher_name(raw, language),
        endpoint_urls=_uris(raw.get("endpointUrls")),
        endpoint_descriptions=_uris(raw.get("endpointDescriptions")),
        licence=vocab_label(raw.get("license"), language),
        access_rights=vocab_label(raw.get("accessRights"), language),
        themes=_labels(raw.get("themes"), language),
        keywords=_keywords(raw, language),
        serves_datasets=serves_ids,
        landing_page=_first_uri(raw.get("landingPages")) or _portal_link("dataservices", raw),
    )


def map_public_service(raw: dict[str, Any], language: str) -> PublicServiceSummary:
    return PublicServiceSummary(
        id=raw.get("id"),
        identifier=_identifier(raw),
        title=pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        publisher=_publisher_name(raw, language),
        themes=_labels(raw.get("themes"), language),
        landing_page=_first_uri(raw.get("landingPages")) or _portal_link("publicservices", raw),
    )


def map_concept(raw: dict[str, Any], language: str) -> ConceptSummary:
    return ConceptSummary(
        id=raw.get("id"),
        identifier=_identifier(raw),
        title=pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        publisher=_publisher_name(raw, language),
        concept_type=raw.get("conceptType"),
        value_type=raw.get("codeListEntryValueType"),
        version=raw.get("version"),
        registration_status=raw.get("registrationStatus"),
        landing_page=_portal_link("concepts", raw),
    )


def map_codelist_entry(raw: dict[str, Any], language: str) -> CodeListEntry:
    valid_from = valid_to = None
    for ann in raw.get("annotations") or []:
        if not isinstance(ann, dict) or ann.get("type") != "Period":
            continue
        text = pick_lang(ann.get("text"), language)
        if ann.get("identifier") == "start":
            valid_from = text
        elif ann.get("identifier") == "end":
            valid_to = text
    return CodeListEntry(
        id=raw.get("id"),
        code=raw.get("code") or raw.get("value") or raw.get("identifier"),
        name=pick_lang(raw.get("name"), language) or pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        valid_from=valid_from,
        valid_to=valid_to,
    )


def map_publisher(raw: dict[str, Any], language: str) -> Publisher:
    return Publisher(
        id=raw.get("id"),
        identifier=raw.get("identifier"),
        name=pick_lang(raw.get("name"), language),
        uid=raw.get("uid"),
        email=raw.get("email") or raw.get("hasEmail"),
        landing_page=_first_uri(raw.get("landingPages")),
    )


def map_catalog(raw: dict[str, Any], language: str) -> CatalogSummary:
    return CatalogSummary(
        id=raw.get("id"),
        identifier=_identifier(raw),
        title=pick_lang(raw.get("title"), language),
        description=pick_lang(raw.get("description"), language),
        publisher=_publisher_name(raw, language),
    )
