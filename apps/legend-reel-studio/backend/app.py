"""Legends Reel Studio — API + static app."""

from __future__ import annotations

import base64
import json
import os
import shutil
import threading
import time
import uuid
from datetime import date, datetime

from fastapi import Body, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

import audio as audio_mod
import content
import db
import library
from render import STYLES, Renderer

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
WEB_DIR = os.path.join(APP_DIR, "web")
DATA_DIR = os.environ.get("LRS_DATA_DIR") or os.path.join(APP_DIR, "data")
BANNER_DIR = os.path.join(DATA_DIR, "banners")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
RENDER_DIR = os.path.join(DATA_DIR, "renders")
BED_PATH = os.path.join(DATA_DIR, "bed.wav")

for d in (DATA_DIR, BANNER_DIR, AUDIO_DIR, RENDER_DIR):
    os.makedirs(d, exist_ok=True)

STATUS_LABELS = {
    "draft": "Nháp",
    "article": "Đã có bài báo",
    "video": "Đã có kịch bản",
    "ready": "Sẵn sàng đăng",
    "scheduled": "Đã lên lịch",
    "published": "Đã đăng",
}

db.init_db()
app = FastAPI(title="Legends Reel Studio", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, dict] = {}
RENDER_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
# serialization helpers                                                       #
# --------------------------------------------------------------------------- #
def media_url(path: str) -> str:
    if not path:
        return ""
    path = os.path.abspath(path)
    assets = os.path.join(WEB_DIR, "assets")
    if path.startswith(DATA_DIR + os.sep):
        return "/media/" + path[len(DATA_DIR) + 1:].replace(os.sep, "/")
    if path.startswith(assets + os.sep):
        return "/assets/" + path[len(assets) + 1:].replace(os.sep, "/")
    return ""


def serialize_project(p: dict) -> dict:
    artist = library.get_artist(p["artist_id"]) or {}
    out = dict(p)
    out["artist"] = artist
    out["banner_url"] = media_url(p.get("banner_image", "")) or f"/assets/{artist.get('cover', 'bg-stage.jpg')}"
    out["render_url"] = media_url(p.get("render_path", ""))
    out["audio_url"] = media_url(p.get("audio_path", ""))
    out["poster_url"] = media_url(os.path.splitext(p.get("render_path", ""))[0] + ".jpg") if p.get("render_path") else ""
    out["checks"] = content.engagement_checks(p)
    out["status_label"] = STATUS_LABELS.get(p.get("status", "draft"), p.get("status", ""))
    return out


def get_or_404(pid: str) -> dict:
    project = db.get_project(pid)
    if not project:
        raise HTTPException(404, "Project không tồn tại")
    return project


def ensure_bed() -> str:
    if not os.path.exists(BED_PATH):
        audio_mod.write_bed(BED_PATH, 30.0)
    return BED_PATH


def save_banner(pid: str, raw: bytes) -> str:
    path = os.path.join(BANNER_DIR, f"{pid}.jpg")
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(raw)
    img = Image.open(tmp).convert("RGB")
    # portrait-first: cover-crop to 3:4 max, keep tall sources tall
    img = ImageOps.exif_transpose(img)
    max_w, max_h = 1400, 2400
    if img.width > max_w or img.height > max_h:
        ratio = min(max_w / img.width, max_h / img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    img.save(path, quality=90, optimize=True)
    os.remove(tmp)
    return path


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
        "styles": {k: {"label": v["label"], "accent": "#%02x%02x%02x" % v["accent"]} for k, v in STYLES.items()},
        "upcoming": library.upcoming_summary(ref, 21),
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
        "status", "article_title", "article_dek", "article_body", "first_comment", "hashtags",
        "video_overlay_text", "fb_hook", "caption", "video_style", "audio_choice",
        "notes", "scheduled_for", "article_titles", "music_links", "video_plan", "seed",
    }
    clean = {k: v for k, v in patch.items() if k in allowed}
    updated = db.update_project(pid, clean)
    return serialize_project(updated)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    get_or_404(pid)
    for suffix in (".mp4", ".jpg"):
        f = os.path.join(RENDER_DIR, pid + suffix)
        if os.path.exists(f):
            os.remove(f)
    b = os.path.join(BANNER_DIR, pid + ".jpg")
    if os.path.exists(b):
        os.remove(b)
    db.delete_project(pid)
    return {"ok": True}


@app.post("/api/projects/{pid}/duplicate")
def duplicate_project(pid: str):
    src = get_or_404(pid)
    copy = db.duplicate_project(pid)
    # keep the artwork with the copy so deleting the original cannot break it
    banner = src.get("banner_image") or ""
    if banner and os.path.exists(banner):
        new_banner = os.path.join(BANNER_DIR, f"{copy['id']}.jpg")
        shutil.copyfile(banner, new_banner)
        copy = db.update_project(copy["id"], {"banner_image": new_banner})
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
                "article_dek": article["dek"],
                "article_body": article["body"],
                "first_comment": article["first_comment"],
                "hashtags": " ".join(article["hashtags"]),
                "music_links": artist["songs"],
            }
        )
        if project.get("status") in (None, "", "draft"):
            patch["status"] = "article"

    if section in ("video", "all"):
        plan = content.video_for(artist, event, article, seed)
        if overlay_text.strip():
            plan["overlay_text"] = overlay_text.strip()
            plan["overlay_words"] = content.word_count(overlay_text)
            plan["scenes"][0]["text"] = overlay_text.strip()
        patch.update(
            {
                "video_plan": plan,
                "video_overlay_text": plan["overlay_text"],
                "fb_hook": plan["fb_hook"],
                "caption": plan["caption"] + "\n\n" + " ".join(plan.get("hashtags") or []),
                "audio_choice": project.get("audio_choice") or "bed",
            }
        )
        if patch.get("status") == "article":
            patch["status"] = "video"
        elif project.get("status") in ("draft", "article", ""):
            patch["status"] = "article" if section == "video" and not article else "video"

    return db.update_project(project["id"], patch)


@app.post("/api/projects/{pid}/generate")
def generate(pid: str, payload: dict = Body(default={})):
    project = get_or_404(pid)
    section = payload.get("section", "all")
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
    plan = project.get("video_plan") or {}
    if plan.get("scenes"):
        plan["scenes"][0]["text"] = text
    plan["overlay_text"] = text
    plan["overlay_words"] = words
    updated = db.update_project(pid, {"video_overlay_text": text, "video_plan": plan})
    return {"project": serialize_project(updated), "words": words, "ok": 9 <= words <= 15}


# --------------------------------------------------------------------------- #
# uploads                                                                     #
# --------------------------------------------------------------------------- #
@app.post("/api/projects/{pid}/banner")
async def upload_banner(pid: str, request: Request):
    """Accept either multipart/form-data (file) or JSON {"data_url": "data:image/..."}."""
    get_or_404(pid)
    raw = b""
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        file = form.get("file")
        if file is not None:
            raw = await file.read()
    else:
        payload = await request.json()
        if payload.get("data_url"):
            raw = base64.b64decode(payload["data_url"].split(",", 1)[-1])
        elif payload.get("url"):
            raise HTTPException(400, "Server không tải được URL trực tiếp, hãy gửi ảnh dạng data_url")
    if not raw:
        raise HTTPException(400, "Thiếu ảnh")
    path = save_banner(pid, raw)
    updated = db.update_project(pid, {"banner_image": path})
    return serialize_project(updated)


@app.post("/api/projects/{pid}/audio")
async def upload_audio(pid: str, file: UploadFile = File(...)):
    get_or_404(pid)
    ext = os.path.splitext(file.filename or "track.mp3")[1].lower() or ".mp3"
    if ext not in {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}:
        raise HTTPException(400, "Định dạng audio không hỗ trợ")
    path = os.path.join(AUDIO_DIR, f"{pid}{ext}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    updated = db.update_project(pid, {"audio_path": path, "audio_choice": "upload"})
    return serialize_project(updated)


@app.post("/api/projects/{pid}/audio-choice")
def audio_choice(pid: str, payload: dict = Body(...)):
    get_or_404(pid)
    choice = payload.get("choice", "bed")
    updated = db.update_project(pid, {"audio_choice": choice})
    return serialize_project(updated)


# --------------------------------------------------------------------------- #
# rendering                                                                   #
# --------------------------------------------------------------------------- #
def _run_render(job_id: str, pid: str) -> None:
    job = JOBS[job_id]
    project = db.get_project(pid)
    artist = library.get_artist(project["artist_id"])
    style = project.get("video_style") or "noir"
    if not (project.get("video_plan") or {}).get("scenes"):
        project = apply_generation(project, section="video", seed=project.get("seed", 1))

    audio_path = ""
    choice = project.get("audio_choice") or "bed"
    if choice == "upload" and project.get("audio_path") and os.path.exists(project["audio_path"]):
        audio_path = project["audio_path"]
    elif choice != "none":
        audio_path = ensure_bed()

    out = os.path.join(RENDER_DIR, f"{pid}.mp4")
    poster = os.path.join(RENDER_DIR, f"{pid}.jpg")

    def progress(frac: float, frame: int, total: int) -> None:
        job.update(
            {
                "progress": round(frac * 100, 1),
                "frame": frame,
                "total_frames": total,
                "message": f"Đang render frame {frame}/{total}",
            }
        )

    try:
        job.update({"status": "running", "progress": 0, "message": "Đang chuẩn bị khung hình"})
        t0 = time.time()
        renderer = Renderer(project, artist, style)
        result = renderer.render(out, audio_path=audio_path, poster_path=poster, progress=progress)
        seconds = time.time() - t0
        db.update_project(pid, {"render_path": out, "render_status": "done", "render_seconds": seconds, "status": "ready"})
        job.update(
            {
                "status": "done",
                "progress": 100,
                "message": "Xong",
                "path": out,
                "url": media_url(out),
                "poster": media_url(poster),
                "seconds": round(seconds, 1),
                "size_mb": round(os.path.getsize(out) / 1024 / 1024, 2),
                "frames": result["frames"],
            }
        )
    except Exception as exc:  # noqa: BLE001
        db.update_project(pid, {"render_status": "error"})
        job.update({"status": "error", "message": str(exc)[:800]})
    finally:
        RENDER_LOCK.release()


@app.post("/api/projects/{pid}/render")
def start_render(pid: str, payload: dict = Body(default={})):
    project = get_or_404(pid)
    if not RENDER_LOCK.acquire(blocking=False):
        raise HTTPException(429, "Đang có một video khác được render, thử lại sau")
    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {
        "id": job_id,
        "project_id": pid,
        "status": "queued",
        "progress": 0,
        "message": "Đang xếp hàng",
        "started": datetime.utcnow().isoformat(),
    }
    style = payload.get("style")
    if style and style in STYLES:
        db.update_project(pid, {"video_style": style})
    thread = threading.Thread(target=_run_render, args=(job_id, pid), daemon=True)
    thread.start()
    return {"job": JOBS[job_id], "project_id": pid}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job không tồn tại")
    return job


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
    md = payload["article_markdown"]
    caption = (project.get("caption") or "").strip()
    md += "\n\n---\n\n## Facebook caption\n\n" + caption
    md += "\n\n## Hashtags\n\n" + (project.get("hashtags") or "")
    return PlainTextResponse(md)


@app.get("/api/projects/{pid}/cover")
def cover(pid: str):
    project = get_or_404(pid)
    artist = library.get_artist(project["artist_id"])
    path = project.get("banner_image")
    if not path or not os.path.exists(path):
        path = os.path.join(WEB_DIR, "assets", artist.get("cover") or "bg-stage.jpg")
    return FileResponse(path)


# --------------------------------------------------------------------------- #
# static app                                                                  #
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


app.mount("/assets", StaticFiles(directory=os.path.join(WEB_DIR, "assets")), name="assets")
app.mount("/media", StaticFiles(directory=DATA_DIR), name="media")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
