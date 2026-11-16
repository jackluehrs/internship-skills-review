"""Fetch internship postings from the public Greenhouse, Lever and Ashby job-board APIs."""
from __future__ import annotations

import html
import json
import re
import ssl
import urllib.request
from urllib.error import HTTPError, URLError

try:  # python.org builds on macOS ship without trusted certificates; certifi fixes that
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

INTERN_RE = re.compile(r"\b(intern|interns|internship|co-?op)\b", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(raw: str) -> str:
    text = html.unescape(raw or "")      # Greenhouse double-escapes its HTML
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "internship-skills-review/0.1"})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as resp:
        return json.load(resp)


def fetch_greenhouse(company: str) -> list[dict]:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true")
    return [
        {
            "source": "greenhouse",
            "company": company,
            "job_id": str(j["id"]),
            "title": j["title"],
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "description": html_to_text(j.get("content", "")),
        }
        for j in data.get("jobs", [])
    ]


def fetch_lever(company: str) -> list[dict]:
    data = get_json(f"https://api.lever.co/v0/postings/{company}?mode=json")
    jobs = []
    for j in data:
        parts = [j.get("descriptionPlain", "")]
        for section in j.get("lists", []):
            parts.append(section.get("text", ""))
            parts.append(html_to_text(section.get("content", "")))
        parts.append(j.get("additionalPlain", ""))
        jobs.append({
            "source": "lever",
            "company": company,
            "job_id": j["id"],
            "title": j["text"],
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "description": " ".join(p for p in parts if p),
        })
    return jobs


def fetch_ashby(company: str) -> list[dict]:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{company}")
    return [
        {
            "source": "ashby",
            "company": company,
            "job_id": j["id"],
            "title": j["title"],
            "location": j.get("location", ""),
            "url": j.get("jobUrl", ""),
            "description": j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml", "")),
        }
        for j in data.get("jobs", [])
    ]


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}


def fetch_internships(companies: dict[str, list[str]]):
    """Yield (source, company, internship_jobs_or_None, error_or_None) for every configured board."""
    for source, names in companies.items():
        if not isinstance(names, list):  # settings like role_filter / goal_boost
            continue
        fetcher = FETCHERS.get(source)
        if not fetcher:
            yield source, "*", None, f"unknown source '{source}'"
            continue
        for company in names:
            try:
                jobs = fetcher(company)
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as e:
                yield source, company, None, str(e)
                continue
            yield source, company, [j for j in jobs if INTERN_RE.search(j["title"])], None
