import pytest

from ai.retrieval.lexical.scoring import lexical_ranking, normalize, terms

pytestmark = pytest.mark.unit

PYTHON = ("offer", "1")
DATA = ("offer", "2")
COOK = ("offer", "3")


def test_documents_without_overlap_are_excluded() -> None:
    documents = [
        (COOK, "Chef cuisinier, restauration"),
        (PYTHON, "Développeur Python Django"),
    ]
    assert lexical_ranking("python", documents) == [PYTHON]


def test_more_shared_terms_rank_first_and_ties_sort_by_key() -> None:
    documents = [
        (DATA, "Python"),
        (PYTHON, "Python Django"),
        (COOK, "Python"),
    ]
    assert lexical_ranking("Python Django", documents) == [PYTHON, DATA, COOK]


def test_accents_and_case_are_folded() -> None:
    assert normalize("Données") == "donnees"
    assert lexical_ranking("DONNEES", [(DATA, "Analyste de données")]) == [DATA]


def test_arabic_tashkeel_and_alef_forms_are_normalised() -> None:
    assert normalize("أَحْمَد") == normalize("احمد")
    assert normalize("إدارة") == normalize("أدارة") == normalize("آدارة") == "ادارة"
    assert normalize("بـيـانـات") == "بيانات"
    assert lexical_ranking("إدارة المشاريع", [(DATA, "ادارة المشاريع")]) == [DATA]


def test_arabic_attached_prefix_is_split_from_latin_skill() -> None:
    assert "sql" in terms("ما عروض العمل التي تذكر Python وSQL")


def test_stop_words_alone_never_match() -> None:
    documents = [(COOK, "le chef et la cuisine"), (DATA, "the data of the team")]
    assert lexical_ranking("le et la the of", documents) == []
    assert lexical_ranking("ما هي", [(DATA, "ما هي البيانات")]) == []


def test_slash_compounds_keep_whole_form_and_parts() -> None:
    assert {"ci/cd", "ci", "cd"} <= terms("pipelines CI/CD")
    assert lexical_ranking("CI/CD", [(DATA, "Intégration continue CI/CD")]) == [DATA]
    assert lexical_ranking("Django", [(PYTHON, "Python/Django")]) == [PYTHON]


def test_symbol_skills_survive_tokenisation() -> None:
    assert {"c++", "c#", "node.js"} <= terms("C++, C# et Node.js.")


def test_empty_query_returns_nothing() -> None:
    assert lexical_ranking("  ", [(DATA, "anything")]) == []
