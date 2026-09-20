# Backend boundary

Future Django + Django REST Framework modular monolith. No project initialization
has been performed. `config/` reserves settings and entrypoints, `apps/` owns
business domains, and `common/` contains domain-neutral technical support.

Future request path: **API → application service → Django ORM → PostgreSQL**.
Transport code does not implement business rules or mutate models directly.
Services enforce authorization and invariants for API, AI-tool and pipeline callers.

See [domain ownership](../docs/architecture/domain_boundaries.md) and
[persistence strategy](../docs/database/persistence_strategy.md).
