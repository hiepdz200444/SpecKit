"""Nhập reel từ link page Facebook: chuẩn hoá số, bóc HTML, lọc "đã nổi"."""

import pytest
from fastapi.testclient import TestClient

import app as app_module
import rivals

client = TestClient(app_module.app)

PAGE = "https://www.facebook.com/OldSchoolMusicPage"


def _post(**extra):
    base = {
        "url": "https://www.facebook.com/OldSchoolMusicPage/posts/1",
        "text": "POV: you heard this voice in 1975 and never forgot it. Whitney at her best.",
        "hook": "POV: you heard this voice in 1975",
        "likes": "1.2K",
        "comments": "84",
        "shares": "12",
        "views": "320K",
        "posted_at": "",
    }
    base.update(extra)
    return base


# --------------------------------------------------------------------------- #
# numbers / helpers                                                          #
# --------------------------------------------------------------------------- #
def test_count_from_text_handles_facebook_forms():
    assert rivals.count_from_text("1.2K") == 1200
    assert rivals.count_from_text("84K") == 84000
    assert rivals.count_from_text("1,2 N") == 1200
    assert rivals.count_from_text("1.234") == 1234
    assert rivals.count_from_text("12 345") == 12345
    assert rivals.count_from_text("1.2M") == 1_200_000
    assert rivals.count_from_text("1,5 Tr") == 1_500_000
    assert rivals.count_from_text("") == 0
    assert rivals.count_from_text("abc") == 0


def test_normalize_page_url_and_label():
    assert rivals.normalize_page_url("facebook.com/OldSchoolMusicPage/?ref=pages") == PAGE
    assert rivals.normalize_page_url("https://web.facebook.com/OldSchoolMusicPage/posts/1") == PAGE
    assert rivals.page_label(PAGE) == "facebook.com/OldSchoolMusicPage"
    assert rivals.normalize_page_url("") == ""


def test_guess_format_and_hook():
    assert rivals.guess_format("POV: you are 12 again") == "pov"
    assert rivals.guess_format("Top 5 songs nobody plays anymore") == "list"
    assert rivals.guess_format("«A quote about the night»") == "quote"
    assert rivals.guess_format("Just a normal story about a tour") == "story"
    assert rivals.hook_from_text("One line here. Second line.") == "One line here."


# --------------------------------------------------------------------------- #
# from_posts                                                                 #
# --------------------------------------------------------------------------- #
def test_clean_url_drops_facebook_tracking():
    assert rivals.clean_url("https://www.facebook.com/P/posts/9?__cft__=abc&__tn__=x") == "https://www.facebook.com/P/posts/9"
    assert rivals.clean_url("https://www.facebook.com/permalink.php?story_fbid=1&id=2&__tn__=x") == "https://www.facebook.com/permalink.php?story_fbid=1&id=2"
    assert rivals.clean_url("https://tiktok.com/@x/video/1?is_from_webapp=1") == "https://tiktok.com/@x/video/1?is_from_webapp=1"


def test_from_posts_normalises_numbers_and_format():
    items = rivals.from_posts([_post(url="https://www.facebook.com/OldSchoolMusicPage/posts/1?__cft__=zz")], PAGE)
    assert len(items) == 1
    item = items[0]
    assert item["url"] == "https://www.facebook.com/OldSchoolMusicPage/posts/1"
    assert item["platform"] == "facebook"
    assert item["views"] == 320_000
    assert item["likes"] == 1200
    assert item["comments"] == 84
    assert item["shares"] == 12
    assert item["format"] == "pov"


def test_from_posts_reads_metrics_out_of_the_text_blob():
    blob = "1.2K reactions · 84 comments · 12 shares · 2.4M views — the night the mic died"
    items = rivals.from_posts([{"url": "https://www.facebook.com/x/posts/9", "text": blob}], PAGE)
    item = items[0]
    assert (item["likes"], item["comments"], item["shares"], item["views"]) == (1200, 84, 12, 2_400_000)


def test_posts_from_html_reads_role_article_blocks():
    html = """
    <html><body>
      <div role="article">
        <div dir="auto">POV: you heard this in 1975 and never forgot it, not once.</div>
        <div aria-label="1.2K reactions">1.2K</div>
        <div>84 comments</div><div>12 shares</div>
        <a href="https://www.facebook.com/OldSchoolMusicPage/posts/111">2 days ago</a>
      </div>
      <div role="article">
        <div dir="auto">Top 5 voices that still stop a room dead, number one is obvious.</div>
        <div>320K views</div>
        <a href="/OldSchoolMusicPage/posts/222">5 days ago</a>
      </div>
    </body></html>
    """
    posts = rivals.posts_from_html(html, PAGE)
    assert len(posts) == 2
    assert posts[0]["url"].startswith("https://www.facebook.com/OldSchoolMusicPage/posts/")
    assert posts[0]["likes"] == 1200 and posts[0]["comments"] == 84
    assert posts[1]["views"] == 320_000
    assert posts[1]["format"] == "list"


# --------------------------------------------------------------------------- #
# POST /api/rivals/from-page                                                  #
# --------------------------------------------------------------------------- #
def test_from_page_keeps_page_label_and_only_viral_when_asked():
    posts = [
        _post(views="2.4M", likes="84K", comments="3.2K", shares="1.1K"),
        {
            "url": "https://www.facebook.com/OldSchoolMusicPage/posts/2",
            "text": "A quiet post about a Tuesday rehearsal nobody remembers.",
            "likes": 3,
            "comments": 0,
            "shares": 0,
            "views": 40,
        },
        {
            "url": "https://www.facebook.com/OldSchoolMusicPage/posts/3",
            "text": "Another ordinary morning post with no story at all.",
            "likes": 8,
            "comments": 1,
            "shares": 0,
            "views": 120,
        },
    ]
    res = client.post("/api/rivals/from-page", json={"page_url": PAGE, "posts": posts, "only_viral": True})
    assert res.status_code == 200
    data = res.json()
    assert data["page_label"] == "facebook.com/OldSchoolMusicPage"
    assert data["added"] == 1
    assert data["filtered_out"] == 2
    reel = data["reels"][0]
    assert reel["source_page"] == "facebook.com/OldSchoolMusicPage"
    assert reel["brief"]["beats"]


def test_only_viral_keeps_the_best_posts_of_a_small_page():
    """Page nhỏ chưa bài nào đạt 60 điểm: giữ top 40% của chính page đó."""
    posts = [
        {
            "url": f"https://www.facebook.com/SmallPage/posts/{i}",
            "text": f"post number {i} about the band and the night they played",
            "likes": i * 40,
            "comments": i * 3,
            "views": 8_000 + i * 1_000,
        }
        for i in range(1, 6)
    ]
    data = client.post(
        "/api/rivals/from-page",
        json={"page_url": "https://www.facebook.com/SmallPage", "posts": posts, "only_viral": True},
    ).json()
    assert data["added"] == 2  # ceil(5 * 0.4)
    assert data["filtered_out"] == 3
    assert data["reels"][0]["score"] >= data["reels"][1]["score"]


def test_from_page_skips_duplicates():
    body = {"page_url": PAGE, "posts": [_post(url="https://www.facebook.com/OldSchoolMusicPage/posts/777")]}
    first = client.post("/api/rivals/from-page", json=body).json()
    second = client.post("/api/rivals/from-page", json=body).json()
    if first["added"]:
        assert second["added"] == 0
        assert second["skipped"] >= 1


def test_from_page_accepts_saved_html():
    html = """
      <div role="article">
        <span dir="auto">She recorded this at nine years old and it still sounds wild today.</span>
        <span aria-label="900 reactions">900</span><span>40 comments</span><span>7 shares</span>
        <a href="https://www.facebook.com/OldSchoolMusicPage/posts/333">1 day ago</a>
      </div>
    """
    res = client.post("/api/rivals/from-page", json={"page_url": PAGE, "html": html})
    assert res.status_code == 200
    data = res.json()
    assert data["added"] == 1
    reel = data["reels"][0]
    assert reel["likes"] == 900
    assert reel["source_page"] == "facebook.com/OldSchoolMusicPage"


def test_from_page_without_content_is_a_400():
    res = client.post("/api/rivals/from-page", json={"page_url": PAGE})
    assert res.status_code == 400
    assert "Không đọc được bài nào" in res.json()["detail"]


def test_page_filter_and_pages_list():
    client.post("/api/rivals/from-page", json={"page_url": PAGE, "posts": [_post(url="https://www.facebook.com/OldSchoolMusicPage/posts/555")]})
    listing = client.get("/api/rivals", params={"page": "oldschoolmusicpage"}).json()
    assert listing["count"] >= 1
    assert all("oldschoolmusicpage" in (r["source_page"] or "").lower() for r in listing["reels"])
    pages = client.get("/api/rivals/pages").json()["pages"]
    assert any(p["page"] == "facebook.com/OldSchoolMusicPage" for p in pages)


def test_only_viral_flag_filters_the_listing():
    client.post("/api/rivals", json={"items": [{"url": "https://www.facebook.com/x/posts/quiet", "hook": "quiet one", "views": 50, "likes": 1}]})
    listing = client.get("/api/rivals", params={"only_viral": True}).json()
    assert all(reel["score"] >= 65 for reel in listing["reels"])
