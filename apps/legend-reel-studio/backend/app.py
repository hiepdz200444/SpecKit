"""Legends Reel Studio — API + static app (article + artist photos + text/voice)."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import time
import zipfile
from datetime import date, datetime, timezone

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

import content
import db
import images as images_mod
import library
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
    artist = library.get_artist(p["artist_id"]) or {}
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
    return {"artists": library.artists_index()}


@app.get("/api/artists/{artist_id}")
def artist_detail(artist_id: str):
    artist = library.get_artist(artist_id)
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
    artist = library.get_artist(project["artist_id"])
    event = project.get("event") or {}
    seed = seed if seed is not None else project.get("seed", 1)
    patch: dict = {"seed": seed}
    article = None

    if section in ("article", "all"):
        article = content.article_for(artist, event, seed)
        patch.update(
            {
                "article_title": article["title"],
                "article_titles": article["title_variants"],
                "article_body": article["body"],
                "first_comment": article["first_comment"],
                "hashtags": " ".join(article["hashtags"]),
                "music_links": artist["songs"],
            }
        )
        if project.get("status") in (None, "", "draft"):
            patch["status"] = "article"

    if section in ("script", "all"):
        plan = content.script_for(artist, event, article, seed)
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
    artist = library.get_artist(project["artist_id"])
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
    artist = library.get_artist(project["artist_id"]) or {}
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
    artist = library.get_artist(project["artist_id"]) or {}
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
    artist = library.get_artist(project["artist_id"]) or {}
    slug = re.sub(r"[^a-z0-9]+", "-", (artist.get("id") or "artist").lower()).strip("-")
    index = (project.get("images") or []).index(image) + 1
    return FileResponse(path, media_type="image/jpeg", filename=f"{slug}-{index:02d}.jpg")


@app.get("/api/projects/{pid}/images.zip")
def download_images_zip(pid: str):
    project = get_or_404(pid)
    artist = library.get_artist(project["artist_id"]) or {}
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
# voice                                                                       #
# --------------------------------------------------------------------------- #
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
        "ext": result["ext"],
        "bytes": result["bytes"],
        "duration": result["duration"],
        "text": result["text"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
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
    artist = library.get_artist(project["artist_id"])
    event = project.get("event") or {}
    payload = content.build_package(project, artist, event)
    if fmt == "json":
        return JSONResponse(payload)
    return PlainTextResponse(payload["article_markdown"])


@app.get("/api/projects/{pid}/bundle.zip")
def download_bundle(pid: str):
    """Everything about one project in a single file the user can save locally."""
    project = get_or_404(pid)
    artist = library.get_artist(project["artist_id"]) or {}
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
    elif path.startswith(("/assets/", "/media/")):
        response.headers.setdefault("Cache-Control", "public, max-age=600")
    return response


app.mount("/assets", StaticFiles(directory=os.path.join(WEB_DIR, "assets")), name="assets")
app.mount("/media", StaticFiles(directory=DATA_DIR), name="media")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
