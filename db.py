"""SQLite storage for fetched job postings."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "internships.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    source      TEXT NOT NULL,   -- greenhouse | lever | ashby | manual
    company     TEXT NOT NULL,
    job_id      TEXT NOT NULL,
    title       TEXT NOT NULL,
    location    TEXT,
    url         TEXT,
    description TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    PRIMARY KEY (source, company, job_id)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_job(conn: sqlite3.Connection, job: dict) -> bool:
    """Insert or refresh a job. Returns True if it was new."""
    ts = now()
    cur = conn.execute(
        "UPDATE jobs SET title=?, location=?, url=?, description=?, last_seen=? "
        "WHERE source=? AND company=? AND job_id=?",
        (job["title"], job["location"], job["url"], job["description"], ts,
         job["source"], job["company"], job["job_id"]),
    )
    if cur.rowcount:
        return False
    conn.execute(
        "INSERT INTO jobs (source, company, job_id, title, location, url, description, first_seen, last_seen) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (job["source"], job["company"], job["job_id"], job["title"], job["location"],
         job["url"], job["description"], ts, ts),
    )
    return True


def active_jobs(conn: sqlite3.Connection, days: int = 14) -> list[sqlite3.Row]:
    """Jobs seen in the last `days` days (older ones were probably taken down)."""
    return conn.execute(
        "SELECT * FROM jobs WHERE last_seen >= datetime('now', ?) OR source = 'manual' "
        "ORDER BY company, title",
        (f"-{days} days",),
    ).fetchall()
