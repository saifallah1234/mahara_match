from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.assistant.models import MockInterviewJob, MockInterviewSession, MockInterviewTurn
from backend.apps.assistant.services.interview_contracts import (
    InterviewConflict,
    InterviewUnavailable,
    fingerprint,
    validate_key,
    validate_language,
    validate_transition,
)
from backend.apps.assistant.services.records import create_conversation
from backend.apps.candidates.models import CV
from backend.apps.candidates.services.records import get_record, own_profile
from backend.apps.documents.models import Document
from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.recruitment.services.job_offers import get_job_offer
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_sessions(actor: User) -> QuerySet[MockInterviewSession]:
    profile = own_profile(actor)
    require_permission(actor, "assistant.mock_interview.use")
    return MockInterviewSession.objects.filter(candidate=profile)


def get_session(actor: User, session_id: UUID | str, *, lock: bool = False) -> MockInterviewSession:
    queryset = list_sessions(actor)
    if lock:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=session_id)
    except MockInterviewSession.DoesNotExist as exc:
        raise DomainNotFoundError("Mock interview not found.") from exc


def transition(session: MockInterviewSession, target: str) -> None:
    validate_transition(session.status, target)
    session.status = target
    session.version += 1
    session.save(update_fields=["status", "version", "updated_at"])


def request_job(
    session: MockInterviewSession,
    stage: str,
    *,
    turn: MockInterviewTurn | None = None,
    payload: dict | None = None,
    priority: int = 0,
) -> MockInterviewJob:
    data = payload or {}
    digest = fingerprint({"turn": turn.pk if turn else None, "payload": data})
    existing = (
        session.jobs.filter(stage=stage, input_fingerprint=digest).order_by("-generation").first()
    )
    if existing:
        if stage == "ANSWER" and existing.status == "CANCELLED" and session.status == "IN_PROGRESS":
            existing.generation += 1
            existing.status = "PENDING"
            existing.attempts = 0
            existing.save()
        return existing
    job, _ = MockInterviewJob.objects.get_or_create(
        session=session,
        stage=stage,
        input_fingerprint=digest,
        generation=1,
        defaults={"turn": turn, "payload": data, "priority": priority},
    )
    return job


@transaction.atomic
def create_session(
    actor: User, *, offer_id: UUID | str, language: str, key: str, cv_id: UUID | str | None = None
) -> MockInterviewSession:
    validate_key(key)
    validate_language(language)
    profile = own_profile(actor)
    require_permission(actor, "assistant.mock_interview.use")
    if not settings.MOCK_INTERVIEW_ENABLED:
        raise InterviewUnavailable("Mock interviews are disabled.")
    # Serialize concurrent create requests using the existing candidate row.
    type(profile).objects.select_for_update().get(pk=profile.pk)
    digest = fingerprint({"offer": offer_id, "cv": cv_id, "language": language})
    existing = list_sessions(actor).filter(idempotency_key=key).first()
    if existing:
        if existing.input_fingerprint != digest:
            raise InterviewConflict("Idempotency key was used for different input.")
        return existing
    offer = get_job_offer(actor, offer_id)
    cv = get_record(actor, CV, cv_id) if cv_id else None
    session = MockInterviewSession.objects.create(
        candidate=profile,
        offer=offer,
        cv=cv,
        language=language,
        conversation=create_conversation(actor, "Entretien blanc"),
        idempotency_key=key,
        input_fingerprint=digest,
    )
    request_job(session, "PREPARE")
    return session


@transaction.atomic
def reserve_followup(session_id: UUID | str, parent_id: UUID | str) -> MockInterviewTurn:
    session = MockInterviewSession.objects.select_for_update().get(pk=session_id)
    if session.status != "THINKING":
        raise InterviewConflict("Follow-up reservation requires answer processing.")
    parent = session.turns.filter(pk=parent_id, kind="MAIN", answer_message__isnull=False).first()
    if parent is None or session.current_turn_id != parent.pk:
        raise InterviewConflict("Follow-up parent must be the answered current main turn.")
    existing = session.turns.filter(kind="FOLLOWUP").first()
    if existing:
        if existing.parent_id != parent.pk:
            raise InterviewConflict("The session follow-up has already been used.")
        return existing
    return MockInterviewTurn.objects.create(session=session, kind="FOLLOWUP", parent=parent)


def start_session(actor: User, session_id: UUID | str) -> MockInterviewSession:
    session = get_session(actor, session_id)
    if session.status in {"IN_PROGRESS", "THINKING", "EVALUATING", "COMPLETED"}:
        return session
    if session.status != "READY":
        raise InterviewConflict("The interview is not ready.")
    from backend.apps.assistant.services.interview_media import check_readiness

    if not check_readiness(session):
        raise InterviewUnavailable("Required media is unavailable.")
    with transaction.atomic():
        current = get_session(actor, session_id, lock=True)
        if current.status != "READY":
            if current.status in {"IN_PROGRESS", "THINKING", "EVALUATING", "COMPLETED"}:
                return current
            raise InterviewConflict("The interview is not ready.")
        current.current_turn = current.turns.get(kind="MAIN", position=1)
        current.save(update_fields=["current_turn", "updated_at"])
        transition(current, "IN_PROGRESS")
        return current


@transaction.atomic
def accept_answer(
    actor: User,
    session_id: UUID | str,
    turn_id: UUID | str,
    *,
    version: int,
    key: str,
    recording: Document,
) -> MockInterviewSession:
    validate_key(key)
    session = get_session(actor, session_id, lock=True)
    turn = session.turns.filter(pk=turn_id).first()
    if turn is None:
        raise DomainNotFoundError("Turn not found.")
    if recording.owner_user_id != actor.pk or recording.type != "INTERVIEW_RECORDING":
        raise DomainValidationError("Invalid interview recording.")
    digest = recording.checksum
    used = session.turns.filter(answer_key=key).first()
    if used:
        if used.pk != turn.pk or used.answer_fingerprint != digest:
            raise InterviewConflict("Idempotency key was used for different input.")
        return session
    if turn.answer_key:
        raise InterviewConflict("An answer has already been accepted.")
    if (
        session.version != version
        or session.current_turn_id != turn.pk
        or session.status != "IN_PROGRESS"
    ):
        raise InterviewConflict("Stale version or inactive turn.")
    turn.recording = recording
    turn.answer_key = key
    turn.answer_fingerprint = digest
    turn.recording_expires_at = timezone.now() + timedelta(
        hours=settings.MOCK_INTERVIEW_RECORDING_RETENTION_HOURS
    )
    turn.save()
    request_job(session, "ANSWER", turn=turn, payload={"checksum": digest})
    transition(session, "THINKING")
    return session


@transaction.atomic
def retry_session(actor: User, session_id: UUID | str) -> MockInterviewSession:
    session = get_session(actor, session_id, lock=True)
    if session.status in {"CANCELLED", "COMPLETED"}:
        raise InterviewConflict("This interview cannot be retried.")
    failed = list(session.jobs.filter(status="FAILED").exclude(stage="VIDEO_BACKGROUND"))
    if not failed:
        if session.jobs.filter(status__in=("PENDING", "QUEUED", "RUNNING", "RETRY_WAIT")).exists():
            return session
        raise InterviewConflict("No failed work is eligible for retry.")
    for job in failed:
        if job.stage == "ANSWER" and (
            not job.turn.recording_id or job.turn.recording_expires_at <= timezone.now()
        ):
            raise InterviewConflict("Recording expired; record this turn again.")
        job.status = "PENDING"
        job.generation += 1
        job.attempts = 0
        job.error_code = ""
        job.publication_status = "UNPUBLISHED"
        job.lease_token = None
        job.lease_until = None
        job.save()
    if session.status == "FAILED":
        stage = failed[0].stage
        transition(
            session,
            "THINKING"
            if stage in {"ANSWER", "ROUTE", "FOLLOWUP"}
            else "EVALUATING"
            if stage == "FEEDBACK"
            else "PREPARING",
        )
    session.error_code = ""
    session.save(update_fields=["error_code", "updated_at"])
    return session


@transaction.atomic
def cancel_session(actor: User, session_id: UUID | str) -> MockInterviewSession:
    session = get_session(actor, session_id, lock=True)
    if session.status == "CANCELLED":
        return session
    transition(session, "CANCELLED")
    session.jobs.exclude(status="SUCCEEDED").update(
        status="CANCELLED", lease_token=None, lease_until=None
    )
    session.turns.filter(recording__isnull=False).update(deletion_pending=True)
    return session
