from django.db.models import QuerySet
from rest_framework import serializers
from rest_framework.viewsets import ReadOnlyModelViewSet

from backend.apps.taxonomy.models import EducationLevel, Language, Skill
from backend.apps.taxonomy.services import catalog


class EducationLevelSerializer(serializers.ModelSerializer[EducationLevel]):
    class Meta:
        model = EducationLevel
        fields = ("id", "name", "description", "level_order")


class LanguageSerializer(serializers.ModelSerializer[Language]):
    class Meta:
        model = Language
        fields = ("id", "code", "name")


class SkillSerializer(serializers.ModelSerializer[Skill]):
    class Meta:
        model = Skill
        fields = ("id", "canonical_name", "category", "description")


class EducationLevelViewSet(ReadOnlyModelViewSet[EducationLevel]):
    queryset = EducationLevel.objects.none()
    serializer_class = EducationLevelSerializer

    def get_queryset(self) -> QuerySet[EducationLevel]:
        return catalog.education_levels()


class LanguageViewSet(ReadOnlyModelViewSet[Language]):
    queryset = Language.objects.none()
    serializer_class = LanguageSerializer

    def get_queryset(self) -> QuerySet[Language]:
        return catalog.languages()


class SkillViewSet(ReadOnlyModelViewSet[Skill]):
    queryset = Skill.objects.none()
    serializer_class = SkillSerializer

    def get_queryset(self) -> QuerySet[Skill]:
        return catalog.skills()
