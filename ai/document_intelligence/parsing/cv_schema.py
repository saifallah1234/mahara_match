# Placement: ai/document_intelligence/parsing/cv_schema.py
"""What the LLM returns for one CV: values as written in the CV, None when absent.

Ported from the OneTech agent project (models.py). Nothing here is a Django model;
the candidate confirms every value before anything reaches their profile.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

DEGREE_LEVEL_GUIDANCE = (
    "Normalize by total years of post-secondary study, NOT by literal degree name - titles "
    "differ across education systems. Examples: French/Tunisian Bac = HIGH_SCHOOL. Classe "
    "Préparatoire (CPGE/CPI) alone = SHORT_CYCLE (2 yrs, no standalone degree). BTS/DUT = "
    "ASSOCIATE (~2 yrs, degree awarded). Licence = BACHELOR (~3 yrs). Diplôme d'Ingénieur, "
    "Master, MBA = MASTER (~5 yrs total). Doctorat/PhD = DOCTORATE (~8 yrs)."
)


class DegreeLevel(StrEnum):
    HIGH_SCHOOL = "high_school"
    SHORT_CYCLE = "short_cycle"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    OTHER = "other"


class SkillCategory(StrEnum):
    PROGRAMMING_LANGUAGE = "programming_language"
    TECHNICAL = "technical"
    TOOL = "tool"
    SOFT = "soft"
    DOMAIN = "domain"
    OTHER = "other"


class PersonalInformation(BaseModel):
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None = Field(description="City and region as written, e.g. 'Ariana, Tunis'.")
    linkedin: str | None
    github: str | None


class PersonalInfoAndSummary(BaseModel):
    personal_information: PersonalInformation
    headline: str | None = Field(
        description="Short title/tagline under the name, as written (e.g. 'Étudiante en Génie "
        "Logiciel'). Null if none."
    )
    professional_summary: str | None


class Education(BaseModel):
    degree: str | None
    degree_level: DegreeLevel | None = Field(default=None, description=DEGREE_LEVEL_GUIDANCE)
    institution: str | None
    field_of_study: str | None
    start_date: str | None
    end_date: str | None
    is_current: bool = Field(default=False, description="True if still in progress.")
    description: str | None


class Experience(BaseModel):
    job_title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    start_date: str | None
    end_date: str | None
    is_current: bool = Field(default=False, description="True if the candidate is still there.")
    description: str | None
    responsibilities: list[str]
    technologies: list[str]


class Project(BaseModel):
    title: str | None
    summary: str | None
    highlights: list[str]
    technologies: list[str]
    github: str | None


class Skill(BaseModel):
    name: str
    category: SkillCategory | None = Field(
        default=None,
        description=(
            "PROGRAMMING_LANGUAGE: coding/query languages (Python, Java, SQL). TECHNICAL: "
            "frameworks, libraries, databases, cloud/DevOps platforms, ML/data concepts. TOOL: "
            "standalone software (Git, Selenium). SOFT: interpersonal skills. DOMAIN: business "
            "domain knowledge. OTHER: anything else. Never a spoken language."
        ),
    )


class Certification(BaseModel):
    name: str
    issuer: str | None
    date: str | None


class SpokenLanguage(BaseModel):
    name: str = Field(description="A human language (French, English, Arabic), never code.")
    proficiency: str | None


class EducationList(BaseModel):
    education: list[Education]


class ExperienceList(BaseModel):
    experience: list[Experience]


class ProjectList(BaseModel):
    projects: list[Project]


class SkillList(BaseModel):
    skills: list[Skill]


class CertificationList(BaseModel):
    certifications: list[Certification]


class SpokenLanguageList(BaseModel):
    spoken_languages: list[SpokenLanguage]


class CVExtraction(BaseModel):
    """The whole result; stored as the CV's raw parse result (G05)."""

    personal_information: PersonalInformation
    headline: str | None = None
    professional_summary: str | None = None
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    spoken_languages: list[SpokenLanguage] = Field(default_factory=list)
