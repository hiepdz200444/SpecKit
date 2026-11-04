"""Artist photos: Wikipedia + Wikimedia Commons (with licence/attribution) and user URLs.

Rules baked into this module:
  * Wikimedia/Wikipedia content is fetched through their public APIs and the
    licence + author are stored next to every image.
  * Pinterest is never scraped. If the operator has an image URL they are
    allowed to use, they paste the direct image URL and the server downloads it.
  * Every download is validated (content type, size, real image bytes) and
    re-encoded to JPEG so the studio never stores a broken or huge original.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from PIL import Image, ImageOps

USER_AGENT = "LegendsReelStudio/2.0 (https://github.com/hiepdz200444/SpecKit; music reels studio)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_FILE_PAGE = "https://commons.wikimedia.org/wiki/File:"
MAX_BYTES = 15 * 1024 * 1024
TIMEOUT = 15
TARGET_IMAGES = 20
OK_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}


class ImageFetchError(RuntimeError):
    """Raised with a Vietnamese message that is safe to show in the UI."""


# --------------------------------------------------------------------------- #
# HTTP helpers                                                                #
# --------------------------------------------------------------------------- #
def _request(url: str, params: dict | None = None) -> urllib.request.Request:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})


def http_json(url: str, params: dict | None = None) -> dict:
    try:
        with urllib.request.urlopen(_request(url, params), timeout=TIMEOUT) as res:
            return json.loads(res.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ImageFetchError(f"Không gọi được API ảnh ({url.split('/')[2]}): {exc}") from exc


def http_bytes(url: str) -> tuple[bytes, str]:
    try:
        with urllib.request.urlopen(_request(url), timeout=TIMEOUT) as res:
            ctype = (res.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = res.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ImageFetchError(f"Không tải được ảnh: {exc}") from exc
    if len(data) > MAX_BYTES:
        raise ImageFetchError("Ảnh quá lớn (giới hạn 15 MB)")
    if not data:
        raise ImageFetchError("URL không trả về dữ liệu")
    return data, ctype


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", text).strip()


def _meta(extmetadata: dict, key: str) -> str:
    item = (extmetadata or {}).get(key) or {}
    return _strip_html(str(item.get("value", "")))


def image_id(url: str) -> str:
    """Stable short id for an image URL (also used as the stored filename)."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


_image_id = image_id


def _candidate(
    *,
    url: str,
    thumb: str = "",
    title: str = "",
    page_url: str = "",
    source: str = "wikimedia",
    width: int = 0,
    height: int = 0,
    license_name: str = "",
    license_url: str = "",
    attribution: str = "",
    description: str = "",
) -> dict:
    return {
        "id": _image_id(url),
        "source": source,
        "title": title,
        "url": url,
        "thumb_url": thumb or url,
        "page_url": page_url,
        "width": width,
        "height": height,
        "license": license_name or "không rõ",
        "license_url": license_url,
        "attribution": attribution,
        "description": description,
    }


# --------------------------------------------------------------------------- #
# Wikipedia + Commons                                                         #
# --------------------------------------------------------------------------- #
def wikipedia_candidates(wiki_title: str) -> list[dict]:
    """The lead portrait used by the artist's Wikipedia article."""
    title = (wiki_title or "").replace(" ", "_")
    if not title:
        return []
    summary = http_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}")
    original = (summary.get("originalimage") or {}).get("source") or ""
    thumb = (summary.get("thumbnail") or {}).get("source") or ""
    if not original:
        return []
    page = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
    return [
        _candidate(
            url=original,
            thumb=thumb,
            title=f"{summary.get('title') or title} — ảnh chính Wikipedia",
            page_url=page,
            source="wikipedia",
            width=int((summary.get("originalimage") or {}).get("width") or 0),
            height=int((summary.get("originalimage") or {}).get("height") or 0),
            license_name="Wikipedia (kiểm tra trang file để chắc chắn)",
            attribution=f"Nguồn: Wikipedia — {page}",
            description=summary.get("description") or "",
        )
    ]


def commons_candidates(wiki_title: str, artist_name: str, limit: int = 30) -> list[dict]:
    """Files from Wikimedia Commons, searched by article title and artist name."""
    searches = []
    if wiki_title:
        searches.append((wiki_title.replace("_", " "), 6))
    if artist_name:
        searches.append((f"{artist_name} singer", 6))
        searches.append((artist_name, 6))

    titles: list[str] = []
    for term, namespace in searches:
        if len(titles) >= limit:
            break
        try:
            data = http_json(
                COMMONS_API,
                {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": term,
                    "srnamespace": namespace,
                    "srlimit": limit,
                },
            )
        except ImageFetchError:
            continue
        for item in (data.get("query") or {}).get("search") or []:
            t = item.get("title") or ""
            if t and t not in titles:
                titles.append(t)

    out: list[dict] = []
    for chunk_start in range(0, len(titles), 20):
        chunk = titles[chunk_start:chunk_start + 20]
        try:
            data = http_json(
                COMMONS_API,
                {
                    "action": "query",
                    "format": "json",
                    "titles": "|".join(chunk),
                    "prop": "imageinfo",
                    "iiprop": "url|size|mime|extmetadata",
                    "iiurlwidth": 1600,
                },
            )
        except ImageFetchError:
            continue
        pages = ((data.get("query") or {}).get("pages") or {}).values()
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            mime = (info.get("mime") or "").lower()
            if mime not in OK_MIME:
                continue
            width, height = int(info.get("width") or 0), int(info.get("height") or 0)
            if width < 400 or height < 400:
                continue
            url = info.get("url") or ""
            if not url:
                continue
            meta = info.get("extmetadata") or {}
            author = _meta(meta, "Artist") or _meta(meta, "Credit")
            out.append(
                _candidate(
                    url=url,
                    thumb=info.get("thumburl") or url,
                    title=page.get("title", "").replace("File:", ""),
                    page_url=COMMONS_FILE_PAGE + urllib.parse.quote((page.get("title") or "").replace("File:", "")),
                    source="wikimedia",
                    width=width,
                    height=height,
                    license_name=_meta(meta, "LicenseShortName"),
                    license_url=_meta(meta, "LicenseUrl"),
                    attribution=author,
                    description=_meta(meta, "ImageDescription")[:280],
                )
            )
    return out


def suggest_for_artist(artist: dict, limit: int = TARGET_IMAGES) -> dict:
    """Collect ~20 candidate photos for one artist."""
    wiki_title = artist.get("wikipedia") or ""
    candidates: list[dict] = []
    errors: list[str] = []

    for loader in (
        lambda: wikipedia_candidates(wiki_title),
        lambda: commons_candidates(wiki_title, artist.get("name", ""), limit=max(limit, 24)),
    ):
        try:
            candidates.extend(loader())
        except ImageFetchError as exc:
            errors.append(str(exc))

    seen, unique = set(), []
    for cand in candidates:
        if cand["url"] in seen:
            continue
        seen.add(cand["url"])
        unique.append(cand)
    return {
        "images": unique[: max(limit, 24)],
        "target": TARGET_IMAGES,
        "errors": errors,
        "sources": ["Wikipedia", "Wikimedia Commons"],
    }


# --------------------------------------------------------------------------- #
# Storing images                                                              #
# --------------------------------------------------------------------------- #
def normalize(raw: bytes) -> tuple[bytes, int, int]:
    """Validate the bytes are a real image and return a JPEG (max 2400px)."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:  # noqa: BLE001 - PIL raises many types on bad input
        raise ImageFetchError("File không phải ảnh hợp lệ (hoặc định dạng chưa hỗ trợ)") from exc
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (12, 13, 18))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    max_w, max_h = 2000, 3000
    if img.width > max_w or img.height > max_h:
        ratio = min(max_w / img.width, max_h / img.height)
        img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue(), img.width, img.height


def store_dir(data_dir: str, project_id: str) -> str:
    path = os.path.join(data_dir, "images", project_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_image(data_dir: str, project_id: str, raw: bytes, record: dict) -> dict:
    """Write normalised JPEG bytes and return the stored image record."""
    jpeg, width, height = normalize(raw)
    folder = store_dir(data_dir, project_id)
    image_id = record.get("id") or _image_id(record.get("url", "") + str(len(os.listdir(folder))))
    filename = f"{image_id}.jpg"
    with open(os.path.join(folder, filename), "wb") as f:
        f.write(jpeg)
    out = dict(record)
    out.update({"id": image_id, "file": f"images/{project_id}/{filename}", "width": width, "height": height, "bytes": len(jpeg)})
    out.setdefault("license", "không rõ")
    out.setdefault("attribution", "")
    out.setdefault("page_url", "")
    out.setdefault("source", "user")
    return out


def _private_host(host: str) -> bool:
    host = (host or "").lower()
    return (
        host in {"localhost", "127.0.0.1", "0.0.0.0", "::1", ""}
        or host.startswith("127.")
        or host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("169.254.")
        or re.match(r"^172\.(1[6-9]|2\d|3[01])\.", host) is not None
    )


def import_from_url(data_dir: str, project_id: str, url: str, meta: dict | None = None) -> dict:
    """Download a direct image URL the operator pasted (Pinterest/Getty/etc.)."""
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise ImageFetchError("Link phải bắt đầu bằng http:// hoặc https://")
    host = urllib.parse.urlparse(url).hostname or ""
    if _private_host(host):
        raise ImageFetchError("Không tải ảnh từ địa chỉ nội bộ / localhost")
    if "pinterest." in host and "/pin/" in url:
        raise ImageFetchError(
            "Đây là link trang Pinterest, không phải link ảnh. Mở ảnh → chuột phải → Copy image address, rồi dán lại."
        )
    if re.search(r"\.(html?|php)$", urllib.parse.urlparse(url).path, re.I):
        raise ImageFetchError("Link này là trang web, không phải file ảnh. Hãy dán link ảnh (.jpg/.png/.webp).")
    raw, ctype = http_bytes(url)
    if ctype and not ctype.startswith("image/"):
        raise ImageFetchError(f"Link trả về {ctype}, không phải ảnh")
    meta = meta or {}
    record = {
        "id": _image_id(url),
        "source": meta.get("source") or ("user" if "wikimedia.org" not in host else "wikimedia"),
        "title": meta.get("title") or os.path.basename(urllib.parse.urlparse(url).path)[:80] or host,
        "url": url,
        "page_url": meta.get("page_url") or url,
        "license": meta.get("license") or "bạn tự chịu trách nhiệm bản quyền",
        "license_url": meta.get("license_url") or "",
        "attribution": meta.get("attribution") or f"Nguồn: {host}",
        "description": meta.get("description") or "",
    }
    return save_image(data_dir, project_id, raw, record)


def import_upload(data_dir: str, project_id: str, raw: bytes, filename: str) -> dict:
    record = {
        "id": _image_id(filename + str(len(raw)) + str(os.urandom(4))),
        "source": "upload",
        "title": filename or "Ảnh tải lên",
        "url": "",
        "page_url": "",
        "license": "bạn tự chịu trách nhiệm bản quyền",
        "license_url": "",
        "attribution": f"Ảnh tải lên: {filename or 'không tên'}",
        "description": "",
    }
    return save_image(data_dir, project_id, raw, record)


def attribution_text(images: list[dict], artist_name: str = "") -> str:
    lines = [
        f"Image credits — {artist_name}".strip(" —"),
        "",
        "Ảnh được lưu trong thư mục này. Kiểm tra lại giấy phép trước khi dùng cho mục đích thương mại.",
        "",
    ]
    for i, img in enumerate(images, 1):
        lines.append(f"{i}. {img.get('title') or '(không tên)'}")
        lines.append(f"   Nguồn: {img.get('source', '')} {img.get('page_url') or img.get('url') or ''}".rstrip())
        lines.append(f"   Giấy phép: {img.get('license') or 'không rõ'}" + (f" — {img.get('license_url')}" if img.get("license_url") else ""))
        if img.get("attribution"):
            lines.append(f"   Tác giả / ghi công: {img['attribution']}")
        if img.get("file"):
            lines.append(f"   File: {os.path.basename(img['file'])}")
        lines.append("")
    return "\n".join(lines)


def as_public(image: dict, media_url) -> dict:
    """Strip server paths and add a browser-usable URL + banner flag."""
    out = dict(image)
    out["url"] = out.get("url", "")
    out["file_url"] = media_url(image.get("file", ""))
    out["is_banner"] = bool(image.get("is_banner"))
    return out
