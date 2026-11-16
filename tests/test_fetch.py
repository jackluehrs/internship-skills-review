import pytest

import fetch


@pytest.mark.parametrize("title, is_intern", [
    ("Software Engineer Intern", True),
    ("Machine Learning Internship (Summer 2027)", True),
    ("Data Science Co-op", True),
    ("Interns - Applied AI", True),
    ("Internal Tools Engineer", False),
    ("Senior Software Engineer", False),
    ("International Tax Manager", False),
])
def test_intern_title_filter(title, is_intern):
    assert bool(fetch.INTERN_RE.search(title)) is is_intern


def test_html_to_text_handles_greenhouse_double_escaping():
    raw = "&lt;p&gt;Experience with &lt;strong&gt;Python&lt;/strong&gt; &amp;amp; SQL&lt;/p&gt;"
    assert fetch.html_to_text(raw) == "Experience with Python & SQL"


def test_fetch_greenhouse_parses_response(monkeypatch):
    fake = {"jobs": [{"id": 1, "title": "ML Intern", "location": {"name": "NYC"},
                      "absolute_url": "https://x/1", "content": "&lt;p&gt;PyTorch&lt;/p&gt;"}]}
    monkeypatch.setattr(fetch, "get_json", lambda url: fake)
    [job] = fetch.fetch_greenhouse("acme")
    assert job == {"source": "greenhouse", "company": "acme", "job_id": "1", "title": "ML Intern",
                   "location": "NYC", "url": "https://x/1", "description": "PyTorch"}


def test_fetch_internships_keeps_only_interns_and_reports_errors(monkeypatch):
    jobs = [{"title": "SWE Intern"}, {"title": "Staff Engineer"}]

    def fake_fetcher(company):
        if company == "broken":
            raise ValueError("bad JSON")
        return jobs

    monkeypatch.setitem(fetch.FETCHERS, "greenhouse", fake_fetcher)
    results = list(fetch.fetch_internships({"role_filter": "x", "greenhouse": ["ok", "broken"]}))
    assert results[0] == ("greenhouse", "ok", [{"title": "SWE Intern"}], None)
    assert results[1][1] == "broken" and results[1][3] == "bad JSON"
