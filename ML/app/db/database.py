"""
Phase 1 — SQLite Database Layer
Stores analysis history, trends, team data
"""

import logging
import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from app.config import settings

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(settings.CLONE_BASE_DIR), "devtrace.db")


def init_db():
    """Create all tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_url      TEXT NOT NULL,
            repo_name     TEXT NOT NULL,
            commit_sha    TEXT DEFAULT '',
            analyzed_at   TEXT NOT NULL,
            quality_score REAL DEFAULT 0,
            security_high INTEGER DEFAULT 0,
            maintainability TEXT DEFAULT 'C',
            tech_debt_hours REAL DEFAULT 0,
            total_files   INTEGER DEFAULT 0,
            total_loc     INTEGER DEFAULT 0,
            duplication_rate REAL DEFAULT 0,
            doc_coverage  REAL DEFAULT 0,
            cyclomatic_avg REAL DEFAULT 0,
            critical_count INTEGER DEFAULT 0,
            vuln_deps     INTEGER DEFAULT 0,
            full_report   TEXT,
            user_id       TEXT DEFAULT 'anonymous',
            cached        INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_runs_repo ON analysis_runs(repo_url);
        CREATE INDEX IF NOT EXISTS idx_runs_user ON analysis_runs(user_id);
        CREATE INDEX IF NOT EXISTS idx_runs_date ON analysis_runs(analyzed_at);

        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            github_login  TEXT UNIQUE,
            github_name   TEXT,
            avatar_url    TEXT,
            access_token  TEXT,
            created_at    TEXT NOT NULL,
            last_seen     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS team_repos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT NOT NULL,
            repo_url  TEXT NOT NULL,
            alias     TEXT,
            added_at  TEXT NOT NULL,
            UNIQUE(user_id, repo_url)
        );

        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id       TEXT PRIMARY KEY,
            slack_webhook TEXT DEFAULT '',
            teams_webhook TEXT DEFAULT '',
            notify_high   INTEGER DEFAULT 1,
            notify_complete INTEGER DEFAULT 1
        );
        """)
    logger.info("✅ DB initialised at %s", DB_PATH)


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Write ──────────────────────────────────────────────────────────

def save_run(report: Dict[str, Any], user_id: str = "anonymous") -> int:
    """Persist a completed analysis report."""
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO analysis_runs
              (repo_url, repo_name, commit_sha, analyzed_at,
               quality_score, security_high, maintainability,
               tech_debt_hours, total_files, total_loc,
               duplication_rate, doc_coverage, cyclomatic_avg,
               critical_count, vuln_deps, full_report, user_id, cached)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            report.get("repo_url", ""),
            report.get("repo_name", ""),
            report.get("commit_sha", ""),
            report.get("analyzed_at", datetime.now(timezone.utc).isoformat()),
            _num(report, "quality_score"),
            report.get("critical_issues_count", 0),
            _str(report, "maintainability"),
            _debt(report),
            report.get("total_files_analyzed", 0),
            report.get("total_lines_of_code", 0),
            report.get("code_health_trend", {}).get("duplication_rate", 0),
            report.get("code_health_trend", {}).get("documentation_coverage", 0),
            report.get("code_health_trend", {}).get("cyclomatic_complexity", 0),
            report.get("critical_issues_count", 0),
            report.get("vulnerable_dependencies", 0),
            json.dumps(report),
            user_id,
            int(report.get("cached", False)),
        ))
        return cur.lastrowid


def upsert_user(user_data: Dict[str, Any]) -> str:
    uid = user_data["id"]
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (id, github_login, github_name, avatar_url, access_token, created_at, last_seen)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              github_name=excluded.github_name,
              avatar_url=excluded.avatar_url,
              access_token=excluded.access_token,
              last_seen=excluded.last_seen
        """, (uid, user_data.get("login",""), user_data.get("name",""),
              user_data.get("avatar_url",""), user_data.get("access_token",""), now, now))
    return uid


def save_notification_settings(user_id: str, slack: str, teams: str,
                                 notify_high: bool, notify_complete: bool):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO notification_settings
              (user_id, slack_webhook, teams_webhook, notify_high, notify_complete)
            VALUES (?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
              slack_webhook=excluded.slack_webhook,
              teams_webhook=excluded.teams_webhook,
              notify_high=excluded.notify_high,
              notify_complete=excluded.notify_complete
        """, (user_id, slack, teams, int(notify_high), int(notify_complete)))


# ── Read ───────────────────────────────────────────────────────────

def get_history(repo_url: str, limit: int = 30) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, repo_name, commit_sha, analyzed_at,
                   quality_score, security_high, maintainability,
                   tech_debt_hours, total_files, total_loc,
                   duplication_rate, doc_coverage, cyclomatic_avg,
                   critical_count, vuln_deps, cached
            FROM analysis_runs
            WHERE repo_url = ?
            ORDER BY analyzed_at DESC LIMIT ?
        """, (repo_url, limit)).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_runs WHERE id=?", (run_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("full_report"):
        try:
            d["full_report"] = json.loads(d["full_report"])
        except Exception:
            pass
    return d


def get_all_repos(user_id: str = "anonymous") -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT repo_url, repo_name,
                   MAX(analyzed_at) as last_analyzed,
                   COUNT(*) as run_count,
                   AVG(quality_score) as avg_quality,
                   MAX(quality_score) as best_quality,
                   MIN(quality_score) as worst_quality
            FROM analysis_runs
            WHERE user_id=?
            GROUP BY repo_url
            ORDER BY last_analyzed DESC
        """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_trend(repo_url: str, limit: int = 20) -> List[Dict]:
    """Get quality trend data points for charts."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT analyzed_at, quality_score, security_high,
                   tech_debt_hours, duplication_rate, doc_coverage,
                   cyclomatic_avg, critical_count, commit_sha
            FROM analysis_runs
            WHERE repo_url=?
            ORDER BY analyzed_at ASC LIMIT ?
        """, (repo_url, limit)).fetchall()
    return [dict(r) for r in rows]


def get_user(user_id: str) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_notification_settings(user_id: str) -> Dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM notification_settings WHERE user_id=?", (user_id,)
        ).fetchone()
    if row:
        return dict(row)
    return {"slack_webhook": "", "teams_webhook": "", "notify_high": True, "notify_complete": True}


def get_leaderboard(limit: int = 10) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT repo_name, repo_url,
                   MAX(quality_score) as best_score,
                   MIN(security_high) as min_security_issues,
                   COUNT(*) as total_runs
            FROM analysis_runs
            GROUP BY repo_url
            ORDER BY best_score DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


# ── Helpers ────────────────────────────────────────────────────────

def _num(r, key):
    v = r.get(key, {})
    if isinstance(v, dict): v = v.get("value", 0)
    try: return float(v)
    except Exception: return 0.0

def _str(r, key):
    v = r.get(key, {})
    if isinstance(v, dict): v = v.get("value", "C")
    return str(v)

def _debt(r):
    v = r.get("estimated_tech_debt_hours", {})
    if isinstance(v, dict): v = v.get("value", "0h")
    try: return float(str(v).replace("h","").strip())
    except Exception: return 0.0
