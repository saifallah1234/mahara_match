# Placement: ai/document_intelligence/parsing/cv_reader.py
"""Read a PDF or DOCX CV into text, sections, bullets, contacts and format risks.

Pure Python, no Django and no model: the deterministic reading used by ATS analysis.
"""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from io import BytesIO
from zipfile import BadZipFile

import docx
import pymupdf
from docx.oxml.ns import qn
from docx.table import Table
from rapidfuzz import fuzz, process

pymupdf.no_recommend_layout()  # the optional layout package would pull in onnxruntime

WORDS_PER_DOCX_PAGE = 500  # shortcut: DOCX has no layout, page count is estimated from words

HEADINGS = {
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "professional profile",
        "about me",
        "objective",
        "career objective",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "internships",
        "internship experience",
    ],
    "projects": ["projects", "personal projects", "academic projects", "selected projects"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tools"],
    "education": ["education", "academic background", "qualifications"],
    "certifications": ["certifications", "certificates", "licenses and certifications"],
    "other": [
        "languages",
        "interests",
        "hobbies",
        "awards",
        "volunteering",
        "references",
        "achievements",
    ],
}
_HEADING_LOOKUP = {phrase: key for key, phrases in HEADINGS.items() for phrase in phrases}
SAFE_FONTS = (
    "arial",
    "helvetica",
    "calibri",
    "cambria",
    "times",
    "georgia",
    "garamond",
    "verdana",
    "tahoma",
    "trebuchet",
    "segoe",
    "liberation",
    "dejavu",
    "roboto",
    "opensans",
    "open sans",
    "lato",
    "carlito",
    "caladea",
    "noto",
    "sourcesans",
    "source sans",
    "courier",
    "aptos",
    "cmr",
    "cmbx",
    "lmroman",
    "lmsans",
)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w])\+?\d[\d\s().-]{6,}\d(?![\w])")
LINK = re.compile(
    r"(?:https?://|www\.)\S+|(?:linkedin\.com|github\.com|gitlab\.com)/\S+", re.IGNORECASE
)
DATE = re.compile(
    r"\b(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?"
    r"(?:19|20)\d{2}\b|\b\d{1,2}/(?:19|20)\d{2}\b|\b(?:present|current)\b",
    re.IGNORECASE,
)
YEAR_RANGE = re.compile(r"(?:19|20)\d{2}\s*[-–/]\s*(?:19|20)\d{2}")
BULLET = re.compile(r"^\s*[•\-*▪‣–●◦·○■►✓]\s*")


class UnreadableCVError(ValueError):
    """The bytes are not a PDF or DOCX this reader can open."""


@dataclass
class CVText:
    lines: list[str]
    page_count: int
    format_risks: dict[str, list[str]]  # risk code -> details (e.g. font names)
    sections: dict[str, list[str]] = field(default_factory=dict)  # in reading order
    bullets: list[str] = field(default_factory=list)  # experience and project bullets

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def has_text_layer(self) -> bool:
        return bool(self.text.strip())


def read_cv(content: bytes) -> CVText:
    if content.startswith(b"%PDF-"):
        cv = _read_pdf(content)
    elif content.startswith(b"PK\x03\x04"):
        cv = _read_docx(content)
    else:
        raise UnreadableCVError("Only PDF and DOCX CVs can be analysed.")
    cv.sections = split_sections(cv.lines)
    cv.bullets = [
        bullet
        for key in ("experience", "projects")
        for bullet in split_bullets(cv.sections.get(key, []))
    ]
    return cv


def contacts(text: str) -> dict[str, list[str]]:
    return {
        "emails": EMAIL.findall(text),
        "phones": [
            phone
            for phone in PHONE.findall(text)
            if sum(char.isdigit() for char in phone) >= 8 and not YEAR_RANGE.fullmatch(phone)
        ],
        "links": LINK.findall(text),
        "dates": DATE.findall(text),
    }


def heading_key(line: str) -> str | None:
    cleaned = re.sub(r"[^a-z& ]", "", line.casefold()).strip()
    if not cleaned or len(cleaned) > 40 or len(cleaned.split()) > 5:
        return None
    match = process.extractOne(cleaned, _HEADING_LOOKUP, scorer=fuzz.ratio, score_cutoff=85)
    return _HEADING_LOOKUP[match[0]] if match else None


def split_sections(lines: Iterable[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in lines:
        key = heading_key(line)
        if key:
            current = key
            sections.setdefault(key, [])
        else:
            sections[current].append(line)
    return sections


def split_bullets(lines: list[str]) -> list[str]:
    if not any(BULLET.match(line) for line in lines):
        return [line for line in lines if len(line.split()) >= 6 and not DATE.search(line)]
    bullets: list[str] = []
    for line in lines:
        if BULLET.match(line):
            bullets.append(BULLET.sub("", line, count=1).strip())
        elif bullets and line[:1].islower():  # wrapped continuation of the previous bullet
            bullets[-1] = f"{bullets[-1]} {line}"
    return [bullet for bullet in bullets if bullet]


def _font_family(name: str) -> str:
    return re.sub(r"^[A-Z]{6}\+", "", name).split(",")[0].split("-")[0].strip()


def _unusual(fonts: Iterable[str]) -> list[str]:
    families = {_font_family(font) for font in fonts if font}
    return sorted(
        family
        for family in families
        if family and not any(safe in family.casefold() for safe in SAFE_FONTS)
    )


def _read_pdf(content: bytes) -> CVText:
    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise UnreadableCVError("The PDF could not be opened.") from exc
    lines: list[str] = []
    fonts: set[str] = set()
    risks: dict[str, list[str]] = {}
    images = tables = side_lines = 0
    with document:
        for page in document.pages():
            width = page.rect.width
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if not text:
                        continue
                    lines.append(text)
                    fonts.update(span["font"] for span in line["spans"] if span["text"].strip())
                    x0, _, x1, _ = line["bbox"]
                    centred = abs((x0 + x1) / 2 - width / 2) < width * 0.05
                    # Lines starting right of a third of the page that are neither centred
                    # nor dates belong to a second column (a right-aligned date is not one).
                    if x0 >= width * 0.35 and not centred and not DATE.search(text):
                        side_lines += 1
            images += len(page.get_images())
            tables += len(page.find_tables().tables)
        page_count = document.page_count
    has_text = any(line.strip() for line in lines)
    if has_text and side_lines >= 8:  # shortcut: layout heuristic, revisit with real CVs
        risks["multi_column"] = []
    if tables:
        risks["tables"] = []
    if has_text and images:  # a scan is reported as missing text, not as images
        risks["images"] = []
    if unusual := _unusual(fonts):
        risks["unusual_fonts"] = unusual
    return CVText(lines=lines, page_count=page_count, format_risks=risks)


def _read_docx(content: bytes) -> CVText:
    try:
        document = docx.Document(BytesIO(content))
    except (BadZipFile, KeyError, ValueError) as exc:
        raise UnreadableCVError("The DOCX file could not be opened.") from exc
    lines: list[str] = []
    for block in document.iter_inner_content():  # body order, so table text stays in its section
        if isinstance(block, Table):
            cells = (cell.text.strip() for row in block.rows for cell in row.cells)
            lines.extend(text for text in cells if text)
        elif block.text.strip():
            lines.append(block.text.strip())
    body = document.element.body.xml
    risks: dict[str, list[str]] = {}
    if any(
        int(cols.get(qn("w:num"), "1")) > 1
        for section in document.sections
        for cols in section._sectPr.findall(qn("w:cols"))
    ):
        risks["multi_column"] = []
    if document.tables:
        risks["tables"] = []
    if "txbxContent" in body:
        risks["text_boxes"] = []
    if "<pic:pic" in body or "<v:imagedata" in body:
        risks["images"] = []
    fonts = {run.font.name for p in document.paragraphs for run in p.runs if run.font.name}
    fonts |= {p.style.font.name for p in document.paragraphs if p.style and p.style.font.name}
    if unusual := _unusual(fonts):
        risks["unusual_fonts"] = unusual
    words = sum(len(line.split()) for line in lines)
    page_breaks = body.count('w:type="page"')
    page_count = max(page_breaks + 1, math.ceil(words / WORDS_PER_DOCX_PAGE), 1)
    return CVText(lines=lines, page_count=page_count, format_risks=risks)
