"""JobSpy adapter that maps its tabular output into standard job candidates."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from pydantic import HttpUrl, JsonValue, ValidationError

from app.models.job import EmploymentType, JobCandidate, SalaryPeriod, WorkplaceType
from app.models.provider import ProviderAvailabilityReason
from app.models.search import RemotePreference, SearchCriteria
from app.providers.base import BaseProvider
from app.providers.errors import (
    ProviderConfigurationError,
    ProviderDependencyError,
    ProviderExecutionError,
    ProviderParsingError,
)

_DEFAULT_RESULT_LIMIT = 25
_MAX_RESULT_LIMIT = 100
DEFAULT_SITES = ("indeed", "linkedin")
_SUPPORTED_SITES = frozenset(DEFAULT_SITES)
_DEFAULT_COUNTRY_INDEED = "South Africa"

logger = logging.getLogger(__name__)


class JobSpyProvider(BaseProvider):
    """Acquire JobSpy listings through the supported JobSpy runtime dependency."""

    code = "jobspy"
    display_name = "JobSpy"
    bootstrap_by_default = True

    @classmethod
    def default_configuration(cls) -> dict[str, JsonValue]:
        """Return the verified JobSpy portal defaults for a newly discovered row."""

        return {
            "sites": list(DEFAULT_SITES),
            "country_indeed": _DEFAULT_COUNTRY_INDEED,
            "results_wanted": _DEFAULT_RESULT_LIMIT,
        }

    @classmethod
    def availability_reason(cls) -> ProviderAvailabilityReason | None:
        """Classify a missing local JobSpy package without importing a portal client."""

        try:
            _load_jobspy_scraper()
        except ProviderDependencyError:
            return "dependency_unavailable"
        return None

    def __init__(self, scrape_jobs: Callable[..., Any] | None = None) -> None:
        """Allow tests to inject a deterministic JobSpy-compatible scraper."""

        self._scrape_jobs = scrape_jobs

    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> Iterable[JobCandidate]:
        """Retrieve and normalise a bounded JobSpy result set."""

        scraper = self._scrape_jobs or _load_jobspy_scraper()
        arguments = _build_jobspy_arguments(criteria, configuration)
        candidates: list[JobCandidate] = []
        site_errors: list[ProviderExecutionError | ProviderParsingError] = []
        for site in arguments["site_name"]:
            try:
                dataframe = scraper(**{**arguments, "site_name": [site]})
                candidates.extend(_normalise_rows(dataframe.to_dict(orient="records")))
            except ProviderConfigurationError:
                raise
            except Exception as exception:
                error = _provider_error_from(exception)
                site_errors.append(error)
                _log_site_failure(site, error)
        if candidates or len(site_errors) < len(arguments["site_name"]):
            return candidates
        raise site_errors[0]


def _load_jobspy_scraper() -> Callable[..., Any]:
    """Lazily import JobSpy so the base application has no scraping dependency."""

    try:
        from jobspy import scrape_jobs  # type: ignore[import-not-found]
    except ModuleNotFoundError as exception:
        raise ProviderDependencyError() from exception
    return cast(Callable[..., Any], scrape_jobs)


def _build_jobspy_arguments(
    criteria: SearchCriteria,
    configuration: Mapping[str, JsonValue],
) -> dict[str, Any]:
    """Translate safe provider-neutral criteria into JobSpy's supported inputs."""

    search_term = criteria.boolean_query or " ".join(criteria.keywords)
    if not search_term:
        raise ProviderConfigurationError("JobSpy requires keywords or a Boolean query")
    if criteria.excluded_keywords:
        search_term = f"{search_term} {' '.join(f'-{term}' for term in criteria.excluded_keywords)}"

    configured_sites = configuration.get("sites", list(DEFAULT_SITES))
    if (
        not isinstance(configured_sites, list)
        or not configured_sites
        or not all(isinstance(site, str) for site in configured_sites)
    ):
        raise ProviderConfigurationError("JobSpy configuration requires a non-empty sites list")
    sites = [site for site in configured_sites if isinstance(site, str)]
    unsupported_sites = sorted(set(sites) - _SUPPORTED_SITES)
    if unsupported_sites:
        names = ", ".join(unsupported_sites)
        raise ProviderConfigurationError(f"JobSpy does not support configured sites: {names}")

    arguments: dict[str, Any] = {
        "site_name": sites,
        "search_term": search_term,
        "location": _first_location(criteria, configuration),
        "results_wanted": _result_limit(configuration),
    }
    if criteria.posted_within_days is not None:
        arguments["hours_old"] = criteria.posted_within_days * 24
    if criteria.remote_preference == RemotePreference.REMOTE:
        arguments["is_remote"] = True

    country = configuration.get("country_indeed", _DEFAULT_COUNTRY_INDEED)
    if isinstance(country, str) and country:
        arguments["country_indeed"] = country
    return {name: value for name, value in arguments.items() if value is not None}


def _provider_error_from(exception: Exception) -> ProviderExecutionError | ProviderParsingError:
    """Return a safe provider error for one failed JobSpy source."""

    if isinstance(exception, ProviderParsingError):
        return exception
    return ProviderExecutionError()


def _log_site_failure(site: str, error: ProviderExecutionError | ProviderParsingError) -> None:
    """Record a safe per-site outcome without logging portal content or exception text."""

    logger.warning(
        "jobspy_site_failed",
        extra={"provider_code": JobSpyProvider.code, "site": site, "category": error.category},
    )


def _first_location(criteria: SearchCriteria, configuration: Mapping[str, JsonValue]) -> str | None:
    """Return the first requested location or an optional configured fallback."""

    if criteria.locations:
        return criteria.locations[0]
    configured_location = configuration.get("location")
    if configured_location is None:
        return None
    if not isinstance(configured_location, str):
        raise ProviderConfigurationError("JobSpy location configuration must be text")
    return configured_location


def _result_limit(configuration: Mapping[str, JsonValue]) -> int:
    """Return a conservative, bounded provider result limit."""

    configured_limit = configuration.get("results_wanted", _DEFAULT_RESULT_LIMIT)
    if isinstance(configured_limit, bool) or not isinstance(configured_limit, int):
        raise ProviderConfigurationError("JobSpy results_wanted must be an integer")
    if not 1 <= configured_limit <= _MAX_RESULT_LIMIT:
        raise ProviderConfigurationError(
            f"JobSpy results_wanted must be between 1 and {_MAX_RESULT_LIMIT}"
        )
    return configured_limit


def _normalise_rows(rows: Iterable[Mapping[str, Any]]) -> list[JobCandidate]:
    """Convert JobSpy rows while retaining valid partial provider success."""

    candidates: list[JobCandidate] = []
    received_row = False
    for row in rows:
        received_row = True
        try:
            candidates.append(_normalise_row(row))
        except (TypeError, ValidationError, ValueError):
            continue
    if not candidates and received_row:
        raise ProviderParsingError()
    return candidates


def _normalise_row(row: Mapping[str, Any]) -> JobCandidate:
    """Map one JobSpy row into the provider-neutral job contract."""

    salary_min = _decimal_value(row.get("min_amount"))
    salary_max = _decimal_value(row.get("max_amount"))
    salary_currency = _text_value(row.get("currency"))
    salary_period = _salary_period(row.get("interval"))
    if (salary_min is not None or salary_max is not None) and (
        salary_currency is None or salary_period is None
    ):
        salary_min = None
        salary_max = None
        salary_currency = None
        salary_period = None

    return JobCandidate(
        source=JobSpyProvider.code,
        source_job_id=_text_value(row.get("id")),
        source_url=_source_url(row),
        title=_required_text(row.get("title"), "title"),
        company=_text_value(row.get("company")),
        location=_text_value(row.get("location")),
        workplace_type=_workplace_type(row.get("is_remote")),
        employment_type=_employment_type(row.get("job_type")),
        description=_text_value(row.get("description")),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        salary_period=salary_period,
        published_at=_datetime_value(row.get("date_posted")),
    )


def _source_url(row: Mapping[str, Any]) -> HttpUrl | None:
    """Return JobSpy's direct URL when possible, then its canonical listing URL."""

    source_url = _text_value(row.get("job_url_direct")) or _text_value(row.get("job_url"))
    return HttpUrl(source_url) if source_url else None


def _required_text(value: Any, field_name: str) -> str:
    """Return required provider text or raise a safe parsing error."""

    text = _text_value(value)
    if text is None:
        raise ProviderParsingError(f"JobSpy row is missing {field_name}")
    return text


def _text_value(value: Any) -> str | None:
    """Normalise nullable JobSpy scalars without importing pandas at runtime."""

    if value is None:
        return None
    text = str(value).strip()
    return None if not text or text.casefold() in {"nan", "none", "<na>"} else text


def _decimal_value(value: Any) -> Decimal | None:
    """Convert a provider amount to a non-negative decimal when available."""

    text = _text_value(value)
    if text is None:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return amount if amount >= 0 else None


def _datetime_value(value: Any) -> datetime | None:
    """Convert common JobSpy date/time values into explicit UTC datetimes."""

    if value is None:
        return None
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _workplace_type(value: Any) -> WorkplaceType:
    """Map JobSpy's remote flag to the standard workplace type."""

    return WorkplaceType.REMOTE if value is True else WorkplaceType.UNKNOWN


def _employment_type(value: Any) -> EmploymentType | None:
    """Map common JobSpy employment labels to the standard enum."""

    normalised = (_text_value(value) or "").casefold().replace("-", "_").replace(" ", "_")
    mappings = {
        "full_time": EmploymentType.FULL_TIME,
        "part_time": EmploymentType.PART_TIME,
        "contract": EmploymentType.CONTRACT,
        "temporary": EmploymentType.TEMPORARY,
        "internship": EmploymentType.INTERNSHIP,
    }
    return mappings.get(normalised, EmploymentType.OTHER if normalised else None)


def _salary_period(value: Any) -> SalaryPeriod | None:
    """Map common JobSpy interval labels to the standard salary period."""

    normalised = (_text_value(value) or "").casefold()
    mappings = {
        "hourly": SalaryPeriod.HOUR,
        "hour": SalaryPeriod.HOUR,
        "daily": SalaryPeriod.DAY,
        "day": SalaryPeriod.DAY,
        "monthly": SalaryPeriod.MONTH,
        "month": SalaryPeriod.MONTH,
        "yearly": SalaryPeriod.YEAR,
        "year": SalaryPeriod.YEAR,
        "annual": SalaryPeriod.YEAR,
    }
    return mappings.get(normalised)
