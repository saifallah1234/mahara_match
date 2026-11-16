# Placement: ai/document_intelligence/ats/profiles.py
"""Role profiles and level tables for ATS analysis, loaded from the YAML files beside this module.

A malformed file raises RoleProfileError on first use, so a typo can never silently zero a score.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

ROLES_DIR = Path(__file__).with_name("roles")
LEVELS_FILE = Path(__file__).with_name("levels.yaml")
TIER_WEIGHTS = {"core": 3, "common": 2, "bonus": 1}
COMPONENTS = ("parseability", "sections", "skill_coverage", "evidence", "content", "length")
SECTIONS = ("summary", "experience", "projects", "skills", "education", "certifications")


class RoleProfileError(ValueError):
    pass


@dataclass(frozen=True)
class Skill:
    name: str
    tier: str
    terms: tuple[str, ...]  # name first, then aliases


@dataclass(frozen=True)
class MetricHint:
    label: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class RoleProfile:
    id: str
    label: str
    version: str
    skills: tuple[Skill, ...]
    action_verbs: frozenset[str]
    metric_hints: tuple[MetricHint, ...]
    weak_phrases: tuple[str, ...]
    section_priority: tuple[str, ...]
    examples: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class LevelConfig:
    id: str
    label: str
    weights: dict[str, float]
    required_sections: tuple[str, ...]
    max_pages: int
    strict_page_limit: bool
    metric_weight: float


def _strings(value: Any, where: str, *, allowed: tuple[str, ...] | None = None) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RoleProfileError(f"{where} must be a non-empty list.")
    items = tuple(str(item).strip() for item in value)
    if not all(items) or (allowed and not set(items) <= set(allowed)):
        raise RoleProfileError(f"{where} has empty or unknown entries: {value!r}")
    return items


def _role(path: Path) -> RoleProfile:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        skills = tuple(
            Skill(
                name=str(entry["name"]),
                tier=tier,
                terms=(str(entry["name"]), *map(str, entry.get("aliases") or [])),
            )
            for tier in TIER_WEIGHTS
            for entry in raw["skills"][tier]
        )
        role = RoleProfile(
            id=str(raw["id"]),
            label=str(raw["label"]),
            version=str(raw["version"]),
            skills=skills,
            action_verbs=frozenset(
                verb.casefold() for verb in _strings(raw["action_verbs"], "action_verbs")
            ),
            metric_hints=tuple(
                MetricHint(str(hint["label"]), _strings(hint["keywords"], "metric keywords"))
                for hint in raw["metric_hints"]
            ),
            weak_phrases=_strings(raw["weak_phrases"], "weak_phrases"),
            section_priority=_strings(
                raw["section_priority"], "section_priority", allowed=SECTIONS
            ),
            examples=tuple(
                (str(example["before"]), str(example["after"])) for example in raw["examples"]
            ),
        )
    except RoleProfileError as exc:
        raise RoleProfileError(f"{path.name}: {exc}") from exc
    except (yaml.YAMLError, KeyError, TypeError, AttributeError) as exc:
        raise RoleProfileError(f"{path.name}: malformed role profile ({exc!r}).") from exc
    if role.id != path.stem:
        raise RoleProfileError(f"{path.name}: id {role.id!r} does not match the file name.")
    if not role.metric_hints or not 3 <= len(role.examples) <= 5:
        raise RoleProfileError(f"{path.name}: needs metric hints and 3 to 5 examples.")
    if not all(any(skill.tier == tier for skill in skills) for tier in TIER_WEIGHTS):
        raise RoleProfileError(f"{path.name}: every skill tier needs at least one skill.")
    return role


def load_roles(directory: Path = ROLES_DIR) -> dict[str, RoleProfile]:
    roles = {path.stem: _role(path) for path in sorted(directory.glob("*.yaml"))}
    if not roles:
        raise RoleProfileError(f"No role profiles in {directory}.")
    return roles


def load_levels(path: Path = LEVELS_FILE) -> dict[str, LevelConfig]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))["levels"]
        levels = {
            level_id: LevelConfig(
                id=level_id,
                label=str(entry["label"]),
                weights={name: float(entry["weights"][name]) for name in COMPONENTS},
                required_sections=_strings(
                    entry["required_sections"], "required_sections", allowed=SECTIONS
                ),
                max_pages=int(entry["max_pages"]),
                strict_page_limit=bool(entry["strict_page_limit"]),
                metric_weight=float(entry["metric_weight"]),
            )
            for level_id, entry in raw.items()
        }
    except (yaml.YAMLError, KeyError, TypeError, AttributeError, ValueError) as exc:
        raise RoleProfileError(f"{path.name}: malformed level table ({exc!r}).") from exc
    if any(sum(level.weights.values()) <= 0 for level in levels.values()):
        raise RoleProfileError(f"{path.name}: weights must sum to more than zero.")
    return levels


@cache
def roles() -> dict[str, RoleProfile]:
    return load_roles()


@cache
def levels() -> dict[str, LevelConfig]:
    return load_levels()
