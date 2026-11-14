# Placement: backend/apps/taxonomy/services/skills.py
"""Skill name normalization and lookup for free-text skills (CV extraction).

One canonical Skill row per real skill: "JS", "javascript" and "Java Script" all
resolve to "JavaScript". Known aliases come from SKILL_ALIASES (same display names
as the evaluation vocabulary); any other name is matched case- and
accent-insensitively against existing canonical names before a new row is made.
"""

import re
import unicodedata

from django.db import IntegrityError, transaction

from backend.apps.taxonomy.models import Skill

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
    """Comparison key: case, accents and spacing do not matter."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", unaccented).strip(" .,;:-")


_ALIAS_TO_CANONICAL = {
    skill_key(alias): canonical
    for canonical, aliases in SKILL_ALIASES.items()
    for alias in (*aliases, canonical)
}


def canonical_skill_name(name: str) -> str:
    """The display name to store: the alias table's canonical form, else the trimmed input."""
    cleaned = re.sub(r"\s+", " ", name).strip(" .,;:-")
    return _ALIAS_TO_CANONICAL.get(skill_key(cleaned), cleaned)


def find_skill(name: str) -> Skill | None:
    """The existing Skill for a free-text name (alias- and case-insensitive), if any."""
    wanted = skill_key(canonical_skill_name(name))
    if not wanted:
        return None
    for skill in Skill.objects.only("id", "canonical_name"):
        if skill_key(skill.canonical_name) == wanted:
            return skill
    return None


def get_or_create_skill(name: str, category: str = "") -> Skill:
    """Find the canonical Skill for `name` or create it (CV extraction, after confirmation)."""
    existing = find_skill(name)
    if existing is not None:
        return existing
    canonical = canonical_skill_name(name)[:150]
    if not canonical:
        raise ValueError("A skill needs a name.")
    try:
        with transaction.atomic():
            return Skill.objects.create(canonical_name=canonical, category=category[:100])
    except IntegrityError:  # created concurrently with the same name
        return Skill.objects.get(canonical_name=canonical)
