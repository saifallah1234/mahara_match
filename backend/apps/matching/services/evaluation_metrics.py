from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from backend.apps.matching.services.evaluation_retrieval import RetrievalCase, relevance_metrics

ABSENCE_CASE_IDS = frozenset(
    {
        "fr_keywords_03",
        "ar_keywords_03",
        "fr_multi_hop_01",
        "ar_multi_hop_01",
        "fr_multi_hop_03",
        "ar_multi_hop_03",
    }
)
METRIC_NAMES = ("mrr", "recall@5", "recall@10", "ndcg@3", "ndcg@5")


def _split_label(label: str) -> tuple[str, str]:
    entity_type, _, entity_id = label.partition(":")
    return entity_type, entity_id


def metrics_for_case(
    case: RetrievalCase,
    ranking: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    relevant = [_split_label(label) for label in case["relevant"]]
    ranked = list(ranking)
    excluded_training = case["id"] in ABSENCE_CASE_IDS
    if excluded_training:
        relevant = [item for item in relevant if item[0] != "training"]
        ranked = [item for item in ranked if item[0] != "training"]

    full_limit = max(len(ranked), 1)
    full_metrics = relevance_metrics(ranked, relevant, full_limit)
    metric_values = {
        "mrr": full_metrics[f"mrr@{full_limit}"],
        "recall@5": relevance_metrics(ranked, relevant, 5)["recall@5"],
        "recall@10": relevance_metrics(ranked, relevant, 10)["recall@10"],
        "ndcg@3": relevance_metrics(ranked, relevant, 3)["ndcg@3"],
        "ndcg@5": relevance_metrics(ranked, relevant, 5)["ndcg@5"],
    }
    return {
        "case_id": case["id"],
        "language": case["language"],
        "category": case["category"],
        "relevant_documents": len(relevant),
        "training_candidates_excluded": excluded_training,
        "metrics": metric_values,
    }


def aggregate_metrics(
    per_case: Sequence[Mapping[str, Any]],
) -> dict[str, float | int]:
    if not per_case:
        return {"cases": 0, "relevant_documents_per_case": 0.0, **dict.fromkeys(METRIC_NAMES, 0.0)}
    result: dict[str, float | int] = {
        "cases": len(per_case),
        "relevant_documents_per_case": sum(int(case["relevant_documents"]) for case in per_case)
        / len(per_case),
    }
    for name in METRIC_NAMES:
        result[name] = sum(float(case["metrics"][name]) for case in per_case) / len(per_case)
    return result


def build_metric_report(
    cases: Sequence[RetrievalCase],
    rankings_by_mode: Mapping[str, Mapping[str, Sequence[tuple[str, str]]]],
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for mode, rankings_by_case in rankings_by_mode.items():
        mode_details = [
            {"mode": mode, **metrics_for_case(case, rankings_by_case.get(case["id"], ()))}
            for case in cases
        ]
        details.extend(mode_details)
        groups: dict[str, Any] = {"global": aggregate_metrics(mode_details)}
        for dimension in ("category", "language"):
            group_names = sorted({str(case[dimension]) for case in mode_details})
            groups[dimension] = {
                group: aggregate_metrics(
                    [case for case in mode_details if case[dimension] == group]
                )
                for group in group_names
            }
        summaries[mode] = groups
    return {"summaries": summaries, "per_case": details}
