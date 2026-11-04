import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

import app as app_module
import library

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


def test_bootstrap_shape(day):
    data = client.get(f"/api/bootstrap?day={day}").json()
    assert data["today"] == day
    assert len(data["artists"]) >= 25
    assert set(data["styles"]) == {"noir", "vhs", "gold"}
    assert "total" in data["stats"]


def test_events_endpoint(day):
    data = client.get(f"/api/events?day={day}&window=30").json()
    assert data["count"] == len(data["events"])
    for ev in data["events"]:
        assert ev["artist"]["songs"]
        assert ev["date"]


def test_unknown_artist_404():
    assert client.get("/api/artists/nobody").status_code == 404


def test_project_lifecycle(day):
    ev = _an_event(day)

    created = client.post("/api/projects", json={"artist_id": ev["artist_id"], "event": ev})
    assert created.status_code == 200
    project = created.json()
    pid = project["id"]
    assert project["article_title"]
    assert project["article_body"]
    assert len(project["music_links"]) == 3
    assert project["video_plan"]["scenes"]
    assert project["caption"]
    assert project["status"] in {"article", "video"}

    # article edits persist
    patched = client.patch(f"/api/projects/{pid}", json={"article_title": "A new title", "status": "article"})
    assert patched.json()["article_title"] == "A new title"
    assert client.get(f"/api/projects/{pid}").json()["status"] == "article"

    # on-video text guardrail
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

    # duplicate keeps the copy, drops renders
    dup = client.post(f"/api/projects/{pid}/duplicate").json()
    assert dup["id"] != pid
    assert dup["status"] == "draft"
    assert dup["article_body"] == project["article_body"]
    assert dup["render_url"] == ""

    # delete
    assert client.delete(f"/api/projects/{dup['id']}").json()["ok"] is True
    assert client.get(f"/api/projects/{dup['id']}").status_code == 404


def test_generate_with_seed_is_repeatable(day):
    ev = _an_event(day, q="whitney", window=30)
    project = client.post("/api/projects", json={"artist_id": ev["artist_id"], "event": ev}).json()
    pid = project["id"]
    first = client.post(f"/api/projects/{pid}/generate", json={"section": "article", "seed": 11}).json()
    second = client.post(f"/api/projects/{pid}/generate", json={"section": "article", "seed": 11}).json()
    assert first["article_body"] == second["article_body"]
    third = client.post(f"/api/projects/{pid}/generate", json={"section": "article", "seed": 12}).json()
    assert third["article_body"] != first["article_body"] or third["article_title"] != first["article_title"]


def test_banner_upload_with_data_url(day):
    ev = _an_event(day)
    pid = client.post("/api/projects", json={"artist_id": ev["artist_id"], "event": ev}).json()["id"]
    import base64
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (300, 400), (30, 20, 10)).save(buf, format="JPEG")
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    res = client.post(f"/api/projects/{pid}/banner", json={"data_url": data_url})
    assert res.status_code == 200
    assert res.json()["banner_url"].endswith(".jpg")


def test_custom_event_created(day):
    res = client.post(
        "/api/events/custom",
        json={"artist_id": "elvis-presley", "date": day, "title": "Graceland opens to the public", "kind": "custom"},
    )
    assert res.status_code == 200
    assert res.json()["title"].startswith("Graceland")


def test_stats_track_renders(day):
    stats = client.get(f"/api/bootstrap?day={day}").json()["stats"]
    assert stats["by_status"]
