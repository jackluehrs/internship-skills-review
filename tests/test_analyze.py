import db
from analyze import analyze, render_report


def job(title, description, company="acme"):
    return {"company": company, "title": title, "description": description, "url": "", "location": ""}


def test_scores_and_ranks_jobs_by_match():
    jobs = [
        job("ML Intern", "Python, PyTorch, SQL and statistics"),
        job("Web Intern", "React, TypeScript, Node.js, GraphQL"),
    ]
    result = analyze(jobs, have={"Python", "SQL"})
    best = result["jobs"][0]
    assert best["job"]["title"] == "ML Intern"
    assert best["matched"] == {"Python", "SQL"}
    assert result["jobs"][1]["score"] == 0


def test_postings_with_few_skills_cannot_score_100_percent():
    result = analyze([job("PM Intern", "Some SQL")], have={"SQL"})
    assert result["jobs"][0]["score"] < 0.5


def test_soft_skills_count_toward_demand_but_not_match_score():
    result = analyze([job("Intern", "Python. Strong collaboration and teamwork.")], have={"Python"})
    assert result["demand"]["Collaboration"] == 1
    assert "Collaboration" not in result["jobs"][0]["missing"]


def test_report_ranks_gaps_by_demand():
    jobs = [job("A", "Python, Docker"), job("B", "Docker, AWS"), job("C", "Docker")]
    report = render_report(analyze(jobs, have={"Python"}), {"Python"}, [])
    assert report.index("**Docker**") < report.index("**AWS**")


def test_db_upsert_is_idempotent(tmp_path):
    conn = db.connect(tmp_path / "test.db")
    row = {"source": "greenhouse", "company": "acme", "job_id": "1", "title": "Intern",
           "location": "", "url": "", "description": "Python"}
    assert db.upsert_job(conn, row) is True
    assert db.upsert_job(conn, row) is False
    assert len(db.active_jobs(conn)) == 1
