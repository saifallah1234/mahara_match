# Applying or enrolling discloses the candidate's identity to that organization

Status: accepted (2026-10-19)

Q19 hides a candidate's name and contact details from recruiters, even when the profile opts into
`RECRUITERS` or `PUBLIC`. Recruiters still received the submitted CV, which carries the name,
while the UI showed "Candidat 1a2b3c4d". Training managers saw only an ID for the people enrolled
in their sessions. We decided that submitting an application, or enrolling in a session, is the
candidate's consent toward that one organization. That organization then sees the candidate's
first name, last name, e-mail and limited profile for the life of the application or enrollment,
including after it reaches a terminal status. The phone number is not disclosed. Other
organizations, and discovery before any application, still follow Q19 and Q28.

## Considered options

- **Keep only the CV (status quo).** Rejected: the CV already discloses the name, so hiding it in
  the UI protected nothing and made the application board and interview scheduling unusable.
- **Disclose only when visibility is not `PRIVATE`.** Rejected: a `PRIVATE` candidate who applies
  has chosen to contact this organization. Withholding their name from it defeats the application.

## Consequences

- Application and enrollment reads for the receiving organization gain identity fields. This is
  a backend change in `recruitment` and `training`, owned by those domains (ticket 17).
- Identity stays visible on terminal applications for history. If the retention review
  (Q19, "retained personal data") shortens that, this ADR is superseded.
