# Infrastructure boundaries

Reserved documentation-only locations: Docker packaging, PostgreSQL operations,
object storage, derived vector indexes, Neo4j graph infrastructure and observability.
No containers, services, SQL, credentials or deployment workflows are configured.

The application remains a modular monolith. Future separate worker processes
for heavy workloads do not establish independent business services or databases.
PostgreSQL schema changes belong to Django migrations, not this directory.
Provider selection and deployment topology remain open where not specified.
