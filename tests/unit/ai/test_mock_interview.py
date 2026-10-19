import pytest

from ai.workflows.mock_interview import (
    MockInterviewModel,
    build_interview_graph,
    validate_feedback,
    validate_questions,
)


def test_graph_uses_injected_evidence_and_three_questions():
    evidence = {"offer": {"title": "Developer"}, "missing_evidence": ["No CV"]}
    result = build_interview_graph(MockInterviewModel(), lambda: evidence).invoke(
        {"operation": "prepare"}
    )
    assert len(result["questions"]) == 3
    assert result["evidence"] == evidence


@pytest.mark.parametrize(
    "output",
    [
        {},
        {"questions": ["one"], "introduction": "hello"},
        {"questions": ["one"] * 3, "introduction": "hello"},
    ],
)
def test_malformed_questions_rejected(output):
    with pytest.raises(ValueError):
        validate_questions(output)


@pytest.mark.parametrize("position", [1, 2, 3])
def test_followup_is_allowed_after_any_main_but_never_twice(position):
    answers = [{"turn_id": str(i), "kind": "MAIN", "text": "à préciser"} for i in range(position)]
    graph = build_interview_graph(MockInterviewModel())
    state = {
        "operation": "answer",
        "answers": answers,
        "current_kind": "MAIN",
        "followup_used": False,
    }
    assert graph.invoke(state)["next_action"] == "followup"
    assert graph.invoke(state | {"followup_used": True})["next_action"] == (
        "next" if position < 3 else "evaluate"
    )
    assert graph.invoke(state | {"current_kind": "FOLLOWUP"})["next_action"] != "followup"


def test_feedback_rejects_invented_excerpts_and_hiring_scores():
    answers = [{"turn_id": "1", "text": "A real answer", "kind": "MAIN"}]
    output = MockInterviewModel().evaluate(answers)
    assert validate_feedback(output, answers) == output
    with pytest.raises(ValueError):
        validate_feedback(output | {"score": 98}, answers)
    output["questions"][0]["excerpts"] = ["invented"]
    with pytest.raises(ValueError):
        validate_feedback(output, answers)
