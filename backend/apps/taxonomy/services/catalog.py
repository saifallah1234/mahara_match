from django.db.models import Exists, OuterRef, Q, QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.apps.taxonomy.models import (
    EducationLevel,
    Language,
    Skill,
    SkillLabel,
    SkillLabelKind,
)
from backend.apps.taxonomy.services.skills import skill_key


def education_levels() -> QuerySet[EducationLevel]:
    return EducationLevel.objects.all()


def languages() -> QuerySet[Language]:
    return Language.objects.all()


def skills() -> QuerySet[Skill]:
    """The working catalogue: local skills (linked to ESCO or not) plus ESCO skills in use.

    The ~14,000 loaded ESCO skills stay out of lists, dropdowns and the retrieval index
    until a candidate, offer, project or training program refers to them; search_skills()
    reaches all of them.
    """
    used = (
        Q(esco_uri__isnull=True)
        | Exists(SkillLabel.objects.filter(skill=OuterRef("pk"), kind=SkillLabelKind.LOCAL))
        | Exists(Skill.objects.filter(pk=OuterRef("pk"), candidateskill__isnull=False))
        | Exists(Skill.objects.filter(pk=OuterRef("pk"), projectskill__isnull=False))
        | Exists(Skill.objects.filter(pk=OuterRef("pk"), offer_skills__isnull=False))
        | Exists(Skill.objects.filter(pk=OuterRef("pk"), training_program_links__isnull=False))
    )
    return Skill.objects.filter(used)


def search_skills(text: str) -> QuerySet[Skill]:
    """Every skill (ESCO included) with a name or alternative name containing `text`."""
    key = skill_key(text)
    if len(key) < 2:
        return Skill.objects.none()
    matching = SkillLabel.objects.filter(key__contains=key).values("skill_id")
    return Skill.objects.filter(pk__in=matching)


def seed_interview_demo_skill(actor: User) -> Skill:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    return Skill.objects.get_or_create(
        canonical_name="Python", defaults={"category": "Programmation"}
    )[0]
