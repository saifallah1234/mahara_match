# Placement: tests/fixtures/cv_review/fake_chat.py
"""Fake chat model for CV section extraction tests (stands in for the Ollama provider)."""

import json
from types import SimpleNamespace
from typing import Any

from ai.document_intelligence.parsing.cv_reader import BULLET


class FakeChat:
    """Answers each section call faithfully: one entry per section with its bullets verbatim."""

    def __init__(self, reply=None):
        self.calls: list[tuple[list[Any], dict[str, Any]]] = []
        self.reply = reply

    def invoke(self, input, **options):  # same parameter name as the ChatModel protocol
        messages = input
        self.calls.append((messages, options))
        if self.reply is not None:
            return self.reply(messages)
        section = messages[-1][1]
        bullets = [BULLET.sub("", line) for line in section.splitlines() if BULLET.match(line)]
        entry = {"title": "", "organisation": "", "dates": "", "bullets": bullets}
        if "Example Logistics" in section:
            entry |= {
                "title": "Data Engineering Intern",
                "organisation": "Example Logistics",
                "dates": "Feb 2024 - Aug 2024",
            }
        entries = [entry]
        return SimpleNamespace(content=json.dumps({"entries": entries}))
