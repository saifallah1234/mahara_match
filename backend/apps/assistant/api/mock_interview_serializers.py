from typing import Any

from django.db.models import Q
from rest_framework import serializers

from backend.apps.assistant.models import MockInterviewJob, MockInterviewSession, MockInterviewTurn


class SessionWriteSerializer(serializers.Serializer[dict[str, Any]]):
    offer_id = serializers.UUIDField()
    cv_id = serializers.UUIDField(required=False)
    language = serializers.CharField(default="fr")


class AnswerWriteSerializer(serializers.Serializer[dict[str, Any]]):
    recording = serializers.FileField()
    version = serializers.IntegerField(min_value=1)


class TurnReadSerializer(serializers.ModelSerializer[MockInterviewTurn]):
    question = serializers.CharField(source="question_message.content", default="")
    answer = serializers.CharField(source="answer_message.content", default="")

    class Meta:
        model = MockInterviewTurn
        fields = (
            "id",
            "kind",
            "position",
            "parent_id",
            "question",
            "answer",
            "transcription_status",
            "evaluation",
        )
        read_only_fields = fields


class JobReadSerializer(serializers.ModelSerializer[MockInterviewJob]):
    class Meta:
        model = MockInterviewJob
        fields = (
            "id",
            "stage",
            "status",
            "publication_status",
            "attempts",
            "error_code",
            "simulated",
        )
        read_only_fields = fields


class SessionReadSerializer(serializers.ModelSerializer[MockInterviewSession]):
    turns = TurnReadSerializer(many=True, read_only=True)
    jobs = JobReadSerializer(many=True, read_only=True)
    allowed_actions = serializers.SerializerMethodField()
    playback = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()

    def get_allowed_actions(self, session: MockInterviewSession) -> list[str]:
        actions = {
            "READY": ["start"],
            "IN_PROGRESS": ["answer"],
            "FAILED": ["retry"],
            "COMPLETED": ["feedback"],
        }.get(session.status, [])
        return actions + (["cancel"] if session.status not in {"CANCELLED", "COMPLETED"} else [])

    def get_playback(self, session: MockInterviewSession) -> dict:
        from backend.apps.assistant.services.interview_media import playback_descriptors

        return playback_descriptors(session)

    def get_availability(self, session: MockInterviewSession) -> dict:
        from datetime import timedelta

        from django.utils import timezone

        cutoff = timezone.now() - timedelta(minutes=15)
        return {
            "initial_media": session.jobs.filter(stage="VIDEO_REQUIRED", status="SUCCEEDED").count()
            == 2,
            "simulated": session.jobs.filter(simulated=True).exists(),
            "worker": "stalled"
            if session.jobs.filter(
                stage__in=("VIDEO_REQUIRED", "VIDEO_BACKGROUND"),
                publication_status="PUBLISHED",
                status__in=("QUEUED", "RUNNING"),
            )
            .filter(
                Q(heartbeat_at__lt=cutoff) | Q(heartbeat_at__isnull=True, updated_at__lt=cutoff)
            )
            .exists()
            else "waiting"
            if session.jobs.filter(
                stage__in=("VIDEO_REQUIRED", "VIDEO_BACKGROUND"),
                status__in=("PENDING", "QUEUED", "RUNNING"),
            ).exists()
            else "idle",
        }

    class Meta:
        model = MockInterviewSession
        fields = (
            "id",
            "offer_id",
            "cv_id",
            "language",
            "status",
            "version",
            "current_turn_id",
            "turns",
            "jobs",
            "allowed_actions",
            "availability",
            "playback",
            "error_code",
            "created_at",
        )
        read_only_fields = fields
