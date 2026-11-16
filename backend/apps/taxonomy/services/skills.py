# Placement: backend/apps/taxonomy/services/skills.py
"""Skill name normalization and lookup for free-text skills (CV extraction, offers).

Tier 1 matching (decision 2026-11-14): a free-text skill links to an existing Skill when,
once normalized (case, accents, spacing), it equals an ESCO preferred label (fr/en/ar,
also without its "(qualifier)") or a local skill's name. SKILL_ALIASES first maps common
variants ("JS" -> "JavaScript"). Fuzzy matching is never used; anything else becomes a
local skill. ESCO itself is loaded by `load_esco_skills` (services/esco.py).
"""

import re
import unicodedata
from typing import Any

from django.db import IntegrityError, transaction

from backend.apps.taxonomy.models import Skill, SkillLabel, SkillLabelKind

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python", "python3", "python 3", "py"),
    "SQL": ("sql", "structured query language"),
    "Docker": ("docker", "conteneurisation", "containerization"),
    "Machine Learning": ("machine learning", "apprentissage automatique", "ml"),
    "Deep Learning": ("deep learning", "apprentissage profond"),
    "Natural Language Processing": (
        "natural language processing",
        "traitement du langage naturel",
        "nlp",
    ),
    "Artificial Intelligence": ("artificial intelligence", "intelligence artificielle", "ai", "ia"),
    "PostgreSQL": ("postgresql", "postgres", "psql"),
    "JavaScript": ("javascript", "js", "java script"),
    "TypeScript": ("typescript", "ts"),
    "React": ("react", "react.js", "reactjs"),
    "Node.js": ("node.js", "nodejs", "node"),
    "Django": ("django",),
    "REST APIs": ("rest api", "api rest", "restful api", "rest apis"),
    "Git": ("git",),
    "GitHub": ("github",),
    "Linux": ("linux",),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "Kubernetes": ("kubernetes", "k8s"),
    "CI/CD": ("ci/cd", "ci cd", "continuous integration", "integration continue"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Java": ("java",),
    "Apache Spark": ("apache spark", "pyspark", "spark"),
    "Excel": ("excel", "microsoft excel"),
    "Power BI": ("power bi", "powerbi"),
    "NumPy": ("numpy",),
    "Pandas": ("pandas",),
    "C#": ("c#", "csharp", "c sharp"),
    "C++": ("c++", "cpp", "c plus plus"),
    "HTML": ("html", "html5"),
    "CSS": ("css", "css3"),
    "MongoDB": ("mongodb", "mongo"),
    "MySQL": ("mysql",),
    "PHP": ("php",),
    "Angular": ("angular", "angularjs"),
    "Vue.js": ("vue", "vue.js", "vuejs"),
    "Spring Boot": ("spring boot", "springboot"),
    "Scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
}


def skill_key(name: str) -> str:
    """Comparison key: case, accents, spacing and edge punctuation do not matter."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", unaccented).strip(" .,;:-")[:255]


def without_qualifier(label: str) -> str:
    """'Python (programmation informatique)' -> 'Python' (ESCO disambiguation qualifiers)."""
    return re.sub(r"\s*\([^)]*\)\s*", " ", label).strip()


_ALIAS_TO_CANONICAL = {
    skill_key(alias): canonical
    for canonical, aliases in SKILL_ALIASES.items()
    for alias in (*aliases, canonical)
}

# Labels that link free text to a skill on their own (tier 1). ESCO alternative labels
# are excluded: some are narrower examples ("Git" under a broad configuration-tools skill).
LINKING_KINDS = (SkillLabelKind.PREFERRED, SkillLabelKind.LOCAL)


def canonical_skill_name(name: str) -> str:
    """The display name to store: the alias table's canonical form, else the trimmed input."""
    cleaned = re.sub(r"\s+", " ", name).strip(" .,;:-")
    return _ALIAS_TO_CANONICAL.get(skill_key(cleaned), cleaned)


def find_skill(name: str) -> Skill | None:
    """Tier 1: the Skill whose ESCO preferred label or local name equals `name` once
    normalized (aliases applied first). Ambiguous names link to nothing."""
    wanted = skill_key(canonical_skill_name(name))
    if not wanted:
        return None
    labelled = (
        SkillLabel.objects.filter(key=wanted, kind__in=LINKING_KINDS)
        .values_list("skill_id", "kind")
        .distinct()
    )
    by_skill: dict[Any, set[str]] = {}
    for skill_id, kind in labelled:
        by_skill.setdefault(skill_id, set()).add(kind)
    if len(by_skill) > 1:  # prefer a skill known locally under this exact name
        local = [skill_id for skill_id, kinds in by_skill.items() if SkillLabelKind.LOCAL in kinds]
        by_skill = {local[0]: {SkillLabelKind.LOCAL}} if len(local) == 1 else {}
    if len(by_skill) == 1:
        return Skill.objects.get(pk=next(iter(by_skill)))
    if labelled:
        return None  # ambiguous: several ESCO skills share this name
    # Skills created outside this service (admin, evaluation data) may have no label yet.
    for skill in Skill.objects.filter(esco_uri__isnull=True).only("id", "canonical_name"):
        if skill_key(skill.canonical_name) == wanted:
            return skill
    return None


def get_or_create_skill(name: str, category: str = "") -> Skill:
    """Find the Skill for `name` (tier 1) or create a local one (CV extraction, after confirmation)."""
    existing = find_skill(name)
    if existing is not None:
        return existing
    canonical = canonical_skill_name(name)[:150]
    if not canonical:
        raise ValueError("A skill needs a name.")
    try:
        with transaction.atomic():
            skill = Skill.objects.create(canonical_name=canonical, category=category[:100])
            add_local_label(skill)
            return skill
    except IntegrityError:  # created concurrently, or the name is taken by an ESCO skill
        return Skill.objects.get(canonical_name=canonical)


def add_local_label(skill: Skill) -> None:
    key = skill_key(skill.canonical_name)
    if key:
        SkillLabel.objects.get_or_create(
            skill=skill,
            key=key,
            kind=SkillLabelKind.LOCAL,
            defaults={"label": skill.canonical_name[:255]},
        )
