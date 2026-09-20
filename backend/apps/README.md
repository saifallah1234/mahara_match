# Business domains

Each defined domain owns its API boundary, application services and future ORM
models. These are directories only, not initialized Django apps. See the complete
[entity ownership map](../../docs/architecture/domain_boundaries.md).

The `platform/` directory is to be imported through a qualified backend namespace
when implementation begins, never as top-level `platform` (a Python standard
library name). Do not add `backend/apps/` to Python's module search path.

`guidance/`, `reporting/` and `community/` reserve documented future scope only.
No model is inferred from their names or descriptions.
