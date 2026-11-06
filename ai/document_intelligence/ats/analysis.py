# Placement: ai/document_intelligence/ats/analysis.py
"""Deterministic ATS analysis of one CV against a role profile and a level (Q26 v1 formula).

Pure Python: bytes in, plain data out. Issue messages are French templates filled with role
profile data (the UI is French; CV content and role data stay English), never model text.
"""

import re
from dataclasses import dataclass, replace
from typing import Any

from rapidfuzz import fuzz, process

from ai.document_intelligence.ats.profiles import (
    TIER_WEIGHTS,
    LevelConfig,
    RoleProfile,
    Skill,
    levels,
    roles,
)
from ai.document_intelligence.parsing.cv_reader import CVText, contacts, read_cv
from ai.document_intelligence.parsing.section_extraction import (
    PARSER_VERSION,
    ChatModel,
    extract_structure,
)
from pipelines.ingestion.language_detection import detect_language_code

READINESS = ("parseability", "sections", "content", "length")
FIT = ("skill_coverage", "evidence")
FORMAT_PENALTIES = {
    "multi_column": 25,
    "tables": 20,
    "text_boxes": 20,
    "images": 10,
    "unusual_fonts": 10,
}
CONTACT_PENALTIES = {"email": 10, "phone": 5}
NUMBER = re.compile(r"\d")
SECTION_LABELS = {
    "summary": "Summary",
    "experience": "Experience",
    "projects": "Projects",
    "skills": "Skills",
    "education": "Education",
    "certifications": "Certifications",
}


class CVReviewError(ValueError):
    """The CV, role or level cannot be analysed; the message is safe to show."""


@dataclass(frozen=True)
class AtsResult:
    role: RoleProfile
    level: LevelConfig
    overall_score: float
    breakdown: dict[str, Any]
    issues: list[dict[str, Any]]
    parsed: dict[str, Any] | None = None  # section structure to cache on the CV; None for a scan


def analyze_cv(
    content: bytes,
    role_id: str,
    level_id: str,
    *,
    model: ChatModel | None = None,
    cached: dict[str, Any] | None = None,
) -> AtsResult:
    """Score a CV; `model` structures sections, `cached` (same document) skips that step."""
    role, level = roles().get(role_id), levels().get(level_id)
    if role is None:
        raise CVReviewError(f"Unknown role {role_id!r}.")
    if level is None:
        raise CVReviewError(f"Unknown level {level_id!r}.")
    try:
        cv = read_cv(content)
    except ValueError as exc:
        raise CVReviewError(str(exc)) from exc
    if cv.has_text_layer and detect_language_code(cv.text) != "en":
        raise CVReviewError("Only English CVs can be analysed for now.")
    if not cv.has_text_layer:
        return _score(cv, role, level)
    if cached is not None and cached.get("parser_version") == PARSER_VERSION:
        parsed = cached
    else:
        parsed = extract_structure(cv.sections, model)
    cv.bullets = [
        bullet
        for key in ("experience", "projects")
        for entry in parsed["sections"].get(key, [])
        for bullet in entry["bullets"]
    ]
    result = _score(cv, role, level)
    result.breakdown["parse_degraded"] = parsed["degraded"]
    return replace(result, parsed=parsed)


def _issue(code: str, severity: str, component: str, message: str, **params: Any) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "component": component,
        "message": message,
        "params": params,
    }


def _term_pattern(term: str) -> re.Pattern[str]:
    flags = 0 if len(term) <= 2 else re.IGNORECASE  # "Go" the language, not "go" the verb
    return re.compile(rf"(?<![\w+#.]){re.escape(term)}(?![\w+#])", flags)


def _mentions(skill: Skill, text: str, words: list[str]) -> bool:
    if any(_term_pattern(term).search(text) for term in skill.terms):
        return True
    for term in skill.terms:  # fuzzy only for long terms: short ones collide too easily
        size = len(term.split())
        if len(term) >= 6 and len(words) >= size:
            grams = [" ".join(words[i : i + size]) for i in range(len(words) - size + 1)]
            if process.extractOne(
                term.casefold(), grams, scorer=fuzz.ratio, score_cutoff=90, processor=str.casefold
            ):
                return True
    return False


def _words(text: str) -> list[str]:
    return re.findall(r"[\w+#./-]+", text)


def _has_metric(bullet: str, role: RoleProfile) -> bool:
    if not NUMBER.search(bullet):
        return False
    lowered = bullet.casefold()
    return any(
        keyword.casefold() in lowered for hint in role.metric_hints for keyword in hint.keywords
    )


def _score(cv: CVText, role: RoleProfile, level: LevelConfig) -> AtsResult:
    issues: list[dict[str, Any]] = []
    found = contacts(cv.text)
    words = _words(cv.text)
    sections = [key for key in cv.sections if key in SECTION_LABELS and key != "header"]

    # Parseability and format
    if not cv.has_text_layer:
        parseability = 0.0
        issues.append(
            _issue(
                "no_text_layer",
                "high",
                "parseability",
                "Le PDF ne contient pas de texte lisible (document scanné) : un ATS ne peut pas "
                "le lire. Exportez votre CV depuis un traitement de texte.",
            )
        )
    else:
        parseability = 100.0 - sum(FORMAT_PENALTIES[risk] for risk in cv.format_risks)
        format_messages = {
            "multi_column": "Mise en page sur plusieurs colonnes : un ATS peut mélanger "
            "l'ordre du texte. Utilisez une seule colonne.",
            "tables": "Tableaux détectés : leur contenu est souvent mal lu par les ATS.",
            "text_boxes": "Zones de texte détectées : leur contenu est souvent ignoré par les ATS.",
            "images": "Images ou icônes détectées : un ATS ne les lit pas ; gardez le texte seul.",
            "unusual_fonts": "Polices inhabituelles ({fonts}) : préférez Arial, Calibri ou "
            "Times New Roman.",
        }
        for risk, details in cv.format_risks.items():
            issues.append(
                _issue(
                    risk,
                    "medium",
                    "parseability",
                    format_messages[risk].format(fonts=", ".join(details)),
                    details=details,
                )
            )
        if not found["emails"]:
            parseability -= CONTACT_PENALTIES["email"]
            issues.append(
                _issue("missing_email", "high", "parseability", "Aucune adresse e-mail trouvée.")
            )
        if not found["phones"]:
            parseability -= CONTACT_PENALTIES["phone"]
            issues.append(
                _issue(
                    "missing_phone", "medium", "parseability", "Aucun numéro de téléphone trouvé."
                )
            )
        if not found["links"]:
            issues.append(
                _issue(
                    "missing_links",
                    "low",
                    "parseability",
                    "Aucun lien trouvé : ajoutez votre profil LinkedIn ou GitHub.",
                )
            )
        parseability = max(parseability, 0.0)

    # Sections: completeness (80%) and order (20%)
    missing = [key for key in level.required_sections if key not in sections]
    ordered = [key for key in sections if key in role.section_priority]
    expected = sorted(ordered, key=role.section_priority.index)
    order_ok = ordered == expected
    sections_score = 0.0
    if cv.has_text_layer:
        sections_score = 80.0 * (1 - len(missing) / len(level.required_sections)) + (
            20.0 if order_ok else 0.0
        )
    if cv.has_text_layer and missing:
        issues.append(
            _issue(
                "missing_sections",
                "high",
                "sections",
                f"Sections manquantes pour {role.label} ({level.label}) : "
                + ", ".join(SECTION_LABELS[key] for key in missing)
                + ".",
                sections=missing,
            )
        )
    if not order_ok:
        issues.append(
            _issue(
                "section_order",
                "low",
                "sections",
                f"Ordre recommandé des sections pour {role.label} : "
                + ", ".join(SECTION_LABELS[key] for key in role.section_priority)
                + ".",
                expected=list(role.section_priority),
            )
        )

    # Role skill coverage: tier weight x evidence (listed only 0.5, used in a bullet 1.0)
    bullet_text = "\n".join(cv.bullets)
    bullet_words = _words(bullet_text)
    skill_rows: list[dict[str, Any]] = []
    for skill in role.skills:
        if _mentions(skill, bullet_text, bullet_words):
            evidence = 1.0
        elif _mentions(skill, cv.text, words):
            evidence = 0.5
        else:
            evidence = 0.0
        skill_rows.append({"name": skill.name, "tier": skill.tier, "evidence": evidence})
    earned = sum(TIER_WEIGHTS[row["tier"]] * row["evidence"] for row in skill_rows)
    skill_coverage = 100.0 * earned / sum(TIER_WEIGHTS[skill.tier] for skill in role.skills)
    missing_core = [
        row["name"] for row in skill_rows if row["tier"] == "core" and not row["evidence"]
    ]
    missing_common = [
        row["name"] for row in skill_rows if row["tier"] == "common" and not row["evidence"]
    ]
    listed_only = [row["name"] for row in skill_rows if row["evidence"] == 0.5]
    if cv.has_text_layer and missing_core:
        issues.append(
            _issue(
                "missing_core_skills",
                "high",
                "skill_coverage",
                f"Compétences clés manquantes pour {role.label} : {', '.join(missing_core)}.",
                skills=missing_core,
            )
        )
    if cv.has_text_layer and missing_common:
        issues.append(
            _issue(
                "missing_common_skills",
                "low",
                "skill_coverage",
                f"Compétences courantes pour {role.label} absentes : {', '.join(missing_common)}.",
                skills=missing_common,
            )
        )
    if listed_only:
        issues.append(
            _issue(
                "skills_without_evidence",
                "medium",
                "skill_coverage",
                "Compétences citées mais jamais utilisées dans une expérience ou un projet : "
                f"{', '.join(listed_only)}. Montrez-les dans une puce.",
                skills=listed_only,
            )
        )

    # Bullets: evidence quality and content quality
    total = len(cv.bullets)
    with_verb = [
        b
        for b in cv.bullets
        if (b.split() or [""])[0].casefold().strip(",.:;") in role.action_verbs
    ]
    with_metric = [b for b in cv.bullets if _has_metric(b, role)]
    with_skill = [b for b in cv.bullets if any(_mentions(s, b, _words(b)) for s in role.skills)]
    weak_counts = {
        phrase: sum(phrase in b.casefold() for b in cv.bullets) for phrase in role.weak_phrases
    }
    weak_bullets = [b for b in cv.bullets if any(p in b.casefold() for p in role.weak_phrases)]
    strong = sum(
        (1.0 if b in with_metric else 1 - level.metric_weight)
        for b in cv.bullets
        if b in with_verb and b in with_skill
    )
    evidence = 100.0 * strong / total if total else 0.0
    if total:
        verb_share, metric_share = len(with_verb) / total, len(with_metric) / total
        weak_free = 1 - len(weak_bullets) / total
        metric_part = 0.4 * level.metric_weight
        content = (
            100.0
            * (0.4 * verb_share + metric_part * metric_share + 0.2 * weak_free)
            / (0.6 + metric_part)
        )
    else:
        content = 0.0
    if cv.has_text_layer and not total:
        issues.append(
            _issue(
                "no_bullets",
                "high",
                "evidence",
                "Aucune puce d'expérience ou de projet détectée : décrivez vos réalisations "
                "sous forme de puces.",
            )
        )
    verbs_hint = ", ".join(sorted(role.action_verbs)[:6])
    if total and len(with_verb) < total:
        issues.append(
            _issue(
                "bullets_without_verb",
                "medium",
                "content",
                f"{total - len(with_verb)} puce(s) sur {total} ne commencent pas par un verbe "
                f"d'action (ex. : {verbs_hint}).",
                count=total - len(with_verb),
                total=total,
            )
        )
    if total and len(with_metric) < total:
        hints = ", ".join(hint.label for hint in role.metric_hints)
        issues.append(
            _issue(
                "bullets_without_metric",
                "medium",
                "content",
                f"{total - len(with_metric)} puce(s) sur {total} n'ont pas de chiffre ; pour "
                f"{role.label}, ajoutez par exemple : {hints}.",
                count=total - len(with_metric),
                total=total,
                hints=[hint.label for hint in role.metric_hints],
            )
        )
    if total and len(with_skill) < total:
        issues.append(
            _issue(
                "bullets_without_skill",
                "low",
                "evidence",
                f"{total - len(with_skill)} puce(s) sur {total} ne citent aucune compétence "
                f"du métier {role.label}.",
                count=total - len(with_skill),
                total=total,
            )
        )
    if weak := {phrase: count for phrase, count in weak_counts.items() if count}:
        issues.append(
            _issue(
                "weak_phrases",
                "medium",
                "content",
                "Expressions faibles : "
                + ", ".join(f"« {phrase} » ({count})" for phrase, count in weak.items())
                + ". Remplacez-les par un verbe d'action.",
                phrases=weak,
            )
        )

    # Length and readability
    length = 0.0
    if cv.has_text_layer:
        extra = cv.page_count - level.max_pages
        length = (
            100.0 if extra <= 0 else 0.0 if level.strict_page_limit else max(0.0, 100 - 50 * extra)
        )
        if extra > 0:
            issues.append(
                _issue(
                    "too_long",
                    "high" if level.strict_page_limit else "medium",
                    "length",
                    f"Le CV fait {cv.page_count} pages ; pour le niveau {level.label}, "
                    f"limitez-le à {level.max_pages} page(s).",
                    pages=cv.page_count,
                    max_pages=level.max_pages,
                )
            )
        if len(words) < 150:
            length = min(length, 50.0)
            issues.append(
                _issue(
                    "too_short",
                    "medium",
                    "length",
                    f"Le CV est très court ({len(words)} mots) : détaillez vos expériences "
                    "et projets.",
                    words=len(words),
                )
            )

    components = {
        "parseability": parseability,
        "sections": sections_score,
        "skill_coverage": skill_coverage,
        "evidence": evidence,
        "content": content,
        "length": length,
    }
    weights = level.weights

    def combine(names: tuple[str, ...]) -> float:
        return round(
            sum(components[n] * weights[n] for n in names) / sum(weights[n] for n in names), 2
        )

    breakdown = {
        "components": {name: round(value, 2) for name, value in components.items()},
        "weights": weights,
        "ats_readiness": combine(READINESS),
        "role_fit": combine(FIT),
        "parse_degraded": False,
        "parser_version": PARSER_VERSION,
        "page_count": cv.page_count,
        "word_count": len(words),
        "sections_found": sections,
        "format_risks": cv.format_risks,
        "contacts": {
            "email": bool(found["emails"]),
            "phone": bool(found["phones"]),
            "links": len(found["links"]),
        },
        "skills": skill_rows,
        "bullets": {
            "total": total,
            "with_action_verb": len(with_verb),
            "with_metric": len(with_metric),
            "with_role_skill": len(with_skill),
            "with_weak_phrase": len(weak_bullets),
        },
    }
    return AtsResult(
        role=role,
        level=level,
        overall_score=combine(READINESS + FIT),
        breakdown=breakdown,
        issues=issues,
    )
