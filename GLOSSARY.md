# Mahara Match

Employment, skills and training matching for Tunisia: candidates, recruiters, training
providers, the ministry and administrators share one platform.

## Recruitment

**Application board**:
The recruiter's view of every application to their organization's offers, grouped by status.
_Avoid_: Pipeline, kanban

**Applicant identity**:
The candidate's first name, last name and e-mail, disclosed to one organization because the
candidate applied to its offer or enrolled in its session. It stays visible for the life of
that application or enrollment, terminal statuses included.
_Avoid_: Contact details, candidate reference

**Limited profile**:
The redacted part of a candidate profile (headline, skills, experiences, education,
governorate, preferences) that recruiters may read when the candidate opted into
`RECRUITERS` or `PUBLIC` visibility, or applied to their offer.
_Avoid_: Public profile, redacted CV

## Matching

**Match score**:
A stored, versioned compatibility score and skill explanation between one candidate and one
offer, recalculated on request.
_Avoid_: Recommendation, compatibility (as a noun for the record)

**Agent suggestion**:
An offer or training program the AI advisor proposes during a conversation; it is never
stored as a match score.
_Avoid_: Match, recommendation record

## Organizations

**Organization member**:
A user attached to an organization and therefore able to act on its offers, applications or
sessions. Only an administrator adds or removes one; members can see each other.
_Avoid_: Colleague, staff, employee

## Data processing

**Pipeline**:
Background processing that moves data between systems, such as an offer import.
_Avoid_: Using it for the application board
