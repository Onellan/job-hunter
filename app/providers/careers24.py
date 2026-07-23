"""Careers24 public-search provider with bounded, stateless HTML acquisition."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, HttpUrl, JsonValue, ValidationError

from app.models.job import EmploymentType, JobCandidate, WorkplaceType
from app.models.search import SearchCriteria
from app.providers.base import BaseProvider
from app.providers.errors import (
    ProviderConfigurationError,
    ProviderDependencyError,
    ProviderExecutionError,
    ProviderParsingError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

_DEFAULT_BASE_URL = "https://www.careers24.com/jobs"
_DEFAULT_MAX_PAGES = 1
_MAX_PAGES = 2
_DEFAULT_RESULTS_WANTED = 20
_MAX_RESULTS_WANTED = 50
_DEFAULT_TIMEOUT_SECONDS = 15
_DEFAULT_RATE_LIMIT_DELAY_MS = 2_000
_DEFAULT_RETRY_ATTEMPTS = 0
_MAX_RETRY_ATTEMPTS = 1
_PUBLIC_HOSTS = frozenset({"careers24.com", "www.careers24.com"})
_ADVERT_PATH_PATTERN = re.compile(r"/jobs/adverts/(?P<id>\d+)(?:-|/|$)", re.IGNORECASE)
_POSTED_PATTERN = re.compile(r"\bPosted:\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\b", re.IGNORECASE)

PageLoader = Callable[[str, int], str]
SleepFunction = Callable[[float], None]


class Careers24Settings(BaseModel):
    """Validated, non-secret settings for Careers24 public search pages."""

    base_url: str = _DEFAULT_BASE_URL
    max_pages: int = Field(default=_DEFAULT_MAX_PAGES, ge=1, le=_MAX_PAGES)
    results_wanted: int = Field(default=_DEFAULT_RESULTS_WANTED, ge=1, le=_MAX_RESULTS_WANTED)
    timeout_seconds: int = Field(default=_DEFAULT_TIMEOUT_SECONDS, ge=5, le=30)
    rate_limit_delay_ms: int = Field(default=_DEFAULT_RATE_LIMIT_DELAY_MS, ge=500, le=10_000)
    retry_attempts: int = Field(default=_DEFAULT_RETRY_ATTEMPTS, ge=0, le=_MAX_RETRY_ATTEMPTS)


class _TransientCareers24Error(ProviderExecutionError):
    """Internal marker for retryable Careers24 server failures."""


class Careers24Provider(BaseProvider):
    """Retrieve Careers24's publicly visible result cards without browser state."""

    code = "careers24"
    display_name = "Careers24"
    bootstrap_by_default = True

    @classmethod
    def default_configuration(cls) -> dict[str, JsonValue]:
        """Return conservative defaults for a newly discovered Careers24 row."""

        return {
            "max_pages": _DEFAULT_MAX_PAGES,
            "results_wanted": _DEFAULT_RESULTS_WANTED,
            "timeout_seconds": _DEFAULT_TIMEOUT_SECONDS,
            "rate_limit_delay_ms": _DEFAULT_RATE_LIMIT_DELAY_MS,
            "retry_attempts": _DEFAULT_RETRY_ATTEMPTS,
        }

    def __init__(
        self,
        page_loader: PageLoader | None = None,
        sleeper: SleepFunction = sleep,
    ) -> None:
        """Allow fixture transport injection while production uses standard HTTPS requests."""

        self._page_loader = page_loader
        self._sleeper = sleeper

    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> Iterable[JobCandidate]:
        """Retrieve a bounded result set from public Careers24 search pages."""

        settings = _settings_from(configuration)
        candidates: list[JobCandidate] = []
        seen_source_ids: set[str] = set()
        for index, url in enumerate(_build_search_urls(criteria, settings)):
            if index:
                self._sleeper(settings.rate_limit_delay_ms / 1_000)
            content = self._load_page(url, settings)
            page_candidates, listing_count = _normalise_page(content, url)
            if listing_count and not page_candidates:
                raise ProviderParsingError()
            for candidate in page_candidates:
                identity = candidate.source_job_id or str(candidate.source_url)
                if identity in seen_source_ids:
                    continue
                seen_source_ids.add(identity)
                candidates.append(candidate)
                if len(candidates) == settings.results_wanted:
                    return candidates
        return candidates

    def _load_page(self, url: str, settings: Careers24Settings) -> str:
        """Load one page with only bounded retries for transient source failures."""

        for attempt in range(settings.retry_attempts + 1):
            try:
                content = (
                    self._page_loader(url, settings.timeout_seconds)
                    if self._page_loader is not None
                    else _request_public_page(url, settings.timeout_seconds)
                )
                if _is_access_block_page(content):
                    raise ProviderExecutionError("Careers24 rejected the public search request")
                return content
            except ProviderRateLimitError:
                if attempt == settings.retry_attempts:
                    raise
            except (ProviderTimeoutError, _TransientCareers24Error):
                if attempt == settings.retry_attempts:
                    raise
            except ProviderExecutionError:
                raise
            self._sleeper(_retry_delay_seconds(settings.rate_limit_delay_ms, attempt))
        raise ProviderExecutionError("Careers24 retry loop ended unexpectedly")


def _settings_from(configuration: Mapping[str, JsonValue]) -> Careers24Settings:
    """Validate settings and prevent routing requests away from Careers24."""

    try:
        settings = Careers24Settings.model_validate(configuration)
    except ValidationError as exception:
        raise ProviderConfigurationError("Careers24 configuration is invalid") from exception
    parsed = urlparse(settings.base_url)
    if parsed.scheme != "https" or parsed.netloc.casefold() not in _PUBLIC_HOSTS:
        raise ProviderConfigurationError(
            "Careers24 base_url must use the public Careers24 HTTPS site"
        )
    if parsed.path.rstrip("/") != "/jobs":
        raise ProviderConfigurationError("Careers24 base_url must target its public jobs path")
    return settings


def _build_search_urls(criteria: SearchCriteria, settings: Careers24Settings) -> list[str]:
    """Build Careers24's public location/keyword path with bounded pagination."""

    keywords = criteria.boolean_query or " ".join(criteria.keywords)
    if not keywords:
        raise ProviderConfigurationError("Careers24 requires keywords or a Boolean query")
    parts = [f"lc-{_slug(criteria.locations[0])}" if criteria.locations else "lc-south-africa"]
    parts.append(f"kw-{_slug(keywords)}")
    search_base = f"{settings.base_url.rstrip('/')}/{'/'.join(parts)}/"
    return [
        search_base if page_number == 1 else f"{search_base}?{urlencode({'page': page_number})}"
        for page_number in range(1, settings.max_pages + 1)
    ]


def _slug(value: str) -> str:
    """Encode visible search text for Careers24's public path syntax."""

    compact = "-".join(value.strip().casefold().split())
    return quote(compact, safe="-")


def _request_public_page(url: str, timeout_seconds: int) -> str:
    """Request one result page without cookies, credentials, profiles, or browser state."""

    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Job-Hunter/0.1 (self-hosted personal job search)",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content = response.read()
            if not isinstance(content, bytes):
                raise ProviderExecutionError("Careers24 returned an invalid public response")
            encoding = response.headers.get_content_charset() or "utf-8"
            return content.decode(encoding, "replace")
    except HTTPError as exception:
        if exception.code == 429:
            raise ProviderRateLimitError() from exception
        if exception.code >= 500:
            raise _TransientCareers24Error() from exception
        raise ProviderExecutionError("Careers24 rejected the public search request") from exception
    except TimeoutError as exception:
        raise ProviderTimeoutError() from exception
    except URLError as exception:
        if isinstance(exception.reason, TimeoutError):
            raise ProviderTimeoutError() from exception
        raise ProviderExecutionError() from exception


def _is_access_block_page(content: str) -> bool:
    """Identify visible anti-bot/error pages so they never look like empty results."""

    normalised = content.casefold()
    return (
        "attention required! | cloudflare" in normalised
        or "sorry, you have been blocked" in normalised
    )


def _normalise_page(content: str, page_url: str) -> tuple[list[JobCandidate], int]:
    """Parse visible advert links from one result page without retaining its HTML."""

    BeautifulSoup = _load_beautiful_soup()
    soup = BeautifulSoup(content, "lxml")
    advert_links = [
        link
        for link in soup.select("a[href*='/jobs/adverts/']")
        if _advert_source_url(link.get("href"), page_url) is not None
    ]
    candidates: list[JobCandidate] = []
    for link in advert_links:
        try:
            candidates.append(_normalise_link(link, page_url))
        except (ProviderParsingError, TypeError, ValidationError, ValueError):
            continue
    return candidates, len(advert_links)


def _normalise_link(link: Any, page_url: str) -> JobCandidate:
    """Map an advert link and its nearest result-card text into a job candidate."""

    source_url = _advert_source_url(link.get("href"), page_url)
    if source_url is None:
        raise ProviderParsingError("Careers24 advert link is invalid")
    card = _result_card(link)
    card_text = _text_value(card.get_text(" ", strip=True)) if card is not None else None
    title = _required_text(link.get_text(" ", strip=True), "title")
    return JobCandidate(
        source=Careers24Provider.code,
        source_job_id=_source_job_id(str(source_url)),
        source_url=source_url,
        title=title,
        company=_first_text(
            card, "[class*='company'], [class*='employer'], [data-testid='company']"
        ),
        location=_first_text(card, "[class*='location'], [data-testid='location']"),
        workplace_type=_workplace_type(card_text),
        employment_type=_employment_type(card_text),
        published_at=_published_at(card_text),
    )


def _advert_source_url(value: object, page_url: str) -> HttpUrl | None:
    """Return only a Careers24 public advert URL from a result-page link."""

    if not isinstance(value, str) or not value.strip():
        return None
    absolute_url = urljoin(page_url, value)
    parsed = urlparse(absolute_url)
    if parsed.scheme != "https" or parsed.netloc.casefold() not in _PUBLIC_HOSTS:
        return None
    if _ADVERT_PATH_PATTERN.search(parsed.path) is None:
        return None
    return HttpUrl(absolute_url)


def _source_job_id(source_url: str) -> str | None:
    """Extract Careers24's stable numeric advert identifier when the URL provides it."""

    match = _ADVERT_PATH_PATTERN.search(urlparse(source_url).path)
    return match.group("id") if match else None


def _result_card(link: Any) -> Any:
    """Return the closest likely result-card ancestor without relying on one CSS class."""

    for ancestor in link.parents:
        attributes = getattr(ancestor, "attrs", {})
        classes = " ".join(attributes.get("class", []))
        normalised_classes = classes.casefold()
        if "job-card" in normalised_classes or getattr(ancestor, "name", None) in {"article", "li"}:
            return ancestor
        if attributes.get("data-job-id") or any(
            marker in normalised_classes for marker in ("vacancy", "result", "listing")
        ):
            return ancestor
    return link.parent


def _first_text(card: Any, selector: str) -> str | None:
    """Extract compact text from one optional stable result-card field."""

    element = card.select_one(selector) if card is not None else None
    return _text_value(element.get_text(" ", strip=True)) if element is not None else None


def _workplace_type(text: str | None) -> WorkplaceType:
    """Infer workplace type only when the visible card explicitly labels it."""

    normalised = (text or "").casefold()
    if "remote" in normalised or "work from home" in normalised:
        return WorkplaceType.REMOTE
    if "hybrid" in normalised:
        return WorkplaceType.HYBRID
    return WorkplaceType.UNKNOWN


def _employment_type(text: str | None) -> EmploymentType | None:
    """Map Careers24's visible employment labels when present on a result card."""

    normalised = (text or "").casefold()
    mappings = (
        ("permanent", EmploymentType.FULL_TIME),
        ("full time", EmploymentType.FULL_TIME),
        ("part time", EmploymentType.PART_TIME),
        ("contract", EmploymentType.CONTRACT),
        ("temporary", EmploymentType.TEMPORARY),
        ("internship", EmploymentType.INTERNSHIP),
    )
    return next((value for label, value in mappings if label in normalised), None)


def _published_at(text: str | None) -> datetime | None:
    """Parse Careers24's visible ``Posted: DD Mon YYYY`` label when available."""

    match = _POSTED_PATTERN.search(text or "")
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%d %b %Y").replace(tzinfo=UTC)
    except ValueError:
        return None


def _required_text(value: object, field_name: str) -> str:
    """Require compact display text before a standard candidate is built."""

    text = _text_value(value)
    if text is None:
        raise ProviderParsingError(f"Careers24 result is missing {field_name}")
    return text


def _text_value(value: object) -> str | None:
    """Normalise whitespace while retaining absent portal fields as ``None``."""

    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _retry_delay_seconds(rate_limit_delay_ms: int, attempt: int) -> float:
    """Return capped exponential backoff derived from the configured polite delay."""

    return float(min(rate_limit_delay_ms * (2**attempt), 10_000)) / 1_000


def _load_beautiful_soup() -> Any:
    """Lazily import HTML parsing dependencies used by the normal provider runtime."""

    try:
        import lxml  # type: ignore[import-untyped]  # noqa: F401
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as exception:
        raise ProviderDependencyError() from exception
    return BeautifulSoup
