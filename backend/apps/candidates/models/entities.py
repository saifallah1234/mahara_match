"""Candidate profile, structured history and CV persistence."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from backend.common.models import UUIDTimestampedModel


class ProfileVisibility(models.TextChoices):
    PRIVATE = "PRIVATE", "Private"
    RECRUITERS = "RECRUITERS", "Recruiters"
    PUBLIC = "PUBLIC", "Public"


class Relocation(models.TextChoices):
    OPEN = "OPEN", "Open to relocate"
    CANNOT = "CANNOT", "Cannot relocate"


class WorkMode(models.TextChoices):
    REMOTE = "REMOTE", "Remote"
    HYBRID = "HYBRID", "Hybrid"
    ONSITE = "ONSITE", "Onsite"


class LanguageLevel(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    C1 = "C1", "C1"
    C2 = "C2", "C2"


class SkillLevel(models.TextChoices):
    BEGINNER = "BEGINNER", "Beginner"
    INTERMEDIATE = "INTERMEDIATE", "Intermediate"
    ADVANCED = "ADVANCED", "Advanced"
    EXPERT = "EXPERT", "Expert"


class CandidateProfile(UUIDTimestampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="candidate_profile"
    )
    birth_date = models.DateField(null=True, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    governorate = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    headline = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    employment_status = models.CharField(max_length=30, blank=True)
    desired_job_title = models.CharField(max_length=150, blank=True)
    availability_date = models.DateField(null=True, blank=True)
    profile_visibility = models.CharField(
        max_length=20, choices=ProfileVisibility.choices, default=ProfileVisibility.PRIVATE
    )
    completion_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        db_table = "candidate_profiles"
        constraints = [
            models.CheckConstraint(
                condition=Q(completion_score__gte=0) & Q(completion_score__lte=100),
                name="candidate_profiles_score_range",
            ),
        ]


class CandidateOwnedModel(UUIDTimestampedModel):
    candidate = models.ForeignKey(
        "candidates.CandidateProfile",
        on_delete=models.PROTECT,
        related_name="%(class)ss",
    )

    class Meta:
        abstract = True


class Experience(CandidateOwnedModel):
    organization_name = models.CharField(max_length=200)
    job_title = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "experiences"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="experiences_dates_ordered",
            )
        ]


class Education(CandidateOwnedModel):
    education_level = models.ForeignKey("taxonomy.EducationLevel", on_delete=models.PROTECT)
    institution = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=150, blank=True)
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "educations"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_year__isnull=True) | Q(end_year__gte=F("start_year")),
                name="educations_years_ordered",
            )
        ]


class CandidateLanguage(UUIDTimestampedModel):
    candidate = models.ForeignKey(
        "candidates.CandidateProfile", on_delete=models.PROTECT, related_name="languages"
    )
    language = models.ForeignKey("taxonomy.Language", on_delete=models.PROTECT)
    level = models.CharField(max_length=2, choices=LanguageLevel.choices)

    class Meta:
        db_table = "candidate_languages"
        constraints = [
            models.UniqueConstraint(
                fields=("candidate", "language"), name="candidate_languages_unique"
            )
        ]


class CandidateSkill(UUIDTimestampedModel):
    candidate = models.ForeignKey(
        "candidates.CandidateProfile", on_delete=models.PROTECT, related_name="skills"
    )
    skill = models.ForeignKey("taxonomy.Skill", on_delete=models.PROTECT)
    level = models.CharField(max_length=20, choices=SkillLevel.choices)
    years_experience = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    validated = models.BooleanField(default=False)
    source = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "candidate_skills"
        constraints = [
            models.UniqueConstraint(fields=("candidate", "skill"), name="candidate_skills_unique"),
            models.CheckConstraint(
                condition=Q(years_experience__isnull=True) | Q(years_experience__gte=0),
                name="candidate_skills_years_nonnegative",
            ),
        ]


class Certification(CandidateOwnedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    certification_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=150, blank=True)
    credential_url = models.URLField(max_length=500, blank=True)

    class Meta:
        db_table = "certifications"
        constraints = [
            models.CheckConstraint(
                condition=Q(expiration_date__isnull=True) | Q(expiration_date__gte=F("issue_date")),
                name="certifications_dates_ordered",
            )
        ]


class CandidatePreference(UUIDTimestampedModel):
    candidate = models.OneToOneField(
        "candidates.CandidateProfile", on_delete=models.PROTECT, related_name="preferences"
    )
    work_mode = models.CharField(max_length=10, choices=WorkMode.choices)
    relocation = models.CharField(max_length=10, choices=Relocation.choices, blank=True)
    distance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum preferred commute distance in kilometres.",
    )

    class Meta:
        db_table = "candidate_preferences"
        constraints = [
            models.CheckConstraint(
                condition=Q(distance__isnull=True) | Q(distance__gte=0),
                name="candidate_preferences_distance_nonnegative",
            )
        ]


class Project(CandidateOwnedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    role = models.CharField(max_length=150, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    project_url = models.URLField(max_length=500, blank=True)
    repository_url = models.URLField(max_length=500, blank=True)
    technologies = models.ManyToManyField("taxonomy.Skill", through="candidates.ProjectSkill")

    class Meta:
        db_table = "projects"
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__isnull=True)
                | Q(end_date__isnull=True)
                | Q(end_date__gte=F("start_date")),
                name="projects_dates_ordered",
            )
        ]


class ProjectSkill(UUIDTimestampedModel):
    project = models.ForeignKey(
        "candidates.Project", on_delete=models.PROTECT, related_name="technology_links"
    )
    skill = models.ForeignKey("taxonomy.Skill", on_delete=models.PROTECT)

    class Meta:
        db_table = "project_skills"
        constraints = [
            models.UniqueConstraint(fields=("project", "skill"), name="project_skills_unique")
        ]


class CV(CandidateOwnedModel):
    document = models.OneToOneField(
        "documents.Document", on_delete=models.PROTECT, related_name="cv"
    )
    title = models.CharField(max_length=200)
    language_code = models.CharField(max_length=16, blank=True)
    is_primary = models.BooleanField(default=False)
    parse_status = models.CharField(max_length=30, blank=True)
    parsed_data_json = models.JSONField(null=True, blank=True)
    version_number = models.PositiveIntegerField()

    class Meta:
        db_table = "cvs"
        constraints = [
            models.UniqueConstraint(
                fields=("candidate", "version_number"), name="cvs_candidate_version_unique"
            ),
            models.UniqueConstraint(
                fields=("candidate",),
                condition=Q(is_primary=True),
                name="cvs_one_primary_per_candidate",
            ),
        ]


class CVAnalysisResult(UUIDTimestampedModel):
    cv = models.ForeignKey(
        "candidates.CV", on_delete=models.PROTECT, related_name="analysis_results"
    )
    target_offer = models.ForeignKey(
        "recruitment.JobOffer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cv_analysis_results",
    )
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    issues_json = models.JSONField(default=list)
    suggestions_json = models.JSONField(default=list)
    analyzed_at = models.DateTimeField()

    class Meta:
        db_table = "cv_analysis_results"
        constraints = [
            models.CheckConstraint(
                condition=Q(overall_score__gte=0) & Q(overall_score__lte=100),
                name="cv_analysis_results_score_range",
            )
        ]
