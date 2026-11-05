"""SQLite storage for reel projects (article + images + text/voice)."""

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

STATUSES = ["draft", "article", "script", "ready", "scheduled", "published"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    artist_id TEXT NOT NULL,
    event_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    seed INTEGER NOT NULL DEFAULT 1,
    article_title TEXT DEFAULT '',
    article_body TEXT DEFAULT '',
    article_titles_json TEXT DEFAULT '[]',
    first_comment TEXT DEFAULT '',
    hashtags TEXT DEFAULT '',
    banner_image TEXT DEFAULT '',
    music_links_json TEXT DEFAULT '[]',
    images_json TEXT DEFAULT '[]',
    video_overlay_text TEXT DEFAULT '',
    fb_hook TEXT DEFAULT '',
    caption TEXT DEFAULT '',
    script_json TEXT DEFAULT '{}',
    voice_json TEXT DEFAULT '{}',
    notes TEXT DEFAULT '',
    scheduled_for TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at DESC);

CREATE TABLE IF NOT EXISTS custom_artists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    aka TEXT DEFAULT '',
    genre TEXT DEFAULT '',
    era TEXT DEFAULT '',
    hometown TEXT DEFAULT '',
    birth TEXT DEFAULT '',
    death TEXT DEFAULT '',
    gender TEXT DEFAULT '',
    legacy TEXT DEFAULT '',
    facts_json TEXT DEFAULT '[]',
    songs_json TEXT DEFAULT '[]',
    source_url TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rival_reels (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL DEFAULT 'facebook',
    url TEXT DEFAULT '',
    artist_name TEXT DEFAULT '',
    hook TEXT DEFAULT '',
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    format TEXT NOT NULL DEFAULT 'story',
    notes TEXT DEFAULT '',
    posted_at TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    remade_project_id TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rivals_created ON rival_reels(created_at DESC);

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

# columns added after the first release; created on old databases by init_db()
ADDED_COLUMNS = {
    "images_json": "TEXT DEFAULT '[]'",
    "script_json": "TEXT DEFAULT '{}'",
    "voice_json": "TEXT DEFAULT '{}'",
    "remake_json": "TEXT DEFAULT '{}'",
}

JSON_FIELDS = {
    "event_json": ("event", dict),
    "article_titles_json": ("article_titles", list),
    "music_links_json": ("music_links", list),
    "images_json": ("images", list),
    "script_json": ("script", dict),
    "voice_json": ("voice", dict),
    "remake_json": ("remake", dict),
}

FIELD_MAP = {
    "status": "status",
    "seed": "seed",
    "article_title": "article_title",
    "article_body": "article_body",
    "first_comment": "first_comment",
    "hashtags": "hashtags",
    "banner_image": "banner_image",
    "video_overlay_text": "video_overlay_text",
    "fb_hook": "fb_hook",
    "caption": "caption",
    "notes": "notes",
    "scheduled_for": "scheduled_for",
}
JSON_IN = {
    "article_titles": "article_titles_json",
    "music_links": "music_links_json",
    "images": "images_json",
    "script": "script_json",
    "voice": "voice_json",
    "event": "event_json",
    "remake": "remake_json",
}


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
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}
        for name, ddl in ADDED_COLUMNS.items():
            if name not in cols:
                conn.execute(f"ALTER TABLE projects ADD COLUMN {name} {ddl}")
        # the old "video" status is now "script" (video rendering was removed)
        conn.execute("UPDATE projects SET status = 'script' WHERE status = 'video'")


def row_to_project(row: sqlite3.Row) -> dict[str, Any]:
    p = dict(row)
    for col, (key, default) in JSON_FIELDS.items():
        if col not in p:
            p[key] = default()
            continue
        raw = p.pop(col, None)
        try:
            loaded = json.loads(raw) if raw else default()
        except json.JSONDecodeError:
            loaded = default()
        p[key] = loaded if isinstance(loaded, type(default())) else default()
    p.pop("video_plan_json", None)
    p["hashtags"] = p.get("hashtags") or ""
    p["images"] = p.get("images") or []
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
    """Copy a project (article, images, script) and reset the publish state."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not row:
        return None
    new_id = uuid.uuid4().hex[:12]
    ts = now()
    reset = {"banner_image": "", "voice_json": "{}", "status": "draft"}
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
        ready = conn.execute("SELECT COUNT(*) c FROM projects WHERE status IN ('ready','scheduled','published')").fetchone()["c"]
        with_banner = conn.execute("SELECT COUNT(*) c FROM projects WHERE banner_image != ''").fetchone()["c"]
    return {"total": total, "by_status": by_status, "ready": ready, "with_banner": with_banner}


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


# --------------------------------------------------------------------------- #
# artists typed in by the operator ("tạo bài viết bằng tên nhân vật")          #
# --------------------------------------------------------------------------- #
CUSTOM_ARTIST_FIELDS = (
    "name", "aka", "genre", "era", "hometown", "birth", "death", "gender", "legacy", "source_url",
)


def create_custom_artist(profile: dict) -> dict:
    import re as _re

    name = (profile.get("name") or "").strip()
    aid = "custom-" + uuid.uuid4().hex[:8]
    values = {key: str(profile.get(key) or "").strip() for key in CUSTOM_ARTIST_FIELDS}
    values["name"] = name
    with connect() as conn:
        conn.execute(
            "INSERT INTO custom_artists (id, name, aka, genre, era, hometown, birth, death, gender, legacy,"
            " facts_json, songs_json, source_url, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                aid,
                values["name"],
                values["aka"],
                values["genre"],
                values["era"],
                values["hometown"],
                values["birth"],
                values["death"],
                values["gender"],
                values["legacy"],
                json.dumps(profile.get("facts") or [], ensure_ascii=False),
                json.dumps(profile.get("songs") or [], ensure_ascii=False),
                values["source_url"],
                now(),
            ),
        )
    del _re  # keep the name lookup simple: ids are generated, names are free-form
    return get_custom_artist(aid)  # type: ignore[return-value]


def row_to_custom_artist(row: sqlite3.Row) -> dict:
    data = dict(row)
    for column, key in (("facts_json", "facts"), ("songs_json", "songs")):
        raw = data.pop(column, "[]")
        try:
            parsed = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            parsed = []
        data[key] = parsed if isinstance(parsed, list) else []
    data["custom"] = True
    return data


def get_custom_artist(aid: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM custom_artists WHERE id = ?", (aid,)).fetchone()
    return row_to_custom_artist(row) if row else None


def list_custom_artists() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM custom_artists ORDER BY created_at DESC").fetchall()
    return [row_to_custom_artist(r) for r in rows]


def find_custom_artist(name: str) -> dict | None:
    needle = (name or "").strip().lower()
    if not needle:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM custom_artists WHERE lower(name) = ? ORDER BY created_at LIMIT 1", (needle,)
        ).fetchone()
    return row_to_custom_artist(row) if row else None


def update_custom_artist(aid: str, patch: dict) -> dict | None:
    sets, params = [], []
    for key in CUSTOM_ARTIST_FIELDS:
        if key in patch and key != "name":
            sets.append(f"{key} = ?")
            params.append(str(patch[key] or "").strip())
    for key, column in (("facts", "facts_json"), ("songs", "songs_json")):
        if key in patch:
            sets.append(f"{column} = ?")
            params.append(json.dumps(patch[key] or [], ensure_ascii=False))
    if not sets:
        return get_custom_artist(aid)
    params.append(aid)
    with connect() as conn:
        conn.execute(f"UPDATE custom_artists SET {', '.join(sets)} WHERE id = ?", params)
    return get_custom_artist(aid)


def delete_custom_artist(aid: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM custom_artists WHERE id = ?", (aid,))
    return cur.rowcount > 0


def count_projects_for_artist(aid: str) -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) c FROM projects WHERE artist_id = ?", (aid,)).fetchone()["c"]


# --------------------------------------------------------------------------- #
# competitor reels ("lọc reels đối thủ đã nổi")                                #
# --------------------------------------------------------------------------- #
RIVAL_FIELDS = (
    "platform", "url", "artist_name", "hook", "views", "likes", "comments", "shares",
    "format", "notes", "posted_at", "status", "remade_project_id",
)


def _rival_values(reel: dict) -> list:
    out = []
    for key in RIVAL_FIELDS:
        value = reel.get(key, "")
        if key in ("views", "likes", "comments", "shares"):
            try:
                out.append(max(0, int(value or 0)))
            except (TypeError, ValueError):
                out.append(0)
        else:
            out.append(str(value or "").strip())
    return out


def create_rival(reel: dict) -> dict:
    rid = uuid.uuid4().hex[:12]
    with connect() as conn:
        conn.execute(
            f"INSERT INTO rival_reels (id, {', '.join(RIVAL_FIELDS)}, created_at)"
            f" VALUES (?, {', '.join(['?'] * len(RIVAL_FIELDS))}, ?)",
            [rid, *_rival_values(reel), now()],
        )
    return get_rival(rid)  # type: ignore[return-value]


def get_rival(rid: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM rival_reels WHERE id = ?", (rid,)).fetchone()
    return dict(row) if row else None


def list_rivals() -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM rival_reels ORDER BY created_at DESC").fetchall()]


def update_rival(rid: str, patch: dict) -> dict | None:
    clean = {k: v for k, v in patch.items() if k in RIVAL_FIELDS}
    if not clean:
        return get_rival(rid)
    sets, params = [], []
    for key, value in clean.items():
        if key in ("views", "likes", "comments", "shares"):
            try:
                value = max(0, int(value or 0))
            except (TypeError, ValueError):
                continue
        else:
            value = str(value or "").strip()
        sets.append(f"{key} = ?")
        params.append(value)
    if not sets:
        return get_rival(rid)
    params.append(rid)
    with connect() as conn:
        conn.execute(f"UPDATE rival_reels SET {', '.join(sets)} WHERE id = ?", params)
    return get_rival(rid)


def delete_rival(rid: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM rival_reels WHERE id = ?", (rid,))
    return cur.rowcount > 0
