"""Pydantic v2 models for i14y-mcp.

Every outbound payload inherits from `I14YResponse`, which makes omitting
attribution and provenance structurally impossible.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .client import ATTRIBUTION

Provenance = Literal["live_api", "cached"]

LANGUAGES = ("de", "fr", "it", "rm", "en")

RESOURCE_TYPES = ("Dataset", "DataService", "PublicService", "Concept", "MappingTable")


class I14YResponse(BaseModel):
    """Common envelope. Do not instantiate directly."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(default=ATTRIBUTION, description="Attribution string.")
    provenance: Provenance = Field(default="live_api", description="Where this payload came from.")
    retrieved_at: str = Field(description="UTC timestamp of retrieval.")


def pick_lang(value: Any, language: str = "de") -> str | None:
    """Collapse an I14Y multilanguage object to a single string.

    I14Y objects look like {"de": "...", "fr": "...", "en": "..."} but fields
    are frequently missing for individual languages. Falls back through
    de -> en -> fr -> it -> rm -> first available, so the caller never gets an
    empty string where text exists in *some* language.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return str(value)

    # Some payloads wrap the multilanguage object one level deeper. Themes use
    # `name`, keywords use `label` (verified live 2026-07-21 on
    # /api/dataservices). Unwrap before looking for language keys, otherwise a
    # dict leaks into a str-typed field.
    for wrapper in ("label", "name", "text", "title"):
        inner = value.get(wrapper)
        if isinstance(inner, dict):
            return pick_lang(inner, language)
        if isinstance(inner, str) and inner:
            return inner

    order = [language] + [x for x in ("de", "en", "fr", "it", "rm") if x != language]
    for key in order:
        text = value.get(key)
        if isinstance(text, str) and text:
            return text
    for text in value.values():
        if isinstance(text, str) and text:
            return text
    return None


def vocab_label(entry: Any, language: str = "de") -> str | None:
    """Extract a readable label from an I14Y vocabulary entry."""
    if not isinstance(entry, dict):
        return None
    return pick_lang(entry.get("name"), language) or entry.get("code")


class SearchHit(BaseModel):
    """One result from the federated catalogue search."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    identifier: str | None = None
    type: str | None = Field(default=None, description="Dataset, Concept, ...")
    title: str | None = None
    description: str | None = None
    publisher: str | None = None
    themes: list[str] = Field(default_factory=list)
    access_rights: str | None = None
    registration_status: str | None = None
    landing_page: str | None = Field(
        default=None, description="Permalink into the I14Y web portal."
    )


class SearchResult(I14YResponse):
    query: str | None = None
    language: str
    total_matched: int = Field(description="Matches reported by the upstream index.")
    returned: int = Field(description="Records in this payload after capping.")
    truncated: bool = Field(description="True when the upstream result set exceeded the cap.")
    hits: list[SearchHit]


class Distribution(BaseModel):
    """A concrete, downloadable representation of a dataset."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    title: str | None = None
    description: str | None = None
    format: str | None = None
    media_type: str | None = None
    download_url: str | None = None
    access_url: str | None = None
    licence: str | None = None
    rights: str | None = None
    byte_size: int | None = None
    issued: str | None = None
    modified: str | None = None


class DatasetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    identifier: str | None = None
    title: str | None = None
    description: str | None = None
    publisher: str | None = None
    themes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    access_rights: str | None = None
    registration_status: str | None = None
    frequency: str | None = None
    landing_page: str | None = None
    distribution_count: int = 0


class DatasetDetail(DatasetSummary):
    contact_email: str | None = None
    contact_name: str | None = None
    languages: list[str] = Field(default_factory=list)
    temporal_coverage: str | None = None
    spatial: list[str] = Field(default_factory=list)
    documentation: list[str] = Field(default_factory=list)
    distributions: list[Distribution] = Field(default_factory=list)


class DatasetListResult(I14YResponse):
    page: int
    page_size: int
    returned: int
    datasets: list[DatasetSummary]


class DatasetDetailResult(I14YResponse):
    dataset: DatasetDetail


class DistributionsResult(I14YResponse):
    dataset_id: str
    dataset_title: str | None = None
    returned: int
    distributions: list[Distribution]


class DataServiceSummary(BaseModel):
    """A registered machine interface — the discovery payload that matters."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    identifier: str | None = None
    title: str | None = None
    description: str | None = None
    publisher: str | None = None
    endpoint_urls: list[str] = Field(default_factory=list)
    endpoint_descriptions: list[str] = Field(
        default_factory=list, description="OpenAPI/Swagger URLs where available."
    )
    licence: str | None = None
    access_rights: str | None = None
    themes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    serves_datasets: list[str] = Field(default_factory=list)
    landing_page: str | None = None


class DataServiceListResult(I14YResponse):
    page: int
    page_size: int
    returned: int
    data_services: list[DataServiceSummary]


class DataServiceDetailResult(I14YResponse):
    data_service: DataServiceSummary


class PublicServiceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    identifier: str | None = None
    title: str | None = None
    description: str | None = None
    publisher: str | None = None
    themes: list[str] = Field(default_factory=list)
    landing_page: str | None = None


class PublicServiceListResult(I14YResponse):
    page: int
    page_size: int
    returned: int
    public_services: list[PublicServiceSummary]


class ConceptSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    identifier: str | None = None
    title: str | None = None
    description: str | None = None
    publisher: str | None = None
    concept_type: str | None = Field(default=None, description="CodeList, Date, Numeric or String.")
    value_type: str | None = None
    version: str | None = None
    registration_status: str | None = None
    landing_page: str | None = None


class ConceptListResult(I14YResponse):
    page: int
    page_size: int
    returned: int
    concepts: list[ConceptSummary]


class ConceptDetailResult(I14YResponse):
    concept: ConceptSummary


class CodeListEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None


class CodeListResult(I14YResponse):
    concept_id: str
    language: str
    page: int
    page_size: int
    returned: int
    entries: list[CodeListEntry]


class Publisher(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    identifier: str | None = None
    name: str | None = None
    uid: str | None = Field(default=None, description="Swiss UID, joins to Zefix.")
    email: str | None = None
    landing_page: str | None = None


class PublisherListResult(I14YResponse):
    page: int
    page_size: int
    returned: int
    publishers: list[Publisher]


class CatalogSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    identifier: str | None = None
    title: str | None = None
    description: str | None = None
    publisher: str | None = None


class CatalogListResult(I14YResponse):
    page: int
    page_size: int
    returned: int
    catalogs: list[CatalogSummary]


class StatusResult(I14YResponse):
    reachable: bool
    base_url: str
    last_successful_call: str | None = None
    checked_endpoints: dict[str, str]
    note: str
