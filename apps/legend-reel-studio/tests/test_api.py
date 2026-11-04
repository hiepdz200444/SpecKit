import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as app_module

client = TestClient(app_module.app)


@pytest.fixture(scope="module")
def day():
    return "2026-11-04"


def _an_event(day: str, q: str = "elvis", window: int = 400) -> dict:
    res = client.get(f"/api/events?day={day}&window={window}&q={q}")
    assert res.status_code == 200
    events = res.json()["events"]
    assert events
    return events[0]


def _create(day: str) -> dict:
    ev = _an_event(day)
    res = client.post("/api/projects", json={"artist_id": ev["artist_id"], "event": ev})
    assert res.status_code == 200
    return res.json()


def test_bootstrap_shape(day):
    data = client.get(f"/api/bootstrap?day={day}").json()
    assert data["today"] == day
    assert len(data["artists"]) >= 25
    assert data["limits"]["article"] == [700, 900]
    assert data["limits"]["overlay"] == [9, 15]
    assert data["limits"]["images"] == 20
    assert data["voices"] and all(v["id"].startswith("en-US-") for v in data["voices"])
    assert "total" in data["stats"]
    assert "styles" not in data  # video rendering was removed


def test_events_endpoint(day):
    data = client.get(f"/api/events?day={day}&window=30").json()
    assert data["count"] == len(data["events"])
    for ev in data["events"]:
        assert ev["artist"]["songs"]
        assert ev["date"]


def test_unknown_artist_404():
    assert client.get("/api/artists/nobody").status_code == 404


def test_project_lifecycle(day):
    project = _create(day)
    pid = project["id"]
    assert project["article_title"]
    assert 700 <= project["article_words"] <= 900
    assert project["article_in_range"] is True
    assert project["article_range"] == [700, 900]
    assert len(project["music_links"]) == 3
    assert project["caption"]
    assert project["fb_hook"]
    assert project["first_comment"]
    assert project["images"] == []
    assert project["image_target"] == 20
    assert project["status"] in {"article", "script"}
    assert "render_url" not in project
    assert "poster_url" not in project

    # article edits persist and the word count is reported back
    patched = client.patch(
        f"/api/projects/{pid}",
        json={"article_title": "A new title", "article_body": "short body only", "status": "article"},
    ).json()
    assert patched["article_title"] == "A new title"
    assert patched["article_words"] == 3
    assert patched["article_in_range"] is False
    assert client.get(f"/api/projects/{pid}").json()["status"] == "article"

    # on-screen text guardrail (9-15 words)
    bad = client.post(f"/api/projects/{pid}/overlay", json={"text": "just three words"})
    assert bad.json()["words"] == 3 and bad.json()["ok"] is False
    good_text = "Elvis would have turned 92 today and this 1969 take still proves everything"
    good = client.post(f"/api/projects/{pid}/overlay", json={"text": good_text})
    assert good.json()["ok"] is True
    assert client.get(f"/api/projects/{pid}").json()["video_overlay_text"] == good_text

    options = client.get(f"/api/projects/{pid}/overlay-options").json()["options"]
    assert len(options) >= 3
    assert all(o["ok"] for o in options)

    # export
    md = client.get(f"/api/projects/{pid}/export?fmt=md").text
    assert "A new title" in md
    assert "youtube.com" in md
    assert "first comment" in md.lower()

    # duplicate keeps the copy, drops the voice + banner
    dup = client.post(f"/api/projects/{pid}/duplicate").json()
    assert dup["id"] != pid
    assert dup["status"] == "draft"
    assert dup["article_body"] == "short body only"
    assert dup["banner_image"] == ""
    assert dup["voice"] == {}

    # delete
    assert client.delete(f"/api/projects/{dup['id']}").json()["ok"] is True
    assert client.get(f"/api/projects/{dup['id']}").status_code == 404


def test_generate_with_seed_is_repeatable(day):
    ev = _an_event(day, q="whitney", window=30)
    pid = client.post("/api/projects", json={"artist_id": ev["artist_id"], "event": ev}).json()["id"]
    first = client.post(f"/api/projects/{pid}/generate", json={"section": "article", "seed": 11}).json()
    second = client.post(f"/api/projects/{pid}/generate", json={"section": "article", "seed": 11}).json()
    assert first["article_body"] == second["article_body"]
    third = client.post(f"/api/projects/{pid}/generate", json={"section": "article", "seed": 12}).json()
    assert third["article_body"] != first["article_body"] or third["article_title"] != first["article_title"]
    assert third["article_in_range"] is True


def test_generate_script_section_only_touches_text(day):
    project = _create(day)
    pid = project["id"]
    res = client.post(f"/api/projects/{pid}/generate", json={"section": "script", "seed": 5}).json()
    assert res["article_body"] == project["article_body"]
    assert res["caption"] and res["overlay_ok"] is True


def test_generate_rejects_unknown_section(day):
    pid = _create(day)["id"]
    assert client.post(f"/api/projects/{pid}/generate", json={"section": "video"}).status_code == 400


def test_image_upload_and_banner(day):
    pid = _create(day)["id"]
    buf = io.BytesIO()
    Image.new("RGB", (300, 400), (30, 20, 10)).save(buf, format="JPEG")
    res = client.post(
        f"/api/projects/{pid}/images/upload",
        files=[("files", ("portrait.jpg", buf.getvalue(), "image/jpeg"))],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["added"] == 1
    project = body["project"]
    assert project["image_count"] == 1
    image = project["images"][0]
    assert image["file_url"].startswith("/media/images/")
    assert image["is_banner"] is True  # first image becomes the banner
    assert project["banner_url"] == image["file_url"]

    # download + zip
    single = client.get(f"/api/projects/{pid}/images/{image['id']}/download")
    assert single.status_code == 200 and single.headers["content-type"] == "image/jpeg"
    zip_res = client.get(f"/api/projects/{pid}/images.zip")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert zip_res.content[:2] == b"PK"

    # delete the only image -> banner falls back to the stage art
    deleted = client.delete(f"/api/projects/{pid}/images/{image['id']}").json()
    assert deleted["project"]["image_count"] == 0
    assert deleted["project"]["banner_url"].startswith("/assets/")


def test_banner_endpoint_is_gone(day):
    pid = _create(day)["id"]
    assert client.post(f"/api/projects/{pid}/banner", json={}).status_code in {404, 405}
    assert client.post(f"/api/projects/{pid}/render", json={}).status_code in {404, 405}
    assert client.get("/api/jobs/anything").status_code == 404


def test_image_upload_rejects_non_image(day):
    pid = _create(day)["id"]
    res = client.post(
        f"/api/projects/{pid}/images/upload",
        files=[("files", ("note.txt", b"not an image", "text/plain"))],
    )
    assert res.status_code == 200
    assert res.json()["added"] == 0
    assert res.json()["errors"]


def test_custom_event_created(day):
    res = client.post(
        "/api/events/custom",
        json={"artist_id": "elvis-presley", "date": day, "title": "Graceland opens to the public", "kind": "custom"},
    )
    assert res.status_code == 200
    assert res.json()["title"].startswith("Graceland")


def test_stats_shape(day):
    stats = client.get(f"/api/bootstrap?day={day}").json()["stats"]
    assert stats["total"] >= 1
    assert "by_status" in stats
    assert "with_banner" in stats


def test_data_url_banner_upload_is_not_supported(day):
    """Banner uploads now go through the images tab (multipart), not data URLs."""
    pid = _create(day)["id"]
    payload = "data:image/jpeg;base64," + base64.b64encode(b"x").decode()
    res = client.post(f"/api/projects/{pid}/banner", json={"data_url": payload})
    assert res.status_code in {404, 405}
