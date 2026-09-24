import uuid

from backend.apps.training.services.contracts import EnrollmentDTO, ProgramDTO


def test_program_dto_instantiation():
    org_id = uuid.uuid4()
    dto = ProgramDTO(
        organization_id=org_id,
        title="Python Deep Dive",
        description="Advanced course",
        level="ADVANCED",
        delivery_mode="ONLINE",
        status="ACTIVE",
        is_paid=True,
        price=199.99,
    )
    assert dto.organization_id == org_id
    assert dto.title == "Python Deep Dive"
    assert dto.is_paid is True
    assert dto.price == 199.99


def test_enrollment_dto_defaults():
    session_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    dto = EnrollmentDTO(session_id=session_id, candidate_id=candidate_id)

    assert dto.session_id == session_id
    assert dto.candidate_id == candidate_id
    assert dto.status == "REGISTERED"
