# Placement: ai/document_intelligence/parsing/cv_extractor.py
"""LLM extraction of a CV into CVExtraction, one focused call per section.

Ported from the OneTech agent project (cv_extractor.py): seven small schemas are
easier for a model to satisfy than one large one. Input is the CV as markdown plus
its hyperlinks and table text (pipelines/document_processing/extraction/cv_text.py).
Values are never invented: missing fields are None and the candidate confirms
everything before it reaches their profile.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol, TypeVar

from pydantic import BaseModel

from ai.document_intelligence.parsing.cv_schema import (
    DEGREE_LEVEL_GUIDANCE,
    CertificationList,
    CVExtraction,
    EducationList,
    ExperienceList,
    PersonalInfoAndSummary,
    ProjectList,
    Skill,
    SkillList,
    SpokenLanguageList,
)

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredLLM(Protocol):
    def generate_structured(
        self, system_prompt: str, user_prompt: str, schema: type[SchemaT]
    ) -> SchemaT: ...


_COMMON = "Return only information contained in the CV. Never invent information. If a field is missing, return null."

PERSONAL_PROMPT = f"""You are an expert CV information extraction system.
Extract ONLY the candidate's personal information, headline and professional summary.
Rules:
- {_COMMON}
- Use the detected hyperlinks to identify LinkedIn and GitHub URLs.
- headline: a short subtitle/tagline near the name (e.g. a field of study + job-seeking intent), as written.
- professional_summary: only an explicit profile/summary/objective statement, preserving the candidate's wording.
  Do NOT write a new summary from scattered information. If none exists, return null.
- location: the city and governorate/region as written near the name or contact details, e.g. 'Tunis, Tunisie'.
- phone: exactly as written, including any country code."""

EDUCATION_PROMPT = f"""You are an expert at extracting education history from CVs.
Extract every education entry (degree, diploma, preparatory class, baccalaureate...).
Rules:
- {_COMMON}
- Each entry is one separate object; never merge two entries. A table row is normally one entry.
- Institution, title, dates and location may be split across cells or lines: combine them into one entry.
- ALWAYS fill degree_level, inferring it from the degree name with this guidance: {DEGREE_LEVEL_GUIDANCE}
- Keep dates as written (e.g. "Sept. 2024", "2021"). Set is_current=true for ongoing studies
  ('Present', "Aujourd'hui", 'En cours', 'Actuel').
- Never return an empty list if any education information exists."""

EXPERIENCE_PROMPT = f"""You are an expert at extracting professional experience from CVs.
Extract every real professional experience: paid jobs, internships (stages), freelance work.
Rules:
- {_COMMON}
- Put EVERY bullet point of a role in "responsibilities"; never summarize or omit any.
- Keep technologies exactly as written, in "technologies".
- Do NOT include academic or personal projects ("Projets Académiques", "Projets Personnels"):
  if the "company" would be a school and the entry is a class project, it is not experience.
- Keep dates as written. Set is_current=true for an ongoing role ('Present', "Aujourd'hui", 'En cours')."""

PROJECT_PROMPT = f"""You are an expert at extracting academic and personal projects from CVs.
Extract every project entry from an Academic/Personal Projects section.
Rules:
- {_COMMON}
- Put EVERY bullet point of a project in "highlights". Keep technologies exactly as written.
- Use the detected hyperlinks to fill "github" when a project links to a repository.
- Do NOT include professional experience or internships."""

SKILL_PROMPT = f"""You are an expert at extracting skills from CVs.
Extract every individual skill as a SEPARATE object.
A skill is a NAMED technology, tool, framework, language, methodology or established competency
(e.g. "Python", "Docker", "Machine Learning", "Agile", "Communication"). It is NOT an action or
responsibility phrase taken from a bullet point (e.g. not "publication de contenus").
Rules:
- {_COMMON}
- Split comma-separated lists ("Langages : Python, Java, SQL") into one object per item.
- Also extract named technologies mentioned in experience, project and education entries.
- Never return spoken languages (French, English, Arabic) as skills."""

CERTIFICATION_PROMPT = f"""You are an expert at extracting certifications from CVs.
Extract every certification entry. {_COMMON} Return an empty list if there are none."""

LANGUAGE_PROMPT = f"""You are an expert at extracting spoken languages from CVs.
Extract every human language (French, English, Arabic, Spanish...) with its level as written
(e.g. "Courant", "Natif", "B2", "Intermédiaire").
Rules:
- {_COMMON}
- Never extract programming languages.
- Return an empty list if there are none."""


def tables_to_text(tables: list[list[list[str | None]]]) -> str:
    """Render detected tables row by row; they are often more reliable than the markdown."""
    lines: list[str] = []
    for table in tables:
        lines.append("Detected table:")
        for row_index, row in enumerate(table, start=1):
            lines.append(f"Row {row_index}:")
            lines.extend(
                f"- Column {column}: {cell.strip()}"
                for column, cell in enumerate(row, start=1)
                if cell
            )
    return "\n".join(lines)


def extract_cv(
    llm: StructuredLLM,
    markdown: str,
    *,
    links: list[str] | None = None,
    tables: list[list[list[str | None]]] | None = None,
    progress: Callable[[str], None] | None = None,
) -> CVExtraction:
    links_text = "\n".join(links or []) or "(none)"
    tables_text = tables_to_text(tables or []) or "(none)"

    def ask(section: str, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        if progress:
            progress(section)
        logger.info("Extracting CV section: %s", section)
        return llm.generate_structured(system, user, schema)

    personal = ask(
        "personal",
        PERSONAL_PROMPT,
        f"CV Markdown:\n\n{markdown}\n\nDetected hyperlinks:\n\n{links_text}",
        PersonalInfoAndSummary,
    )
    education = ask(
        "education",
        EDUCATION_PROMPT,
        f"CV Markdown (look for an Education / Formation / Diplômes section):\n\n{markdown}\n\n"
        f"Detected tables (authoritative when present):\n\n{tables_text}",
        EducationList,
    )
    experience = ask(
        "experience",
        EXPERIENCE_PROMPT,
        f"CV Markdown (look for Experience / Expérience Professionnelle):\n\n{markdown}",
        ExperienceList,
    )
    projects = ask(
        "projects",
        PROJECT_PROMPT,
        f"CV Markdown (look for Projects / Projets):\n\n{markdown}\n\n"
        f"Detected hyperlinks:\n\n{links_text}",
        ProjectList,
    )
    skills = ask(
        "skills",
        SKILL_PROMPT,
        f"CV Markdown (look for Skills / Compétences and technologies elsewhere):\n\n{markdown}",
        SkillList,
    )
    certifications = ask(
        "certifications",
        CERTIFICATION_PROMPT,
        f"CV Markdown (look for a Certifications section):\n\n{markdown}",
        CertificationList,
    )
    languages = ask(
        "languages",
        LANGUAGE_PROMPT,
        f"CV Markdown (look for Languages / Langues):\n\n{markdown}",
        SpokenLanguageList,
    )
    return CVExtraction(
        personal_information=personal.personal_information,
        headline=personal.headline,
        professional_summary=personal.professional_summary,
        education=education.education,
        experience=experience.experience,
        projects=projects.projects,
        skills=_dedupe_skills(skills),
        certifications=certifications.certifications,
        spoken_languages=languages.spoken_languages,
    )


def _dedupe_skills(result: SkillList) -> list[Skill]:
    seen: set[str] = set()
    unique: list[Skill] = []
    for skill in result.skills:
        key = " ".join(skill.name.casefold().split())
        if key and key not in seen:
            seen.add(key)
            unique.append(skill)
    return unique
