# Mahara Match

Mahara Match supports the employment journey in Tunisia: candidate preparation,
explainable recommendations, recruitment follow-up and training orientation.
People retain responsibility for recruitment decisions.

The ANETI employment advisor is the system's AI agent for recommendations and CV
corrections/improvements, as clarified by the user on 2026-09-20. See
[CONTEXT.md](CONTEXT.md) and decision Q22 in the
[question register](docs/architecture/open_questions.md) for the source reconciliation.

This repository currently contains **architecture, documentation and development
tooling only**. There is no initialized Django project, API, database schema, AI
implementation, pipeline, deployment or application test suite.

## Start here

1. Read [CONTEXT.md](CONTEXT.md) and [AGENT.md](AGENT.md).
2. Consult the [logical data model](mahara_match_data_modeling.md) and
   [preliminary specification](Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf).
3. Read the [architecture](docs/architecture/overview.md),
   [domain ownership](docs/architecture/domain_boundaries.md), and
   [open questions](docs/architecture/open_questions.md).
4. Follow the [team workflow](docs/team/development_workflow.md).
5. Use the [collaborative implementation roadmap](docs/team/implementation_roadmap.md)
   and [Phase 1 data/backend execution plan](docs/team/phase_01_data_backend.md)
   for assignments, future file locations, decision gates and merge order.

## Development environment

Install Python 3.12 and uv. From the repository root:

```bash
uv sync --locked
```

The development group is installed by default. `uv.lock` records exact resolved
versions; `pyproject.toml` declares the tools. Runtime dependencies are deferred.
pytest-django may bring Django transitively into the development environment;
this does not initialize Django or choose the future runtime dependency policy.

When working in a Git checkout, install hooks with:

```bash
uv run --frozen pre-commit install
```

Git initialization and remote setup are separate team tasks. No remote, branches,
or hooks are created automatically by this scaffold.

## Verification

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy .
uv run --frozen pytest
```

The equivalent commands inside the activated environment are `ruff check .`,
`ruff format --check .`, `mypy .`, and `pytest`.
Ruff and mypy currently check configuration and empty package markers only.
**pytest exits with code 5 because no tests exist yet.** Do not hide this with a
dummy test or reinterpret it as a passing application test suite. Add real tests
with implementation. Django settings and mypy plugins are intentionally unset.
Once meaningful tests exist, use `uv run --frozen pytest --cov --cov-report=term-missing`.
No coverage target is imposed on an empty scaffold.

## Repository map

| Location | Responsibility |
| --- | --- |
| `backend/apps/` | Business domains, future API/services/ORM boundaries |
| `backend/config/` | Future Django configuration, currently empty |
| `backend/common/` | Domain-neutral technical helpers only |
| `ai/` | Future agents, workflows, retrieval, document intelligence and evaluation |
| `pipelines/` | Future data processing and background orchestration |
| `infrastructure/` | Future deployment and storage infrastructure boundaries |
| `tests/` | Unit, integration and end-to-end test locations |
| `docs/` | Architecture, persistence, AI, workflows and collaboration |
| `scripts/` | Reserved development/maintenance commands |
| `.github/workflows/` | Reserved automation; no executable workflows yet |

Empty folders are retained using `.gitkeep`; reserved product areas have scope
READMEs. Empty `__init__.py` files mark only the three top-level Python packages.
