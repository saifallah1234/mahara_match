<!-- Placement: data/reference/esco/README.md -->
# ESCO skills extract

`esco_skills_v1.2.1.csv.gz` (1.7 MB) holds the 13,939 skills of **ESCO v1.2.1** (released
2025-12-10) with their preferred and alternative labels in French, English and Arabic.

**This is a modified version of ESCO**: it was trimmed to the columns the application needs
(URI, skill type, reuse level, digital-collection flag, labels in three languages); the
descriptions, hierarchy and occupation links were removed.

## Licence and attribution

ESCO is the European Commission's classification of Skills, Competences and Occupations,
reused under the Commission Decision of 12 December 2011 on the reuse of Commission
documents (2011/833/EU): free of charge, for any purpose, provided that:

- the application shows: "This service uses the ESCO classification of the European
  Commission." with a link to https://ec.europa.eu/esco (done in the landing page footer
  and the workspace sidebar, in French);
- any modified version is labelled as such (this file is).

## Load it

```
uv run python backend/manage.py migrate --settings=backend.config.settings.development
uv run python backend/manage.py load_esco_skills --settings=backend.config.settings.development
```

Idempotent, about 30 seconds. Local skills whose name equals an ESCO preferred label (in any
of the three languages, also without its "(qualifier)") are linked and keep their name.
See [CV extraction](../../../docs/architecture/cv_extraction.md#skills) for the matching rules.

## Rebuild it (new ESCO version)

Download the classification packages from https://esco.ec.europa.eu/en/use-esco/download
(version, content "classification", languages fr + en + ar, file type CSV; the link arrives
by e-mail), then:

```
uv run python -m pipelines.normalization.esco_extract <folder with the 3 zips> --out data/reference/esco/esco_skills_<version>.csv.gz
```

and point `DEFAULT_EXTRACT` in `backend/apps/taxonomy/services/esco.py` at the new file.
