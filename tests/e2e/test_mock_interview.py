"""Real browser and REST journey; speech/video/storage remain explicit local doubles."""

import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.db import connections
from playwright.sync_api import expect, sync_playwright
from rest_framework_simplejwt.tokens import AccessToken

from ai.speech.providers import MockTTS, Transcript
from backend.apps.assistant.models import MockInterviewSession
from backend.apps.assistant.services.interview_jobs import run_one
from backend.apps.documents.models import Document
from backend.common.storage import object_storage
from tests.integration.assistant.conftest import local_media  # noqa: F401
from tests.integration.conftest import interview, phase3  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


@pytest.mark.parametrize("followup", [False, True])
def test_browser_interview_journey(request, live_server, followup, monkeypatch, settings, tmp_path):
    data = request.getfixturevalue("interview")
    request.getfixturevalue("local_media")
    uploads: dict[str, bytes] = {}
    store = object_storage.upload_object

    def record_upload(key, content, mime):
        uploads[key] = content
        return store(key, content, mime)

    monkeypatch.setattr(object_storage, "upload_object", record_upload)
    if followup:
        from backend.apps.assistant.services import interview_jobs

        answers = []

        class STT:
            def transcribe(self, audio, language):
                answers.append(1)
                return Transcript(
                    "à préciser" if len(answers) == 1 else "Voici mon exemple.", {"simulated": True}
                )

        monkeypatch.setattr(
            interview_jobs, "speech_provider", lambda kind: STT() if kind == "stt" else MockTTS()
        )
        settings.MOCK_INTERVIEW_DERIVATIVE_DIR = str(tmp_path)
        subprocess.run(
            [
                settings.INTERVIEW_FFMPEG,
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=64x64:d=0.2",
                "-an",
                "-c:v",
                "libx264",
                str(tmp_path / "followup.mp4"),
            ],
            check=True,
        )
    directory = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    assert (directory / "index.html").is_file(), "Build frontend before the browser test."

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def do_GET(self):
            if not Path(self.translate_path(self.path)).is_file():
                self.path = "/index.html"
            super().do_GET()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    token = str(AccessToken.for_user(data["candidate"]))

    def run_task():
        try:
            return run_one()
        finally:
            connections.close_all()

    tasks = ThreadPoolExecutor(max_workers=1)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chromium",
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--autoplay-policy=no-user-gesture-required",
                ],
            )
            context = browser.new_context(permissions=["microphone", "camera"])
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def proxy(route):
                path = urlsplit(route.request.url).path
                if path == "/api/v1/auth/token/refresh/":
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps({"access": token}),
                    )
                else:
                    route.fulfill(
                        response=route.fetch(
                            url=live_server.url
                            + path
                            + (
                                "?" + urlsplit(route.request.url).query
                                if urlsplit(route.request.url).query
                                else ""
                            )
                        )
                    )

            page.route("**/api/v1/**", proxy)
            page.goto(
                f"http://127.0.0.1:{server.server_port}/#/candidat/entretiens-blancs?offer={data['offer'].pk}"
            )
            try:
                page.get_by_role("button", name="Préparer l’entretien", exact=True).click(
                    timeout=30000
                )
            except Exception as exc:
                raise AssertionError((page.locator("body").inner_text(), errors)) from exc
            expect(page.get_by_text("État : Préparation", exact=True)).to_be_visible()
            for _ in range(20):
                if not tasks.submit(run_task).result():
                    break
            expect(
                page.get_by_role("button", name="Annuler l’entretien", exact=True)
            ).to_be_visible()
            page.get_by_role("button", name="Commencer", exact=True).click()
            expect(page.get_by_text("État : Introduction", exact=True)).to_be_visible()
            expect(page.get_by_text("Question 1/3", exact=True)).not_to_be_visible()
            interviewer = page.get_by_role("region", name="Recruteur virtuel").locator("video")
            expect(interviewer).to_be_visible()
            frame = interviewer.bounding_box()
            camera = page.get_by_role("region", name="Vous").get_by_text("Votre caméra s’activera")
            assert frame and frame["width"] > 280 and frame["height"] > 500
            assert abs(frame["height"] - (camera.bounding_box() or {"height": 0})["height"]) < 2
            page.get_by_role("button", name="Lire", exact=True).click()
            for position in [1, "followup", 2, 3] if followup else [1, 2, 3]:
                expect(page.get_by_text("État : Question", exact=True)).to_be_visible()
                expect(
                    page.get_by_text(
                        "Relance" if position == "followup" else f"Question {position}/3",
                        exact=True,
                    )
                ).to_be_visible()
                page.get_by_role("button", name="Lire", exact=True).click()
                if position == "followup":
                    page.wait_for_timeout(350)
                    assert page.locator("video").evaluate("video => video.muted && video.ended")
                    assert page.locator("audio").evaluate("audio => !audio.ended")
                    expect(
                        page.get_by_role("button", name="Démarrer l’enregistrement")
                    ).not_to_be_visible()
                expect(page.get_by_label("Aperçu de votre caméra")).to_be_visible()
                expect(
                    page.get_by_text("Seul l’audio est envoyé ; la vidéo reste sur votre appareil.")
                ).to_be_visible()
                page.get_by_role("button", name="Démarrer l’enregistrement", exact=True).click()
                expect(page.get_by_role("timer")).to_be_visible()
                page.wait_for_timeout(1100)
                page.get_by_role("button", name="Arrêter l’enregistrement", exact=True).click()
                expect(page.get_by_label("Revoir votre réponse")).to_be_visible()
                expect(page.get_by_role("button", name="Réenregistrer", exact=True)).to_be_visible()
                if position == 1:
                    page.get_by_role("button", name="Réenregistrer", exact=True).click()
                    page.wait_for_timeout(1100)
                    page.get_by_role("button", name="Arrêter l’enregistrement", exact=True).click()
                    expect(page.get_by_label("Revoir votre réponse")).to_be_visible()
                page.get_by_role("button", name="Envoyer la réponse", exact=True).click()
                expect(page.get_by_text("État : Analyse", exact=True)).to_be_visible()
                for _ in range(20):
                    if not tasks.submit(run_task).result():
                        break
                if position == 1:
                    page.reload()
            expect(page.get_by_text("Votre retour", exact=True)).to_be_visible(timeout=15000)
            page.get_by_role("button", name="Lire", exact=True).click()
            page.wait_for_function("document.querySelector('audio')?.ended === true")
            assert page.locator("video").evaluate("video => video.muted")
            assert (
                tasks.submit(lambda: MockInterviewSession.objects.get().status).result()
                == "COMPLETED"
            )
            assert (
                tasks.submit(
                    lambda: (
                        MockInterviewSession.objects.get()
                        .turns.filter(kind="MAIN", answer_message__isnull=False)
                        .count()
                    )
                ).result()
                == 3
            )
            context.close()
            browser.close()
        recordings = tasks.submit(
            lambda: list(
                Document.objects.filter(type="INTERVIEW_RECORDING").values_list(
                    "storage_uri", flat=True
                )
            )
        ).result()
        assert len(recordings) == (4 if followup else 3)
        path = tmp_path / "answer.webm"

        def probe(stream):
            return subprocess.run(
                [settings.INTERVIEW_FFMPEG, "-v", "error", "-i", str(path)]
                + ["-map", f"0:{stream}:0", "-f", "null", "-"],
                capture_output=True,
            )

        for key in recordings:
            path.write_bytes(uploads[key])
            assert probe("a").returncode == 0
            video = probe("v")
            assert video.returncode != 0 and b"matches no streams" in video.stderr
    finally:
        tasks.submit(connections.close_all).result()
        tasks.shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
