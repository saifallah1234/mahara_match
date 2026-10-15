"""Assistant-owned rehearsal sessions; separate from recruitment appointments."""

from typing import Any

from django.db import models
from django.db.models import Q

from backend.common.models import UUIDTimestampedModel


class MockInterviewSession(UUIDTimestampedModel):
    candidate: Any = models.ForeignKey("candidates.CandidateProfile", on_delete=models.PROTECT)
    offer: Any = models.ForeignKey("recruitment.JobOffer", on_delete=models.PROTECT)
    cv: Any = models.ForeignKey("candidates.CV", on_delete=models.SET_NULL, null=True, blank=True)
    conversation: Any = models.OneToOneField("assistant.Conversation", on_delete=models.PROTECT)
    language: Any = models.CharField(max_length=5, default="fr")
    status: Any = models.CharField(max_length=20, default="PREPARING", db_index=True)
    current_turn: Any = models.ForeignKey(
        "assistant.MockInterviewTurn",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_sessions",
    )
    version: Any = models.PositiveIntegerField(default=1)
    idempotency_key: Any = models.CharField(max_length=255)
    input_fingerprint: Any = models.CharField(max_length=64)
    evidence: Any = models.JSONField(default=dict)
    checkpoint: Any = models.JSONField(default=dict)
    feedback: Any = models.JSONField(default=dict)
    error_code: Any = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("candidate", "idempotency_key"), name="mock_session_key"
            ),
            models.CheckConstraint(
                condition=Q(language__in=("fr", "en", "ar-TN")), name="mock_language"
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=(
                        "PREPARING",
                        "READY",
                        "IN_PROGRESS",
                        "THINKING",
                        "EVALUATING",
                        "COMPLETED",
                        "FAILED",
                        "CANCELLED",
                    )
                ),
                name="mock_session_status",
            ),
        ]


class MockInterviewTurn(UUIDTimestampedModel):
    session: Any = models.ForeignKey(
        MockInterviewSession, on_delete=models.CASCADE, related_name="turns"
    )
    kind: Any = models.CharField(max_length=10, default="MAIN")
    position: Any = models.PositiveSmallIntegerField(null=True, blank=True)
    parent: Any = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    question_message: Any = models.OneToOneField(
        "assistant.ConversationMessage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interview_question",
    )
    answer_message: Any = models.OneToOneField(
        "assistant.ConversationMessage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interview_answer",
    )
    recording: Any = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_recordings",
    )
    answer_key: Any = models.CharField(max_length=255, blank=True)
    answer_fingerprint: Any = models.CharField(max_length=64, blank=True)
    transcription_status: Any = models.CharField(max_length=20, default="PENDING")
    evaluation: Any = models.JSONField(default=dict)
    audio: Any = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_audio",
    )
    video: Any = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_videos",
    )
    provider_metadata: Any = models.JSONField(default=dict)
    recording_expires_at: Any = models.DateTimeField(null=True, blank=True)
    deletion_pending: Any = models.BooleanField(default=False)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        kind="MAIN",
                        position__isnull=False,
                        position__gte=1,
                        position__lte=3,
                        parent__isnull=True,
                    )
                    | Q(kind="FOLLOWUP", position__isnull=True, parent__isnull=False)
                ),
                name="mock_turn_shape",
            ),
            models.UniqueConstraint(
                fields=("session", "position"), condition=Q(kind="MAIN"), name="mock_main_position"
            ),
            models.UniqueConstraint(
                fields=("session",), condition=Q(kind="FOLLOWUP"), name="mock_one_followup"
            ),
            models.UniqueConstraint(
                fields=("session", "answer_key"),
                condition=~Q(answer_key=""),
                name="mock_answer_key",
            ),
        ]


class MockInterviewJob(UUIDTimestampedModel):
    session: Any = models.ForeignKey(
        MockInterviewSession, on_delete=models.CASCADE, related_name="jobs"
    )
    turn: Any = models.ForeignKey(
        MockInterviewTurn, on_delete=models.CASCADE, null=True, blank=True, related_name="jobs"
    )
    stage: Any = models.CharField(max_length=30)
    generation: Any = models.PositiveIntegerField(default=1)
    input_fingerprint: Any = models.CharField(max_length=64)
    publication_status: Any = models.CharField(max_length=20, default="UNPUBLISHED")
    status: Any = models.CharField(max_length=20, default="PENDING", db_index=True)
    priority: Any = models.PositiveSmallIntegerField(default=0)
    attempts: Any = models.PositiveSmallIntegerField(default=0)
    lease_token: Any = models.UUIDField(null=True, blank=True)
    lease_until: Any = models.DateTimeField(null=True, blank=True)
    heartbeat_at: Any = models.DateTimeField(null=True, blank=True)
    retry_at: Any = models.DateTimeField(null=True, blank=True)
    avatar_key: Any = models.CharField(max_length=30, blank=True)
    audio: Any = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_job_audio",
    )
    output: Any = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_job_outputs",
    )
    payload: Any = models.JSONField(default=dict)
    configuration_fingerprint: Any = models.CharField(max_length=64, blank=True)
    error_code: Any = models.CharField(max_length=100, blank=True)
    simulated: Any = models.BooleanField(default=False)

    class Meta:
        ordering = ("priority", "created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("session", "stage", "input_fingerprint", "generation"),
                name="mock_job_generation",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=(
                        "PENDING",
                        "QUEUED",
                        "RUNNING",
                        "SUCCEEDED",
                        "RETRY_WAIT",
                        "FAILED",
                        "CANCELLED",
                    )
                ),
                name="mock_job_status",
            ),
        ]
