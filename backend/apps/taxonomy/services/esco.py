# Placement: backend/apps/taxonomy/services/esco.py
"""Load the ESCO skills extract (data/reference/esco) into skills + skill_labels.

Idempotent. Steps, in one transaction:
1. Existing local skills whose name matches exactly one ESCO preferred label (tier 1,
   fr/en/ar, also without the "(qualifier)") are linked to it; their name is kept.
2. Missing ESCO skills are created, named after the French preferred label.
3. ESCO metadata (type, reuse level, digital flag) and ESCO labels are refreshed.
4. Every local skill (linked or not) gets a LOCAL label: found by name, kept in lists.

ESCO is the European Commission's classification, reused under Commission Decision
2011/833/EU; the extract is a trimmed (modified) version. See data/reference/esco/README.md.
"""

from __future__ import annotations

import csv
import gzip
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction

from backend.apps.taxonomy.models import Skill, SkillLabel, SkillLabelKind
from backend.apps.taxonomy.services.skills import add_local_label, skill_key, without_qualifier

LANGUAGES = ("fr", "en", "ar")
DEFAULT_EXTRACT = (
    Path(settings.BASE_DIR) / "data" / "reference" / "esco" / "esco_skills_v1.2.1.csv.gz"
)
BATCH = 5000


@dataclass
class LoadReport:
    created: int = 0
    linked_local: list[tuple[str, str]] = field(default_factory=list)  # (local name, ESCO label)
    labels: int = 0
    esco_total: int = 0


def read_extract(path: Path = DEFAULT_EXTRACT) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _preferred_keys(row: dict[str, str]) -> set[str]:
    keys: set[str] = set()
    for lang in LANGUAGES:
        label = row.get(f"preferred_{lang}", "")
        if label:
            keys.update(k for k in (skill_key(label), skill_key(without_qualifier(label))) if k)
    return keys


@transaction.atomic
def load_esco(rows: list[dict[str, str]]) -> LoadReport:
    report = LoadReport(esco_total=len(rows))
    by_uri = {row["uri"]: row for row in rows}
    linked: dict[str, Skill] = {
        skill.esco_uri: skill
        for skill in Skill.objects.filter(esco_uri__in=list(by_uri))
        if skill.esco_uri
    }

    # 1. Link local skills whose name is exactly one ESCO preferred label.
    uris_by_key: dict[str, set[str]] = defaultdict(set)
    for uri, row in by_uri.items():
        for key in _preferred_keys(row):
            uris_by_key[key].add(uri)
    for skill in Skill.objects.filter(esco_uri__isnull=True):
        uris = uris_by_key.get(skill_key(skill.canonical_name), set())
        if len(uris) == 1:
            uri = next(iter(uris))
            if uri not in linked:
                skill.esco_uri = uri
                skill.save(update_fields=["esco_uri", "updated_at"])
                linked[uri] = skill
                report.linked_local.append((skill.canonical_name, by_uri[uri]["preferred_fr"]))

    # 2. Create the ESCO skills not in the table yet.
    taken = set(Skill.objects.values_list("canonical_name", flat=True))
    new_skills = []
    for uri, row in by_uri.items():
        if uri in linked:
            continue
        name = _free_name(row, taken)
        taken.add(name)
        new_skills.append(Skill(canonical_name=name, esco_uri=uri))
    Skill.objects.bulk_create(new_skills, batch_size=BATCH)
    report.created = len(new_skills)
    linked.update(
        {
            skill.esco_uri: skill
            for skill in Skill.objects.filter(esco_uri__in=[s.esco_uri for s in new_skills])
            if skill.esco_uri
        }
    )

    # 3. Metadata and ESCO labels.
    to_update = []
    for uri, skill in linked.items():
        row = by_uri[uri]
        skill.esco_skill_type = row["skill_type"][:30]
        skill.esco_reuse_level = row["reuse_level"][:30]
        skill.is_digital = row["digital"] == "1"
        to_update.append(skill)
    Skill.objects.bulk_update(
        to_update, ["esco_skill_type", "esco_reuse_level", "is_digital"], batch_size=BATCH
    )
    SkillLabel.objects.filter(
        skill__esco_uri__isnull=False,
        kind__in=(SkillLabelKind.PREFERRED, SkillLabelKind.ALTERNATIVE),
    ).delete()
    labels: dict[tuple[object, str, str], SkillLabel] = {}
    for uri, skill in linked.items():
        row = by_uri[uri]
        for lang in LANGUAGES:
            preferred = row.get(f"preferred_{lang}", "")
            for label in dict.fromkeys(x for x in (preferred, without_qualifier(preferred)) if x):
                _add(labels, skill, label, lang, SkillLabelKind.PREFERRED)
            for label in (row.get(f"alternatives_{lang}") or "").split("\n"):
                if label.strip():
                    _add(labels, skill, label.strip(), lang, SkillLabelKind.ALTERNATIVE)
    SkillLabel.objects.bulk_create(labels.values(), batch_size=BATCH)
    report.labels = len(labels)

    # 4. Local skills, including the ones just linked, keep a LOCAL label: they stay
    # findable by their own name and stay in the working catalogue.
    linked_now = {name for name, _ in report.linked_local}
    for skill in Skill.objects.exclude(labels__kind=SkillLabelKind.LOCAL):
        if skill.esco_uri is None or skill.canonical_name in linked_now:
            add_local_label(skill)
    return report


def _add(
    labels: dict[tuple[object, str, str], SkillLabel],
    skill: Skill,
    label: str,
    language: str,
    kind: str,
) -> None:
    key = skill_key(label)
    if key and (skill.pk, key, kind) not in labels:
        labels[(skill.pk, key, kind)] = SkillLabel(
            skill=skill, label=label[:255], key=key, language=language, kind=kind
        )


def _free_name(row: dict[str, str], taken: set[str]) -> str:
    """French preferred label; disambiguated when another skill already has that name."""
    french = row["preferred_fr"] or row["preferred_en"]
    for candidate in (
        french,
        f"{french} ({row['preferred_en']})",
        f"{french} [{row['uri'].rsplit('/', 1)[-1][:8]}]",
    ):
        if candidate[:150] not in taken:
            return candidate[:150]
    return f"{french[:140]} [{row['uri'].rsplit('/', 1)[-1]}]"[:150]
