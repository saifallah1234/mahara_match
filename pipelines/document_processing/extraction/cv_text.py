# Placement: pipelines/document_processing/extraction/cv_text.py
"""CV file -> markdown text, hyperlinks and tables (no interpretation).

Ported from the OneTech agent project (cv_parser.py), working on bytes instead of
a path. PDFs are converted with pymupdf4llm (text layer, OCR only where a page has
no text). JPEG/PNG CVs are scanned images: they go through Tesseract OCR, which must
be installed (Windows default: C:\\Program Files\\Tesseract-OCR, languages fra+eng).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

PDF = "application/pdf"
IMAGES = {"image/jpeg", "image/png"}
OCR_LANGUAGES = "fra+eng"
_WINDOWS_TESSDATA = Path(r"C:\Program Files\Tesseract-OCR\tessdata")


class UnsupportedCVFile(ValueError):
    """The file type cannot be read as a CV."""


class EmptyCVText(ValueError):
    """No text could be read (blank scan, image-only PDF without OCR...)."""


@dataclass
class CVText:
    markdown: str
    links: list[str] = field(default_factory=list)
    tables: list[list[list[str | None]]] = field(default_factory=list)


def read_cv(content: bytes, mime_type: str) -> CVText:
    import pymupdf

    _configure_tesseract()
    if mime_type == PDF:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            result = CVText(
                markdown=_markdown(document, force_ocr=False),
                links=_links(document),
                tables=_tables(document),
            )
    elif mime_type in IMAGES:
        with pymupdf.open() as document:
            pixmap = pymupdf.Pixmap(content)
            if pixmap.alpha:  # OCR needs an image without transparency
                pixmap = pymupdf.Pixmap(pixmap, 0)
            page = document.new_page(width=pixmap.width, height=pixmap.height)
            page.insert_image(page.rect, pixmap=pixmap)
            result = CVText(markdown=_markdown(document, force_ocr=True))
    else:
        raise UnsupportedCVFile(f"Cannot read a CV of type {mime_type!r}.")

    if len(result.markdown.strip()) < 30:
        raise EmptyCVText("No readable text was found in this CV.")
    return result


def _configure_tesseract() -> None:
    if not os.environ.get("TESSDATA_PREFIX") and _WINDOWS_TESSDATA.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(_WINDOWS_TESSDATA)


def _markdown(document: object, *, force_ocr: bool) -> str:
    import pymupdf4llm  # type: ignore[import-untyped]  # ships no type information

    text: str = pymupdf4llm.to_markdown(
        document, force_ocr=force_ocr, ocr_language=OCR_LANGUAGES, show_progress=False
    )
    return text


def _links(document: object) -> list[str]:
    links: list[str] = []
    for page in document:  # type: ignore[attr-defined]
        for link in page.get_links():
            uri = link.get("uri")
            if uri and uri not in links:
                links.append(uri)
    return links


def _tables(document: object) -> list[list[list[str | None]]]:
    tables: list[list[list[str | None]]] = []
    for page in document:  # type: ignore[attr-defined]
        found = list(page.find_tables(strategy="lines_strict").tables)
        if not found:  # borderless CV templates: detect columns from text positions
            found = list(page.find_tables(strategy="text").tables)
        for table in found:
            rows = table.extract()
            if rows and any(any(cell for cell in row) for row in rows):
                tables.append([[_clean_cell(cell) for cell in row] for row in rows])
    return tables


def _clean_cell(cell: str | None) -> str | None:
    if not cell:
        return cell
    cell = cell.replace("<br>", " ").replace("<br/>", " ")
    cell = re.sub(r"\*\*|_", "", cell)
    return re.sub(r"\s+", " ", cell).strip()
