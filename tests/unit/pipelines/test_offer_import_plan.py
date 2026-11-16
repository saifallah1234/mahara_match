# Placement: tests/unit/pipelines/test_offer_import_plan.py
"""Keywords and page limit of an automatic run (no keyword given)."""

from typing import Any

import pytest

from pipelines.ingestion.offer_import import SOURCES, automatic_plan

TANITJOBS = SOURCES["tanitjobs"]


def test_defaults_are_an_empty_search_over_two_pages() -> None:
    assert automatic_plan(TANITJOBS, {}) == ([""], 2)


def test_configuration_overrides_keywords_and_pages() -> None:
    plan = automatic_plan(
        TANITJOBS, {"keywords": [" informatique ", "", "informatique"], "max_pages": 5}
    )
    assert plan == (["informatique", ""], 5)


@pytest.mark.parametrize(
    "configuration",
    [
        None,
        [],
        {"keywords": "python"},
        {"keywords": []},
        {"keywords": [1, 2]},
        {"max_pages": 0},
        {"max_pages": True},
        {"max_pages": "3"},
    ],
)
def test_invalid_values_fall_back_to_the_defaults(configuration: Any) -> None:
    assert automatic_plan(TANITJOBS, configuration) == ([""], 2)
