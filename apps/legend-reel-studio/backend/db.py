"""SQLite storage for reels projects."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("LRS_DATA_DIR") or os.path.join(APP_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "studio.db")

STATUSES = ["draft", "article", "video", "ready", "scheduled", "published"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    artist_id TEXT NOT NULL,
    event_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    seed INTEGER NOT NULL DEFAULT 1,
    article_title TEXT DEFAULT '',
    article_dek TEXT DEFAULT '',
    article_body TEXT DEFAULT '',
    article_titles_json TEXT DEFAULT '[]',
    first_comment TEXT DEFAULT '',
    hashtags TEXT DEFAULT '',
    banner_image TEXT DEFAULT '',
    music_links_json TEXT DEFAULT '[]',
    video_overlay_text TEXT DEFAULT '',
    fb_hook TEXT DEFAULT '',
    caption TEXT DEFAULT '',
    video_plan_json TEXT DEFAULT '{}',
    video_style TEXT DEFAULT 'noir',
    audio_choice TEXT DEFAULT '',
    audio_path TEXT DEFAULT '',
    render_path TEXT DEFAULT '',
    render_status TEXT DEFAULT '',
    render_seconds REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    scheduled_for TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at DESC);

CREATE TABLE IF NOT EXISTS custom_events (
    id TEXT PRIMARY KEY,
    artist_id TEXT NOT NULL,
    date TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'custom',
    title TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


JSON_FIELDS = {"event_json": "event", "article_titles_json": "article_titles", "music_links_json": "music_links", "video_plan_json": "video_plan"}


def row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    p = dict(row)
    for col, key in JSON_FIELDS.items():
        raw = p.pop(col, None)
        try:
            p[key] = json.loads(raw) if raw else ({} if key == "video_plan" else [])
        except json.JSONDecodeError:
            p[key] = {} if key == "video_plan" else []
    p["hashtags"] = p.get("hashtags") or ""
    return p


def list_projects(status: str = "", q: str = "", limit: int = 200) -> list[dict]:
    sql = "SELECT * FROM projects"
    clauses, params = [], []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if q:
        clauses.append("(lower(article_title) LIKE ? OR lower(fb_hook) LIKE ? OR lower(artist_id) LIKE ?)")
        needle = f"%{q.lower()}%"
        params.extend([needle, needle, needle])
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        return [row_to_project(r) for r in conn.execute(sql, params).fetchall()]


def get_project(pid: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    return row_to_project(row) if row else None


def create_project(artist_id: str, event: dict, seed: int = 1) -> dict:
    pid = uuid.uuid4().hex[:12]
    ts = now()
    with connect() as conn:
        conn.execute(
            "INSERT INTO projects (id, artist_id, event_json, status, seed, created_at, updated_at)"
            " VALUES (?, ?, ?, 'draft', ?, ?, ?)",
            (pid, artist_id, json.dumps(event), seed, ts, ts),
        )
    return get_project(pid)  # type: ignore[return-value]


FIELD_MAP = {
    "status": "status",
    "seed": "seed",
    "article_title": "article_title",
    "article_dek": "article_dek",
    "article_body": "article_body",
    "first_comment": "first_comment",
    "hashtags": "hashtags",
    "banner_image": "banner_image",
    "video_overlay_text": "video_overlay_text",
    "fb_hook": "fb_hook",
    "caption": "caption",
    "video_style": "video_style",
    "audio_choice": "audio_choice",
    "audio_path": "audio_path",
    "render_path": "render_path",
    "render_status": "render_status",
    "notes": "notes",
    "scheduled_for": "scheduled_for",
}
JSON_IN = {"article_titles": "article_titles_json", "music_links": "music_links_json", "video_plan": "video_plan_json", "event": "event_json"}


def update_project(pid: str, patch: dict[str, Any]) -> dict | None:
    sets, params = [], []
    for key, value in patch.items():
        if key in FIELD_MAP:
            sets.append(f"{FIELD_MAP[key]} = ?")
            params.append(value)
        elif key in JSON_IN:
            sets.append(f"{JSON_IN[key]} = ?")
            params.append(json.dumps(value, ensure_ascii=False))
    if not sets:
        return get_project(pid)
    sets.append("updated_at = ?")
    params.append(now())
    params.append(pid)
    with connect() as conn:
        conn.execute(f"UPDATE projects SET {', '.join(sets)} WHERE id = ?", params)
    return get_project(pid)


def delete_project(pid: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    return cur.rowcount > 0


def duplicate_project(pid: str) -> dict | None:
    """Copy a project row (article, script, caption) without its rendered media."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not row:
        return None
    new_id = uuid.uuid4().hex[:12]
    ts = now()
    reset = {"render_path": "", "render_status": "", "render_seconds": 0, "audio_path": "", "banner_image": "", "status": "draft"}
    cols = [c for c in row.keys() if c not in {"id", "created_at", "updated_at"}]
    values = [reset.get(c, row[c]) for c in cols]
    with connect() as conn:
        conn.execute(
            f"INSERT INTO projects (id, {', '.join(cols)}, created_at, updated_at)"
            f" VALUES (?, {', '.join(['?'] * len(cols))}, ?, ?)",
            [new_id, *values, ts, ts],
        )
    return get_project(new_id)


def stats() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"]
        by_status = {r["status"]: r["c"] for r in conn.execute("SELECT status, COUNT(*) c FROM projects GROUP BY status")}
        rendered = conn.execute("SELECT COUNT(*) c FROM projects WHERE render_path != ''").fetchone()["c"]
    return {"total": total, "by_status": by_status, "rendered": rendered}


def add_custom_event(artist_id: str, date_str: str, title: str, kind: str = "custom", note: str = "") -> dict:
    eid = uuid.uuid4().hex[:10]
    with connect() as conn:
        conn.execute(
            "INSERT INTO custom_events (id, artist_id, date, kind, title, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (eid, artist_id, date_str, kind, title, note, now()),
        )
    return {"id": eid, "artist_id": artist_id, "date": date_str, "kind": kind, "title": title, "note": note}


def list_custom_events() -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM custom_events ORDER BY date").fetchall()]
