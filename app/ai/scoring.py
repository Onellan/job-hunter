"""Small deterministic job scorer that never sends user or job data off-device."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.models.job import JobRecord, WorkplaceType
from app.models.scoring import JobScore, ScoringProfile
from app.models.search import RemotePreference

_ROLE_WEIGHT = 20
_SKILL_WEIGHT = 25
_SALARY_WEIGHT = 15
_REMOTE_WEIGHT = 10
_LEADERSHIP_WEIGHT = 7
_EXPERIENCE_WEIGHT = 5
_PROJECT_MANAGEMENT_WEIGHT = 6
_BUSINESS_ANALYSIS_WEIGHT = 6
_AGILE_WEIGHT = 6
_EXPERIENCE_PATTERN = re.compile(r"\b(\d{1,2})\s*\+?\s+years?\b", re.IGNORECASE)


@dataclass(frozen=True)
class _Criterion:
    """One score contribution with an available weight and human-readable result."""

    weight: int
    earned: float
    available: bool
    reason: str


class DeterministicJobScorer:
    """Score normalised jobs with transparent local keyword and value comparisons."""

    def score(self, job: JobRecord, profile: ScoringProfile) -> JobScore:
        """Return a bounded score, data confidence, matches, gaps, and concise reasons."""

        text = _job_text(job)
        criteria: list[_Criterion] = []
        matched_skills = _matches(profile.skills, text)
        missing_skills = _missing(profile.skills, matched_skills)
        criteria.extend(
            (
                _role_criterion(profile, job, text),
                _skill_criterion(profile, matched_skills, missing_skills),
                _salary_criterion(profile, job),
                _remote_criterion(profile, job),
                _keyword_criterion(profile.leadership, text, _LEADERSHIP_WEIGHT, "leadership"),
                _experience_criterion(profile, text),
                _keyword_criterion(
                    profile.project_management,
                    text,
                    _PROJECT_MANAGEMENT_WEIGHT,
                    "project management",
                ),
                _keyword_criterion(
                    profile.business_analysis,
                    text,
                    _BUSINESS_ANALYSIS_WEIGHT,
                    "business analysis",
                ),
                _keyword_criterion(profile.agile, text, _AGILE_WEIGHT, "agile delivery"),
            )
        )
        active = [criterion for criterion in criteria if criterion.weight]
        if not active:
            return JobScore(
                score=0,
                confidence=0,
                reasons=["Configure scoring preferences to calculate a match score."],
            )
        total_weight = sum(criterion.weight for criterion in active)
        earned = sum(criterion.earned for criterion in active)
        available_weight = sum(criterion.weight for criterion in active if criterion.available)
        return JobScore(
            score=round(earned / total_weight * 100),
            confidence=round(available_weight / total_weight * 100),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            reasons=[criterion.reason for criterion in active],
        )


def _role_criterion(profile: ScoringProfile, job: JobRecord, text: str) -> _Criterion:
    """Score target-role matches primarily against the compact job title."""

    if not profile.target_roles:
        return _disabled_criterion()
    matched_roles = _matches(profile.target_roles, job.title.casefold())
    if matched_roles:
        return _Criterion(
            _ROLE_WEIGHT, _ROLE_WEIGHT, True, f"Matches target role: {matched_roles[0]}."
        )
    title_available = bool(job.title.strip())
    return _Criterion(_ROLE_WEIGHT, 0, title_available, "Does not match a configured target role.")


def _skill_criterion(
    profile: ScoringProfile,
    matched_skills: list[str],
    missing_skills: list[str],
) -> _Criterion:
    """Award proportional skill points and make unfulfilled skills visible."""

    if not profile.skills:
        return _disabled_criterion()
    ratio = len(matched_skills) / len(profile.skills)
    if matched_skills:
        reason = f"Matches {len(matched_skills)} of {len(profile.skills)} configured skills."
    else:
        reason = "Does not mention configured skills."
    return _Criterion(_SKILL_WEIGHT, _SKILL_WEIGHT * ratio, True, reason)


def _salary_criterion(profile: ScoringProfile, job: JobRecord) -> _Criterion:
    """Compare disclosed salary data to an explicitly configured minimum only."""

    if profile.minimum_salary is None:
        return _disabled_criterion()
    salary = job.salary_max or job.salary_min
    if salary is None:
        return _Criterion(_SALARY_WEIGHT, 0, False, "Salary is not disclosed.")
    if salary >= profile.minimum_salary:
        return _Criterion(
            _SALARY_WEIGHT, _SALARY_WEIGHT, True, "Disclosed salary meets your minimum."
        )
    return _Criterion(_SALARY_WEIGHT, 0, True, "Disclosed salary is below your minimum.")


def _remote_criterion(profile: ScoringProfile, job: JobRecord) -> _Criterion:
    """Score remote/on-site/hybrid preference only when the user sets one."""

    if profile.remote_preference == RemotePreference.ANY:
        return _disabled_criterion()
    desired = {
        RemotePreference.REMOTE: WorkplaceType.REMOTE,
        RemotePreference.HYBRID: WorkplaceType.HYBRID,
        RemotePreference.ON_SITE: WorkplaceType.ON_SITE,
    }[profile.remote_preference]
    if job.workplace_type == WorkplaceType.UNKNOWN:
        return _Criterion(_REMOTE_WEIGHT, 0, False, "Workplace arrangement is not disclosed.")
    if job.workplace_type == desired:
        return _Criterion(
            _REMOTE_WEIGHT, _REMOTE_WEIGHT, True, "Matches your workplace preference."
        )
    return _Criterion(_REMOTE_WEIGHT, 0, True, "Does not match your workplace preference.")


def _experience_criterion(profile: ScoringProfile, text: str) -> _Criterion:
    """Compare explicit years-of-experience language to a configured minimum."""

    if profile.minimum_experience_years is None:
        return _disabled_criterion()
    years = [int(value) for value in _EXPERIENCE_PATTERN.findall(text)]
    if not years:
        return _Criterion(
            _EXPERIENCE_WEIGHT, 0, False, "Required experience is not stated clearly."
        )
    if max(years) <= profile.minimum_experience_years:
        return _Criterion(
            _EXPERIENCE_WEIGHT,
            _EXPERIENCE_WEIGHT,
            True,
            "Experience requirement fits your profile.",
        )
    return _Criterion(_EXPERIENCE_WEIGHT, 0, True, "Experience requirement exceeds your profile.")


def _keyword_criterion(enabled: bool, text: str, weight: int, label: str) -> _Criterion:
    """Score a configured capability through concise, explainable keyword groups."""

    if not enabled:
        return _disabled_criterion()
    terms = {
        "leadership": ("lead", "leadership", "mentor", "manage", "manager"),
        "project management": ("project management", "project manager", "delivery"),
        "business analysis": ("business analysis", "business analyst", "requirements gathering"),
        "agile delivery": ("agile", "scrum", "kanban"),
    }[label]
    if any(_contains_term(text, term) for term in terms):
        return _Criterion(weight, weight, True, f"Mentions {label}.")
    return _Criterion(weight, 0, True, f"Does not mention {label}.")


def _disabled_criterion() -> _Criterion:
    """Return a zero-weight criterion for an unset user preference."""

    return _Criterion(0, 0, False, "")


def _job_text(job: JobRecord) -> str:
    """Join small job fields for local matching without retaining an extra copy."""

    return " ".join(filter(None, (job.title, job.description, job.company))).casefold()


def _matches(values: Iterable[str], text: str) -> list[str]:
    """Return configured values that occur as case-insensitive standalone terms."""

    return [value for value in values if _contains_term(text, value)]


def _missing(values: Iterable[str], matches: Iterable[str]) -> list[str]:
    """Return configured values absent from the matched skill set in input order."""

    matched = {value.casefold() for value in matches}
    return [value for value in values if value.casefold() not in matched]


def _contains_term(text: str, value: str) -> bool:
    """Match a configured phrase at word boundaries while supporting symbols such as C++."""

    return bool(re.search(rf"(?<!\w){re.escape(value.casefold())}(?!\w)", text))
