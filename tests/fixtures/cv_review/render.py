# Placement: tests/fixtures/cv_review/render.py
"""Render the synthetic CV set (synthetic_cvs.yaml) to PDF or DOCX bytes for tests."""

from functools import cache
from io import BytesIO
from pathlib import Path
from typing import Any

import docx
import pymupdf
import yaml
from docx.oxml import parse_xml

FIXTURES = Path(__file__).with_name("synthetic_cvs.yaml")
PAGE_BOTTOM = 790  # A4 is 842 pt high


@cache
def _data() -> dict[str, Any]:
    return yaml.safe_load(FIXTURES.read_text(encoding="utf-8"))


def synthetic_cvs() -> list[dict[str, Any]]:
    return list(_data()["cvs"])


def cv_spec(cv_id: str) -> dict[str, Any]:
    return next(spec for spec in synthetic_cvs() if spec["id"] == cv_id)


def cv_lines(spec: dict[str, Any]) -> list[str]:
    lines = list(_data()["bases"][spec["base"]])
    lines = [line for line in lines if not any(part in line for part in spec.get("drop", []))]
    for old, new in spec.get("replace", {}).items():
        lines = [line.replace(old, new) for line in lines]
    if repeat := spec.get("repeat_bullets"):
        start = lines.index("Experience") + 2
        end = lines.index("Projects")
        lines[end:end] = lines[start:end] * repeat
    return lines + list(spec.get("append", []))


def render(cv_id: str) -> bytes:
    spec = cv_spec(cv_id)
    lines = cv_lines(spec)
    layout = spec.get("layout", "single")
    return _pdf(lines, layout) if spec["format"] == "pdf" else _docx(lines, layout)


def _png() -> bytes:
    return pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 16, 16), False).tobytes("png")


def _pdf(lines: list[str], layout: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    y = 50.0
    if layout == "two_column":
        split = lines.index("Projects")
        for column, x in ((lines[:split], 40), (lines[split:], 320)):
            y = 50.0
            for line in column:
                page.insert_textbox(pymupdf.Rect(x, y, x + 260, y + 30), line, fontsize=9)
                y += 26
        return document.tobytes()
    for line in lines:
        if y > PAGE_BOTTOM:
            page, y = document.new_page(), 50.0
        page.insert_text((50, y), line, fontsize=10)
        y += 15
    if layout == "table":
        top = y + 10
        for row in range(3):
            for col in range(3):
                rect = pymupdf.Rect(
                    50 + col * 150, top + row * 20, 200 + col * 150, top + 20 + row * 20
                )
                page.draw_rect(rect, color=(0, 0, 0), width=1)
                page.insert_text((rect.x0 + 4, rect.y1 - 6), f"Tool {row}-{col}", fontsize=9)
    if layout == "image":
        page.insert_image(pymupdf.Rect(500, 40, 530, 70), stream=_png())
    if layout == "icon_font":
        page.insert_text((50, y + 10), "4 4 4", fontsize=10, fontname="zadb")
    if layout == "scan":
        pixmap = page.get_pixmap(dpi=72)
        scanned = pymupdf.open()
        scanned.new_page().insert_image(scanned[0].rect, pixmap=pixmap)
        return scanned.tobytes()
    return document.tobytes()


TEXTBOX = (
    '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:v="urn:schemas-microsoft-com:vml"><w:pict><v:shape style="width:200pt;height:40pt">'
    "<v:textbox><w:txbxContent><w:p><w:r><w:t>Open to relocation</w:t></w:r></w:p>"
    "</w:txbxContent></v:textbox></v:shape></w:pict></w:r>"
)


def _docx(lines: list[str], layout: str) -> bytes:
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    if layout == "table":
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Tools"
        table.cell(0, 1).text = "Git"
    if layout == "textbox":
        document.add_paragraph()._p.append(parse_xml(TEXTBOX))
    if layout == "columns":
        cols = parse_xml(
            '<w:cols xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'w:num="2"/>'
        )
        document.sections[0]._sectPr.append(cols)
    if layout == "image":
        document.add_picture(BytesIO(_png()))
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
