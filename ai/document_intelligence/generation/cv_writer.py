# Placement: ai/document_intelligence/generation/cv_writer.py
"""Write the CV draft as an ATS-friendly DOCX or PDF.

One column, standard English headings in the role's section order, plain "•" bullets, no tables,
icons or images, and a real text layer. Content comes from the original CV's sections (the ticket
01 reader) with the candidate's accepted rewrites, summary and confirmed skills applied.
Pure Python: bytes in, bytes out, nothing is stored.
"""

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import docx
import pymupdf
from docx.shared import Pt

from ai.document_intelligence.ats.analysis import SECTION_LABELS
from ai.document_intelligence.ats.profiles import LevelConfig, RoleProfile
from ai.document_intelligence.ats.rewrite import PLACEHOLDER
from ai.document_intelligence.parsing.cv_reader import BULLET, read_cv

FORMATS = ("pdf", "docx")
LABELS = {**SECTION_LABELS, "other": "Additional Information"}
ORDER = tuple(LABELS)
ENTRY_SECTIONS = ("experience", "projects", "education", "certifications")

Item = tuple[str, str]  # (kind, text): kind is "name", "text", "entry" or "bullet"
Block = tuple[str | None, list[Item]]  # (heading, items); the header has no heading


@dataclass(frozen=True)
class GeneratedCV:
    content: bytes
    placeholders: int  # unresolved [X] placeholders: warn, do not block
    missing_sections: list[str]  # sections the level requires that the CV still lacks


def generate_cv(
    original: bytes, draft: dict[str, Any], role: RoleProfile, level: LevelConfig, file_format: str
) -> GeneratedCV:
    if file_format not in FORMATS:
        raise ValueError(f"Unknown format {file_format!r}; use pdf or docx.")
    sections = _sections(read_cv(original).sections, draft)
    order = [key for key in role.section_priority if key in sections]
    order += [key for key in ORDER if key in sections and key not in order]
    blocks: list[Block] = [(None, sections.get("header", []))] + [
        (LABELS[key], sections[key]) for key in order
    ]
    text = "\n".join(line for _, items in blocks for _, line in items)
    write = _pdf if file_format == "pdf" else _docx
    return GeneratedCV(
        content=write(blocks),
        placeholders=len(PLACEHOLDER.findall(text)),
        missing_sections=[key for key in level.required_sections if key not in sections],
    )


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".").casefold()


def _sections(read: dict[str, list[str]], draft: dict[str, Any]) -> dict[str, list[Item]]:
    rewrites = {
        _normal(choice["original"]): choice["text"]
        for choice in (draft.get("bullets") or {}).values()
        if choice.get("decision") == "accept" and choice.get("text")
    }
    sections: dict[str, list[Item]] = {}
    for key, lines in read.items():
        items: list[Item] = []
        for line in lines:
            if BULLET.match(line):
                items.append(("bullet", BULLET.sub("", line, count=1).strip()))
            elif items and items[-1][0] == "bullet" and line[:1].islower():
                items[-1] = ("bullet", f"{items[-1][1]} {line.strip()}")  # wrapped bullet
            else:
                # An entry starts the section or follows a bullet; its other lines are notes.
                entry = key in ENTRY_SECTIONS and (not items or items[-1][0] == "bullet")
                kind = "entry" if entry else "text"
                items.append((kind, line.strip()))
        items = [(kind, rewrites.get(_normal(text), text)) for kind, text in items]
        if items or key == "header":
            sections[key] = items
    if sections.get("header"):
        sections["header"][0] = ("name", sections["header"][0][1])
    if summary := draft.get("summary"):
        sections["summary"] = [("text", summary)]
    listed = " ".join(text for _, text in sections.get("skills", [])).casefold()
    if added := [s for s in draft.get("confirmed_skills") or [] if s.casefold() not in listed]:
        skills = sections.setdefault("skills", [])
        if skills and skills[-1][0] == "text":
            skills[-1] = ("text", ", ".join([skills[-1][1].rstrip(" ,."), *added]))
        else:
            skills.append(("text", ", ".join(added)))
    return sections


# PDF: A4, embedded Helvetica-compatible fonts (TextWriter keeps "•", "–" and "’" in the text layer).
PAGE = pymupdf.paper_rect("a4")
MARGIN, INDENT, BOTTOM = 50.0, 12.0, PAGE.height - 50.0
STYLE = {  # kind: (bold, size, space before)
    "name": (True, 16.0, 0.0),
    "heading": (True, 12.0, 10.0),
    "entry": (True, 10.0, 4.0),
    "text": (False, 10.0, 0.0),
    "bullet": (False, 10.0, 0.0),
}


def _wrap(text: str, font: pymupdf.Font, size: float, width: float) -> list[str]:
    """Greedy wrap that prefers a lowercase word at the start of each continuation line.

    The reader joins a wrapped bullet line to its bullet only when the line starts lowercase.
    shortcut: a run of 6+ capitalised words at a break still splits the bullet on read-back;
    revisit if real drafts hit it.
    """
    lines: list[list[str]] = [[]]
    for word in text.split():
        line = lines[-1]
        if not line or font.text_length(" ".join([*line, word]), size) <= width:
            line.append(word)
            continue
        cut = len(line)
        if not word[:1].islower():
            cut = next(
                (
                    i
                    for i in range(len(line) - 1, max(len(line) - 6, 0), -1)
                    if line[i][:1].islower()
                ),
                cut,
            )
        lines[-1], carry = line[:cut], line[cut:]
        lines.append([*carry, word])
    return [" ".join(line) for line in lines if line]


def _pdf(blocks: list[Block]) -> bytes:
    fonts = {False: pymupdf.Font("helv"), True: pymupdf.Font("hebo")}
    document = pymupdf.open()
    page = document.new_page(width=PAGE.width, height=PAGE.height)
    writer: pymupdf.TextWriter | None = None
    y = MARGIN
    writers: list[tuple[pymupdf.Page, pymupdf.TextWriter]] = []

    def put(text: str, kind: str) -> None:
        nonlocal page, writer, y
        bold, size, before = STYLE[kind]
        x = MARGIN + (INDENT if kind == "bullet" else 0.0)
        width = PAGE.width - MARGIN - x
        for index, line in enumerate(_wrap(text, fonts[bold], size, width)):
            y += (before if index == 0 else 0.0) + size * 1.35
            if writer is None or y > BOTTOM:
                if writer is not None:
                    page = document.new_page(width=PAGE.width, height=PAGE.height)
                    y = MARGIN + size * 1.35
                writer = pymupdf.TextWriter(page.rect)
                writers.append((page, writer))
            prefix = "• " if kind == "bullet" and index == 0 else ""
            start = x - (fonts[bold].text_length(prefix, size) if prefix else 0.0)
            writer.append((start, y), prefix + line, font=fonts[bold], fontsize=size)

    for heading, items in blocks:
        if heading:
            put(heading, "heading")
        for kind, text in items:
            put(text, kind)
    for target, text_writer in writers:
        text_writer.write_text(target)
    return bytes(document.tobytes(garbage=3, deflate=True))


def _docx(blocks: list[Block]) -> bytes:
    document = docx.Document()
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(10.5)
    for heading, items in blocks:
        if heading:
            run = document.add_paragraph().add_run(heading)
            run.bold, run.font.size = True, Pt(12)
        for kind, text in items:
            paragraph = document.add_paragraph()
            run = paragraph.add_run(f"• {text}" if kind == "bullet" else text)
            run.bold = kind in ("name", "entry")
            if kind == "name":
                run.font.size = Pt(16)
            if kind == "bullet":
                paragraph.paragraph_format.left_indent = Pt(12)
                paragraph.paragraph_format.first_line_indent = Pt(-8)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
