# Identity integration gate

PostgreSQL model, migration, service and HTTP tests are added when Person 4's
`Organization` and `OrganizationMember` models are merged and Person 1 can generate
the shared `identity/0001_initial.py`. Until then, creating a fake organization model
or weakening `UserRole.organization` to a bare UUID would violate the agreed domain
ownership and referential-integrity contract.
