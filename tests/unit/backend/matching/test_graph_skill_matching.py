from backend.apps.matching.services.retrieval import skill_is_mentioned


def test_skill_mention_is_case_insensitive() -> None:
    assert skill_is_mentioned("Offres Python et SQL", "Python")
    assert skill_is_mentioned("offres python et sql", "SQL")


def test_multi_word_and_symbol_skills_are_matched() -> None:
    assert skill_is_mentioned("Docker et Machine Learning", "Machine Learning")
    assert skill_is_mentioned("pipelines CI/CD automatisés", "CI/CD")
    assert skill_is_mentioned("offres Apache Spark", "Apache Spark")


def test_arabic_attached_prefix_is_matched() -> None:
    assert skill_is_mentioned("ما عروض العمل التي تذكر Python وSQL", "SQL")


def test_java_does_not_match_javascript() -> None:
    assert not skill_is_mentioned("développeur JavaScript", "Java")
