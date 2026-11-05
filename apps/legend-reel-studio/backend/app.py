"""Legends Reel Studio — API + static app (article + artist photos + text/voice)."""

from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import subprocess
import time
import zipfile
from datetime import date, datetime, timezone
from urllib.parse import quote

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

import content
import db
import fb_fetch
import images as images_mod
import library
import profiles
import rivals as rivals_mod
import voice as voice_mod

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
WEB_DIR = os.path.join(APP_DIR, "web")
DATA_DIR = os.environ.get("LRS_DATA_DIR") or os.path.join(APP_DIR, "data")
IMAGE_DIR = os.path.join(DATA_DIR, "images")
VOICE_DIR = os.path.join(DATA_DIR, "voice")
MAX_IMAGES = 60
IMAGE_ID_RE = re.compile(r"^[a-f0-9]{8,32}$")

for d in (DATA_DIR, IMAGE_DIR, VOICE_DIR):
    os.makedirs(d, exist_ok=True)

APP_VERSION = "2.5.0"
_COMMIT_CACHE: dict[str, str] = {}


def app_commit() -> str:
    """Short git commit of the running copy (empty when it was not a clone)."""
    if "commit" in _COMMIT_CACHE:
        return _COMMIT_CACHE["commit"]
    commit = ""
    if shutil.which("git"):
        try:
            out = subprocess.run(
                ["git", "-C", os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if out.returncode == 0:
                commit = out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            commit = ""
    _COMMIT_CACHE["commit"] = commit
    return commit


def version_info() -> dict:
    return {
        "app": "legend-reel-studio",
        "version": APP_VERSION,
        "commit": app_commit(),
        "features": [
            "article-700-900",
            "artist-images-auto",
            "browser-image-fallback",
            "bundle-download",
            "voice-new-take-per-render",
            "no-video-render",
            "rivals-ranking",
            "rivals-remake",
            "rivals-page-import",
            "rivals-page-scan",
            "rivals-chrome-impersonate",
            "rivals-from-html",
            "rivals-bookmarklet",
            "rivals-session",
            "facebook-page-extractor",
            "article-by-name",
        ],
    }


def resolve_artist(artist_id: str) -> dict:
    """Curated library artist, or a profile the operator created by name."""
    artist = library.get_artist(artist_id)
    if artist:
        return artist
    return db.get_custom_artist(artist_id) or {}


STATUS_LABELS = {
    "draft": "Nháp",
    "article": "Đã có bài báo",
    "script": "Đã có text & voice",
    "ready": "Sẵn sàng đăng",
    "scheduled": "Đã lên lịch",
    "published": "Đã đăng",
}

db.init_db()
app = FastAPI(title="Legends Reel Studio", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# serialization helpers                                                       #
# --------------------------------------------------------------------------- #
def media_url(path: str) -> str:
    if not path:
        return ""
    path = path if os.path.isabs(path) else os.path.join(DATA_DIR, path)
    path = os.path.abspath(path)
    assets = os.path.join(WEB_DIR, "assets")
    if path.startswith(DATA_DIR + os.sep):
        return "/media/" + path[len(DATA_DIR) + 1:].replace(os.sep, "/")
    if path.startswith(assets + os.sep):
        return "/assets/" + path[len(assets) + 1:].replace(os.sep, "/")
    return ""


def _images(project: dict) -> list[dict]:
    return [images_mod.as_public(img, media_url) for img in (project.get("images") or [])]


def _banner_url(project: dict, public_images: list[dict], artist: dict) -> str:
    banner = project.get("banner_image") or ""
    for img in public_images:
        if img.get("id") == banner and img.get("file_url"):
            return img["file_url"]
    if banner and os.path.isabs(banner) and os.path.exists(banner):
        return media_url(banner)
    return f"/assets/{artist.get('cover', 'bg-stage.jpg')}"


def serialize_project(p: dict) -> dict:
    artist = resolve_artist(p["artist_id"])
    out = dict(p)
    out["artist"] = artist
    public_images = _images(p)
    banner = _banner_url(p, public_images, artist)
    for img in public_images:
        img["is_banner"] = bool(banner) and img.get("file_url") == banner
    out["images"] = public_images
    out["image_count"] = len(public_images)
    out["image_target"] = images_mod.TARGET_IMAGES
    out["banner_url"] = banner
    voice = dict(p.get("voice") or {})
    if voice.get("file"):
        voice["url"] = media_url(voice["file"])
    out["voice"] = voice
    stats = content.article_stats(p.get("article_body") or "")
    out["article_words"] = stats["words"]
    out["article_range"] = [stats["min"], stats["max"]]
    out["article_in_range"] = stats["in_range"]
    out["overlay_words"] = content.word_count(p.get("video_overlay_text") or "")
    out["overlay_ok"] = content.OVERLAY_MIN_WORDS <= out["overlay_words"] <= content.OVERLAY_MAX_WORDS
    out["checks"] = content.engagement_checks(out)
    out["status_label"] = STATUS_LABELS.get(p.get("status", "draft"), p.get("status", ""))
    return out


def get_or_404(pid: str) -> dict:
    project = db.get_project(pid)
    if not project:
        raise HTTPException(404, "Dự án không tồn tại")
    return project


def _remove_media(pid: str) -> None:
    for folder in (os.path.join(IMAGE_DIR, pid), os.path.join(VOICE_DIR, pid)):
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)


# --------------------------------------------------------------------------- #
# bootstrap / library                                                         #
# --------------------------------------------------------------------------- #
@app.get("/api/bootstrap")
def bootstrap(day: str = Query(default="")):
    ref = date.fromisoformat(day) if day else date.today()
    return {
        "today": ref.isoformat(),
        "today_label": ref.strftime("%d/%m/%Y"),
        "artists": library.artists_index(),
        "stats": db.stats(),
        "status_labels": STATUS_LABELS,
        "upcoming": library.upcoming_summary(ref, 21),
        "limits": {
            "article": [content.ARTICLE_MIN_WORDS, content.ARTICLE_MAX_WORDS],
            "overlay": [content.OVERLAY_MIN_WORDS, content.OVERLAY_MAX_WORDS],
            "images": images_mod.TARGET_IMAGES,
        },
        "voices": voice_mod.NEURAL_VOICES,
        "tts_engines": voice_mod.engines(),
        "custom_artists": db.list_custom_artists(),
        "rivals": {
            "count": len(db.list_rivals()),
            "session": fb_fetch.cookie_status(),
            "transports": fb_fetch.transport_status(),
            "platforms": rivals_mod.PLATFORMS,
            "formats": rivals_mod.FORMATS,
            "platform_labels": rivals_mod.PLATFORM_LABEL,
            "format_labels": rivals_mod.FORMAT_LABEL,
        },
        "version": version_info(),
    }


@app.get("/api/events")
def events(
    day: str = Query(default=""),
    window: int = Query(default=7, ge=0, le=400),
    q: str = Query(default=""),
    kinds: str = Query(default=""),
):
    ref = date.fromisoformat(day) if day else date.today()
    kind_list = [k for k in kinds.split(",") if k] if kinds else []
    items = library.search_events(ref=ref, window=window, q=q, kinds=kind_list)
    return {"date": ref.isoformat(), "window": window, "count": len(items), "events": items}


@app.get("/api/artists")
def artists():
    return {"artists": library.artists_index(), "custom": db.list_custom_artists()}


@app.get("/api/artists/custom")
def custom_artists():
    return {"artists": db.list_custom_artists()}


@app.post("/api/artists/custom")
def create_custom_artist(payload: dict = Body(...)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Cần tên nhân vật")
    existing = db.find_custom_artist(name)
    if existing:
        return {"artist": existing, "created": False}
    profile = profiles.normalize({**payload, "name": name})
    artist = db.create_custom_artist(profile)
    return {"artist": artist, "created": True}


@app.patch("/api/artists/custom/{aid}")
def patch_custom_artist(aid: str, payload: dict = Body(...)):
    if not db.get_custom_artist(aid):
        raise HTTPException(404, "Không tìm thấy nhân vật")
    return {"artist": db.update_custom_artist(aid, payload)}


@app.delete("/api/artists/custom/{aid}")
def remove_custom_artist(aid: str):
    if not db.get_custom_artist(aid):
        raise HTTPException(404, "Không tìm thấy nhân vật")
    if db.count_projects_for_artist(aid):
        raise HTTPException(400, "Nhân vật này đang có dự án — xoá dự án trước")
    db.delete_custom_artist(aid)
    return {"ok": True}


@app.get("/api/artists/{artist_id}")
def artist_detail(artist_id: str):
    artist = resolve_artist(artist_id)
    if not artist:
        raise HTTPException(404, "Không tìm thấy nghệ sĩ")
    return {"artist": artist}


@app.post("/api/events/custom")
def create_custom_event(payload: dict = Body(...)):
    return db.add_custom_event(
        artist_id=payload["artist_id"],
        date_str=payload["date"],
        title=payload["title"],
        kind=payload.get("kind", "custom"),
        note=payload.get("note", ""),
    )


# --------------------------------------------------------------------------- #
# projects                                                                    #
# --------------------------------------------------------------------------- #
@app.get("/api/projects")
def projects(status: str = "", q: str = ""):
    return {"projects": [serialize_project(p) for p in db.list_projects(status=status, q=q)]}


@app.post("/api/projects")
def create_project(payload: dict = Body(...)):
    artist_id = payload.get("artist_id", "")
    if not library.get_artist(artist_id):
        raise HTTPException(400, "artist_id không hợp lệ")
    event = payload.get("event") or {}
    if not event.get("kind"):
        raise HTTPException(400, "Thiếu sự kiện")
    seed = int(payload.get("seed") or (int(time.time() * 1000) % 99991))
    project = db.create_project(artist_id, event, seed)
    if payload.get("generate", True):
        project = apply_generation(project, section="all", seed=seed)
    return serialize_project(project)


@app.post("/api/projects/custom")
def create_project_for_name(payload: dict = Body(...)):
    """Tạo bài viết bằng tên nhân vật: name (+ optional profile) + occasion."""
    name = (payload.get("name") or payload.get("artist_name") or "").strip()
    if not name:
        raise HTTPException(400, "Cần tên nhân vật")
    artist = db.find_custom_artist(name)
    if not artist:
        profile = profiles.normalize({**(payload.get("profile") or {}), **(payload or {}), "name": name})
        artist = db.create_custom_artist(profile)
    else:
        patch = {k: v for k, v in (payload.get("profile") or payload).items() if k in profiles.normalize({})}
        patch.pop("name", None)
        if patch:
            artist = db.update_custom_artist(artist["id"], patch) or artist

    event_payload = payload.get("event") or {}
    kind = event_payload.get("kind") or "custom"
    date_str = event_payload.get("date") or date.today().isoformat()
    event = profiles.make_event(
        artist,
        kind,
        date_str,
        title=event_payload.get("title", ""),
        note=event_payload.get("note", ""),
        years=int(event_payload.get("years") or 0),
    )
    seed = int(payload.get("seed") or (int(time.time() * 1000) % 99991))
    project = db.create_project(artist["id"], event, seed)
    if payload.get("generate", True):
        project = apply_generation(project, section="all", seed=seed)
    return serialize_project(project)


@app.get("/api/projects/{pid}")
def project_detail(pid: str):
    return serialize_project(get_or_404(pid))


@app.patch("/api/projects/{pid}")
def patch_project(pid: str, patch: dict = Body(...)):
    get_or_404(pid)
    allowed = {
        "status", "article_title", "article_body", "first_comment", "hashtags",
        "video_overlay_text", "fb_hook", "caption", "notes", "scheduled_for",
        "article_titles", "music_links", "script", "seed",
    }
    clean = {k: v for k, v in patch.items() if k in allowed}
    updated = db.update_project(pid, clean)
    return serialize_project(updated)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    get_or_404(pid)
    _remove_media(pid)
    db.delete_project(pid)
    return {"ok": True}


@app.post("/api/projects/{pid}/duplicate")
def duplicate_project(pid: str):
    src = get_or_404(pid)
    copy = db.duplicate_project(pid)
    assert copy is not None
    # copy the images folder too, so deleting the original cannot break the copy
    src_dir = os.path.join(IMAGE_DIR, pid)
    if os.path.isdir(src_dir):
        shutil.copytree(src_dir, os.path.join(IMAGE_DIR, copy["id"]), dirs_exist_ok=True)
    new_images = []
    for img in src.get("images") or []:
        item = dict(img)
        if item.get("file"):
            item["file"] = item["file"].replace(f"images/{pid}/", f"images/{copy['id']}/")
        new_images.append(item)
    banner = src.get("banner_image") or ""
    copy = db.update_project(copy["id"], {"images": new_images, "banner_image": banner, "voice": {}})
    return serialize_project(copy)


# --------------------------------------------------------------------------- #
# generation                                                                  #
# --------------------------------------------------------------------------- #
def apply_generation(project: dict, section: str = "all", seed: int | None = None, overlay_text: str = "") -> dict:
    artist = resolve_artist(project["artist_id"])
    event = project.get("event") or {}
    seed = seed if seed is not None else project.get("seed", 1)
    patch: dict = {"seed": seed}
    article = None
    # operator-typed names use the profile generator (it never invents facts)
    gen = profiles if artist.get("custom") else content

    if section in ("article", "all"):
        article = gen.article_for(artist, event, seed)
        patch.update(
            {
                "article_title": article["title"],
                "article_titles": article["title_variants"],
                "article_body": article["body"],
                "first_comment": article["first_comment"],
                "hashtags": " ".join(article["hashtags"]),
                "music_links": article.get("music_links") or artist.get("songs") or [],
            }
        )
        if project.get("status") in (None, "", "draft"):
            patch["status"] = "article"

    if section in ("script", "all"):
        plan = gen.script_for(artist, event, article, seed)
        if overlay_text.strip():
            plan["overlay_text"] = overlay_text.strip()
            plan["overlay_words"] = content.word_count(overlay_text)
            plan["overlay_ok"] = content.OVERLAY_MIN_WORDS <= plan["overlay_words"] <= content.OVERLAY_MAX_WORDS
        patch.update(
            {
                "script": plan,
                "video_overlay_text": plan["overlay_text"],
                "fb_hook": plan["fb_hook"],
                "caption": plan["caption"],
                "hashtags": " ".join(plan.get("hashtags") or []),
            }
        )
        if (project.get("status") or "draft") in ("draft", "article"):
            patch["status"] = "script"

    return db.update_project(project["id"], patch)


@app.post("/api/projects/{pid}/generate")
def generate(pid: str, payload: dict = Body(default={})):
    project = get_or_404(pid)
    section = payload.get("section", "all")
    if section not in ("article", "script", "all"):
        raise HTTPException(400, "section phải là article, script hoặc all")
    seed = payload.get("seed")
    seed = int(seed) if seed is not None else int(time.time() * 1000) % 99991
    overlay = payload.get("overlay_text", "")
    updated = apply_generation(project, section=section, seed=seed, overlay_text=overlay)
    return serialize_project(updated)


@app.get("/api/projects/{pid}/overlay-options")
def overlay_options(pid: str):
    project = get_or_404(pid)
    artist = resolve_artist(project["artist_id"])
    event = project.get("event") or {}
    return {"options": content.overlay_variants(artist, event)}


@app.post("/api/projects/{pid}/overlay")
def set_overlay(pid: str, payload: dict = Body(...)):
    project = get_or_404(pid)
    text = (payload.get("text") or "").strip()
    words = content.word_count(text)
    script = dict(project.get("script") or {})
    script["overlay_text"] = text
    script["overlay_words"] = words
    script["overlay_ok"] = content.OVERLAY_MIN_WORDS <= words <= content.OVERLAY_MAX_WORDS
    updated = db.update_project(pid, {"video_overlay_text": text, "script": script})
    return {
        "project": serialize_project(updated),
        "words": words,
        "ok": content.OVERLAY_MIN_WORDS <= words <= content.OVERLAY_MAX_WORDS,
        "range": [content.OVERLAY_MIN_WORDS, content.OVERLAY_MAX_WORDS],
    }


# --------------------------------------------------------------------------- #
# artist images                                                               #
# --------------------------------------------------------------------------- #
def _store_images(pid: str, project: dict, incoming: list[dict]) -> tuple[list[dict], list[str]]:
    current = list(project.get("images") or [])
    known = {img.get("id") for img in current}
    known_urls = {img.get("url") for img in current if img.get("url")}
    added, errors = [], []
    for record in incoming:
        if len(current) >= MAX_IMAGES:
            errors.append(f"Dự án đã đạt giới hạn {MAX_IMAGES} ảnh")
            break
        item = dict(record)
        filename = item.pop("filename", "") or "image.jpg"
        raw = item.pop("_raw", b"")
        data_url = item.pop("data_url", "")
        url = item.get("url") or ""
        if data_url and not raw:
            try:
                raw = images_mod.decode_data_url(data_url)
            except images_mod.ImageFetchError as exc:
                errors.append(f"{url or filename}: {exc}")
                continue
        if url and url in known_urls:
            continue
        try:
            if raw and not url:
                stored = images_mod.import_upload(DATA_DIR, pid, raw, filename)
            elif raw:
                stored = images_mod.save_image(DATA_DIR, pid, raw, item)
            else:
                stored = images_mod.import_from_url(DATA_DIR, pid, url, item)
        except images_mod.ImageFetchError as exc:
            errors.append(f"{url or filename}: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001 - never break a batch on one bad file
            errors.append(f"{url or filename}: {exc}")
            continue
        if stored.get("id") in known:
            # same file already in the project (e.g. the same URL pasted twice)
            continue
        current.append(stored)
        known.add(stored["id"])
        if stored.get("url"):
            known_urls.add(stored["url"])
        added.append(stored)
    if added:
        db.update_project(pid, {"images": current})
        project["images"] = current
        if not project.get("banner_image"):
            db.update_project(pid, {"banner_image": added[0]["id"]})
            project["banner_image"] = added[0]["id"]
    return added, errors


@app.get("/api/projects/{pid}/images")
def list_images(pid: str):
    project = get_or_404(pid)
    return {
        "images": _images(project),
        "target": images_mod.TARGET_IMAGES,
        "banner": project.get("banner_image", ""),
    }


@app.get("/api/projects/{pid}/images/suggest")
def suggest_images(pid: str, limit: int = Query(default=20, ge=1, le=40)):
    project = get_or_404(pid)
    artist = resolve_artist(project["artist_id"])
    try:
        data = images_mod.suggest_for_artist(artist, limit=limit)
    except images_mod.ImageFetchError as exc:
        raise HTTPException(502, str(exc)) from exc
    existing_urls = {img.get("url") for img in project.get("images") or [] if img.get("url")}
    data["images"] = [img for img in data["images"] if img["url"] not in existing_urls]
    data["existing"] = len(project.get("images") or [])
    return data


@app.post("/api/projects/{pid}/images")
def add_images(pid: str, payload: dict = Body(...)):
    project = get_or_404(pid)
    incoming: list[dict] = []
    if payload.get("url"):
        incoming.append({"url": payload["url"], **_meta_from(payload)})
    for url in payload.get("urls") or []:
        if isinstance(url, str) and url.strip():
            incoming.append({"url": url.strip(), **_meta_from(payload, drop_url=True)})
    for item in payload.get("images") or []:
        if isinstance(item, dict) and (item.get("url") or item.get("data_url")):
            incoming.append({k: v for k, v in item.items() if k != "file_url"})
    if not incoming:
        raise HTTPException(400, "Cần ít nhất một link ảnh (url hoặc urls)")
    added, errors = _store_images(pid, project, incoming)
    return {
        "project": serialize_project(get_or_404(pid)),
        "added": len(added),
        "errors": errors,
    }


def _meta_from(payload: dict, drop_url: bool = False) -> dict:
    keep = ("source", "title", "page_url", "license", "license_url", "attribution", "description")
    meta = {k: payload[k] for k in keep if payload.get(k)}
    if drop_url:
        meta.pop("url", None)
    return meta


@app.post("/api/projects/{pid}/images/auto")
def auto_images(pid: str, payload: dict = Body(default={})):
    """Fetch and store artist photos in one call (server-side download)."""
    project = get_or_404(pid)
    artist = resolve_artist(project["artist_id"])
    current = list(project.get("images") or [])
    remaining = MAX_IMAGES - len(current)
    if remaining <= 0:
        return {"project": serialize_project(project), "added": 0, "suggested": 0, "errors": [f"Dự án đã đạt {MAX_IMAGES} ảnh"]}
    try:
        count = int(payload.get("count") or images_mod.TARGET_IMAGES)
    except (TypeError, ValueError):
        count = images_mod.TARGET_IMAGES
    count = max(1, min(count, remaining))
    try:
        data = images_mod.suggest_for_artist(artist, limit=max(count, 24))
    except images_mod.ImageFetchError as exc:
        raise HTTPException(502, str(exc)) from exc
    known_urls = {img.get("url") for img in current if img.get("url")}
    picks = [c for c in data["images"] if c["url"] not in known_urls][:count]
    added, errors = _store_images(pid, project, picks)
    return {
        "project": serialize_project(get_or_404(pid)),
        "added": len(added),
        "suggested": len(data["images"]),
        "errors": (data.get("errors") or []) + errors,
    }


@app.post("/api/projects/{pid}/images/upload")
async def upload_images(pid: str, request: Request):
    project = get_or_404(pid)
    ctype = request.headers.get("content-type", "")
    if not ctype.startswith("multipart/form-data"):
        raise HTTPException(400, "Cần gửi multipart/form-data")
    form = await request.form()
    incoming: list[dict] = []
    for _, value in form.multi_items():
        if hasattr(value, "read"):
            raw = await value.read()
            if not raw:
                continue
            name = getattr(value, "filename", "") or "image.jpg"
            incoming.append({"_raw": raw, "filename": name, "source": "upload"})
    if not incoming:
        raise HTTPException(400, "Thiếu file ảnh")
    added, errors = _store_images(pid, project, incoming)
    return {"project": serialize_project(get_or_404(pid)), "added": len(added), "errors": errors}


def _find_image(project: dict, image_id: str) -> dict:
    if not IMAGE_ID_RE.match(image_id or ""):
        raise HTTPException(400, "image_id không hợp lệ")
    for img in project.get("images") or []:
        if img.get("id") == image_id:
            return img
    raise HTTPException(404, "Ảnh không tồn tại trong dự án")


@app.patch("/api/projects/{pid}/images/{image_id}")
def patch_image(pid: str, image_id: str, payload: dict = Body(...)):
    project = get_or_404(pid)
    _find_image(project, image_id)
    if payload.get("is_banner"):
        project = db.update_project(pid, {"banner_image": image_id})
    return {"project": serialize_project(project)}


@app.delete("/api/projects/{pid}/images/{image_id}")
def delete_image(pid: str, image_id: str):
    project = get_or_404(pid)
    image = _find_image(project, image_id)
    remaining = [img for img in project.get("images") or [] if img.get("id") != image_id]
    patch = {"images": remaining}
    if project.get("banner_image") == image_id:
        patch["banner_image"] = remaining[0]["id"] if remaining else ""
    db.update_project(pid, patch)
    path = os.path.join(DATA_DIR, image.get("file", ""))
    if image.get("file") and os.path.exists(path):
        os.remove(path)
    return {"project": serialize_project(get_or_404(pid)), "ok": True}


@app.get("/api/projects/{pid}/images/{image_id}/download")
def download_image(pid: str, image_id: str):
    project = get_or_404(pid)
    image = _find_image(project, image_id)
    path = os.path.join(DATA_DIR, image.get("file", ""))
    if not os.path.exists(path):
        raise HTTPException(404, "File ảnh không còn trên đĩa")
    artist = resolve_artist(project["artist_id"])
    slug = re.sub(r"[^a-z0-9]+", "-", (artist.get("id") or "artist").lower()).strip("-")
    index = (project.get("images") or []).index(image) + 1
    return FileResponse(path, media_type="image/jpeg", filename=f"{slug}-{index:02d}.jpg")


@app.get("/api/projects/{pid}/images.zip")
def download_images_zip(pid: str):
    project = get_or_404(pid)
    artist = resolve_artist(project["artist_id"])
    slug = re.sub(r"[^a-z0-9]+", "-", (artist.get("id") or "artist").lower()).strip("-")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, image in enumerate(project.get("images") or [], 1):
            path = os.path.join(DATA_DIR, image.get("file", ""))
            if image.get("file") and os.path.exists(path):
                archive.write(path, arcname=f"{slug}-{index:02d}.jpg")
        archive.writestr("ATTRIBUTION.txt", images_mod.attribution_text(project.get("images") or [], artist.get("name", "")))
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{slug}-images.zip"'}
    return Response(buffer.getvalue(), media_type="application/zip", headers=headers)


# --------------------------------------------------------------------------- #
# competitor reels: filter what already went viral, then remake it            #
# --------------------------------------------------------------------------- #
@app.get("/api/rivals")
def list_rivals(
    q: str = Query(default=""),
    platform: str = Query(default=""),
    fmt: str = Query(default=""),
    status: str = Query(default=""),
    sort: str = Query(default="score"),
    min_score: int = Query(default=0, ge=0, le=100),
    only_unused: bool = Query(default=False),
    page: str = Query(default=""),
    only_viral: bool = Query(default=False),
):
    items = [rivals_mod.with_score(r) for r in db.list_rivals()]
    needle = q.strip().lower()
    if needle:
        items = [
            r for r in items
            if needle in (r.get("artist_name") or "").lower()
            or needle in (r.get("hook") or "").lower()
            or needle in (r.get("notes") or "").lower()
        ]
    if platform:
        items = [r for r in items if r.get("platform") == platform]
    if fmt:
        items = [r for r in items if r.get("format") == fmt]
    if status:
        items = [r for r in items if r.get("status") == status]
    if only_unused:
        items = [r for r in items if not r.get("remade_project_id")]
    if page:
        needle_page = page.lower().strip()
        items = [r for r in items if needle_page in str(r.get("source_page") or "").lower()]
    floor = max(min_score, 65 if only_viral else 0)
    items = [r for r in items if r["score"] >= floor]

    keys = {
        "score": lambda r: (r["score"], r.get("views") or 0),
        "views": lambda r: r.get("views") or 0,
        "engagement": lambda r: r.get("engagement") or 0,
        "recent": lambda r: r.get("created_at") or "",
    }
    items.sort(key=keys.get(sort, keys["score"]), reverse=True)
    page_counts: dict[str, int] = {}
    for reel in db.list_rivals():
        label = str(reel.get("source_page") or "").strip()
        if label:
            page_counts[label] = page_counts.get(label, 0) + 1
    return {
        "reels": items,
        "count": len(items),
        "pages": [{"page": k, "count": v} for k, v in sorted(page_counts.items())],
        "platforms": rivals_mod.PLATFORMS,
        "formats": rivals_mod.FORMATS,
        "format_labels": rivals_mod.FORMAT_LABEL,
        "platform_labels": rivals_mod.PLATFORM_LABEL,
        "bulk_help": rivals_mod.BULK_HELP,
    }


@app.post("/api/rivals")
def add_rivals(payload: dict = Body(...)):
    items: list[dict] = []
    if isinstance(payload.get("items"), list):
        items = [i for i in payload["items"] if isinstance(i, dict)]
    if payload.get("lines"):
        items += rivals_mod.parse_bulk(payload["lines"])
    if payload.get("url") or payload.get("hook"):
        items.append({k: v for k, v in payload.items() if k not in ("lines", "items")})
    if not items:
        raise HTTPException(400, "Cần ít nhất một reel (lines, items hoặc url)")

    created, errors = [], []
    for item in items:
        record = _reel_record(item)
        if not record["url"] and not record["hook"] and not record["artist_name"]:
            errors.append("Bỏ qua một dòng vì thiếu cả link, hook và tên nghệ sĩ")
            continue
        created.append(rivals_mod.with_score(db.create_rival(record)))
    return {"reels": created, "added": len(created), "errors": errors}


def _reel_record(item: dict, source_page: str = "") -> dict:
    platform = (item.get("platform") or rivals_mod.platform_from_url(item.get("url", ""))).lower()
    if platform not in rivals_mod.PLATFORMS:
        platform = "facebook"
    fmt = (item.get("format") or "story").lower()
    if fmt not in rivals_mod.FORMATS:
        fmt = "story"
    return {
        "platform": platform,
        "url": str(item.get("url") or "").strip(),
        "artist_name": str(item.get("artist_name") or "").strip(),
        "hook": str(item.get("hook") or "").strip(),
        "views": rivals_mod.count_from_text(item.get("views")),
        "likes": rivals_mod.count_from_text(item.get("likes")),
        "comments": rivals_mod.count_from_text(item.get("comments")),
        "shares": rivals_mod.count_from_text(item.get("shares")),
        "format": fmt,
        "notes": str(item.get("notes") or "").strip(),
        "posted_at": str(item.get("posted_at") or "").strip(),
        "source_page": source_page or str(item.get("source_page") or "").strip(),
    }


def _save_page_items(
    items: list[dict],
    page_url: str,
    label: str,
    *,
    only_viral: bool = False,
    min_score: int = 0,
) -> dict:
    """Khử trùng, chấm điểm, lọc "đã nổi" và lưu — dùng chung cho mọi đường nhập."""
    existing = db.list_rivals()
    seen_urls = {str(r.get("url") or "").lower() for r in existing if r.get("url")}
    seen_hooks = {
        (str(r.get("hook") or "").lower(), str(r.get("source_page") or ""))
        for r in existing
        if r.get("hook") and r.get("platform") == "facebook"
    }

    skipped, low = 0, 0
    candidates: list[dict] = []
    batch_urls: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        record = _reel_record(item, label)
        if not record["url"] and not record["hook"]:
            skipped += 1
            continue
        url_key = record["url"].lower()
        hook_key = (record["hook"].lower(), record["source_page"])
        if (url_key and url_key in seen_urls) or (record["hook"] and hook_key in seen_hooks) or (url_key and url_key in batch_urls):
            skipped += 1
            continue
        if url_key:
            batch_urls.add(url_key)
        candidates.append(rivals_mod.with_score({**record, "id": ""}))

    # "đã nổi" = điểm ≥ 60. Page nhỏ chưa bài nào đạt 60 thì giữ nhóm nổi nhất
    # của chính page đó (top 40%) để bạn vẫn có cái để làm lại, không bị rỗng.
    keep = set(range(len(candidates)))
    if only_viral and candidates:
        best = max(c["score"] for c in candidates)
        if best >= 60:
            keep = {i for i, c in enumerate(candidates) if c["score"] >= 60}
        else:
            ranked = sorted(range(len(candidates)), key=lambda i: candidates[i]["score"], reverse=True)
            keep = set(ranked[: max(1, math.ceil(len(candidates) * 0.4))])

    created = []
    for index, candidate in enumerate(candidates):
        score = candidate["score"]
        if only_viral and index not in keep:
            low += 1
            continue
        if min_score and score < min_score:
            low += 1
            continue
        record = {k: v for k, v in candidate.items() if k not in rivals_mod.SCORE_FIELDS}
        created.append(rivals_mod.with_score(db.create_rival(record)))

    created.sort(key=lambda r: r["score"], reverse=True)
    return {
        "reels": created,
        "added": len(created),
        "skipped": skipped,
        "filtered_out": low,
        "candidates": len(candidates),
    }


@app.post("/api/rivals/scan-page")
def scan_rivals_page(payload: dict = Body(...)):
    """Dán link page → studio tự đọc page đó và chỉ giữ bài đã nổi.

    Không cần DevTools, không cần copy mã: máy chủ gọi facebook.com (thử lần lượt
    UA trình duyệt / crawler, và cookie phiên nếu bạn đã lưu một lần), bóc số
    liệu từ HTML, chấm điểm rồi lưu.

    Nếu Facebook chặn, phản hồi có `status="blocked"` + `attempts` để giao diện
    giải thích, kèm gợi ý lưu cookie phiên (`POST /api/rivals/session`).
    """
    raw = str(payload.get("page_url") or payload.get("url") or "").strip()
    if not raw:
        raise HTTPException(400, "Cần link page Facebook của đối thủ")
    if rivals_mod.is_single_post(raw):
        target = rivals_mod.clean_url(raw)
    else:
        target = rivals_mod.normalize_page_url(raw)
    if not target:
        raise HTTPException(400, "Link không giống link page Facebook — dán dạng facebook.com/ten-page")

    label = rivals_mod.page_label(target)
    only_viral = bool(payload.get("only_viral", True))
    min_score = int(payload.get("min_score") or 0)
    limit = max(1, min(120, int(payload.get("limit") or 40)))

    scan = fb_fetch.scan_page(
        target,
        cookie="" if payload.get("ignore_session") else fb_fetch.load_cookie(),
        budget_s=float(payload.get("budget_s") or fb_fetch.DEFAULT_BUDGET_S),
    )
    posts = (scan.get("posts") or [])[:limit]
    result = {
        "status": scan["status"],
        "message": fb_fetch.explain(scan),
        "scanned": len(scan.get("posts") or []),
        "attempts": scan.get("attempts") or [],
        "page_url": scan.get("page_url") or target,
        "page_label": scan.get("page_label") or label,
        "cookie_used": scan.get("cookie_used", False),
        "needs_session": scan.get("needs_session", False),
        "elapsed_ms": scan.get("elapsed_ms", 0),
        "session": fb_fetch.cookie_status(),
        "transports": scan.get("transports") or [],
        "capabilities": scan.get("capabilities") or fb_fetch.transport_status(),
        "reels": [],
        "added": 0,
        "skipped": 0,
        "filtered_out": 0,
        "candidates": 0,
        "errors": [],
    }
    if not posts:
        return JSONResponse(result)

    items = rivals_mod.from_posts(posts, target)
    saved = _save_page_items(
        items,
        target,
        result["page_label"],
        only_viral=only_viral,
        min_score=min_score,
    )
    result.update(saved)
    return JSONResponse(result)


@app.get("/api/rivals/session")
def get_rivals_session():
    """Cookie phiên Facebook đã lưu (một lần) để máy chủ đọc được page."""
    return fb_fetch.cookie_status()


@app.post("/api/rivals/session")
def save_rivals_session(payload: dict = Body(...)):
    """Lưu cookie phiên Facebook (cục bộ, `data/fb_session.json`, quyền 600).

    Dán cookie một lần là từ đó chỉ cần dán link page. Studio chỉ gửi cookie này
    tới facebook.com, không gửi cho bên thứ ba.
    """
    raw = str(payload.get("cookie") or "").strip()
    if not raw:
        raise HTTPException(400, "Cần cookie dạng `c_user=…; xs=…`")
    if not fb_fetch.parse_cookie(raw):
        raise HTTPException(400, "Cookie không đúng dạng cặp tên=giá trị")
    try:
        return fb_fetch.save_cookie(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.delete("/api/rivals/session")
def clear_rivals_session():
    return fb_fetch.clear_cookie()


def _reels_from_html(html: str, page_url: str = "") -> list[dict]:
    """Bóc reel từ HTML người dùng lưu (Ctrl+S) — thử cả JSON nhúng lẫn DOM."""
    items = fb_fetch.extract_posts(html, page_url)
    items += rivals_mod.posts_from_html(html, page_url)
    return items


@app.post("/api/rivals/from-html")
def import_from_html(payload: dict = Body(...)):
    """Nhập từ HTML của trang Facebook (Ctrl+S) — không cần DevTools.

    Đây là đường chắc chắn nhất khi Facebook chặn máy chủ: trang bạn lưu đã là
    bản đã đăng nhập, có đủ số liệu trong DOM và trong JSON nhúng.
    """
    html = str(payload.get("html") or "")
    if len(html.strip()) < 200:
        raise HTTPException(400, "File HTML quá nhỏ — hãy lưu nguyên trang (Ctrl+S) rồi thử lại")
    page_url = rivals_mod.normalize_page_url(payload.get("page_url") or "")
    label = rivals_mod.page_label(page_url) if page_url else ""
    items = _reels_from_html(html, page_url)
    if not items:
        raise HTTPException(
            400,
            "Không thấy reel nào trong file HTML. Hãy mở đúng tab reels/videos của page, cuộn vài lần rồi lưu trang.",
        )
    saved = _save_page_items(
        items,
        page_url,
        label,
        only_viral=bool(payload.get("only_viral", True)),
        min_score=int(payload.get("min_score") or 0),
    )
    return {**saved, "page_url": page_url, "page_label": label, "scanned": len(items), "errors": []}


@app.get("/api/rivals/bookmarklet")
def rivals_bookmarklet(request: Request):
    """Một dòng `javascript:` để kéo lên thanh bookmark (không cần DevTools).

    Nội dung lấy từ `web/assets/fb-extract.js` (một nguồn duy nhất), thay địa chỉ
    studio bằng origin đang mở, bỏ chú thích và gộp thành một dòng.
    """
    source_path = os.path.join(WEB_DIR, "assets", "fb-extract.js")
    try:
        with open(source_path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except OSError as exc:  # pragma: no cover - chỉ khi thiếu file
        raise HTTPException(500, f"Không đọc được fb-extract.js: {exc}") from exc
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    origin = str(request.base_url).rstrip("/")
    source = re.sub(r"const STUDIO = [^;]+;", f'const STUDIO = "{origin}";', source, count=1)
    code = " ".join(line.strip() for line in source.splitlines() if line.strip())
    return {
        "href": "javascript:" + quote(code, safe=""),
        "origin": origin,
        "length": len(code),
    }


@app.post("/api/rivals/from-page")
def import_from_page(payload: dict = Body(...)):
    """Ba đường nhập tay khi Facebook không cho máy chủ đọc page.

    1. `posts`: JSON do `web/assets/fb-extract.js` trích từ trang bạn đang mở.
    2. `html`:  HTML bạn lưu từ trang (Ctrl+S) — studio tự bóc khối `role="article"`.
    3. `page_url` + `items`: danh sách bạn tự gõ nhưng muốn gắn chung một page.

    Đường chính vẫn là `POST /api/rivals/scan-page` (chỉ cần link page).
    """
    page_url = rivals_mod.normalize_page_url(payload.get("page_url") or "")
    label = rivals_mod.page_label(page_url) if page_url else ""

    items: list[dict] = []
    if isinstance(payload.get("posts"), list):
        items += rivals_mod.from_posts(payload["posts"], page_url)
    if payload.get("html"):
        items += _reels_from_html(str(payload["html"]), page_url)
    if isinstance(payload.get("items"), list):
        items += [_reel_record(i, label) for i in payload["items"] if isinstance(i, dict)]
    if not items:
        raise HTTPException(
            400,
            "Không đọc được bài nào. Dán link page vào ô trên để studio tự đọc, hoặc dán JSON lấy từ trang.",
        )

    saved = _save_page_items(
        items,
        page_url,
        label,
        only_viral=bool(payload.get("only_viral")),
        min_score=int(payload.get("min_score") or 0),
    )
    return {
        **saved,
        "page_url": page_url,
        "page_label": label,
        "errors": [],
    }


@app.get("/api/rivals/pages")
def rival_pages():
    """Which competitor pages already have reels saved (for the filter dropdown)."""
    counts: dict[str, int] = {}
    for reel in db.list_rivals():
        page = str(reel.get("source_page") or "").strip()
        if page:
            counts[page] = counts.get(page, 0) + 1
    pages = [{"page": page, "count": count} for page, count in sorted(counts.items())]
    return {"pages": pages}


@app.patch("/api/rivals/{rid}")
def patch_rival(rid: str, payload: dict = Body(...)):
    if not db.get_rival(rid):
        raise HTTPException(404, "Không tìm thấy reel")
    updated = db.update_rival(rid, payload)
    return {"reel": rivals_mod.with_score(updated or {})}


@app.delete("/api/rivals/{rid}")
def remove_rival(rid: str):
    if not db.delete_rival(rid):
        raise HTTPException(404, "Không tìm thấy reel")
    return {"ok": True}


def _pick_library_event(artist: dict, ref: date) -> dict | None:
    try:
        events = library.artist_events(artist, ref, 365)
    except Exception:  # noqa: BLE001 - a remake must never fail because of calendar math
        return None
    return events[0] if events else None


def _remake_event(artist: dict, payload: dict, reel: dict) -> dict:
    event_payload = payload.get("event") or {}
    if event_payload.get("kind") and event_payload.get("date") and event_payload.get("years") is not None:
        return event_payload
    if artist.get("custom"):
        return profiles.make_event(
            artist,
            event_payload.get("kind") or "custom",
            event_payload.get("date") or date.today().isoformat(),
            title=event_payload.get("title") or (reel.get("hook") or ""),
            note=event_payload.get("note", ""),
            years=int(event_payload.get("years") or 0),
        )
    event = _pick_library_event(artist, date.today())
    if event:
        return event
    return profiles.make_event(
        artist,
        "custom",
        date.today().isoformat(),
        title=event_payload.get("title") or (reel.get("hook") or f"{artist.get('name', '')} — remake"),
        note=event_payload.get("note", ""),
    )


@app.post("/api/rivals/{rid}/remake")
def remake_rival(rid: str, payload: dict = Body(default={})):
    """Turn a winning competitor reel into a new project with the same structure."""
    reel = db.get_rival(rid)
    if not reel:
        raise HTTPException(404, "Không tìm thấy reel")
    scored = rivals_mod.with_score(reel)

    artist_id = (payload.get("artist_id") or "").strip()
    artist = resolve_artist(artist_id) if artist_id else {}
    if not artist:
        name = (payload.get("artist_name") or reel.get("artist_name") or "").strip()
        if not name:
            raise HTTPException(400, "Chọn nghệ sĩ hoặc nhập tên nhân vật để làm lại")
        artist = library.get_artist(name.lower().replace(" ", "-")) or db.find_custom_artist(name) or {}
        if not artist:
            artist = db.create_custom_artist(profiles.normalize({"name": name}))

    event = _remake_event(artist, payload, reel)
    seed = int(payload.get("seed") or (int(time.time() * 1000) % 99991))
    project = db.create_project(artist["id"], event, seed)
    remake = {
        "rival_id": rid,
        "platform": reel.get("platform", ""),
        "platform_label": rivals_mod.PLATFORM_LABEL.get(reel.get("platform", ""), ""),
        "url": reel.get("url", ""),
        "hook": reel.get("hook", ""),
        "artist_name": reel.get("artist_name", ""),
        "views": reel.get("views") or 0,
        "score": scored["score"],
        "tier": scored["tier"],
        "format": reel.get("format", ""),
        "format_label": rivals_mod.FORMAT_LABEL.get(reel.get("format", ""), ""),
        "brief": scored["brief"],
        "remade_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    project = db.update_project(project["id"], {"remake": remake})
    if payload.get("generate", True):
        project = apply_generation(project, section="all", seed=seed)
    db.update_rival(rid, {"status": "remaking", "remade_project_id": project["id"]})
    return {"project": serialize_project(project), "reel": rivals_mod.with_score(db.get_rival(rid) or {})}


# --------------------------------------------------------------------------- #
# voice                                                                       #
# --------------------------------------------------------------------------- #
@app.get("/api/version")
def version():
    return version_info()


@app.get("/api/voices")
def voices():
    return {"voices": voice_mod.NEURAL_VOICES, "engines": voice_mod.engines(), "default": voice_mod.DEFAULT_VOICE}


@app.post("/api/projects/{pid}/voice")
def make_voice(pid: str, payload: dict = Body(...)):
    project = get_or_404(pid)
    text = (payload.get("text") or "").strip()
    voice = payload.get("voice") or voice_mod.DEFAULT_VOICE
    if not text:
        text = project.get("video_overlay_text") or ""
    try:
        result = voice_mod.synthesize(DATA_DIR, pid, text, voice)
    except voice_mod.VoiceError as exc:
        raise HTTPException(400, str(exc)) from exc
    record = {
        "file": result["file"],
        "engine": result["engine"],
        "voice": result["voice"],
        "requested_voice": result.get("requested_voice", result["voice"]),
        "applied": bool(result.get("applied", True)),
        "note": result.get("note", ""),
        "ext": result["ext"],
        "bytes": result["bytes"],
        "duration": result["duration"],
        "text": result["text"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    previous = (project.get("voice") or {}).get("file")
    if previous and previous != record["file"]:
        stale = os.path.join(DATA_DIR, previous)
        if os.path.exists(stale):
            try:
                os.remove(stale)
            except OSError:
                pass
    updated = serialize_project(db.update_project(pid, {"voice": record}))
    return {"project": updated, "voice": updated["voice"]}


@app.delete("/api/projects/{pid}/voice")
def delete_voice(pid: str):
    project = get_or_404(pid)
    for stale in (project.get("voice") or {}).get("file"),:
        if stale:
            path = os.path.join(DATA_DIR, stale)
            if os.path.exists(path):
                os.remove(path)
    updated = db.update_project(pid, {"voice": {}})
    return {"project": serialize_project(updated), "ok": True}


# --------------------------------------------------------------------------- #
# export                                                                      #
# --------------------------------------------------------------------------- #
@app.get("/api/projects/{pid}/export")
def export_project(pid: str, fmt: str = "md"):
    project = get_or_404(pid)
    artist = resolve_artist(project["artist_id"])
    event = project.get("event") or {}
    payload = content.build_package(project, artist, event)
    if fmt == "json":
        return JSONResponse(payload)
    return PlainTextResponse(payload["article_markdown"])


@app.get("/api/projects/{pid}/bundle.zip")
def download_bundle(pid: str):
    """Everything about one project in a single file the user can save locally."""
    project = get_or_404(pid)
    artist = resolve_artist(project["artist_id"])
    event = project.get("event") or {}
    slug = re.sub(r"[^a-z0-9]+", "-", (artist.get("id") or "artist").lower()).strip("-")
    package = content.build_package(project, artist, event)
    images = project.get("images") or []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("article.md", package.get("article_markdown", ""))
        archive.writestr("project.json", json.dumps(serialize_project(project), ensure_ascii=False, indent=2))
        archive.writestr(
            "HUONG-DAN.txt",
            images_mod.bundle_readme({**project, "status_label": STATUS_LABELS.get(project.get("status"), project.get("status", ""))}, artist, len(images)),
        )
        for index, image in enumerate(images, 1):
            path = os.path.join(DATA_DIR, image.get("file", ""))
            if image.get("file") and os.path.exists(path):
                archive.write(path, arcname=f"images/{index:02d}.jpg")
        archive.writestr("images/ATTRIBUTION.txt", images_mod.attribution_text(images, artist.get("name", "")))
        voice = project.get("voice") or {}
        voice_path = os.path.join(DATA_DIR, voice.get("file", "")) if voice.get("file") else ""
        if voice_path and os.path.exists(voice_path):
            archive.write(voice_path, arcname=f"voice/{slug}.{voice.get('ext') or 'mp3'}")
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{slug}-bundle.zip"'}
    return Response(buffer.getvalue(), media_type="application/zip", headers=headers)


@app.get("/api/projects/{pid}/cover")
def cover(pid: str):
    project = serialize_project(get_or_404(pid))
    url = project["banner_url"]
    path = os.path.join(DATA_DIR, url[len("/media/"):]) if url.startswith("/media/") else os.path.join(WEB_DIR, url.lstrip("/"))
    if not os.path.exists(path):
        raise HTTPException(404, "Chưa có ảnh bìa")
    return FileResponse(path)


# --------------------------------------------------------------------------- #
# client diagnostics                                                          #
# --------------------------------------------------------------------------- #
CLIENT_LOG = os.path.join(DATA_DIR, "client.log")


@app.post("/api/client-log")
def client_log(payload: dict = Body(default={})):
    """The browser posts what it could not reach; we keep it for troubleshooting."""
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": str(payload.get("event", ""))[:120],
        "message": str(payload.get("message", ""))[:2000],
        "detail": str(payload.get("detail", ""))[:4000],
    }
    try:
        with open(CLIENT_LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass
    print(f"[client] {entry['event']}: {entry['message'][:300]}", flush=True)
    return {"ok": True}


@app.get("/api/client-log")
def read_client_log(limit: int = Query(default=50, ge=1, le=500)):
    if not os.path.exists(CLIENT_LOG):
        return {"entries": []}
    with open(CLIENT_LOG, encoding="utf-8") as handle:
        lines = handle.read().splitlines()[-limit:]
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"entries": entries}


# --------------------------------------------------------------------------- #
# static app                                                                  #
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@app.middleware("http")
async def _fresh_shell(request, call_next):
    """The shell (html/js/css) must never be served from a stale browser cache."""
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-cache"
    elif path.startswith("/media/voice/"):
        # voiceover files must never come from cache: the user may re-record with
        # another voice at any time and expects to hear the new take
        response.headers["Cache-Control"] = "no-store"
    elif path.startswith(("/assets/", "/media/")):
        response.headers.setdefault("Cache-Control", "public, max-age=600")
    return response


app.mount("/assets", StaticFiles(directory=os.path.join(WEB_DIR, "assets")), name="assets")
app.mount("/media", StaticFiles(directory=DATA_DIR), name="media")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
