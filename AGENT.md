# Instructions for future coding agents

1. Read [CONTEXT.md](CONTEXT.md) before changing this repository.
2. Consult the [data model](mahara_match_data_modeling.md) and
   [specification PDF](Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf) when requirements matter.
   Apply recorded user clarifications: the ANETI employment advisor is the system's
   AI agent for recommendations and CV assistance, not a human account role (Q22).
   Do not infer human advisor accounts or assignments from the superseded source wording.
3. Preserve the modular monolith and [domain boundaries](docs/architecture/domain_boundaries.md).
4. Use Django ORM and future Django migrations as the relational schema authority.
   Do not create competing SQL schemas or a second ORM.
5. Never let agents or tools access relational databases or import Django models
   directly. Use authorized application services.
6. Keep business services in `backend/`, AI capabilities in `ai/`, and data
   processing/orchestration in `pipelines/`.
7. Never introduce duplicate domain concepts. Check the ownership map first.
8. Avoid unnecessary dependencies. Explain additions and update `pyproject.toml`
   and `uv.lock` together; keep runtime additions scoped to the feature.
9. Run Ruff, mypy and relevant tests when implementation begins. Report actual
   results and limitations, including an empty test suite.
10. Update architecture documentation and CONTEXT.md when decisions change.
11. Document ambiguity in [open_questions.md](docs/architecture/open_questions.md)
    with a source reference instead of inventing business rules.
12. Avoid unrelated module changes. Coordinate shared contracts and migration
    changes with the relevant owners.

## Current stage and future verification

The foundation contains no functionality. Do not infer that README descriptions,
empty directories, configuration names or source logical tables already exist as
implemented features. Feature implementation requires a subsequent task.

Expected commands from an activated development environment:

```bash
ruff check .
ruff format --check .
mypy .
pytest
```

Alternatively prefix each with `uv run --frozen`. pytest currently collects no
tests and returns exit code 5; no fake tests or fabricated Django settings should
be added to make that appear successful. Do not add Black.

Confirm external actions with the user when implementing the product's agent
workflows, as required by the specification. This product rule is distinct from
authorization to edit repository files.
