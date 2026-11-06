# Placement: tests/integration/candidates/test_cv_review_api.py
"""ATS analysis API: roles, create, list, retrieve, ownership and refusal paths."""

from collections.abc import Iterator
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils import timezone

from backend.apps.candidates.models import CV, CandidateProfile, CVAnalysisResult
from backend.apps.documents.models import Document
from backend.apps.identity.models import User
from tests.fixtures.cv_review.fake_chat import FakeChat
from tests.fixtures.cv_review.render import render
from tests.integration.candidates.test_cv_access_and_deletion import (
    account,
    candidate,
    client_for,
    organization,
    recruiter,
)

pytestmark = pytest.mark.django_db

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture(autouse=True)
def chat() -> Iterator[FakeChat]:
    """Swap the chat provider; by default it fails like an unreachable Ollama."""
    model = FakeChat(lambda messages: (_ for _ in ()).throw(ConnectionError("Ollama is down")))
    with patch("backend.apps.candidates.services.cv_review.get_chat_model", return_value=model):
        yield model


@pytest.fixture
def storage() -> Iterator[dict[str, bytes]]:
    objects: dict[str, bytes] = {}
    target = "backend.apps.documents.services.documents.object_storage"
    with (
        patch(
            f"{target}.upload_object",
            side_effect=lambda key, data, mime: objects.update({key: data}),
        ),
        patch(f"{target}.download_object", side_effect=lambda key: objects[key]),
        patch(f"{target}.delete_object", side_effect=lambda key: objects.pop(key)),
    ):
        yield objects


def stored_cv(
    user: User, profile: CandidateProfile, content: bytes, storage: dict[str, bytes], **extra
) -> CV:
    version = CV.objects.filter(candidate=profile).count() + 1
    key = f"documents/{user.id}/cv-{version}"
    storage[key] = content
    document = Document.objects.create(
        owner_user=user,
        type="CV",
        storage_uri=key,
        file_name=f"resume-{version}.pdf",
        mime_type="application/pdf",
        size_bytes=len(content),
        checksum=sha256(content).hexdigest(),
        scan_status="PENDING",
        uploaded_at=timezone.now(),
    )
    return CV.objects.create(
        candidate=profile, document=document, title="CV", version_number=version, **extra
    )


def analyse(client, cv_id, role="data_engineer", level="junior"):
    return client.post(
        reverse("cv-analysis-result-list"),
        {"cv": str(cv_id), "role_profile_id": role, "level": level},
        format="json",
    )


def test_candidate_lists_roles_and_other_roles_are_refused() -> None:
    user, _ = candidate()
    response = client_for(user).get(reverse("cv-review-role-list"))
    assert response.status_code == 200
    assert {row["id"]: row["label"] for row in response.json()} == {
        "data_engineer": "Data Engineer",
        "software_engineer": "Software Engineer",
    }
    assert all(row["version"] for row in response.json())

    reviewer = account("reviewer@example.test")
    recruiter(reviewer, organization("11"))
    assert client_for(reviewer).get(reverse("cv-review-role-list")).status_code == 403


def test_uploaded_docx_is_analysed_then_listed_and_retrieved(storage) -> None:
    user, profile = candidate()
    client = client_for(user)
    profile_before = model_to_dict(profile)
    upload = client.post(
        reverse("document-list"),
        {"type": "CV", "file": SimpleUploadedFile("cv.docx", render("se_good_docx"), DOCX)},
        format="multipart",
    )
    assert upload.status_code == 201
    cv = client.post(reverse("cv-list"), {"document": upload.json()["id"], "title": "CV"})
    assert cv.status_code == 201

    created = analyse(client, cv.json()["id"], "software_engineer")

    assert created.status_code == 201
    body = created.json()
    assert body["role_profile_id"] == "software_engineer"
    assert body["role_profile_version"] == "1"
    assert body["level"] == "junior"
    assert body["target_offer"] is None
    assert body["cv_draft_json"] == {}
    assert set(body["breakdown_json"]["components"]) == {
        "parseability",
        "sections",
        "skill_coverage",
        "evidence",
        "content",
        "length",
    }
    assert 0 < body["breakdown_json"]["role_fit"] <= 100
    assert float(body["overall_score"]) > 50
    listed = client.get(reverse("cv-analysis-result-list")).json()["results"]
    assert [row["id"] for row in listed] == [body["id"]]
    retrieved = client.get(reverse("cv-analysis-result-detail", args=(body["id"],)))
    assert retrieved.json()["breakdown_json"] == body["breakdown_json"]
    profile.refresh_from_db()
    assert model_to_dict(profile) == profile_before
    assert not profile.skills.exists() and not profile.experiences.exists()
    assert not profile.projects.exists() and not profile.educations.exists()


def test_scan_is_stored_with_zero_parseability(storage) -> None:
    user, profile = candidate()
    cv = stored_cv(user, profile, render("de_scan_pdf"), storage)
    response = analyse(client_for(user), cv.id)
    assert response.status_code == 201
    assert response.json()["breakdown_json"]["components"]["parseability"] == 0
    assert [issue["code"] for issue in response.json()["issues_json"]] == ["no_text_layer"]


@pytest.mark.parametrize(
    ("fixture", "role", "level", "message"),
    [
        ("de_good_pdf", "astronaut", "junior", "role"),
        ("de_good_pdf", "data_engineer", "senior", "level"),
        ("fr_pdf", "data_engineer", "junior", "English"),
        (None, "data_engineer", "junior", "PDF and DOCX"),
    ],
)
def test_invalid_requests_return_400_without_storing(
    storage, fixture, role, level, message
) -> None:
    user, profile = candidate()
    content = render(fixture) if fixture else b"\x89PNG\r\n\x1a\nimage"
    cv = stored_cv(user, profile, content, storage)
    response = analyse(client_for(user), cv.id, role, level)
    assert response.status_code == 400
    assert message in str(response.json())
    assert not CVAnalysisResult.objects.exists()


def test_other_candidates_cv_and_analysis_are_hidden(storage) -> None:
    owner, owner_profile = candidate("owner@example.test")
    other, _ = candidate("other@example.test")
    cv = stored_cv(owner, owner_profile, render("de_good_pdf"), storage)
    analysis_id = analyse(client_for(owner), cv.id).json()["id"]

    assert analyse(client_for(other), cv.id).status_code == 404
    detail = reverse("cv-analysis-result-detail", args=(analysis_id,))
    assert client_for(other).get(detail).status_code == 404
    assert client_for(other).get(reverse("cv-analysis-result-list")).json()["results"] == []
    assert CVAnalysisResult.objects.count() == 1


def test_deleted_or_purged_cv_cannot_be_analysed(storage) -> None:
    user, profile = candidate()
    client = client_for(user)
    deleted = stored_cv(user, profile, render("de_good_pdf"), storage)
    assert client.delete(reverse("cv-detail", args=(deleted.id,))).status_code == 204
    deleted.refresh_from_db()
    assert deleted.bytes_purged_at is not None
    assert analyse(client, deleted.id).status_code == 404

    purged = stored_cv(
        user, profile, render("de_good_pdf"), storage, bytes_purged_at=timezone.now()
    )
    assert analyse(client, purged.id).status_code == 400
    assert not CVAnalysisResult.objects.exists()


def test_non_candidates_cannot_analyse(storage) -> None:
    user, profile = candidate()
    cv = stored_cv(user, profile, render("de_good_pdf"), storage)
    reviewer = account("reviewer@example.test")
    recruiter(reviewer, organization("12"))
    assert analyse(client_for(reviewer), cv.id).status_code == 403
    assert client_for(reviewer).get(reverse("cv-analysis-result-list")).status_code == 403


def test_rerun_on_the_same_document_reuses_the_cached_structure(storage, chat) -> None:
    user, profile = candidate()
    cv = stored_cv(user, profile, render("de_good_pdf"), storage)
    client = client_for(user)
    chat.reply = None  # the fake now answers with a valid structure

    first = analyse(client, cv.id)
    calls = len(chat.calls)
    second = analyse(client, cv.id, "software_engineer")

    assert first.status_code == second.status_code == 201
    assert calls == 3 and len(chat.calls) == calls
    assert first.json()["breakdown_json"]["parse_degraded"] is False
    assert second.json()["breakdown_json"]["parse_degraded"] is False
    assert first.json()["breakdown_json"]["bullets"]["total"] == 8
    assert second.json()["breakdown_json"]["bullets"]["total"] == 8
    stored = client.get(reverse("cv-detail", args=(cv.id,))).json()
    assert stored["parse_status"] == "parsed"
    assert stored["parsed_data_json"]["sections"]["experience"][0]["title"] == (
        "Data Engineering Intern"
    )


def test_analysis_is_stored_degraded_when_the_model_fails(storage, chat) -> None:
    user, profile = candidate()
    cv = stored_cv(user, profile, render("de_good_pdf"), storage)
    client = client_for(user)

    first = analyse(client, cv.id)
    assert first.status_code == 201
    assert first.json()["breakdown_json"]["parse_degraded"] is True
    assert first.json()["breakdown_json"]["bullets"]["total"] == 8
    assert CVAnalysisResult.objects.filter(cv=cv).count() == 1
    assert client.get(reverse("cv-detail", args=(cv.id,))).json()["parse_status"] == "degraded"

    chat.reply = None  # Ollama is back: a degraded parse is not reused
    second = analyse(client, cv.id)
    assert second.json()["breakdown_json"]["parse_degraded"] is False
    assert len(chat.calls) == 1 + 3  # the first transport error stops further calls


@pytest.fixture
def embeddings_down() -> Iterator[None]:
    with patch(
        "backend.apps.candidates.services.cv_review.embed", side_effect=ConnectionError("down")
    ):
        yield


def first_bullet(body) -> tuple[str, str]:
    entries = body["breakdown_json"]["structure"]["entries"]
    key = next(name for name in ("experience", "projects") if entries.get(name))
    return f"{key}.0.0", entries[key][0]["bullets"][0]


def test_rewrite_then_accept_edit_reject_and_confirm_a_missing_skill(
    storage, chat, embeddings_down
) -> None:
    user, profile = candidate()
    profile_before = model_to_dict(profile)
    client = client_for(user)
    cv = stored_cv(user, profile, render("de_good_pdf"), storage)
    body = analyse(client, cv.id).json()
    detail = body["id"]
    key, original = first_bullet(body)
    first_word = original.split()[0]
    rest = original[len(first_word) :]
    chat.reply = lambda messages: SimpleNamespace(content=f"Built{rest} [X]")

    rewrite = client.post(
        reverse("cv-analysis-result-rewrite", args=(detail,)), {"bullet": key}, format="json"
    )
    assert rewrite.status_code == 200
    assert rewrite.json()["source"] == "model" and rewrite.json()["original"] == original
    proposed = rewrite.json()["text"]
    assert proposed.endswith("[X]")
    assert (
        client.get(reverse("cv-analysis-result-detail", args=(detail,))).json()["cv_draft_json"]
        == {}
    )  # nothing stored until accepted

    draft_url = reverse("cv-analysis-result-draft", args=(detail,))
    accepted = client.patch(
        draft_url, {"bullet": key, "decision": "accept", "text": proposed}, format="json"
    )
    assert accepted.status_code == 200
    assert accepted.json()["cv_draft_json"]["bullets"][key] == {
        "original": original,
        "decision": "accept",
        "text": proposed,
    }
    edited_text = proposed.replace("[X]", "for 4 teams")
    edited = client.patch(
        draft_url, {"bullet": key, "decision": "accept", "text": edited_text}, format="json"
    )
    assert edited.json()["cv_draft_json"]["bullets"][key]["text"] == edited_text
    rejected = client.patch(draft_url, {"bullet": key, "decision": "reject"}, format="json")
    assert rejected.json()["cv_draft_json"]["bullets"][key] == {
        "original": original,
        "decision": "reject",
        "text": original,
    }

    known = next(row["name"] for row in body["breakdown_json"]["skills"] if row["evidence"])
    known_skill = client.patch(draft_url, {"skill": known, "has_experience": True}, format="json")
    assert known_skill.status_code == 400  # only missing core skills are asked about

    text = "Data Engineer building pipelines."
    summary = client.patch(draft_url, {"summary": text}, format="json")
    assert summary.json()["cv_draft_json"]["summary"] == text
    unknown = {"bullet": "experience.9.9", "decision": "reject"}
    assert client.patch(draft_url, unknown, format="json").status_code == 400
    assert client.patch(draft_url, {}, format="json").status_code == 400

    profile.refresh_from_db()
    assert model_to_dict(profile) == profile_before
    assert not profile.skills.exists() and not profile.experiences.exists()


def test_missing_core_skill_question_enters_the_draft_only_after_yes(storage) -> None:
    user, profile = candidate()
    client = client_for(user)
    cv = stored_cv(user, profile, render("se_good_pdf"), storage)
    body = analyse(client, cv.id, "data_engineer").json()
    missing = [
        row["name"]
        for row in body["breakdown_json"]["skills"]
        if row["tier"] == "core" and not row["evidence"]
    ]
    assert missing
    draft_url = reverse("cv-analysis-result-draft", args=(body["id"],))
    no = client.patch(draft_url, {"skill": missing[0], "has_experience": False}, format="json")
    assert no.status_code == 200
    assert no.json()["cv_draft_json"]["confirmed_skills"] == []
    yes = client.patch(draft_url, {"skill": missing[0], "has_experience": True}, format="json")
    assert yes.json()["cv_draft_json"]["confirmed_skills"] == [missing[0]]
    assert not profile.skills.exists()


def test_rewrite_falls_back_to_the_rule_when_the_model_is_down(storage, embeddings_down) -> None:
    user, profile = candidate()
    client = client_for(user)
    cv = stored_cv(user, profile, render("de_good_pdf"), storage)
    body = analyse(client, cv.id).json()
    key, _ = first_bullet(body)
    response = client.post(
        reverse("cv-analysis-result-rewrite", args=(body["id"],)), {"bullet": key}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["source"] == "rule" and response.json()["suggestion"]
    summary = client.post(reverse("cv-analysis-result-summary", args=(body["id"],)))
    assert summary.status_code == 200 and summary.json()["source"] == "rule"


def test_other_candidates_cannot_rewrite_or_edit_the_draft(storage, embeddings_down) -> None:
    owner, owner_profile = candidate("owner@example.test")
    other, _ = candidate("other@example.test")
    cv = stored_cv(owner, owner_profile, render("de_good_pdf"), storage)
    body = analyse(client_for(owner), cv.id).json()
    key, _ = first_bullet(body)
    intruder = client_for(other)
    args = (body["id"],)
    assert (
        intruder.post(
            reverse("cv-analysis-result-rewrite", args=args), {"bullet": key}, format="json"
        ).status_code
        == 404
    )
    assert intruder.post(reverse("cv-analysis-result-summary", args=args)).status_code == 404
    assert (
        intruder.patch(
            reverse("cv-analysis-result-draft", args=args),
            {"bullet": key, "decision": "reject"},
            format="json",
        ).status_code
        == 404
    )
    assert CVAnalysisResult.objects.get().cv_draft_json == {}
