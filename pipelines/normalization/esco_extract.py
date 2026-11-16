# Placement: pipelines/normalization/esco_extract.py
"""Build the trimmed, trilingual ESCO skills file committed in data/reference/esco/.

The official download (https://esco.ec.europa.eu/en/use-esco/download, one CSV package
per language, delivered by e-mail link) is about 30 MB per language. This keeps what the
application needs: one row per skill with its URI, type, reuse level, digital flag, and
preferred + alternative labels in French, English and Arabic.

    uv run python -m pipelines.normalization.esco_extract <folder with the 3 zips or folders> \
        --out data/reference/esco/esco_skills_v1.2.1.csv.gz

Pure Python, no Django. The result is a modified (trimmed) version of ESCO and must be
labelled as such (ESCO licence; see data/reference/esco/README.md).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

LANGUAGES = ("fr", "en", "ar")
COLUMNS = (
    "uri",
    "skill_type",
    "reuse_level",
    "digital",
    *(f"preferred_{lang}" for lang in LANGUAGES),
    *(f"alternatives_{lang}" for lang in LANGUAGES),
)


def _csv_rows(source: Path, lang: str, name: str) -> Iterator[dict[str, str]]:
    """Rows of `<name>_<lang>.csv` from an extracted folder or a downloaded zip."""
    file_name = f"{name}_{lang}.csv"
    folder_match = list(source.glob(f"**/{file_name}"))
    if folder_match:
        with folder_match[0].open(encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)
        return
    for archive in source.glob(f"*{lang}*.zip"):
        with zipfile.ZipFile(archive) as bundle:
            member = next((m for m in bundle.namelist() if m.endswith(file_name)), None)
            if member:
                with bundle.open(member) as raw:
                    yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
                return
    raise FileNotFoundError(f"{file_name} not found in {source}")


def build_rows(source: Path) -> list[dict[str, str]]:
    skills: dict[str, dict[str, str]] = {}
    for lang in LANGUAGES:
        for row in _csv_rows(source, lang, "skills"):
            entry = skills.setdefault(
                row["conceptUri"],
                {
                    "uri": row["conceptUri"],
                    "skill_type": row["skillType"],
                    "reuse_level": row["reuseLevel"],
                    "digital": "0",
                },
            )
            entry[f"preferred_{lang}"] = row["preferredLabel"].strip()
            alternatives = dict.fromkeys(
                a.strip() for a in row["altLabels"].splitlines() if a.strip()
            )
            entry[f"alternatives_{lang}"] = "\n".join(alternatives)
    for row in _csv_rows(source, "en", "digitalSkillsCollection"):
        if row["conceptUri"] in skills:
            skills[row["conceptUri"]]["digital"] = "1"
    return [skills[uri] for uri in sorted(skills)]


def write_extract(rows: list[dict[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8", newline="", compresslevel=9) as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in COLUMNS} for row in rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the trimmed trilingual ESCO skills file.")
    parser.add_argument("source", type=Path, help="folder with the fr/en/ar CSV zips or folders")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    rows = build_rows(args.source)
    write_extract(rows, args.out)
    digital = sum(row["digital"] == "1" for row in rows)
    print(f"{len(rows)} skills ({digital} digital) written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
