# Common technical support

- `exceptions/`: future shared technical exception conventions.
- `logging/`: future logging/correlation helpers; not business audit records.
- `storage/`: future object-storage adapters; not document metadata ownership.

Keep this area domain-neutral. Application state, models, authorization decisions
and business workflows belong in their owning apps. Notifications and audit
records belong to `apps/platform/`; documents belong to `apps/documents/`.
