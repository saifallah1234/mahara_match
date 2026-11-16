<!-- Placement: docs/architecture/cv_extraction.md -->
# CV extraction (profile pre-filling)

Ported from the OneTech agent project (2026-11-14). A candidate analyses one of their
uploaded CVs; the result pre-fills a review form on the Profil page; nothing reaches the
profile until the candidate confirms it (CONTEXT.md: extracted information must be
confirmed by the candidate).

It only reads the CV to save typing: the CV is neither modified nor evaluated. CV critique
and improvement suggestions (ATS, `CVAnalysisResult`) are a separate, not yet built feature.
The UI calls it "Lire mon CV"; the API and code call it parsing.

```
Profil page "Lire mon CV"
  -> POST /api/v1/cvs/{id}/parse/            CV.parse_status = PROCESSING (202)
  -> background: python -m pipelines.document_processing.cv_parsing --cv-id <id>
       cv_file_for_parsing (service, MinIO)  -> file bytes
       extraction/cv_text.py                 -> markdown, links, tables (PyMuPDF; Tesseract OCR for images)
       ai/document_intelligence/parsing      -> CVExtraction (7 focused LLM calls)
       cv_adapter.py                         -> proposal (ISO dates, governorate, CEFR levels...)
       store_cv_parse_result (service)       -> CV.parsed_data_json, PARSED (or FAILED + reason)
  -> GET  /api/v1/cvs/{id}/profile-proposal/ references resolved (skill, language, education level ids)
  -> POST /api/v1/cvs/{id}/apply-proposal/   only the confirmed rows, all or nothing (201)
```

| Piece | Where |
| --- | --- |
| Text extraction | `pipelines/document_processing/extraction/cv_text.py` |
| LLM providers (Gemini -> Groq -> Ollama) | `ai/llm/providers/structured.py` |
| Schema and prompts | `ai/document_intelligence/parsing/cv_schema.py`, `cv_extractor.py` |
| Proposal (pure) | `pipelines/document_processing/cv_adapter.py` |
| Background entry point | `pipelines/document_processing/cv_parsing.py` (log: `logs/cv/<cv id>.log`) |
| Service and API | `backend/apps/candidates/services/cv_parsing.py`, CV viewset actions |
| Skills, education levels | `backend/apps/taxonomy/services/skills.py`, `education.py`, `seed_education_levels` |
| Review panel | `frontend/src/pages/candidat/CvImport.tsx`, `frontend/src/lib/cvProposal.ts` |

## Rules

- **Raw vs validated (G05):** the raw extraction and the proposal stay in `CV.parsed_data_json`,
  linked to the CV; profile records are only created by `apply-proposal`.
- **Providers (decision 2026-11-14):** with `GEMINI_API_KEY` / `GROQ_API_KEY` in `.env`, the CV
  text is sent to Google / Groq (seconds per CV). Without keys, or when they fail or hit quotas,
  the local Ollama model (`CV_OLLAMA_MODEL`, default `qwen2.5:7b`) is used: private, about
  8 minutes per CV on a CPU-only PC. The provider used is shown on the review panel.
- **Skills:** see [Skills](#skills) below. Skills already on the profile are never duplicated or
  changed. Added skills have `source = "CV"` and `validated = False`.
- **Education levels:** the Bac+N scale (with EQF reference) seeded by `seed_education_levels`;
  the LLM's degree level (bachelor, master...) maps to it.
- **Languages:** only languages present in the taxonomy (fr, en, ar today) can be added.
- One analysis per CV at a time; a PROCESSING state older than 30 minutes counts as crashed.

## Skills

The `skills` table holds the ESCO v1.2.1 skills (loaded by `load_esco_skills` from
[data/reference/esco](../../data/reference/esco/README.md)) plus **local** skills that ESCO lacks
(Docker, React, Odoo...). Names under which a skill is found are in `skill_labels`.

Tier 1 matching (`taxonomy/services/skills.py`, decision 2026-11-14): a free-text skill links to a
skill when, normalized (case, accents, spacing), it equals an ESCO **preferred** label in fr, en or
ar (also without its "(qualifier)"), or a local skill's name. A short alias table first maps common
variants (`JS` -> `JavaScript`, `k8s` -> `Kubernetes`). It is never fuzzy (fuzzy matching linked
"Docker" to "docks"), and ESCO **alternative** labels never link on their own: some are narrower
examples ("Git" is an alternative label of a broad configuration-tools skill). A name shared by
several ESCO skills links to nothing. Anything unmatched becomes a local skill when confirmed.
Measured on a real CV: 8 of 48 skills link to ESCO; most modern tech tools are not in ESCO, while
ESCO is rich for non-IT and soft skills. Meaning-based suggestions (tier 2) are not built yet.

Lists, dropdowns and the retrieval index use the working catalogue (`catalog.skills()`): local
skills plus ESCO skills in use. `GET /api/v1/skills/?search=<text>` searches all of them.

## Setup

```
uv run python backend/manage.py seed_education_levels --settings=backend.config.settings.development
uv run python backend/manage.py load_esco_skills --settings=backend.config.settings.development
```

Needs object storage (MinIO, `MINIO_*` in `.env`) for uploaded CVs, Tesseract for image CVs
(`C:\Program Files\Tesseract-OCR`, languages fra+eng), and Ollama and/or provider keys.
