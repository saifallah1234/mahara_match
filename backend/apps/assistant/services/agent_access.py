"""Who may run the ANETI agent, and in which role.

Candidates with a profile run candidate routes; verified recruiters run recruiter
routes. A user holding both roles is assumed impossible in this iteration, and the
candidate role is checked first. Training managers, ministry and admin are refused.
"""

from typing import Literal

from backend.apps.candidates.services.discovery import list_candidates
from backend.apps.candidates.services.records import own_profile, require_candidate
from backend.apps.identity.models import User
from backend.common.exceptions import DomainPermissionError

AgentRole = Literal["candidate", "recruiter"]


def agent_role(actor: User) -> AgentRole:
    try:
        require_candidate(actor)
    except DomainPermissionError:
        pass
    else:
        own_profile(actor)  # A candidate without a profile keeps the existing not-found error.
        return "candidate"
    list_candidates(actor)  # Raises DomainPermissionError unless a verified recruiter.
    return "recruiter"
