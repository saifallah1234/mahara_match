# Identity migration

The initial migration includes the custom `User`, `Organization`,
`OrganizationMember` and RBAC tables. Seed baseline roles and permissions with
`python backend/manage.py seed_rbac` after migrating a new database.
