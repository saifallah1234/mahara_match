# Placement: tests/unit/ai/test_cv_rewrite.py
"""Bullet rewrites and summary proposals with the chat model faked (no database, no Ollama)."""

from types import SimpleNamespace

import pytest

from ai.document_intelligence.ats.profiles import roles
from ai.document_intelligence.ats.rewrite import propose_summary, rewrite_bullet
from tests.fixtures.cv_review.fake_chat import FakeChat

pytestmark = pytest.mark.unit

ROLE = roles()["data_engineer"]
ORIGINAL = "Worked on data pipelines in Python for the finance team"


def replying(*texts):
    answers = iter(texts)
    return FakeChat(lambda messages: SimpleNamespace(content=next(answers)))


def test_valid_rewrite_with_placeholder_is_returned_at_rewrite_temperature():
    model = replying("Built Python data pipelines for the finance team, cutting runtime by [X%]")
    result = rewrite_bullet(ORIGINAL, ROLE, model)
    assert result == {
        "original": ORIGINAL,
        "text": "Built Python data pipelines for the finance team, cutting runtime by [X%]",
        "source": "model",
        "suggestion": None,
    }
    assert [options["options"]["temperature"] for _, options in model.calls] == [0.4]


@pytest.mark.parametrize(
    "invented",
    [
        "Built Python data pipelines processing 40 GB for the finance team",  # number
        "Built Python data pipelines on Airflow for the finance team",  # tool
        "Built pandas data pipelines for the finance team",  # lowercase role skill
        "Built Python data pipelines for the Acme Bank finance team",  # company
        "Built Python data pipelines\nfor the finance team",  # two lines
        "Built Python data pipelines on [Snowflake] for the finance team",  # bracket smuggling
        "Built Python data pipelines moving [40 GB] for the finance team",
        "Built five Python data pipelines for the finance team",  # number word
        "Built Python data pipelines " + "and more " * 12,  # over 25 words
    ],
)
def test_invented_fact_is_retried_cooler_then_falls_back_to_the_rule(invented):
    model = replying(invented, invented)
    result = rewrite_bullet(ORIGINAL, ROLE, model)
    assert result["source"] == "rule" and result["text"] is None
    assert "worked on" in result["suggestion"]  # names the weak phrase to replace
    assert [options["options"]["temperature"] for _, options in model.calls] == [0.4, 0.1]


def test_retry_can_succeed():
    model = replying("Built pipelines with 3 Spark jobs", "- Built Python data pipelines [X]")
    assert rewrite_bullet(ORIGINAL, ROLE, model)["text"] == "Built Python data pipelines [X]"


def test_unreachable_model_falls_back_without_retrying():
    model = FakeChat(lambda messages: (_ for _ in ()).throw(ConnectionError("down")))
    assert rewrite_bullet(ORIGINAL, ROLE, model)["source"] == "rule"
    assert len(model.calls) == 1
    assert rewrite_bullet(ORIGINAL, ROLE, None)["source"] == "rule"


def test_closest_examples_come_from_embeddings_else_the_first_ones():
    befores = [before for before, _ in ROLE.examples]

    def embed(texts):  # the bullet is closest to the last example
        return [[1.0, 0.0] if text in (ORIGINAL, befores[-1]) else [0.0, 1.0] for text in texts]

    model = replying("Built Python data pipelines [X]", "Built Python data pipelines [X]")
    rewrite_bullet(ORIGINAL, ROLE, model, embed=embed)
    assert befores[-1] in model.calls[0][0][0][1]

    def broken(texts):
        raise RuntimeError("no embeddings")

    rewrite_bullet(ORIGINAL, ROLE, model, embed=broken)
    prompt = model.calls[1][0][0][1]
    assert befores[0] in prompt and befores[-1] not in prompt


# Fixed set: (original, model output). Compare the rejection rate after prompt changes.
FIXED = [
    (ORIGINAL, "Built Python data pipelines for the finance team [X]"),
    (ORIGINAL, "Built Python data pipelines for the finance team in 2 weeks"),
    (
        "Helped with SQL reports for 3 regions",
        "Automated SQL reports for 3 regions, saving [X] hours",
    ),
    ("Helped with SQL reports for 3 regions", "Automated SQL reports in Snowflake for 3 regions"),
    ("Responsible for loading CSV files", "Ingested CSV files into PostgreSQL daily"),
    ("Responsible for loading CSV files", "Automated loading of [X] CSV files per day"),
    ("Migrated cron jobs to AWS", "Migrated [X] cron jobs to AWS, reaching [X%] on-time runs"),
    ("Migrated cron jobs to AWS", "Migrated cron jobs to AWS for Globex Corporation"),
]


def test_rejection_rate_over_the_fixed_bullet_set():
    rejected = sum(
        rewrite_bullet(original, ROLE, replying(output, output))["source"] == "rule"
        for original, output in FIXED
    )
    rate = rejected / len(FIXED)
    print(f"validator rejection rate: {rate:.0%}")
    assert rate == 0.5


STRUCTURE = {
    "entries": {
        "experience": [
            {
                "title": "Data Engineering Intern",
                "organisation": "Example Logistics",
                "dates": "2024",
                "bullets": ["Built ETL pipelines in Python loading 2 TB of shipment data"],
            }
        ]
    },
    "skills": ["SQL, Python, Docker"],
}


def test_summary_uses_only_cv_facts_and_the_role_label():
    good = (
        "Data Engineer with internship experience at Example Logistics. "
        "Built ETL pipelines in Python and SQL loading 2 TB of shipment data."
    )
    assert propose_summary(STRUCTURE, ROLE, replying(good))["text"] == good

    invented = "Data Engineer with 5 years of experience in Spark at Example Logistics."
    result = propose_summary(STRUCTURE, ROLE, replying(invented, invented))
    assert result["source"] == "rule" and "Data Engineer" in result["suggestion"]
