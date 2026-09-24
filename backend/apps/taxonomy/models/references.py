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

    class Meta:
        db_table = "skills"
        ordering = ("canonical_name", "id")

    def __str__(self) -> str:
        return self.canonical_name
