"""Bounded local extraction of broadly recognisable technology and role skills."""

from __future__ import annotations

import re

_KNOWN_SKILLS = (
    "agile",
    "aws",
    "azure",
    "business analysis",
    "c#",
    "docker",
    "fastapi",
    "git",
    "java",
    "javascript",
    "kubernetes",
    "leadership",
    "linux",
    "machine learning",
    "power bi",
    "product management",
    "project management",
    "python",
    "react",
    "scrum",
    "sql",
    "tableau",
    "typescript",
)
_MAX_SKILLS = 80


def extract_skills(text: str, additional_skills: list[str] | None = None) -> list[str]:
    """Extract a stable, bounded set of known and configured skills from plain text."""

    candidates = {skill.casefold() for skill in (*_KNOWN_SKILLS, *(additional_skills or []))}
    normalized = text.casefold()
    return sorted(skill for skill in candidates if _contains_skill(normalized, skill.casefold()))[
        :_MAX_SKILLS
    ]


def _contains_skill(text: str, skill: str) -> bool:
    """Match words and punctuation-bearing skills without accidental substrings."""

    return re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", text) is not None
