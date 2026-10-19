import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder

from backend.apps.assistant.models import MockInterviewSession
from backend.apps.candidates.services.records import interview_profile_evidence
from backend.apps.recruitment.services.job_offers import interview_offer_evidence


def interview_evidence(session: MockInterviewSession) -> dict[str, Any]:
    actor = session.candidate.user
    candidate = interview_profile_evidence(actor, session.cv_id)
    cv = candidate.get("cv")
    missing = []
    if not cv or not cv["parsed_data"]:
        missing.append("No stored CV parsing results; no new CV extraction was performed.")
    if cv and len(json.dumps(cv["parsed_data"], cls=DjangoJSONEncoder)) > 12000:
        cv["parsed_data"] = None
        missing.append("Stored CV parsing exceeds the bounded evidence budget.")
    if not candidate["skills"]:
        missing.append("No recorded candidate skills.")
    offer = interview_offer_evidence(actor, session.offer_id)
    if not offer["company"]:
        missing.append("Actual employer name is not recorded.")
    return json.loads(
        json.dumps(
            {"candidate": candidate, "offer": offer, "missing_evidence": missing},
            cls=DjangoJSONEncoder,
        )
    )
