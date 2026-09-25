# Identity migration integration gate

The custom `User`, `Organization`, and `OrganizationMember` models are all owned by
the identity app and must be included in its first migration. The organization and
membership models are integrated with the identity RBAC implementation. Generate
and review the initial identity migration and the following RBAC seed migration once
the integrated model state is approved for migration generation.
