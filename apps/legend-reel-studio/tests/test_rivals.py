"""Competitor reels: import, score, filter and remake."""

import pytest
from fastapi.testclient import TestClient

import app as app_module
import rivals

client = TestClient(app_module.app)

SAMPLE = "\n".join(
    [
        "https://tiktok.com/@x/video/1 | tiktok | 1.2M | 84k | 2.1k | 900 | Whitney Houston | The note nobody talks about | story",
        "https://instagram.com/reel/abc/ | instagram | 320k | 25k | 1.4k | 600 | Selena | She recorded this at nine | pov",
        "https://facebook.com/watch/?v=2 | facebook | 45k | 1200 | 80 | 12 | Elvis Presley | The last take | tribute",
    ]
)


def _seed() -> dict:
    res = client.post("/api/rivals", json={"lines": SAMPLE})
    assert res.status_code == 200
    return res.json()


def test_parse_numbers_and_lines():
    assert rivals.parse_number("1.2M") == 1_200_000
    assert rivals.parse_number("84k") == 84_000
    assert rivals.parse_number("1,234") == 1234
    assert rivals.parse_number("2.1 nghìn") == 2100
    items = rivals.parse_bulk(SAMPLE)
    assert len(items) == 3
    assert items[0]["platform"] == "tiktok"
    assert items[0]["views"] == 1_200_000
    assert items[0]["artist_name"] == "Whitney Houston"
    assert items[0]["hook"] == "The note nobody talks about"
    assert items[0]["format"] == "story"


def test_import_scores_each_reel():
    body = _seed()
    assert body["added"] == 3
    reels = body["reels"]
    assert all(0 <= r["score"] <= 100 for r in reels)
    assert all(r["tier"] for r in reels)
    top = max(reels, key=lambda r: r["score"])
    assert top["score"] >= 75
    assert top["brief"]["beats"] and top["brief"]["remake_rules"]
    million = next(r for r in reels if r["views"] == 1_200_000)
    assert million["score"] >= 70
    assert million["platform_label"] == "TikTok"
    assert million["brief"]["format_label"] == "Kể chuyện (story)"


def test_filters_and_sorting():
    _seed()
    tiktok = client.get("/api/rivals?platform=tiktok").json()
    assert tiktok["count"] >= 1 and all(r["platform"] == "tiktok" for r in tiktok["reels"])

    strong = client.get("/api/rivals?min_score=70").json()
    assert all(r["score"] >= 70 for r in strong["reels"])

    by_views = client.get("/api/rivals?sort=views").json()["reels"]
    assert by_views[0]["views"] >= by_views[-1]["views"]

    search = client.get("/api/rivals?q=selena").json()["reels"]
    assert search and all("selena" in (r["artist_name"] + r["hook"]).lower() for r in search)

    unused = client.get("/api/rivals?only_unused=true").json()["reels"]
    assert all(not r["remade_project_id"] for r in unused)


def test_remake_library_artist_creates_a_project_with_the_brief():
    body = _seed()
    reel = body["reels"][0]
    res = client.post(f"/api/rivals/{reel['id']}/remake", json={"artist_name": "Whitney Houston"})
    assert res.status_code == 200
    data = res.json()
    project = data["project"]
    assert 700 <= project["article_words"] <= 900
    assert project["remake"]["rival_id"] == reel["id"]
    assert project["remake"]["brief"]["beats"]
    assert project["remake"]["score"] == reel["score"]
    assert data["reel"]["status"] == "remaking"
    assert data["reel"]["remade_project_id"] == project["id"]

    # the remake brief travels with the export and the full download
    md = client.get(f"/api/projects/{project['id']}/export?fmt=md").text
    assert "Remake brief" in md
    bundle = client.get(f"/api/projects/{project['id']}/bundle.zip")
    assert bundle.status_code == 200


def test_remake_unknown_name_creates_a_profile():
    body = _seed()
    reel = body["reels"][1]
    res = client.post(f"/api/rivals/{reel['id']}/remake", json={"artist_name": "A Name Nobody Curated"})
    assert res.status_code == 200
    project = res.json()["project"]
    assert project["artist"]["custom"] is True
    assert project["artist"]["name"] == "A Name Nobody Curated"
    assert 700 <= project["article_words"] <= 900


def test_remake_without_any_artist_is_rejected():
    res = client.post(
        "/api/rivals",
        json={"items": [{"url": "https://tiktok.com/x", "platform": "tiktok", "hook": "hook only", "views": 10_000}]},
    )
    reel = res.json()["reels"][0]
    assert reel["artist_name"] == ""
    bad = client.post(f"/api/rivals/{reel['id']}/remake", json={})
    assert bad.status_code == 400
    assert "nghệ sĩ" in bad.json()["detail"]


def test_delete_and_patch_reel():
    body = _seed()
    rid = body["reels"][0]["id"]
    before = next(r for r in body["reels"] if r["id"] == rid)["score"]
    patched = client.patch(f"/api/rivals/{rid}", json={"hook": "new hook", "views": 5_000_000}).json()["reel"]
    assert patched["hook"] == "new hook"
    assert patched["views"] == 5_000_000
    assert patched["score"] <= before or patched["score"] >= 60  # more views, same engagement
    assert patched["reach_points"] >= 45
    assert client.delete(f"/api/rivals/{rid}").status_code == 200
    assert client.delete(f"/api/rivals/{rid}").status_code == 404
