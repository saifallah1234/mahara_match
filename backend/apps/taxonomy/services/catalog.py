from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import IdentityPermissionCode
from backend.apps.taxonomy.models import EducationLevel, Language, Skill


def education_levels() -> QuerySet[EducationLevel]:
    return EducationLevel.objects.all()


def languages() -> QuerySet[Language]:
    return Language.objects.all()


def skills() -> QuerySet[Skill]:
    return Skill.objects.all()


def seed_interview_demo_skill(actor: User) -> Skill:
    require_permission(actor, IdentityPermissionCode.MANAGE_RBAC)
    return Skill.objects.get_or_create(
        canonical_name="Python", defaults={"category": "Programmation"}
    )[0]
