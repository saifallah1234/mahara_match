# Identity migration integration gate

The custom `User` must be created in the identity app's first migration. The same
app also owns `Organization` and `OrganizationMember`, whose model files are assigned
to Person 4 and are not present yet.

Do not generate or hand-write `0001_initial.py` until those P4 models are merged.
Person 1 then generates and reviews the complete initial identity migration and the
following RBAC seed migration from the integrated model state.
