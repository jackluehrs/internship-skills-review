"""Compare your skills to the skills internships ask for."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from skills import CATEGORY, SOFT_SKILLS, extract_skills, normalize

ROOT = Path(__file__).parent


def read_resume(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise SystemExit("Reading a PDF resume needs pypdf:  pip install pypdf")
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    return path.read_text(errors="ignore")


def load_profile(skills_file: Path = ROOT / "my_skills.txt", resume: Path | None = None) -> tuple[set[str], list[str]]:
    """Return (canonical skills you have, skills you listed that aren't in the taxonomy)."""
    have: set[str] = set()
    unknown: list[str] = []
    if skills_file.exists():
        for line in skills_file.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            canon = normalize(line)
            if canon:
                have.add(canon)
            else:
                unknown.append(line)
    if resume is None:
        resume = next((p for p in sorted(ROOT.glob("resume.*")) if p.suffix.lower() in {".pdf", ".txt", ".md"}), None)
    if resume and resume.exists():
        have |= extract_skills(read_resume(resume))
    return have, unknown


def analyze(jobs, have: set[str]) -> dict:
    job_skills = []
    demand = Counter()
    for job in jobs:
        found = extract_skills(f"{job['title']}\n{job['description'] or ''}")
        demand.update(found)
        found -= SOFT_SKILLS  # boilerplate in nearly every posting; don't let it skew match scores
        matched = found & have
        score = len(matched) / max(len(found), 3)  # postings listing 1-2 skills shouldn't score 100%
        job_skills.append({"job": job, "skills": found, "matched": matched,
                           "missing": found - have, "score": score})
    job_skills.sort(key=lambda r: (r["score"], len(r["matched"])), reverse=True)
    return {"total": len(jobs), "demand": demand, "jobs": job_skills}


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:.0f}%" if total else "0%"


def render_report(result: dict, have: set[str], unknown: list[str], top_n: int = 15) -> str:
    total, demand = result["total"], result["demand"]
    if not total:
        return "# Internship Skills Report\n\nNo internships in the database yet. Run `python3 main.py fetch` first.\n"

    lines = ["# Internship Skills Report", "",
             f"Based on **{total}** internship postings. Percent = share of postings mentioning the skill.", ""]

    lines += ["## ✅ Skills you have (ranked by demand)", ""]
    owned = sorted((s for s in have - SOFT_SKILLS if demand[s]), key=lambda s: -demand[s])
    lines += [f"- **{s}** — {pct(demand[s], total)}" for s in owned] or ["- (none of your skills appear in these postings yet)"]
    unused = sorted(s for s in have if not demand[s])
    if unused:
        lines += ["", f"Not mentioned in any posting: {', '.join(unused)}"]

    lines += ["", "## ❌ Skills to work on (ranked by demand)", ""]
    gaps = [(s, n) for s, n in demand.most_common() if s not in have and s not in SOFT_SKILLS]
    by_cat: dict[str, list[str]] = {}
    for s, n in gaps:
        if n / total >= 0.05:  # skip skills in fewer than 5% of postings
            by_cat.setdefault(CATEGORY[s], []).append(f"{s} ({pct(n, total)})")
    lines += [f"{i}. **{s}** — {pct(n, total)} of postings" for i, (s, n) in enumerate(gaps[:10], 1)]
    if by_cat:
        lines += ["", "### All gaps by category (≥5% of postings)", ""]
        lines += [f"- **{cat}:** {', '.join(items)}" for cat, items in by_cat.items()]

    soft = sorted(SOFT_SKILLS, key=lambda s: -demand[s])
    lines += ["", "## 🤝 Soft skills employers mention", "",
              ", ".join(f"{s} ({pct(demand[s], total)})" for s in soft if demand[s]),
              "", "_Show these with concrete examples on your resume (team projects, presentations)._"]

    lines += ["", f"## 🎯 Best-matching internships (top {top_n})", "",
              "| Match | Company | Role | Missing |", "|---|---|---|---|"]
    for r in result["jobs"][:top_n]:
        j = r["job"]
        missing = ", ".join(sorted(r["missing"], key=lambda s: -demand[s])[:5]) or "—"
        title = f"[{j['title']}]({j['url']})" if j["url"] else j["title"]
        lines.append(f"| {r['score']:.0%} | {j['company']} | {title} | {missing} |")

    if unknown:
        lines += ["", "---", f"_Skills from my_skills.txt not in the taxonomy (add them to skills.py to track them): "
                  f"{', '.join(unknown)}_"]
    return "\n".join(lines) + "\n"
