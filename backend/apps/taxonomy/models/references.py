"""Canonical education, language and skill references."""

from django.db import models

from backend.common.models import UUIDTimestampedModel


class EducationLevel(UUIDTimestampedModel):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    level_order = models.PositiveIntegerField(unique=True)

    class Meta:
        db_table = "education_levels"
        ordering = ("level_order", "id")

    def __str__(self) -> str:
        return self.name


class Language(UUIDTimestampedModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        db_table = "languages"
        ordering = ("code", "id")

    def __str__(self) -> str:
        return self.name


class Skill(UUIDTimestampedModel):
    canonical_name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    # ESCO link (decision 2026-11-14). NULL = local skill not in ESCO (Docker, Odoo...).
    esco_uri = models.CharField(  # noqa: DJ001 - NULL distinguishes local skills; unique when set.
        max_length=255, unique=True, null=True, blank=True
    )
    # ESCO skillType (knowledge, skill/competence) and reuseLevel (transversal ... occupation-specific)
    esco_skill_type = models.CharField(max_length=30, blank=True)
    esco_reuse_level = models.CharField(max_length=30, blank=True)
    is_digital = models.BooleanField(default=False)  # in ESCO's digital skills collection

    class Meta:
        db_table = "skills"
        ordering = ("canonical_name", "id")

    def __str__(self) -> str:
        return self.canonical_name


class SkillLabelKind(models.TextChoices):
    PREFERRED = "PREFERRED", "ESCO preferred label"
    ALTERNATIVE = "ALTERNATIVE", "ESCO alternative label"
    LOCAL = "LOCAL", "Local name"


class SkillLabel(UUIDTimestampedModel):
    """A name under which a skill is found. `key` is the normalized lookup form.

    PREFERRED and LOCAL labels link free text to a skill automatically; ALTERNATIVE
    labels (sometimes narrower examples in ESCO) are only used for search.
    """

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="labels")
    label = models.CharField(max_length=255)
    key = models.CharField(max_length=255, db_index=True)
    language = models.CharField(max_length=8, blank=True)
    kind = models.CharField(max_length=12, choices=SkillLabelKind.choices)

    class Meta:
        db_table = "skill_labels"
        ordering = ("skill", "kind", "key")
        constraints = [
            models.UniqueConstraint(
                fields=("skill", "key", "kind"), name="skill_labels_skill_key_kind_unique"
            )
        ]

    def __str__(self) -> str:
        return self.label
