# Placement: tests/unit/pipelines/test_esco_extract.py
"""Trimmed trilingual extract built from ESCO's per-language CSV packages."""

import csv
import gzip
from pathlib import Path

from pipelines.normalization.esco_extract import build_rows, write_extract

HEADER = (
    "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,altLabels,hiddenLabels,status\n"
)


def _package(root: Path, lang: str, rows: list[str], digital: list[str] | None = None) -> None:
    folder = root / lang
    folder.mkdir(parents=True)
    (folder / f"skills_{lang}.csv").write_text(HEADER + "".join(rows), encoding="utf-8")
    digital_rows = "".join(f"KnowledgeSkillCompetence,{uri},x,released\n" for uri in digital or [])
    (folder / f"digitalSkillsCollection_{lang}.csv").write_text(
        "conceptType,conceptUri,preferredLabel,status\n" + digital_rows, encoding="utf-8"
    )


def test_one_row_per_skill_with_three_languages(tmp_path: Path) -> None:
    uri = "http://data.europa.eu/esco/skill/abc"
    _package(
        tmp_path,
        "fr",
        [f'Skill,{uri},knowledge,sector-specific,Python (programmation),"Python3\nPy",,released\n']
        * 2,
    )
    _package(
        tmp_path,
        "en",
        [f'Skill,{uri},knowledge,sector-specific,Python (programming),"Python3",,released\n'],
        [uri],
    )
    _package(tmp_path, "ar", [f"Skill,{uri},knowledge,sector-specific,بايثون,,,released\n"])

    rows = build_rows(tmp_path)

    assert len(rows) == 1  # duplicated source rows collapse
    row = rows[0]
    assert (row["preferred_fr"], row["preferred_en"], row["preferred_ar"]) == (
        "Python (programmation)",
        "Python (programming)",
        "بايثون",
    )
    assert row["alternatives_fr"] == "Python3\nPy" and row["digital"] == "1"

    out = tmp_path / "out.csv.gz"
    write_extract(rows, out)
    with gzip.open(out, "rt", encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle))[0]["alternatives_fr"] == "Python3\nPy"
