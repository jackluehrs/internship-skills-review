import pytest

from skills import extract_skills, normalize


@pytest.mark.parametrize("text, skill", [
    ("Experience with Python and SQL", "Python"),
    ("Proficient in C++ or Java", "C++"),
    ("Familiar with C#/.NET", "C#"),
    ("Languages: Python, C, and Java", "C"),
    ("Backend services in Go, Python", "Go"),
    ("Build REST APIs", "REST APIs"),
    ("Experience with React and TypeScript", "React"),
    ("Built RAG pipelines with LangChain", "RAG"),
    ("Retrieval-augmented generation", "RAG"),
    ("Deploy models with SageMaker", "SageMaker / Vertex / Azure ML"),
    ("Work directly with clients to scope projects", "Client-Facing"),
])
def test_detects_skill(text, skill):
    assert skill in extract_skills(text)


@pytest.mark.parametrize("text, skill", [
    ("AP Physics C Mechanics", "C"),           # course name, not the language
    ("Series C funding", "C"),
    ("the rest of the team", "REST APIs"),     # ordinary English words
    ("we excel in teamwork", "Excel"),
    ("react quickly to changes", "React"),
    ("Go big or go home", "Go"),
    ("Never share your Social Security number", "Security"),
    ("across payment rails like ACH", "Ruby on Rails"),
    ("Scalable systems", "Scala"),
    ("internal tools", "Rust"),
])
def test_ignores_false_positive(text, skill):
    assert skill not in extract_skills(text)


def test_normalize_maps_aliases_to_canonical_names():
    assert normalize("reactjs") == "React"
    assert normalize("postgres") == "PostgreSQL"
    assert normalize("python") == "Python"
    assert normalize("GDScript") is None
