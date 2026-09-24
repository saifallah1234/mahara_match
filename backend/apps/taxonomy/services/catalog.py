from django.db.models import QuerySet

from backend.apps.taxonomy.models import EducationLevel, Language, Skill


def education_levels() -> QuerySet[EducationLevel]:
    return EducationLevel.objects.all()


def languages() -> QuerySet[Language]:
    return Language.objects.all()


def skills() -> QuerySet[Skill]:
    return Skill.objects.all()
