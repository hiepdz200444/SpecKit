"""Đọc page Facebook đối thủ từ phía máy chủ studio — chỉ cần dán link page.

Trước đây studio bắt người dùng copy một đoạn JS rồi dán vào Console của
Facebook. Cách đó vừa thủ công vừa bị Facebook chặn (cảnh báo self-XSS "Dừng
lại!" + Permissions-Policy). Module này làm việc đó ở phía máy chủ:

    link page  ──►  thử vài URL/UA khác nhau  ──►  bóc số liệu  ──►  chấm điểm

Facebook chỉ trả nội dung công khai khi request "giống người thật" hoặc khi có
phiên đăng nhập, nên ta thử lần lượt:

1. `/<page>/reels/`, `/<page>/videos/`, `/<page>` với UA Chrome, không cookie.
2. Cùng các URL đó với UA crawler (Googlebot / facebookexternalhit).
3. Nếu người dùng đã lưu cookie phiên (một lần, lưu cục bộ trong `data/`),
   thử lại với cookie đó — đây là đường chắc chắn nhất.

Mọi lần thử đều được ghi lại trong `attempts` để giao diện giải thích được vì
sao không đọc được, thay vì chỉ báo "lỗi".

Không gửi dữ liệu đi đâu ngoài facebook.com; cookie chỉ nằm trên máy bạn
(`data/fb_session.json`, quyền 600) và chỉ dùng cho các request tới facebook.com.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import rivals as rivals_mod

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("LRS_DATA_DIR") or os.path.join(APP_DIR, "data")
SESSION_PATH = os.path.join(DATA_DIR, "fb_session.json")

MAX_BYTES = 6_000_000
DEFAULT_BUDGET_S = 30.0
DEFAULT_TIMEOUT_S = 12.0

UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
UA_GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
UA_FACEBOOK_HIT = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"

UA_LABEL = {
    UA_BROWSER: "trình duyệt",
    UA_GOOGLEBOT: "crawler Google",
    UA_FACEBOOK_HIT: "facebookexternalhit",
}


# --------------------------------------------------------------------------- #
# cookie phiên (tuỳ chọn, lưu cục bộ)                                          #
# --------------------------------------------------------------------------- #
def parse_cookie(raw: str) -> dict[str, str]:
    """`c_user=1; xs=abc` → {'c_user': '1', 'xs': 'abc'}."""
    out: dict[str, str] = {}
    for part in re.split(r"[;\n]", str(raw or "")):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key, value = key.strip().strip('"'), value.strip().strip('"')
        if key and value and key.lower() not in ("cookie", "path", "domain", "expires"):
            out[key] = value
    return out


def cookie_header(raw: str) -> str:
    """Giữ toàn bộ cookie Facebook người dùng dán (c_user, xs, datr, sb, fr, …).

    Phiên Facebook cần cả bộ cookie mới ổn định, nên chỉ bỏ những cặp rỗng và
    cắt bớt nếu chuỗi quá dài.
    """
    parsed = parse_cookie(raw)
    header = "; ".join(f"{key}={value}" for key, value in parsed.items())
    return header[:4000]


def load_cookie() -> str:
    raw = os.environ.get("FB_COOKIE", "")
    if raw:
        return cookie_header(raw)
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return ""
    return cookie_header(str(data.get("cookie") or ""))


def save_cookie(raw: str) -> dict[str, Any]:
    header = cookie_header(raw)
    if not header:
        raise ValueError("Cookie rỗng — cần ít nhất cặp c_user và xs")
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {
        "cookie": header,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(SESSION_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    try:
        os.chmod(SESSION_PATH, 0o600)
    except OSError:
        pass
    return cookie_status()


def clear_cookie() -> dict[str, Any]:
    try:
        os.remove(SESSION_PATH)
    except OSError:
        pass
    return cookie_status()


def cookie_status() -> dict[str, Any]:
    header = load_cookie()
    names = [name for name in parse_cookie(header)]
    saved_at = ""
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as handle:
            saved_at = str(json.load(handle).get("saved_at") or "")
    except (OSError, ValueError):
        saved_at = ""
    return {
        "saved": bool(header),
        "cookies": names,
        "has_xs": "xs" in names,
        "saved_at": saved_at,
        "source": "env" if os.environ.get("FB_COOKIE") else ("file" if header else ""),
        "preview": (f"{names[0]}=…" if names else ""),
    }


# --------------------------------------------------------------------------- #
# HTTP: ba kiểu client, vì facebook.com phân biệt rất rõ                      #
# --------------------------------------------------------------------------- #
# Đo thực tế: cùng một URL, client Python mang UA Chrome bị trả thẳng HTTP 400
# (lệch dấu vân tay TLS/HTTP2), còn UA crawler thì được 200 nhưng kèm tường đăng
# nhập. Vì vậy mỗi URL được thử bằng ba kiểu client:
#   impersonate → curl_cffi giả lập TLS + HTTP/2 của Chrome (giống trình duyệt thật)
#   http2       → httpx với HTTP/2
#   plain       → httpx/urllib HTTP/1.1
TRANSPORT_LABEL = {
    "impersonate": "Chrome giả lập",
    "http2": "HTTP/2",
    "plain": "HTTP thường",
}


@dataclass
class Attempt:
    label: str
    url: str
    ua: str
    cookie: bool = False
    transport: str = "plain"
    status: int = 0
    size: int = 0
    posts: int = 0
    blocked: bool = False
    note: str = ""
    snippet: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "url": self.url,
            "ua": UA_LABEL.get(self.ua, self.ua[:40]) if self.ua else TRANSPORT_LABEL.get(self.transport, self.transport),
            "transport": TRANSPORT_LABEL.get(self.transport, self.transport),
            "cookie": self.cookie,
            "status": self.status,
            "size": self.size,
            "posts": self.posts,
            "blocked": self.blocked,
            "note": self.note,
            "snippet": self.snippet,
        }


def transport_status() -> dict[str, Any]:
    """Thư viện nào đang có — quyết định studio có đọc được Facebook hay không."""
    try:
        import curl_cffi  # type: ignore  # noqa: F401

        impersonate = True
    except ImportError:
        impersonate = False
    try:
        import h2  # type: ignore  # noqa: F401

        http2 = True
    except ImportError:
        http2 = False
    return {
        "curl_cffi": impersonate,
        "http2": http2,
        "recommended": "impersonate" if impersonate else ("http2" if http2 else "plain"),
        "install": "" if impersonate else "pip install curl_cffi httpx[http2]",
    }


def available_transport(transport: str) -> str:
    """Hạ cấp transport khi thiếu thư viện, để nhật ký ghi đúng thứ đã dùng."""
    if transport == "impersonate":
        return "impersonate" if transport_status()["curl_cffi"] else "http2"
    if transport == "http2":
        return "http2" if transport_status()["http2"] else "plain"
    return transport


def _headers(ua: str, cookie: str = "") -> dict[str, str]:
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }
    if ua:
        headers["User-Agent"] = ua
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _clip(text: str) -> str:
    return (text or "")[:MAX_BYTES]


def _get_impersonate(url: str, ua: str, cookie: str, timeout: float):
    """curl_cffi: TLS + HTTP/2 giống Chrome thật (vượt qua kiểm tra client)."""
    from curl_cffi import requests as curl_requests  # type: ignore

    headers = {"Accept-Language": "en-US,en;q=0.9"}
    if ua:
        headers["User-Agent"] = ua
    if cookie:
        headers["Cookie"] = cookie
    session = curl_requests.Session(impersonate="chrome")
    try:
        response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    finally:
        session.close()
    return response.status_code, str(response.url), _clip(response.text), ""


def _get_httpx(url: str, ua: str, cookie: str, timeout: float, http2: bool):
    import httpx  # type: ignore

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers=_headers(ua, cookie),
        http2=http2,
    ) as client:
        response = client.get(url)
        return response.status_code, str(response.url), _clip(response.text), ""


def _get_urllib(url: str, ua: str, cookie: str, timeout: float):
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, headers=_headers(ua, cookie))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw = response.read(MAX_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, response.geturl(), raw.decode(charset, "replace"), ""
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(MAX_BYTES).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            body = ""
        return exc.code, url, body, ""


def _http_get(
    url: str,
    ua: str,
    cookie: str = "",
    timeout: float = DEFAULT_TIMEOUT_S,
    transport: str = "plain",
):
    """(status, final_url, text, error) — tự hạ cấp transport khi thiếu thư viện."""
    if transport == "impersonate":
        try:
            return _get_impersonate(url, ua, cookie, timeout)
        except ImportError:
            transport = "http2"
        except Exception as exc:  # noqa: BLE001
            return 0, url, "", f"curl_cffi: {type(exc).__name__}: {exc}"

    if transport == "http2":
        try:
            return _get_httpx(url, ua, cookie, timeout, True)
        except ImportError:
            transport = "plain"
        except Exception as exc:  # noqa: BLE001
            return 0, url, "", f"httpx: {type(exc).__name__}: {exc}"

    try:
        return _get_httpx(url, ua, cookie, timeout, False)
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        return 0, url, "", f"httpx: {type(exc).__name__}: {exc}"

    try:
        return _get_urllib(url, ua, cookie, timeout)
    except Exception as exc:  # noqa: BLE001
        return 0, url, "", f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------- #
# nhận diện tường đăng nhập                                                    #
# --------------------------------------------------------------------------- #
_BLOCK_MARKERS = (
    'id="login_form"',
    "name=\"login_form\"",
    '"login_form"',
    "log into facebook",
    "bạn phải đăng nhập",
    "you must log in to continue",
    "login/?next=",
    "/checkpoint/",
    "cookies required",
)

_LOGIN_URL_HINTS = ("/login", "checkpoint", "/recover", "/two_step_verification")


def looks_blocked(html: str, status: int, final_url: str) -> bool:
    """Trang này có phải tường đăng nhập / checkpoint của Facebook?"""
    lowered_url = (final_url or "").lower()
    if any(hint in lowered_url for hint in _LOGIN_URL_HINTS):
        return True
    if status in (401, 403):
        return True
    text = (html or "").lower()
    if not text.strip():
        return False
    return any(marker in text for marker in _BLOCK_MARKERS)


# --------------------------------------------------------------------------- #
# bóc dữ liệu khỏi HTML                                                       #
# --------------------------------------------------------------------------- #
_VIDEO_ANCHORS = (
    re.compile(r'"video_id"\s*:\s*"?(\d{4,25})"?'),
    re.compile(r'"videoId"\s*:\s*"?(\d{4,25})"?'),
)
_POST_ANCHOR = re.compile(r'"post_id"\s*:\s*"?(\d{4,30})"?')

_ID_PATTERNS = (
    re.compile(r"/reels?/(\d{4,})"),
    re.compile(r"/videos?/(\d{4,})"),
    re.compile(r"[?&]v=(\d{4,})"),
    re.compile(r"/posts?/(\d{4,})"),
    re.compile(r"story_fbid=(\d{4,})"),
)


def post_key(url: str, text: str = "", fallback_id: str = "") -> str:
    """Khoá khử trùng cho một bài: id trong URL, không thì id neo, không thì chữ."""
    for pattern in _ID_PATTERNS:
        match = pattern.search(url or "")
        if match:
            return match.group(1)
    if fallback_id:
        return f"id:{fallback_id}"
    return (url or (text or "")[:100]).lower().strip()


_METRIC_KEYS = {
    "views": ("play_count", "video_view_count", "video_play_count", "view_count", "plays_count"),
    "likes": ("reaction_count", "likes_count", "like_count", "reactions_count"),
    "comments": ("comment_count", "comments_count", "comment_total_count"),
    "shares": ("share_count", "shares_count", "reshare_count"),
}

_URL_KEYS = ("permalink_url", "wwwURL", "www_url", "story_url", "url", "open_graph_url")


def _unescape_json_text(value: str) -> str:
    text = str(value or "")
    text = text.replace("\\/", "/").replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    text = text.replace('\\"', '"').replace("\\\\", "\\")

    def unicode_repl(match: re.Match) -> str:
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return ""

    text = re.sub(r"\\u([0-9a-fA-F]{4})", unicode_repl, text)
    return re.sub(r"\s+", " ", text).strip()


def _int_field(blob: str, keys: tuple[str, ...]) -> int:
    for key in keys:
        patterns = (
            rf'"{key}"\s*:\s*"?(\d{{1,15}})"?',
            rf'"{key}"\s*:\s*\{{[^{{}}]{{0,160}}?"count"\s*:\s*(\d{{1,15}})',
            rf'"{key}"\s*:\s*\{{[^{{}}]{{0,160}}?"total_count"\s*:\s*(\d{{1,15}})',
        )
        for pattern in patterns:
            match = re.search(pattern, blob)
            if match:
                return int(match.group(1))
    return 0


def _text_field(blob: str) -> str:
    for pattern in (
        r'"message"\s*:\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.){5,2000})"',
        r'"title"\s*:\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.){5,2000})"',
        r'"(?:accessibility_caption|description|snippet)"\s*:\s*"((?:[^"\\]|\\.){5,2000})"',
        r'"text"\s*:\s*"((?:[^"\\]|\\.){20,2000})"',
    ):
        match = re.search(pattern, blob)
        if match:
            text = _unescape_json_text(match.group(1))
            if len(text) >= 5:
                return text
    return ""


def _url_field(blob: str, video_id: str = "") -> str:
    for key in _URL_KEYS:
        for match in re.finditer(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.){{10,400}})"', blob):
            candidate = _unescape_json_text(match.group(1))
            if not candidate.lower().startswith("http"):
                continue
            if not re.search(r"(facebook\.com|fb\.watch)", candidate, re.I):
                continue
            if re.search(r"/(reel|reels|videos?|watch|posts?)/|story_fbid=|permalink\.php", candidate, re.I):
                return candidate
    if video_id:
        return f"https://www.facebook.com/reel/{video_id}"
    return ""


def _posted_at(blob: str) -> str:
    for key in ("creation_time", "publish_time", "created_time"):
        match = re.search(rf'"{key}"\s*:\s*(\d{{10,13}})', blob)
        if match:
            stamp = int(match.group(1))
            if stamp > 10**12:
                stamp //= 1000
            try:
                return datetime.fromtimestamp(stamp, tz=timezone.utc).date().isoformat()
            except (OverflowError, OSError, ValueError):
                return ""
    return ""


def _json_posts(html: str, window: tuple[int, int] = (2500, 3500)) -> list[dict]:
    """Bài nằm trong JSON nhúng (`require("ServerJS")`) của HTML Facebook.

    Mỗi `video_id`/`post_id` là một điểm neo; nội dung của bài thường nằm ngay
    sau điểm neo, nên cửa sổ đọc ưu tiên phía trước rồi mới lùi về sau.
    """
    text = html or ""
    before, after = window
    anchors: list[tuple[str, int, str]] = []
    for pattern in _VIDEO_ANCHORS:
        for match in pattern.finditer(text):
            anchors.append((match.group(1), match.start(), "video"))
    for match in _POST_ANCHOR.finditer(text):
        anchors.append((match.group(1), match.start(), "post"))
    anchors.sort(key=lambda item: item[1])

    found: dict[str, dict] = {}
    for ident, index, kind in anchors:
        blob = text[index : index + after] + " " + text[max(0, index - before) : index]
        metrics = {
            "views": _int_field(blob, _METRIC_KEYS["views"]),
            "likes": _int_field(blob, _METRIC_KEYS["likes"]),
            "comments": _int_field(blob, _METRIC_KEYS["comments"]),
            "shares": _int_field(blob, _METRIC_KEYS["shares"]),
        }
        current = found.get(ident)
        if current is None:
            found[ident] = {
                "_id": ident,
                "url": _url_field(blob, ident if kind == "video" else ""),
                "text": _text_field(blob),
                "posted_at": _posted_at(blob),
                **metrics,
            }
        else:  # cùng một bài xuất hiện nhiều lần — giữ số lớn nhất
            for field_name, value in metrics.items():
                current[field_name] = max(int(current.get(field_name) or 0), value)
            current["url"] = current.get("url") or _url_field(blob, ident if kind == "video" else "")
            current["text"] = current.get("text") or _text_field(blob)
            current["posted_at"] = current.get("posted_at") or _posted_at(blob)
    return list(found.values())


_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY = {
    "&amp;": "&",
    "&quot;": '"',
    "&#039;": "'",
    "&#39;": "'",
    "&lt;": "<",
    "&gt;": ">",
    "&nbsp;": " ",
}


def html_to_text(html: str) -> str:
    plain = re.sub(r"<script.*?</script>", " ", html or "", flags=re.S | re.I)
    plain = re.sub(r"<style.*?</style>", " ", plain, flags=re.S | re.I)
    plain = _TAG_RE.sub(" ", plain)
    for entity, char in _ENTITY.items():
        plain = plain.replace(entity, char)
    return re.sub(r"\s+", " ", plain).strip()


_OG_KEYS = ("og:title", "og:description")


def _meta(html: str, prop: str) -> str:
    patterns = (
        rf'<meta[^>]+property=["\']{prop}["\'][^>]+content=["\']([^"\']{{2,600}})["\']',
        rf'<meta[^>]+content=["\']([^"\']{{2,600}})["\'][^>]+property=["\']{prop}["\']',
        rf'<meta[^>]+name=["\']{prop}["\'][^>]+content=["\']([^"\']{{2,600}})["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, html or "", re.I)
        if match:
            return html_to_text(match.group(1))
    return ""


def og_post(html: str, page_url: str = "") -> dict | None:
    """Trang một reel/video công khai: chỉ còn og:* + vài con số trong meta."""
    title = _meta(html, "og:title")
    description = _meta(html, "og:description")
    if not title and not description:
        return None
    blob = f"{title} {description}"
    url = ""
    match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html or "", re.I)
    if match:
        url = match.group(1)
    if not url:
        match = re.search(rf'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']', html or "", re.I)
        url = match.group(1) if match else page_url
    likes = rivals_mod.metric_from_text(blob, rivals_mod._LIKE_WORDS)
    comments = rivals_mod.metric_from_text(blob, rivals_mod._COMMENT_WORDS)
    shares = rivals_mod.metric_from_text(blob, rivals_mod._SHARE_WORDS)
    views = rivals_mod.metric_from_text(blob, rivals_mod._VIEW_WORDS)
    return {
        "url": url,
        "text": description or title,
        "hook": title,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "views": views,
        "posted_at": "",
    }


def _article_posts(html: str, page_url: str = "") -> list[dict]:
    """Khối `role="article"` — bản HTML mà Facebook trả cho crawler."""
    out: list[dict] = []
    for chunk in re.split(r"role=[\"']article[\"']", html or "", flags=re.I)[1:]:
        block = chunk[:20_000]
        aria = " ".join(re.findall(r"aria-label=[\"']([^\"']{2,160})[\"']", block, flags=re.I))
        plain = html_to_text(block)
        if aria:
            plain = f"{plain} {aria}".strip()
        if len(plain) < 25:
            continue
        link = re.search(
            r'href=["\']([^"\']*(?:/posts/|/videos/|/reel/|story_fbid=|permalink\.php)[^"\']*)["\']',
            block,
            re.I,
        )
        url = link.group(1) if link else ""
        if url.startswith("/"):
            url = "https://www.facebook.com" + url
        out.append(
            {
                "url": url,
                "text": plain[:1500],
                "views": rivals_mod.metric_from_text(plain, rivals_mod._VIEW_WORDS),
                "likes": rivals_mod.metric_from_text(plain, rivals_mod._LIKE_WORDS),
                "comments": rivals_mod.metric_from_text(plain, rivals_mod._COMMENT_WORDS),
                "shares": rivals_mod.metric_from_text(plain, rivals_mod._SHARE_WORDS),
            }
        )
    return out


def extract_posts(html: str, page_url: str = "") -> list[dict]:
    """Mọi bài đọc được từ một trang HTML của Facebook (đã gộp & khử trùng)."""
    if not html:
        return []
    items: list[dict] = []
    items.extend(_json_posts(html))
    items.extend(_article_posts(html, page_url))
    single = og_post(html, page_url)
    if single:
        items.append(single)

    posts: list[dict] = []
    seen: set[str] = set()
    for item in items:
        text = str(item.get("text") or "").strip()
        url = str(item.get("url") or "").strip()
        counts = sum(int(item.get(key) or 0) for key in ("views", "likes", "comments", "shares"))
        if not text and counts == 0:
            continue
        key = post_key(url, text, str(item.get("_id") or ""))
        if not key or key in seen:
            continue
        seen.add(key)
        posts.append(
            {
                "url": url,
                "text": text,
                "hook": rivals_mod.hook_from_text(text),
                "views": int(item.get("views") or 0),
                "likes": int(item.get("likes") or 0),
                "comments": int(item.get("comments") or 0),
                "shares": int(item.get("shares") or 0),
                "posted_at": str(item.get("posted_at") or ""),
            }
        )
    posts.sort(key=lambda p: (p["views"], p["likes"], p["comments"]), reverse=True)
    return posts


# --------------------------------------------------------------------------- #
# URL cần thử                                                                 #
# --------------------------------------------------------------------------- #
def page_variants(page_url: str) -> list[tuple[str, str]]:
    """[(nhãn, url)] cho một link page: reels → videos → tường page."""
    url = (page_url or "").strip()
    if not url:
        return []
    if rivals_mod.is_single_post(url):
        return [("bài đơn", url)]
    match = re.match(r"^https?://(?:www\.|web\.|m\.)?facebook\.com/profile\.php\?id=(\d+)", url, re.I)
    if match:
        page_id = match.group(1)
        return [
            ("reels", f"https://www.facebook.com/profile.php?id={page_id}&sk=reels"),
            ("videos", f"https://www.facebook.com/profile.php?id={page_id}&sk=videos"),
            ("page", f"https://www.facebook.com/profile.php?id={page_id}"),
        ]
    clean = url.rstrip("/").split("?")[0]
    return [
        ("reels", f"{clean}/reels/"),
        ("videos", f"{clean}/videos/"),
        ("page", clean),
    ]


def plan_attempts(page_url: str, cookie: str) -> list[dict[str, str]]:
    """Thứ tự thử: có phiên thì thử phiên trước, rồi mới tới các UA crawler.

    Mỗi lần thử là một bộ ba (URL, UA, transport) — vì facebook.com trả 400 cho
    client Python mang UA Chrome, nhưng lại trả 200 cho UA crawler.
    """
    variants = page_variants(page_url)
    if len(variants) == 1:  # link một bài: chỉ đọc đúng bài đó
        label, url = variants[0]
        plans = [
            {"label": f"{label} · chrome", "url": url, "ua": "", "transport": "impersonate", "cookie": cookie},
            {"label": f"{label} · http2", "url": url, "ua": UA_BROWSER, "transport": "http2", "cookie": cookie},
            {"label": f"{label} · googlebot", "url": url, "ua": UA_GOOGLEBOT, "transport": "plain", "cookie": ""},
        ]
        return [plan for plan in plans if plan["cookie"] or not cookie]

    by_label = {label: url for label, url in variants}
    reels = by_label.get("reels") or variants[0][1]
    videos = by_label.get("videos") or reels
    wall = by_label.get("page") or reels
    mbasic = re.sub(r"^https?://(?:www\.|web\.|m\.)?facebook\.com/", "https://mbasic.facebook.com/", wall)

    plans: list[dict[str, str]] = []
    if cookie:
        plans += [
            {"label": "reels · phiên của bạn", "url": reels, "ua": "", "transport": "impersonate", "cookie": cookie},
            {"label": "reels · phiên + googlebot", "url": reels, "ua": UA_GOOGLEBOT, "transport": "plain", "cookie": cookie},
            {"label": "videos · phiên của bạn", "url": videos, "ua": "", "transport": "impersonate", "cookie": cookie},
            {"label": "page · phiên của bạn", "url": wall, "ua": "", "transport": "impersonate", "cookie": cookie},
        ]
        if mbasic and mbasic != wall:
            plans.append({"label": "mbasic · phiên của bạn", "url": mbasic, "ua": "", "transport": "impersonate", "cookie": cookie})

    plans += [
        {"label": "reels · chrome", "url": reels, "ua": "", "transport": "impersonate", "cookie": ""},
        {"label": "reels · http2", "url": reels, "ua": UA_BROWSER, "transport": "http2", "cookie": ""},
        {"label": "reels · googlebot", "url": reels, "ua": UA_GOOGLEBOT, "transport": "plain", "cookie": ""},
        {"label": "videos · googlebot", "url": videos, "ua": UA_GOOGLEBOT, "transport": "plain", "cookie": ""},
        {"label": "reels · facebookhit", "url": reels, "ua": UA_FACEBOOK_HIT, "transport": "plain", "cookie": ""},
        {"label": "page · googlebot", "url": wall, "ua": UA_GOOGLEBOT, "transport": "plain", "cookie": ""},
    ]
    return plans


# --------------------------------------------------------------------------- #
# điểm vào                                                                    #
# --------------------------------------------------------------------------- #
def scan_page(
    page_url: str,
    *,
    cookie: str = "",
    budget_s: float = DEFAULT_BUDGET_S,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_attempts: int = 12,
) -> dict:
    """Đọc page và trả về bài thô + nhật ký.

    `status`: `ok` (có bài) · `blocked` (Facebook đòi đăng nhập) · `denied`
    (Facebook từ chối client máy chủ bằng HTTP 400) · `empty` (đọc được trang
    nhưng không có bài/số liệu) · `error` (lỗi mạng/URL).
    """
    page_url = rivals_mod.normalize_page_url(page_url) or (page_url or "").strip()
    cookie = cookie_header(cookie)
    started = time.monotonic()
    attempts: list[Attempt] = []
    posts: list[dict] = []
    blocked_seen = False
    denied_seen = False

    for plan in plan_attempts(page_url, cookie):
        if len(attempts) >= max_attempts:
            break
        if time.monotonic() - started > budget_s:
            break
        transport = available_transport(plan["transport"])
        attempt = Attempt(
            label=plan["label"],
            url=plan["url"],
            ua=plan["ua"],
            cookie=bool(plan["cookie"]),
            transport=transport,
        )
        status, final_url, html, error = _http_get(
            plan["url"], plan["ua"], plan["cookie"], timeout_s, transport
        )
        attempt.status = status
        attempt.size = len(html or "")
        if error:
            attempt.note = error
        else:
            found = extract_posts(html, page_url)
            attempt.posts = len(found)
            if found:
                posts.extend(found)
            attempt.snippet = html_to_text(html)[:180]
            if found:
                attempt.note = f"{len(found)} bài"
            elif status == 400:
                attempt.blocked = True
                attempt.note = "HTTP 400 — Facebook chặn client máy chủ (kiểm tra TLS/bot)"
                denied_seen = True
            elif looks_blocked(html, status, final_url):
                attempt.blocked = True
                attempt.note = "Facebook trả trang đăng nhập thay vì nội dung"
                blocked_seen = True
            elif status in (403, 429):
                attempt.blocked = True
                attempt.note = f"HTTP {status} — bị chặn/tạm giới hạn"
                denied_seen = True
            else:
                attempt.note = "không thấy bài/số liệu nào trong HTML"
        attempts.append(attempt)
        if attempt.posts >= 3:
            break
        if attempt.posts and time.monotonic() - started > budget_s * 0.6:
            break

    # gộp nhiều lần thử (reels + videos) và khử trùng
    merged: dict[str, dict] = {}
    for post in posts:
        text = str(post.get("text") or "")
        url = str(post.get("url") or "")
        digits = re.search(r"(\d{6,})", url)
        key = digits.group(1) if digits else (url or text[:100]).lower()
        current = merged.get(key)
        if current is None:
            merged[key] = post
            continue
        for name in ("views", "likes", "comments", "shares"):
            current[name] = max(int(current.get(name) or 0), int(post.get(name) or 0))
        current["text"] = current.get("text") or text
        current["url"] = current.get("url") or url
    final = list(merged.values())
    final.sort(key=lambda p: (p["views"], p["likes"], p["comments"]), reverse=True)

    if final:
        status_name = "ok"
    elif blocked_seen:
        status_name = "blocked"
    elif denied_seen:
        status_name = "denied"
    elif attempts and all(attempt.status == 0 for attempt in attempts):
        status_name = "error"
    else:
        status_name = "empty"

    return {
        "status": status_name,
        "page_url": page_url,
        "page_label": rivals_mod.page_label(page_url) if page_url else "",
        "posts": final,
        "attempts": [attempt.as_dict() for attempt in attempts],
        "needs_session": status_name in ("blocked", "empty", "denied") and not cookie,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "cookie_used": bool(cookie),
        "transports": sorted({attempt.transport for attempt in attempts}),
        "capabilities": transport_status(),
    }


def explain(scan: dict) -> str:
    """Một câu giải thích cho người dùng, theo kết quả quét."""
    status = scan.get("status")
    label = scan.get("page_label") or "page"
    if status == "ok":
        return f"Đọc được {len(scan.get('posts') or [])} bài từ {label}."
    if status == "blocked":
        if scan.get("cookie_used"):
            return (
                f"Facebook vẫn trả trang đăng nhập cho {label} dù đã có cookie phiên — "
                "cookie có thể đã hết hạn. Dán cookie mới, hoặc lấy bài bằng trình duyệt (2 nút bên dưới)."
            )
        return (
            f"Facebook trả trang đăng nhập cho {label} thay vì nội dung. "
            "Dán cookie phiên một lần rồi bấm tìm lại — máy chủ sẽ đọc bằng chính phiên của bạn."
        )
    if status == "denied":
        return (
            f"Facebook từ chối request từ máy chủ cho {label} (HTTP 400/403 — kiểm tra bot). "
            "Cách chắc ăn: dán cookie phiên, kéo nút bookmark để đọc bằng trình duyệt, "
            "hoặc tải trang HTML (Ctrl+S) lên studio."
        )
    if status == "empty":
        return (
            f"Đọc được HTML của {label} nhưng không thấy bài nào có số liệu. "
            "Page có thể để riêng tư, hoặc Facebook chỉ trả khung rỗng — thử cookie phiên hoặc tải HTML trang lên."
        )
    return f"Không gọi được Facebook cho {label}. Kiểm tra mạng rồi thử lại."
