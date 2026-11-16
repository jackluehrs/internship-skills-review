"""Internship Skills Review.

Usage:
  python3 main.py                       Fetch new postings, then show the report (same as pressing Run)
  python3 main.py fetch                 Pull internships from Greenhouse, Lever and Ashby into the database
  python3 main.py add FILE [--company X --title Y --url Z]
                                        Add a posting you copied from anywhere else (text file)
  python3 main.py report [--resume R] [--role "software|data"]
                                        Show skills you have vs. skills to work on (also writes report.md)
  python3 main.py list                  List internships in the database
"""
import argparse
import hashlib
import json
import re
import webbrowser
from pathlib import Path

import db
from analyze import ROOT, analyze, load_profile, render_report
from fetch import fetch_internships
from visual import build_data, write_html


def cmd_fetch(args):
    companies = json.loads((ROOT / "companies.json").read_text())
    conn = db.connect()
    total = new = 0
    for source, company, jobs, err in fetch_internships(companies):
        if err:
            print(f"  ✗ {source}/{company}: {err}")
            continue
        added = sum(db.upsert_job(conn, j) for j in jobs)
        total += len(jobs)
        new += added
        print(f"  ✓ {source}/{company}: {len(jobs)} internships ({added} new)")
    conn.commit()
    print(f"\n{total} internships found, {new} new.")


def cmd_add(args):
    path = Path(args.file)
    text = path.read_text(errors="ignore")
    conn = db.connect()
    db.upsert_job(conn, {
        "source": "manual",
        "company": args.company or "unknown",
        "job_id": hashlib.sha1(text.encode()).hexdigest()[:12],
        "title": args.title or path.stem,
        "location": "",
        "url": args.url or "",
        "description": text,
    })
    conn.commit()
    print(f"Added '{args.title or path.stem}'.")


def cmd_report(args):
    have, unknown = load_profile(resume=Path(args.resume) if args.resume else None)
    if not have:
        print("No skills found. Fill in my_skills.txt and/or put your resume in this folder as resume.pdf or resume.txt.\n")
    jobs = db.active_jobs(db.connect())
    settings = json.loads((ROOT / "companies.json").read_text())
    role = args.role or settings.get("role_filter")
    if role and role != "all":
        role_re = re.compile(role, re.IGNORECASE)
        jobs = [j for j in jobs if role_re.search(j["title"])]
    result = analyze(jobs, have)
    report = render_report(result, have, unknown, top_n=args.top)
    (ROOT / "report.md").write_text(report)
    print(report)
    html_path = write_html(
        build_data(result, have, unknown, role if role != "all" else None,
                   goal_label=None if args.role else settings.get("goal_label"),
                   boost=settings.get("goal_boost")),
        ROOT / "report.html")
    print(f"(Saved to report.md and {html_path.name})")
    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())


def cmd_list(args):
    for j in db.active_jobs(db.connect()):
        print(f"{j['company']:<12} {j['title'][:70]:<70} {j['location'] or ''}")


def main():
    p = argparse.ArgumentParser(description="Find which skills internships want that you have and don't have.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("fetch").set_defaults(func=cmd_fetch)
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("--company")
    a.add_argument("--title")
    a.add_argument("--url")
    a.set_defaults(func=cmd_add)
    r = sub.add_parser("report")
    r.add_argument("--resume", help="path to resume (.pdf/.txt); default: resume.* in this folder")
    r.add_argument("--role", help='only postings whose title matches, e.g. "software|data" '
                   '(default: role_filter in companies.json; "all" = no filter)')
    r.add_argument("--top", type=int, default=15, help="how many best-matching internships to show")
    r.add_argument("--no-open", action="store_true", help="don't open report.html in the browser")
    r.set_defaults(func=cmd_report)
    sub.add_parser("list").set_defaults(func=cmd_list)
    args = p.parse_args()
    if args.cmd is None:  # no command (e.g. VS Code's Run button): fetch fresh postings, then report
        cmd_fetch(args)
        print()
        cmd_report(p.parse_args(["report"]))
        return
    args.func(args)


if __name__ == "__main__":
    main()
