import sqlite3
from datetime import datetime
from config import DB_PATH, DATA_DIR

ALLOWED_UPDATE_COLS = {"cover_letter", "applied_at", "apply_method", "notes"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT,
            title TEXT NOT NULL,
            employer TEXT,
            location TEXT,
            url TEXT NOT NULL UNIQUE,
            hours TEXT,
            salary TEXT,
            description TEXT,
            employer_email TEXT,
            found_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            cover_letter TEXT,
            applied_at TEXT,
            apply_method TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()


def job_exists(url):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def is_duplicate(title, employer, location):
    """Check if a job with similar title/employer/location already exists.
    Uses case-insensitive matching to catch cross-board duplicates."""
    conn = get_db()
    row = conn.execute(
        """SELECT 1 FROM jobs
           WHERE LOWER(TRIM(title)) = LOWER(TRIM(?))
           AND LOWER(TRIM(COALESCE(employer, ''))) = LOWER(TRIM(COALESCE(?, '')))""",
        (title, employer),
    ).fetchone()
    conn.close()
    return row is not None


def save_job(job):
    conn = get_db()
    conn.execute(
        """INSERT OR IGNORE INTO jobs
           (source, external_id, title, employer, location, url, hours, salary,
            description, employer_email, found_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job["source"],
            job.get("external_id"),
            job["title"],
            job.get("employer"),
            job.get("location"),
            job["url"],
            job.get("hours"),
            job.get("salary"),
            job.get("description"),
            job.get("employer_email"),
            datetime.now().isoformat(),
            "new",
        ),
    )
    conn.commit()
    conn.close()


def update_job_status(url, status, **kwargs):
    for key in kwargs:
        if key not in ALLOWED_UPDATE_COLS:
            raise ValueError(f"Invalid column for update: {key}")
    conn = get_db()
    updates = ["status = ?"]
    values = [status]
    for key, val in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(val)
    values.append(url)
    conn.execute(
        f"UPDATE jobs SET {', '.join(updates)} WHERE url = ?",
        values,
    )
    conn.commit()
    conn.close()


def get_new_jobs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM jobs WHERE status = 'new'").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job_stats():
    conn = get_db()
    stats = {}
    for status in ["new", "applied", "emailed", "skipped", "failed"]:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM jobs WHERE status = ?", (status,)
        ).fetchone()
        stats[status] = row["c"]
    stats["total"] = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()["c"]
    conn.close()
    return stats
