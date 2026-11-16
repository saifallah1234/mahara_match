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

## CV review

**ATS analysis**:
A stored review of one CV against one role at one level, producing an ATS readiness, a role fit, a breakdown and a list of issues. It is improvement feedback, never a hiring decision.
_Avoid_: CV score, CV analysis result (as a name for the concept)

**ATS readiness**:
How reliably an applicant tracking system can read the CV: format, sections, length and wording quality. It does not depend on the chosen role.
_Avoid_: ATS score, ATS compatibility

**Role fit**:
How well the CV's skills and evidence cover the chosen role profile. Not the same as a match score, which is candidate-to-offer.
_Avoid_: Role match, match score

**Role profile**:
A versioned definition of one target role (core, common and bonus skills with aliases, action verbs, metric hints, example bullets). It is the reference a CV is reviewed against.
_Avoid_: Job template, virtual job description

**Evidence**:
A skill backed by a bullet in an experience or project, as opposed to a skill that only appears in the skills list.
_Avoid_: Proof, usage

**CV draft**:
The analysed CV's parsed data plus the edits the candidate accepted during review; the source from which an ATS-friendly CV file is generated. The candidate profile is not changed by it.
_Avoid_: Improved CV, new CV

## Data processing

**Pipeline**:
Background processing that moves data between systems, such as an offer import.
_Avoid_: Using it for the application board
