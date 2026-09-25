from django.contrib import admin

from backend.apps.training.models import (
    TrainingEnrollment,
    TrainingProgram,
    TrainingRecommendation,
    TrainingSession,
    TrainingSkill,
)


@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "level", "delivery_mode", "status", "is_free")
    list_filter = ("status", "level", "delivery_mode", "is_free")
    search_fields = ("title", "description", "organization__legal_name")


@admin.register(TrainingSkill)
class TrainingSkillAdmin(admin.ModelAdmin):
    list_display = ("program", "skill_id", "target_level")


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ("program", "start_date", "end_date", "capacity", "status")
    list_filter = ("status",)


@admin.register(TrainingEnrollment)
class TrainingEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("session", "candidate_id", "status", "completion_rate", "enrolled_at")
    list_filter = ("status",)


@admin.register(TrainingRecommendation)
class TrainingRecommendationAdmin(admin.ModelAdmin):
    list_display = ("candidate_id", "program", "score", "model_version", "created_at")
    list_filter = ("model_version",)
