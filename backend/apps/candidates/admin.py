from django.contrib import admin

from backend.apps.candidates.models import (
    CV,
    CandidateLanguage,
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    Certification,
    CVAnalysisResult,
    Education,
    Experience,
    Project,
    ProjectSkill,
)

for model in (
    CandidateProfile,
    Experience,
    Education,
    CandidateLanguage,
    CandidateSkill,
    Certification,
    CandidatePreference,
    Project,
    ProjectSkill,
    CV,
    CVAnalysisResult,
):
    admin.site.register(model)
