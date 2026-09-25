# Training integration gate

PostgreSQL model, migration, service and HTTP tests (capacity limits, duplicate
enrollment handling, RBAC-scoped queries) are added once Person 4's `Organization`
model lands and `makemigrations` can run for the whole project. Until then these
behaviors are only verified indirectly through the unit-level contract, serializer
and route tests in `tests/unit/backend/training/`.