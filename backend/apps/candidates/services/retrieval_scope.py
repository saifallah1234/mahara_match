"""Candidate data open to retrieval.

A candidate contributes their own skills as graph seeds. Verified recruiters may
retrieve opted-in profiles through the limited Q19 view only: headline, skills,
experience titles, education, governorate and work preferences. Names, contact
details, birth dates and CVs never enter retrieval text or results.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from backend.apps.candidates.models import CandidateProfile, CandidateSkill
from backend.apps.candidates.services.discovery import list_candidates, list_indexable_profiles
from backend.apps.candidates.services.records import list_records
from backend.apps.identity.models import User
from backend.common.retrieval import RetrievalDocument


def own_skill_ids(actor: User) -> list[UUID]:
    return list(list_records(actor, CandidateSkill).values_list("skill_id", flat=True))


def discoverable_profiles(actor: User) -> QuerySet[CandidateProfile]:
    """Opted-in profiles; raises DomainPermissionError unless the actor is a verified recruiter."""
    return list_candidates(actor)


def retrievable_profiles() -> QuerySet[CandidateProfile]:
    return list_indexable_profiles()


def limited_profile_documents(profiles: QuerySet[CandidateProfile]) -> list[RetrievalDocument]:
    documents = []
    for profile in _with_limited_fields(profiles):
        view = _limited_view(profile)
        text = "\n".join(
            part
            for part in (
                view["headline"],
                ", ".join(view["skills"]),
                ", ".join(view["experience_titles"]),
                ", ".join(view["education"]),
                view["governorate"],
                view["work_mode"],
            )
            if part
        )
        documents.append(RetrievalDocument("candidate_profile", profile.id, text, view["headline"]))
    return documents


def profile_ids_for_skills(
    profiles: QuerySet[CandidateProfile], skill_ids: Iterable[UUID]
) -> Counter[UUID]:
    links = CandidateSkill.objects.filter(candidate__in=profiles, skill_id__in=list(skill_ids))
    return Counter(candidate_id for (candidate_id,) in links.values_list("candidate_id"))


def limited_profile_view(actor: User, profile_ids: Iterable[UUID]) -> list[dict[str, Any]]:
    """Live Q19 display fields for in-scope profiles, in the order of ``profile_ids``."""
    wanted = list(profile_ids)
    by_id = {
        profile.id: profile
        for profile in _with_limited_fields(discoverable_profiles(actor).filter(id__in=wanted))
    }
    return [
        {"id": str(profile_id), **_limited_view(by_id[profile_id])}
        for profile_id in wanted
        if profile_id in by_id
    ]


def _with_limited_fields(profiles: QuerySet[CandidateProfile]) -> QuerySet[CandidateProfile]:
    return profiles.select_related("preferences").prefetch_related(
        "skills__skill", "experiences", "educations__education_level"
    )


def _limited_view(profile: CandidateProfile) -> dict[str, Any]:
    preferences = getattr(profile, "preferences", None)
    return {
        "headline": profile.headline,
        "skills": sorted(link.skill.canonical_name for link in profile.skills.all()),
        "experience_titles": [experience.job_title for experience in profile.experiences.all()],
        "education": [
            " - ".join(
                part for part in (education.education_level.name, education.field_of_study) if part
            )
            for education in profile.educations.all()
        ],
        "governorate": profile.governorate,
        "work_mode": preferences.work_mode if preferences else "",
    }
