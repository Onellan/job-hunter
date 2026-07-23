"""Pnet Playwright provider with bounded pagination and fixture-testable parsing."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any, Literal
from urllib.parse import quote, urlencode, urljoin

from pydantic import BaseModel, Field, HttpUrl, JsonValue, ValidationError

from app.models.job import EmploymentType, JobCandidate, WorkplaceType
from app.models.search import RemotePreference, SearchCriteria
from app.providers.base import BaseProvider
from app.providers.errors import (
    ProviderConfigurationError,
    ProviderDependencyError,
    ProviderExecutionError,
    ProviderParsingError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

_DEFAULT_BASE_URL = "https://www.pnet.co.za/jobs"
_DEFAULT_MAX_PAGES = 2
_MAX_PAGES = 10
_DEFAULT_TIMEOUT_MS = 30_000
_DEFAULT_RATE_LIMIT_DELAY_MS = 1_500
_DEFAULT_RETRY_ATTEMPTS = 1
_MAX_RETRY_ATTEMPTS = 2
_LISTING_SELECTOR = "article[data-testid='job-card'], article.job-card, article.job-item"
_TITLE_SELECTOR = "[data-testid='job-title'] a, h2 a, h3 a, a.job-title"
_COMPANY_SELECTOR = "[data-testid='company'], .company, .job-company"
_LOCATION_SELECTOR = "[data-testid='location'], .location, .job-location"
_DESCRIPTION_SELECTOR = "[data-testid='job-description'], .description, .job-description"
_DETAIL_SELECTOR = "[data-testid='job-meta'], .job-meta, .job-details"

PageLoader = Callable[[Sequence[str], "PnetSettings"], Iterable[str]]
SleepFunction = Callable[[float], None]
PnetRuntimeDiagnostic = Literal["dependency_unavailable", "browser_unavailable"]


class PnetSettings(BaseModel):
    """Validated non-secret runtime settings for the Pnet adapter."""

    base_url: str = _DEFAULT_BASE_URL
    max_pages: int = Field(default=_DEFAULT_MAX_PAGES, ge=1, le=_MAX_PAGES)
    timeout_ms: int = Field(default=_DEFAULT_TIMEOUT_MS, ge=5_000, le=60_000)
    rate_limit_delay_ms: int = Field(default=_DEFAULT_RATE_LIMIT_DELAY_MS, ge=250, le=10_000)
    retry_attempts: int = Field(default=_DEFAULT_RETRY_ATTEMPTS, ge=0, le=_MAX_RETRY_ATTEMPTS)
    listing_selector: str = Field(default=_LISTING_SELECTOR, min_length=1, max_length=500)


@dataclass(frozen=True)
class _PageResult:
    """One parsed Pnet page kept small enough for bounded provider processing."""

    content: str
    source_url: str


class _TransientPnetError(ProviderExecutionError):
    """Internal marker for safe retryable upstream server responses."""


class PnetProvider(BaseProvider):
    """Acquire Pnet results with one short-lived browser per provider run."""

    code = "pnet"
    display_name = "Pnet"
    bootstrap_by_default = True

    @classmethod
    def default_configuration(cls) -> dict[str, JsonValue]:
        """Return the conservative Pnet defaults for a newly discovered row."""

        return {
            "max_pages": _DEFAULT_MAX_PAGES,
            "timeout_ms": _DEFAULT_TIMEOUT_MS,
            "rate_limit_delay_ms": _DEFAULT_RATE_LIMIT_DELAY_MS,
            "retry_attempts": _DEFAULT_RETRY_ATTEMPTS,
        }

    @classmethod
    def availability_reason(cls) -> PnetRuntimeDiagnostic | None:
        """Return the local Playwright/Chromium availability category."""

        return check_pnet_runtime()

    def __init__(
        self,
        page_loader: PageLoader | None = None,
        sleeper: SleepFunction = sleep,
    ) -> None:
        """Allow deterministic page loading in tests while production uses Playwright."""

        self._page_loader = page_loader
        self._sleeper = sleeper

    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> Iterable[JobCandidate]:
        """Retrieve a bounded Pnet result set and normalise valid partial results."""

        settings = _settings_from(configuration)
        urls = _build_search_urls(criteria, settings)
        pages = self._load_pages(urls, settings)
        return _normalise_pages(pages, settings)

    def _load_pages(self, urls: Sequence[str], settings: PnetSettings) -> Iterable[_PageResult]:
        """Load pages through an injected fixture loader or one Playwright browser lifecycle."""

        if self._page_loader is not None:
            return [
                _PageResult(content=content, source_url=url)
                for content, url in zip(self._page_loader(urls, settings), urls, strict=False)
            ]
        return self._load_pages_with_playwright(urls, settings)

    def _load_pages_with_playwright(
        self,
        urls: Sequence[str],
        settings: PnetSettings,
    ) -> Iterable[_PageResult]:
        """Visit all bounded pages with one browser, closing it even after a source failure."""

        sync_playwright, timeout_error, playwright_error = _load_playwright()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.set_default_navigation_timeout(settings.timeout_ms)
                    results: list[_PageResult] = []
                    for index, url in enumerate(urls):
                        if index:
                            self._sleeper(settings.rate_limit_delay_ms / 1_000)
                        results.append(
                            _PageResult(
                                content=self._load_page_with_retry(
                                    page,
                                    url,
                                    settings,
                                    timeout_error,
                                    playwright_error,
                                ),
                                source_url=url,
                            )
                        )
                    return results
                finally:
                    browser.close()
        except (ProviderExecutionError, ProviderRateLimitError, ProviderTimeoutError):
            raise
        except Exception as exception:
            raise ProviderExecutionError() from exception

    def _load_page_with_retry(
        self,
        page: Any,
        url: str,
        settings: PnetSettings,
        timeout_error: type[Exception],
        playwright_error: type[Exception],
    ) -> str:
        """Navigate once or retry only timeout, rate-limit, and transient browser failures."""

        for attempt in range(settings.retry_attempts + 1):
            try:
                response = page.goto(url, wait_until="domcontentloaded")
                status_code = response.status if response is not None else 200
                if status_code == 429:
                    raise ProviderRateLimitError()
                if status_code >= 500:
                    raise _TransientPnetError("Pnet returned a transient server error")
                if status_code >= 400:
                    raise ProviderExecutionError("Pnet rejected the configured search")
                return str(page.content())
            except timeout_error as exception:
                if attempt == settings.retry_attempts:
                    raise ProviderTimeoutError() from exception
            except ProviderRateLimitError:
                if attempt == settings.retry_attempts:
                    raise
            except _TransientPnetError as exception:
                if attempt == settings.retry_attempts:
                    raise ProviderExecutionError() from exception
            except playwright_error as exception:
                if attempt == settings.retry_attempts:
                    raise ProviderExecutionError() from exception
            except ProviderExecutionError:
                raise
            self._sleeper(_retry_delay_seconds(settings.rate_limit_delay_ms, attempt))
        raise ProviderExecutionError("Pnet retry loop ended unexpectedly")


def check_pnet_runtime() -> PnetRuntimeDiagnostic | None:
    """Return a safe local diagnostic when Pnet cannot start its Chromium browser.

    This check imports Playwright and inspects its configured Chromium executable
    path only. It does not launch a browser, download software, or contact Pnet.
    """

    try:
        executable_path = _chromium_executable_path()
    except ModuleNotFoundError:
        return "dependency_unavailable"
    except Exception:
        # This is an isolated startup diagnostic. A broken local Playwright
        # installation must not prevent the application from serving other providers.
        return "browser_unavailable"
    return None if Path(executable_path).is_file() else "browser_unavailable"


def _settings_from(configuration: Mapping[str, JsonValue]) -> PnetSettings:
    """Validate provider-owned settings without allowing arbitrary browser behaviour."""

    try:
        settings = PnetSettings.model_validate(configuration)
    except ValidationError as exception:
        raise ProviderConfigurationError("Pnet configuration is invalid") from exception
    if not settings.base_url.startswith("https://www.pnet.co.za/"):
        raise ProviderConfigurationError("Pnet base_url must use the public Pnet HTTPS site")
    return settings


def _build_search_urls(criteria: SearchCriteria, settings: PnetSettings) -> list[str]:
    """Build Pnet's keyword path and bounded page query without exposing portal syntax upstream."""

    keywords = criteria.boolean_query or " ".join(criteria.keywords)
    if not keywords:
        raise ProviderConfigurationError("Pnet requires keywords or a Boolean query")
    keyword_path = quote(keywords.strip().replace(" ", "-"), safe="-")
    search_base = f"{settings.base_url.rstrip('/')}/{keyword_path}"
    query = _search_query(criteria)
    urls: list[str] = []
    for page_number in range(1, settings.max_pages + 1):
        page_query = {**query, "page": str(page_number)}
        urls.append(f"{search_base}?{urlencode(page_query)}")
    return urls


def _search_query(criteria: SearchCriteria) -> dict[str, str]:
    """Translate only stable Pnet-compatible filters into a conservative query string."""

    query: dict[str, str] = {}
    if criteria.locations:
        query["location"] = criteria.locations[0]
    if criteria.remote_preference == RemotePreference.REMOTE:
        query["remote"] = "true"
    return query


def _normalise_pages(pages: Iterable[_PageResult], settings: PnetSettings) -> list[JobCandidate]:
    """Parse bounded HTML pages while preserving valid partial cards from each page."""

    candidates: list[JobCandidate] = []
    received_listing = False
    for page in pages:
        page_candidates, listing_count = _normalise_page(page, settings)
        received_listing = received_listing or listing_count > 0
        candidates.extend(page_candidates)
    if received_listing and not candidates:
        raise ProviderParsingError()
    return candidates


def _normalise_page(page: _PageResult, settings: PnetSettings) -> tuple[list[JobCandidate], int]:
    """Parse one Pnet page without retaining the document after normalisation."""

    BeautifulSoup = _load_beautiful_soup()
    soup = BeautifulSoup(page.content, "lxml")
    cards = soup.select(settings.listing_selector)
    candidates: list[JobCandidate] = []
    for card in cards:
        try:
            candidates.append(_normalise_card(card, page.source_url))
        except (ProviderParsingError, TypeError, ValidationError, ValueError):
            continue
    return candidates, len(cards)


def _normalise_card(card: Any, page_url: str) -> JobCandidate:
    """Map one Pnet result card into the standard contract without inventing missing values."""

    title_link = card.select_one(_TITLE_SELECTOR)
    title = _required_text(title_link.get_text(" ", strip=True) if title_link else None, "title")
    source_url = _source_url(title_link.get("href") if title_link else None, page_url)
    details = _text_from(card.select_one(_DETAIL_SELECTOR))
    return JobCandidate(
        source=PnetProvider.code,
        source_job_id=_text_value(card.get("data-job-id") or card.get("data-id")),
        source_url=source_url,
        title=title,
        company=_text_from(card.select_one(_COMPANY_SELECTOR)),
        location=_text_from(card.select_one(_LOCATION_SELECTOR)),
        workplace_type=_workplace_type(card.get_text(" ", strip=True)),
        employment_type=_employment_type(details),
        description=_text_from(card.select_one(_DESCRIPTION_SELECTOR)),
    )


def _source_url(value: str | None, page_url: str) -> HttpUrl | None:
    """Return a direct absolute listing URL when the card exposes one."""

    text = _text_value(value)
    return HttpUrl(urljoin(page_url, text)) if text else None


def _workplace_type(text: str) -> WorkplaceType:
    """Infer only explicit Pnet work-location labels from visible card content."""

    normalised = text.casefold()
    if "work from home" in normalised or "remote" in normalised:
        return WorkplaceType.REMOTE
    if "hybrid" in normalised:
        return WorkplaceType.HYBRID
    return WorkplaceType.UNKNOWN


def _employment_type(text: str | None) -> EmploymentType | None:
    """Map Pnet's common contract labels when they are present on a result card."""

    normalised = (text or "").casefold()
    mappings = (
        ("permanent", EmploymentType.FULL_TIME),
        ("full time", EmploymentType.FULL_TIME),
        ("part time", EmploymentType.PART_TIME),
        ("contract", EmploymentType.CONTRACT),
        ("temporary", EmploymentType.TEMPORARY),
        ("internship", EmploymentType.INTERNSHIP),
    )
    return next(
        (employment_type for label, employment_type in mappings if label in normalised), None
    )


def _text_from(element: Any) -> str | None:
    """Extract compact visible text from an optional BeautifulSoup element."""

    return _text_value(element.get_text(" ", strip=True)) if element is not None else None


def _required_text(value: str | None, field_name: str) -> str:
    """Require a small durable text value before constructing a candidate."""

    text = _text_value(value)
    if text is None:
        raise ProviderParsingError(f"Pnet card is missing {field_name}")
    return text


def _text_value(value: object) -> str | None:
    """Normalise portal text while preserving absent values as ``None``."""

    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _retry_delay_seconds(rate_limit_delay_ms: int, attempt: int) -> float:
    """Return capped exponential backoff derived from the configured polite page delay."""

    return float(min(rate_limit_delay_ms * (2**attempt), 10_000)) / 1_000


def _load_beautiful_soup() -> Any:
    """Lazily import HTML parsing dependencies so the base install stays lightweight."""

    try:
        import lxml  # type: ignore[import-untyped]  # noqa: F401
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as exception:
        raise ProviderDependencyError() from exception
    return BeautifulSoup


def _load_playwright() -> tuple[Callable[[], Any], type[Exception], type[Exception]]:
    """Lazily import Playwright only when a live Pnet run starts."""

    try:
        from playwright.sync_api import (  # type: ignore[import-not-found]
            Error,
            TimeoutError,
            sync_playwright,
        )
    except ModuleNotFoundError as exception:
        raise ProviderDependencyError() from exception
    return sync_playwright, TimeoutError, Error


def _chromium_executable_path() -> str:
    """Return Playwright's local Chromium path without launching a browser."""

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        return str(playwright.chromium.executable_path)
