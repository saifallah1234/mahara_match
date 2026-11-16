# Placement: tests/e2e/test_workspace_walkthrough.py
"""One browser walk-through per role over the seed_demo accounts, at 1400×800.

Checks what a user sees: the sidebar sign-out button and the page title stay in view after
scrolling a long page, the active sidebar link carries aria-current, no API call fails and no
console error occurs on any workspace page (again at 390×844, without sideways scrolling), the
ministry pages show the chart and the highlighted gaps, recruiter search results are above the
fold, and an example question in the candidate assistant gets a reply. Needs `npm --prefix frontend
run build` first and the disposable local database (tests/README.md "Fast local run").
Screenshots land in the test's tmp_path for the manual check.
"""

import json
import re
import threading
from collections.abc import Iterator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.core.management import call_command
from playwright.sync_api import Page, expect, sync_playwright
from rest_framework_simplejwt.tokens import AccessToken

from ai.llm.providers.embeddings import EmbeddingUnavailable
from backend.apps.identity.models import User

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

DEMO = "demo.mahara.test"
# (account, a long page to scroll, every workspace page of that role)
ROLES = {
    "candidat": (
        f"candidat@{DEMO}",
        "/candidat/profil",
        [
            "/candidat",
            "/candidat/profil",
            "/candidat/cv",
            "/candidat/offres",
            "/candidat/candidatures",
            "/candidat/formations",
            "/candidat/assistant",
        ],
    ),
    "recruteur": (
        f"recruteur@{DEMO}",
        "/recruteur/offres/nouvelle",
        [
            "/recruteur",
            "/recruteur/entreprise",
            "/recruteur/offres",
            "/recruteur/offres/nouvelle",
            "/recruteur/candidatures",
            "/recruteur/entretiens",
            "/recruteur/candidats",
            "/recruteur/assistant",
        ],
    ),
    "formation": (
        f"formation@{DEMO}",
        "/formation",
        ["/formation", "/formation/programmes", "/formation/sessions", "/formation/organisme"],
    ),
    "ministere": (
        f"ministere@{DEMO}",
        "/ministere/competences",
        ["/ministere", "/ministere/competences"],
    ),
    "admin": (
        f"admin@{DEMO}",
        "/admin/referentiels",
        [
            "/admin",
            "/admin/comptes",
            "/admin/demandes",
            "/admin/organisations",
            "/admin/referentiels",
            "/admin/imports",
            "/admin/audit",
        ],
    ),
}


# The deepest element sticking out past the right edge, or "" when the page fits.
WIDEST_OVERFLOW = """() => {
  if (document.documentElement.scrollWidth <= innerWidth) return ''
  const out = [...document.querySelectorAll('body *')].filter((e) => e.getBoundingClientRect().right > innerWidth + 1)
  const e = out[out.length - 1]
  return e ? `${e.tagName}.${e.className} "${(e.textContent || '').slice(0, 60)}"` : 'unknown'
}"""


def _ollama_down(_: str) -> list[float]:
    raise EmbeddingUnavailable("The walk-through never calls Ollama.")


@pytest.fixture
def frontend() -> Iterator[str]:
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
    try:
        yield f"http://127.0.0.1:{server.server_port}/#"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _visit(page: Page, url: str, problems: list[str]) -> None:
    page.goto(url)
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    expect(page.get_by_text("Chargement…")).to_have_count(0, timeout=15000)
    assert not problems, (url, problems)


@pytest.mark.parametrize("role", list(ROLES))
def test_workspace_walkthrough(role, live_server, frontend, settings, monkeypatch, tmp_path):
    email, long_page, pages = ROLES[role]
    settings.DEBUG = True  # seed_demo refuses to run otherwise
    call_command("seed_demo", password="walkthrough-only", verbosity=0)
    monkeypatch.setattr("ai.tools.job_search.embed_query", _ollama_down)
    monkeypatch.setattr(
        "ai.agents.anetai.get_chat_model", lambda **_: pytest.fail("French replies are templates.")
    )
    token = str(AccessToken.for_user(User.objects.get(email=email)))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chromium")
        page = browser.new_page(viewport={"width": 1400, "height": 800})
        problems: list[str] = []
        page.on("pageerror", lambda error: problems.append(f"page error: {error}"))
        page.on(
            "console",
            lambda message: (
                problems.append(f"console: {message.text}") if message.type == "error" else None
            ),
        )
        page.on(
            "response",
            lambda response: (
                problems.append(f"{response.status} {response.url}")
                if "/api/" in response.url and response.status >= 400
                else None
            ),
        )

        def proxy(route):
            parts = urlsplit(route.request.url)
            if parts.path == "/api/v1/auth/token/refresh/":
                route.fulfill(
                    status=200, content_type="application/json", body=json.dumps({"access": token})
                )
            else:
                query = f"?{parts.query}" if parts.query else ""
                route.fulfill(response=route.fetch(url=live_server.url + parts.path + query))

        page.route("**/api/v1/**", proxy)

        for path in pages:
            _visit(page, frontend + path, problems)
            expect(page.locator("aside nav a[aria-current='page']")).to_have_count(1)
            page.screenshot(path=tmp_path / f"{role}{path.replace('/', '_')}.png")

        if role == "ministere":
            _visit(page, frontend + "/ministere", problems)
            expect(
                page.get_by_role("heading", name="Offres et formations par gouvernorat")
            ).to_be_visible()
            _visit(page, frontend + "/ministere/competences", problems)
            gaps = page.locator(
                "section", has=page.get_by_role("heading", name="Les trois plus grands écarts")
            )
            expect(gaps.get_by_role("listitem").first).to_be_visible()
            expect(page.get_by_text(re.compile("^Chiffres de démonstration"))).to_be_visible()
        if role == "recruteur":
            _visit(page, frontend + "/recruteur/candidats", problems)
            expect(page.locator("a[href*='/recruteur/candidats/']").first).to_be_in_viewport()
            page.get_by_role("button", name="Plus de filtres").click()
            expect(page.get_by_text("Mode de travail")).to_be_visible()

        page.set_viewport_size({"width": 390, "height": 844})
        for path in pages:
            _visit(page, frontend + path, problems)
            # The sidebar slides away on phones; wait for it so screenshots do not catch it midway.
            expect(page.get_by_role("button", name="Se déconnecter")).not_to_be_in_viewport()
            wide = page.evaluate(WIDEST_OVERFLOW)
            assert not wide, f"{path} scrolls sideways on a phone: {wide}"
            page.screenshot(
                path=tmp_path / f"phone_{role}{path.replace('/', '_')}.png", full_page=True
            )

        # A short window keeps the desktop layout and makes the seeded pages long enough to scroll.
        page.set_viewport_size({"width": 1400, "height": 400})
        _visit(page, frontend + long_page, problems)
        assert page.evaluate("document.documentElement.scrollHeight > innerHeight + 50"), (
            f"{long_page} is not long enough to check scrolling."
        )
        page.mouse.wheel(0, 100_000)
        page.wait_for_function("scrollY > 50")
        expect(page.get_by_role("button", name="Se déconnecter")).to_be_in_viewport()
        expect(page.get_by_role("heading", level=1)).to_be_in_viewport()

        if role == "candidat":
            page.set_viewport_size({"width": 1400, "height": 800})
            # Scores are calculated automatically on the first visit; no button is pressed.
            _visit(page, frontend + "/candidat/offres", problems)
            expect(
                page.locator("article").get_by_text(re.compile(r"^Compatibilité \d+ %$")).first
            ).to_be_visible(timeout=15000)
            _visit(page, frontend + "/candidat", problems)
            best = page.locator(
                "section", has=page.get_by_role("heading", name="Mes meilleures correspondances")
            )
            expect(best.get_by_text("À acquérir").first).to_be_visible()
            expect(best.get_by_text("Formation suggérée").first).to_be_visible()
            page.screenshot(path=tmp_path / "candidat_dashboard_matches.png")
            page.set_viewport_size({"width": 1400, "height": 800})
            _visit(page, frontend + "/candidat/assistant", problems)
            page.get_by_role("button", name="Quelles offres d’emploi me correspondent ?").click()
            expect(page.get_by_text(re.compile(r"^1\. .+ chez "))).to_be_visible(timeout=30000)
            page.screenshot(path=tmp_path / "candidat_assistant_reply.png")

        assert not problems, problems
        browser.close()
    print(f"Screenshots: {tmp_path}")
