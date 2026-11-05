"""Đọc page Facebook từ phía máy chủ: dán link page là ra reels nổi."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

import app as app_module
import fb_fetch
import rivals

client = TestClient(app_module.app)

PAGE = "https://www.facebook.com/OldSchoolMusicPage"


# --------------------------------------------------------------------------- #
# HTML giả lập cấu trúc Facebook (JSON nhúng + khối role="article")            #
# --------------------------------------------------------------------------- #
def _video(
    vid: str,
    *,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    text: str = "A story about a night nobody forgot",
    stamp: int = 1730000000,
    url: str = "",
) -> str:
    link = url or f"https://www.facebook.com/reel/{vid}"
    escaped = link.replace("/", "\\/")
    return (
        '{"__typename":"Video","video_id":"' + vid + '",'
        f'"play_count":{views},'
        f'"reaction_count":{{"count":{likes}}},'
        f'"comment_count":{{"count":{comments}}},'
        f'"share_count":{{"count":{shares}}},'
        f'"creation_time":{stamp},'
        f'"permalink_url":"{escaped}",'
        f'"message":{{"text":"{text}"}}}}'
    )


def _feed_html(*blocks: str) -> str:
    return (
        "<html><head><title>Old School Music</title></head><body>"
        '<script type="application/json" data-sjs>'
        '{"require":[["ScheduledServerJS","handle",null,[{"__bbox":{"result":{"data":{'
        '"node":{"page_id":"123","items":[' + ",".join(blocks) + "]}}}}]]]]}"
        "</script></body></html>"
    )


LOGIN_WALL = (
    '<html><body><div id="login_form"><h1>Log into Facebook</h1>'
    "<p>You must log in to continue.</p></form></div></body></html>"
)


# --------------------------------------------------------------------------- #
# URL: page, page dạng id số, link một bài                                     #
# --------------------------------------------------------------------------- #
def test_normalize_page_url_keeps_profile_id_and_single_posts():
    assert rivals.normalize_page_url("facebook.com/OldSchoolMusicPage/?ref=pages") == PAGE
    assert (
        rivals.normalize_page_url("https://web.facebook.com/OldSchoolMusicPage/posts/1") == PAGE
    )
    # page dạng id số (đúng dạng link trong ảnh người dùng dán)
    profile = "https://www.facebook.com/profile.php?id=61565510541149"
    assert rivals.normalize_page_url("facebook.com/profile.php?id=61565510541149&ref=x") == profile
    assert rivals.page_label(profile) == "facebook.com/profile.php?id=61565510541149"
    # link một bài giữ nguyên để studio đọc đúng reel đó
    reel = "https://www.facebook.com/reel/1150200123"
    assert rivals.normalize_page_url(reel) == reel
    assert rivals.is_single_post(reel)
    assert rivals.is_single_post("https://www.facebook.com/watch/?v=123456")
    assert rivals.is_single_post("https://www.facebook.com/x/posts/123")
    assert not rivals.is_single_post(PAGE)


def test_page_variants_cover_reels_videos_and_wall():
    assert fb_fetch.page_variants(PAGE) == [
        ("reels", f"{PAGE}/reels/"),
        ("videos", f"{PAGE}/videos/"),
        ("page", PAGE),
    ]
    profile = "https://www.facebook.com/profile.php?id=61565510541149"
    labels = [label for label, _ in fb_fetch.page_variants(profile)]
    urls = [url for _, url in fb_fetch.page_variants(profile)]
    assert labels == ["reels", "videos", "page"]
    assert urls[0].endswith("id=61565510541149&sk=reels")
    # dán link một reel: chỉ thử đúng bài đó
    assert fb_fetch.page_variants("https://www.facebook.com/reel/900") == [
        ("bài đơn", "https://www.facebook.com/reel/900"),
    ]


def test_plan_attempts_uses_saved_session_first():
    plans = fb_fetch.plan_attempts(PAGE, "c_user=1; xs=abc")
    assert plans[0]["label"] == "reels · phiên của bạn"
    assert plans[0]["cookie"] == "c_user=1; xs=abc"
    assert plans[0]["transport"] == "impersonate"  # TLS giả lập Chrome, không phải UA trần
    assert plans[0]["ua"] == ""  # curl_cffi tự đặt UA khớp dấu vân tay
    assert any(plan["label"].startswith("mbasic") for plan in plans)

    no_cookie = fb_fetch.plan_attempts(PAGE, "")
    assert all(plan["cookie"] == "" for plan in no_cookie)
    labels = {plan["label"] for plan in no_cookie}
    assert {"reels · chrome", "reels · http2", "reels · googlebot", "reels · facebookhit"} <= labels
    assert {plan["transport"] for plan in no_cookie} >= {"impersonate", "http2", "plain"}


def test_plan_attempts_for_a_single_reel_reads_only_that_post():
    reel = "https://www.facebook.com/reel/123456789"
    labels = [plan["label"] for plan in fb_fetch.plan_attempts(reel, "")]
    assert labels and all(label.startswith("bài đơn") for label in labels)


# --------------------------------------------------------------------------- #
# bóc dữ liệu                                                                 #
# --------------------------------------------------------------------------- #
def test_extract_posts_reads_embedded_video_json():
    html = _feed_html(
        _video("1111", views=2_400_000, likes=84_000, comments=3_200, shares=1_100,
               text="POV: you heard this voice in 1975 and never forgot it."),
        _video("2222", views=12_000, likes=400, comments=20, shares=5,
               text="Top 5 voices that still stop a room dead"),
    )
    posts = fb_fetch.extract_posts(html, PAGE)
    assert len(posts) == 2
    top = posts[0]
    assert top["views"] == 2_400_000 and top["likes"] == 84_000
    assert top["comments"] == 3_200 and top["shares"] == 1_100
    assert top["url"] == "https://www.facebook.com/reel/1111"  # đã bỏ escape \/
    assert top["posted_at"] == "2024-10-27"
    assert top["hook"].startswith("POV: you heard this voice")
    assert posts[1]["views"] == 12_000


def test_extract_posts_merges_duplicate_videos_and_keeps_biggest_numbers():
    html = _feed_html(
        _video("3333", views=900, likes=10),
        _video("3333", views=45_000, likes=1_800, comments=95, shares=12),
    )
    posts = fb_fetch.extract_posts(html, PAGE)
    assert len(posts) == 1
    assert posts[0]["views"] == 45_000
    assert posts[0]["likes"] == 1_800
    assert posts[0]["comments"] == 95


def test_extract_posts_reads_article_blocks_and_metric_text():
    html = """
    <html><body>
      <div role="article">
        <div dir="auto">She recorded this at nine years old and it still sounds wild today.</div>
        <div aria-label="1.2K reactions">1.2K</div><div>84 comments</div><div>1.1K shares</div>
        <div>2.4M views</div>
        <a href="https://www.facebook.com/OldSchoolMusicPage/posts/111">2 days ago</a>
      </div>
    </body></html>
    """
    posts = fb_fetch.extract_posts(html, PAGE)
    assert len(posts) == 1
    assert posts[0]["url"] == "https://www.facebook.com/OldSchoolMusicPage/posts/111"
    assert posts[0]["views"] == 2_400_000
    assert posts[0]["likes"] == 1200
    assert posts[0]["comments"] == 84
    assert posts[0]["shares"] == 1100


def test_extract_posts_uses_og_meta_for_a_single_reel_page():
    html = """
    <html><head>
      <meta property="og:title" content="The note nobody talks about" />
      <meta property="og:description" content="1.2M views · 84K reactions · 3.2K comments" />
      <meta property="og:url" content="https://www.facebook.com/reel/777" />
    </head><body></body></html>
    """
    posts = fb_fetch.extract_posts(html, "https://www.facebook.com/reel/777")
    assert len(posts) == 1
    assert posts[0]["url"] == "https://www.facebook.com/reel/777"
    assert posts[0]["views"] == 1_200_000
    assert posts[0]["likes"] == 84_000
    assert posts[0]["comments"] == 3200


def test_extract_posts_ignores_login_wall():
    assert fb_fetch.extract_posts(LOGIN_WALL, PAGE) == []


def test_looks_blocked_detects_login_wall_but_not_real_feed():
    assert fb_fetch.looks_blocked(LOGIN_WALL, 200, PAGE)
    feed = _feed_html(_video("8888", views=100, likes=5))
    assert not fb_fetch.looks_blocked(feed, 200, PAGE)
    assert fb_fetch.looks_blocked("<html></html>", 200, "https://www.facebook.com/login/?next=x")


# --------------------------------------------------------------------------- #
# cookie phiên (một lần)                                                       #
# --------------------------------------------------------------------------- #
def test_parse_cookie_skips_junk_keys():
    parsed = fb_fetch.parse_cookie("cookie: nope; path=/; domain=.facebook.com; c_user=1; xs=2; empty=")
    assert parsed == {"c_user": "1", "xs": "2"}


def test_cookie_roundtrip_and_masking(tmp_path, monkeypatch):
    monkeypatch.setattr(fb_fetch, "SESSION_PATH", str(tmp_path / "fb_session.json"))
    monkeypatch.delenv("FB_COOKIE", raising=False)
    assert fb_fetch.load_cookie() == ""
    status = fb_fetch.save_cookie("c_user=61565; xs=secret; datr=abc; fr=0xyz")
    assert status["saved"] and status["has_xs"]
    assert status["cookies"] == ["c_user", "xs", "datr", "fr"]
    assert "secret" not in json.dumps(status)
    header = fb_fetch.load_cookie()
    assert header == "c_user=61565; xs=secret; datr=abc; fr=0xyz"  # giữ cả bộ cookie phiên
    cleared = fb_fetch.clear_cookie()
    assert cleared["saved"] is False


# --------------------------------------------------------------------------- #
# scan_page: chặn / đọc được                                                   #
# --------------------------------------------------------------------------- #
def test_scan_page_reports_blocked_when_facebook_wants_a_login(monkeypatch):
    calls = []

    def fake_get(url, ua, cookie="", timeout=0, transport="plain"):
        calls.append((url, ua, cookie, transport))
        return 200, url, LOGIN_WALL, ""

    monkeypatch.setattr(fb_fetch, "_http_get", fake_get)
    monkeypatch.setattr(fb_fetch, "load_cookie", lambda: "")
    scan = fb_fetch.scan_page(PAGE, cookie="", max_attempts=3)
    assert scan["status"] == "blocked"
    assert scan["needs_session"] is True
    assert scan["posts"] == []
    assert len(scan["attempts"]) == 3
    assert all(attempt["blocked"] for attempt in scan["attempts"])
    assert "cookie phiên" in fb_fetch.explain(scan)
    assert calls[0][0] == f"{PAGE}/reels/"
    assert calls[0][3] == "impersonate"
    assert scan["attempts"][0]["transport"] == "Chrome giả lập"


def test_scan_page_stops_at_the_first_target_with_posts(monkeypatch):
    feed = _feed_html(_video("4444", views=500_000, likes=9_000, comments=400, shares=90))

    def fake_get(url, ua, cookie="", timeout=0, transport="plain"):
        if url.endswith("/reels/"):
            return 200, url, feed, ""
        return 200, url, LOGIN_WALL, ""

    monkeypatch.setattr(fb_fetch, "_http_get", fake_get)
    scan = fb_fetch.scan_page(PAGE, cookie="", max_attempts=6)
    assert scan["status"] == "ok"
    assert scan["needs_session"] is False
    assert len(scan["posts"]) == 1
    assert scan["posts"][0]["views"] == 500_000
    assert scan["page_label"] == "facebook.com/OldSchoolMusicPage"


def test_scan_page_marks_network_errors(monkeypatch):
    monkeypatch.setattr(
        fb_fetch,
        "_http_get",
        lambda url, ua, cookie="", timeout=0, transport="plain": (0, url, "", "ConnectError: boom"),
    )
    scan = fb_fetch.scan_page(PAGE, cookie="", max_attempts=2)
    assert scan["status"] == "error"
    assert scan["attempts"][0]["note"].startswith("ConnectError")


# --------------------------------------------------------------------------- #
# POST /api/rivals/scan-page                                                   #
# --------------------------------------------------------------------------- #
def _fake_scan(posts, status="ok", needs_session=False):
    return {
        "status": status,
        "page_url": PAGE,
        "page_label": "facebook.com/OldSchoolMusicPage",
        "posts": posts,
        "attempts": [{"label": "reels", "url": f"{PAGE}/reels/", "ua": "trình duyệt",
                      "cookie": False, "status": 200, "size": 10, "posts": len(posts),
                      "blocked": False, "note": ""}],
        "needs_session": needs_session,
        "elapsed_ms": 120,
        "cookie_used": False,
    }


def test_scan_page_endpoint_imports_only_viral(monkeypatch):
    hot_id, quiet_id = (str(uuid.uuid4().int)[:12] for _ in range(2))
    posts = [
        {"url": f"https://www.facebook.com/reel/{hot_id}", "text": f"The night the mic died on live radio {hot_id}",
         "hook": f"The night the mic died {hot_id}", "views": 2_400_000, "likes": 84_000,
         "comments": 3_200, "shares": 1_100, "posted_at": ""},
        {"url": f"https://www.facebook.com/reel/{quiet_id}", "text": f"A quiet Tuesday rehearsal nobody talks about {quiet_id}",
         "hook": f"A quiet Tuesday {quiet_id}", "views": 40, "likes": 2, "comments": 0, "shares": 0,
         "posted_at": ""},
    ]
    monkeypatch.setattr(fb_fetch, "scan_page", lambda url, **kwargs: _fake_scan(posts))
    res = client.post("/api/rivals/scan-page", json={"page_url": PAGE, "only_viral": True})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["scanned"] == 2
    assert data["added"] == 1
    assert data["filtered_out"] == 1
    reel = data["reels"][0]
    assert reel["source_page"] == "facebook.com/OldSchoolMusicPage"
    assert reel["views"] == 2_400_000
    assert reel["score"] >= 65
    assert data["attempts"][0]["url"].endswith("/reels/")


def test_scan_page_endpoint_explains_a_blocked_page(monkeypatch):
    monkeypatch.setattr(
        fb_fetch,
        "scan_page",
        lambda url, **kwargs: _fake_scan([], status="blocked", needs_session=True),
    )
    data = client.post("/api/rivals/scan-page", json={"page_url": PAGE}).json()
    assert data["status"] == "blocked"
    assert data["needs_session"] is True
    assert data["added"] == 0
    assert "cookie phiên" in data["message"]
    assert data["session"]["saved"] in (True, False)


def test_scan_page_endpoint_accepts_a_profile_id_link(monkeypatch):
    seen = {}

    def fake_scan(url, **kwargs):
        seen["url"] = url
        return _fake_scan([])

    monkeypatch.setattr(fb_fetch, "scan_page", fake_scan)
    data = client.post(
        "/api/rivals/scan-page",
        json={"page_url": "https://www.facebook.com/profile.php?id=61565510541149"},
    ).json()
    assert seen["url"] == "https://www.facebook.com/profile.php?id=61565510541149"
    assert data["page_label"] == "facebook.com/OldSchoolMusicPage"  # nhãn do scan trả về


def test_scan_page_endpoint_needs_a_link():
    res = client.post("/api/rivals/scan-page", json={"page_url": "  "})
    assert res.status_code == 400
    assert "link page" in res.json()["detail"].lower()


# --------------------------------------------------------------------------- #
# cookie phiên qua API                                                         #
# --------------------------------------------------------------------------- #
def test_session_endpoints_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(fb_fetch, "SESSION_PATH", str(tmp_path / "fb_session.json"))
    monkeypatch.delenv("FB_COOKIE", raising=False)
    saved = client.post("/api/rivals/session", json={"cookie": "c_user=61565; xs=abc123"})
    assert saved.status_code == 200
    assert saved.json()["has_xs"] is True
    assert client.get("/api/rivals/session").json()["saved"] is True
    assert client.delete("/api/rivals/session").json()["saved"] is False
    assert client.post("/api/rivals/session", json={"cookie": ""}).status_code == 400


def test_bootstrap_exposes_session_state(monkeypatch):
    monkeypatch.setattr(fb_fetch, "cookie_status", lambda: {"saved": False, "cookies": []})
    boot = client.get("/api/bootstrap").json()
    assert boot["rivals"]["session"]["saved"] is False


# --------------------------------------------------------------------------- #
# HTTP thật (server nội bộ) — kiểm tra UA/cookie và toàn bộ đường quét          #
# --------------------------------------------------------------------------- #
import http.server  # noqa: E402
import socketserver  # noqa: E402
import threading  # noqa: E402


def _header(headers, name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


class _FakeFacebook(http.server.BaseHTTPRequestHandler):
    html = ""
    status = 200
    seen: list = []

    def do_GET(self):  # noqa: N802 - API của http.server
        _FakeFacebook.seen.append((self.path, dict(self.headers)))
        body = self.html.encode("utf-8")
        self.send_response(self.status)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: D102 - im lặng khi test
        pass


@pytest.fixture()
def fake_facebook():
    _FakeFacebook.html = ""
    _FakeFacebook.status = 200
    _FakeFacebook.seen = []
    server = socketserver.TCPServer(("127.0.0.1", 0), _FakeFacebook)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_http_get_sends_browser_headers_and_cookie(fake_facebook):
    _FakeFacebook.html = _feed_html(_video("9191", views=1500, likes=30))
    status, final_url, text, error = fb_fetch._http_get(
        f"{fake_facebook}/page/reels/", fb_fetch.UA_BROWSER, "c_user=61565; xs=abc"
    )
    assert error == "" and status == 200
    assert final_url == f"{fake_facebook}/page/reels/"
    assert '"video_id"' in text
    path, headers = _FakeFacebook.seen[-1]
    assert path == "/page/reels/"
    assert headers.get("User-Agent") == fb_fetch.UA_BROWSER
    assert "c_user=61565" in headers.get("Cookie", "")
    assert "en-US" in headers.get("Accept-Language", "")


def test_scan_page_end_to_end_over_http(fake_facebook, monkeypatch):
    _FakeFacebook.html = _feed_html(
        _video("9292", views=987_000, likes=12_000, comments=800, shares=210,
               text="The night the mic died on live radio, and nobody stopped the tape."),
    )
    monkeypatch.setattr(
        fb_fetch, "page_variants", lambda url: [("reels", f"{fake_facebook}/page/reels/")]
    )
    scan = fb_fetch.scan_page("http://127.0.0.1/page", cookie="c_user=1; xs=2")
    assert scan["status"] == "ok"
    assert scan["cookie_used"] is True
    assert scan["posts"][0]["views"] == 987_000
    assert scan["attempts"][0]["cookie"] is True
    assert _FakeFacebook.seen[0][1].get("Cookie", "").startswith("c_user=1")


def test_scan_page_reports_blocked_on_403(fake_facebook, monkeypatch):
    _FakeFacebook.status = 403
    _FakeFacebook.html = LOGIN_WALL
    monkeypatch.setattr(
        fb_fetch, "page_variants", lambda url: [("reels", f"{fake_facebook}/page/reels/")]
    )
    scan = fb_fetch.scan_page("http://127.0.0.1/page", cookie="")
    assert scan["status"] == "blocked"
    assert scan["attempts"][0]["status"] == 403
    assert scan["attempts"][0]["snippet"]


def test_impersonate_transport_reaches_the_page(fake_facebook):
    """curl_cffi giả lập Chrome thật — đường chính để Facebook không trả 400."""
    pytest.importorskip("curl_cffi")
    _FakeFacebook.html = _feed_html(_video("9393", views=77_000, likes=900))
    status, final_url, text, error = fb_fetch._http_get(
        f"{fake_facebook}/page/reels/", "", "", fb_fetch.DEFAULT_TIMEOUT_S, "impersonate"
    )
    assert error == "" and status == 200
    assert '"video_id"' in text
    path, headers = _FakeFacebook.seen[-1]
    assert path == "/page/reels/"
    # curl_cffi đặt UA + sec-ch-ua khớp dấu vân tay Chrome
    assert _header(headers, "user-agent").lower().startswith("mozilla/5.0")
    assert "chrome" in _header(headers, "sec-ch-ua").lower()


def test_impersonate_falls_back_when_curl_cffi_is_missing(fake_facebook, monkeypatch):
    _FakeFacebook.html = _feed_html(_video("9494", views=1000, likes=10))

    def missing(*args, **kwargs):
        raise ImportError("No module named 'curl_cffi'")

    monkeypatch.setattr(fb_fetch, "_get_impersonate", missing)
    status, _url, text, error = fb_fetch._http_get(
        f"{fake_facebook}/p", fb_fetch.UA_BROWSER, "", 5, "impersonate"
    )
    assert error == "" and status == 200 and '"video_id"' in text


def test_http_400_is_reported_as_denied(fake_facebook, monkeypatch):
    _FakeFacebook.status = 400
    _FakeFacebook.html = "<html><body>Bad Request</body></html>"
    monkeypatch.setattr(
        fb_fetch, "page_variants", lambda url: [("reels", f"{fake_facebook}/page/reels/")]
    )
    scan = fb_fetch.scan_page("http://127.0.0.1/page", cookie="", max_attempts=3)
    assert scan["status"] == "denied"
    assert scan["needs_session"] is True
    assert any("HTTP 400" in attempt["note"] for attempt in scan["attempts"])
    assert "HTTP 400" in fb_fetch.explain(scan)


# --------------------------------------------------------------------------- #
# Tải HTML trang lên + bookmarklet (đường không cần DevTools)                   #
# --------------------------------------------------------------------------- #
def test_from_html_endpoint_reads_a_saved_page():
    vid = str(uuid.uuid4().int)[:10]
    html = _feed_html(
        _video(vid, views=1_500_000, likes=40_000, comments=900, shares=300,
               text=f"The tape rolled and nobody in the room knew it was history {vid}")
    )
    res = client.post(
        "/api/rivals/from-html",
        json={"html": html, "page_url": PAGE, "only_viral": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["scanned"] == 1 and data["added"] == 1
    reel = data["reels"][0]
    assert reel["views"] == 1_500_000
    assert reel["source_page"] == "facebook.com/OldSchoolMusicPage"


def test_from_html_rejects_a_file_without_reels():
    short = client.post("/api/rivals/from-html", json={"html": "<html></html>"})
    assert short.status_code == 400
    empty = client.post("/api/rivals/from-html", json={"html": "<html><body>" + "x" * 400 + "</body></html>"})
    assert empty.status_code == 400
    assert "reel" in empty.json()["detail"]


def test_bookmarklet_endpoint_builds_a_javascript_url():
    import urllib.parse

    data = client.get("/api/rivals/bookmarklet").json()
    assert data["href"].startswith("javascript:")
    code = urllib.parse.unquote(data["href"][len("javascript:"):])
    assert 'const STUDIO = "http://testserver"' in code
    assert 'role="article"' in code
    assert "/api/rivals/from-page" in code
    assert "\n" not in code  # một dòng để dán vào bookmark
