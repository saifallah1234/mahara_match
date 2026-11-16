from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ai.tools.interview_evidence import retrieve_evidence

GRAPH_VERSION = "mock-interview-v1"


class InterviewState(TypedDict, total=False):
    operation: str
    evidence: dict[str, Any]
    questions: list[str]
    introduction: str
    answers: list[dict[str, Any]]
    current_kind: str
    followup_used: bool
    next_action: str
    followup: str
    feedback: dict[str, Any]


def validate_questions(output: dict[str, Any]) -> dict[str, Any]:
    questions = output.get("questions")
    introduction = output.get("introduction")
    if (
        not isinstance(questions, list)
        or len(questions) != 3
        or any(not isinstance(q, str) or not q.strip() or len(q) > 2000 for q in questions)
    ):
        raise ValueError("Exactly three bounded questions are required.")
    if (
        len(set(questions)) != 3
        or not isinstance(introduction, str)
        or not introduction.strip()
        or len(introduction) > 2000
    ):
        raise ValueError("Invalid introduction or duplicate questions.")
    return {"questions": questions, "introduction": introduction}


def validate_feedback(output: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, Any]:
    rows = output.get("questions")
    if (
        set(output) != {"questions", "summary"}
        or not isinstance(output["summary"], str)
        or not output["summary"].strip()
        or len(output["summary"]) > 4000
        or not isinstance(rows, list)
        or len(rows) != len(answers)
    ):
        raise ValueError("Invalid feedback structure.")
    for row, answer in zip(rows, answers, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != {"turn_id", "strengths", "gaps", "excerpts", "improvements"}
            or row["turn_id"] != answer["turn_id"]
        ):
            raise ValueError("Invalid feedback turn.")
        for key in ("strengths", "gaps", "excerpts", "improvements"):
            if (
                not isinstance(row[key], list)
                or len(row[key]) > 10
                or any(
                    not isinstance(value, str) or not value.strip() or len(value) > 2000
                    for value in row[key]
                )
            ):
                raise ValueError("Invalid feedback entries.")
        if not row["excerpts"] or any(excerpt not in answer["text"] for excerpt in row["excerpts"]):
            raise ValueError("Feedback excerpt is not grounded in the answer.")
    return output


class MockInterviewModel:
    """Deterministic simulated reasoning; does not call a model service."""

    def prepare(self, evidence: dict[str, Any]) -> dict[str, Any]:
        title = evidence["offer"]["title"][:200]
        return {
            "introduction": f"Bienvenue à cet entretien blanc pour le poste de {title}. Nous allons aborder trois questions.",
            "questions": [
                f"Présentez votre parcours et son lien avec le poste de {title}.",
                "Décrivez une situation où vous avez utilisé une compétence demandée dans cette offre.",
                "Comment aborderiez-vous vos premières semaines dans ce poste ?",
            ],
        }

    def decide(self, state: InterviewState) -> dict[str, Any]:
        wants_followup = "à préciser" in state["answers"][-1]["text"].lower()
        if (
            wants_followup
            and not state.get("followup_used")
            and state.get("current_kind") == "MAIN"
        ):
            return {
                "next_action": "followup",
                "followup": "Pouvez-vous préciser votre rôle et le résultat de cet exemple ?",
            }
        return {
            "next_action": "next"
            if sum(a["kind"] == "MAIN" for a in state["answers"]) < 3
            else "evaluate"
        }

    def evaluate(self, answers: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "questions": [
                {
                    "turn_id": a["turn_id"],
                    "strengths": ["Une réponse a été fournie."],
                    "gaps": ["Ce retour simulé ne mesure pas la qualité de la réponse."],
                    "excerpts": [a["text"][:200]],
                    "improvements": ["Précisez votre contribution et les résultats concrets."],
                }
                for a in answers
            ],
            "summary": "Retour simulé pour vérifier le parcours local. Aucun modèle d'évaluation réel n'a été utilisé.",
        }


def build_interview_graph(model: Any, retrieve: Callable[[], dict[str, Any]] | None = None) -> Any:
    def prepare(state: InterviewState) -> dict[str, Any]:
        if retrieve is None:
            raise ValueError("Evidence service required.")
        return {"evidence": retrieve_evidence(retrieve)}

    def questions(state: InterviewState) -> dict[str, Any]:
        return validate_questions(model.prepare(state["evidence"]))

    def decide(state: InterviewState) -> dict[str, Any]:
        output = model.decide(state)
        action = output.get("next_action")
        if action not in {"followup", "next", "evaluate"}:
            raise ValueError("Invalid model routing output.")
        # The model only judges whether a follow-up is needed; the answer count decides between
        # the next question and feedback (the model chose "evaluate" after one answer, 2026-11-08).
        move_on = "next" if sum(a["kind"] == "MAIN" for a in state["answers"]) < 3 else "evaluate"
        followup = output.get("followup")
        usable = isinstance(followup, str) and followup.strip() and len(followup) <= 2000
        # A follow-up is optional: an unusable one moves on rather than failing the interview.
        if (
            action != "followup"
            or not usable
            or state.get("followup_used")
            or state.get("current_kind") == "FOLLOWUP"
        ):
            action = move_on
        if action == "evaluate" and sum(a["kind"] == "MAIN" for a in state["answers"]) != 3:
            raise ValueError("Cannot evaluate before three main answers.")
        return output | {"next_action": action}

    def evaluate(state: InterviewState) -> dict[str, Any]:
        return {"feedback": validate_feedback(model.evaluate(state["answers"]), state["answers"])}

    graph = StateGraph(InterviewState)
    graph.add_node("prepare_interview", prepare)
    graph.add_node("generate_questions", questions)
    graph.add_node("decide_next", decide)
    graph.add_node("generate_followup", lambda state: {"followup": state["followup"]})
    graph.add_node("activate_next", lambda state: {})
    graph.add_node("evaluate_interview", evaluate)
    graph.add_conditional_edges(
        START,
        lambda state: {
            "prepare": "prepare_interview",
            "answer": "decide_next",
            "feedback": "evaluate_interview",
        }[state["operation"]],
    )
    graph.add_edge("prepare_interview", "generate_questions")
    graph.add_edge("generate_questions", END)
    graph.add_conditional_edges(
        "decide_next",
        lambda state: state["next_action"],
        {"followup": "generate_followup", "next": "activate_next", "evaluate": END},
    )
    graph.add_edge("generate_followup", END)
    graph.add_edge("activate_next", END)
    graph.add_edge("evaluate_interview", END)
    return graph.compile()
