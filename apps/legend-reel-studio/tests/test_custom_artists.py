"""Tạo bài viết bằng tên nhân vật (profile generator, never invents facts)."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

import app as app_module
import profiles

client = TestClient(app_module.app)


def _create(name: str, **extra):
    payload = {"name": name, "event": {"kind": "birthday", "date": "2026-08-29"}, **extra}
    return client.post("/api/projects/custom", json=payload)


def test_name_only_creates_a_700_900_word_project():
    res = _create("Michael Jackson")
    assert res.status_code == 200
    project = res.json()
    assert project["artist"]["name"] == "Michael Jackson"
    assert project["artist"]["custom"] is True
    assert 700 <= project["article_words"] <= 900
    assert project["article_in_range"] is True
    assert 9 <= project["overlay_words"] <= 15
    assert project["status"] == "script"
    assert project["voice"]["file"] if project.get("voice") else True
    # no invented song titles: only search links with neutral labels
    links = project["music_links"]
    assert len(links) == 3
    assert [l["title"] for l in links] == ["Greatest hits", "Live performance", "Interview"]
    for link in links:
        assert link["youtube"].startswith("https://www.youtube.com/results?search_query=")
        assert "Michael+Jackson" in link["youtube"]


def test_name_only_music_links_are_searches_not_video_ids():
    res = _create("Charlie Chaplin")
    assert res.status_code == 200
    for link in res.json()["music_links"]:
        assert "watch?v=" not in link["youtube"]
        assert "Charlie" in link["youtube"]


def test_profile_fields_flow_into_the_copy():
    payload = {
        "name": "Selena Quintanilla",
        "profile": {
            "aka": "La Reina",
            "genre": "Tejano / Pop",
            "era": "1980s-1990s",
            "birth": "1971",
            "death": "1995",
            "gender": "female",
            "facts": ["She recorded her first album at nine."],
            "songs": [{"title": "Como La Flor", "year": "1992"}, {"title": "Bidi Bidi Bom Bom", "year": "1994"}],
        },
        "event": {"kind": "memorial", "date": "2026-03-31"},
    }
    res = client.post("/api/projects/custom", json=payload)
    assert res.status_code == 200
    project = res.json()
    assert project["artist"]["aka"] == "La Reina"
    assert 700 <= project["article_words"] <= 900
    body = project["article_body"]
    assert "Como La Flor" in body
    assert "She recorded her first album at nine." in body
    assert "her" in body.lower()  # female pronouns
    assert [link["title"] for link in project["music_links"]] == ["Como La Flor", "Bidi Bidi Bom Bom"]
    assert all(link["youtube"].startswith("https://www.youtube.com/results") for link in project["music_links"])
    assert "#SelenaQuintanilla" in project["hashtags"]


def test_same_name_reuses_the_profile_instead_of_duplicating():
    first = _create("Buddy Holly").json()
    second = _create("Buddy Holly").json()
    assert first["artist_id"] == second["artist_id"]
    listed = client.get("/api/artists").json()
    names = [a["name"] for a in listed["custom"]]
    assert names.count("Buddy Holly") == 1


def test_missing_name_is_rejected():
    res = client.post("/api/projects/custom", json={"name": "  "})
    assert res.status_code == 400


def test_custom_artist_can_be_generated_again_and_exported():
    created = _create("Otis Redding").json()
    pid = created["id"]
    again = client.post(f"/api/projects/{pid}/generate", json={"section": "all", "seed": 4242})
    assert again.status_code == 200
    assert 700 <= again.json()["article_words"] <= 900

    md = client.get(f"/api/projects/{pid}/export?fmt=md")
    assert md.status_code == 200
    assert "Otis Redding" in md.text

    bundle = client.get(f"/api/projects/{pid}/bundle.zip")
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        assert "article.md" in archive.namelist()


def test_custom_artist_with_projects_cannot_be_deleted_blindly():
    created = _create("Etta James").json()
    aid = created["artist_id"]
    blocked = client.delete(f"/api/artists/custom/{aid}")
    assert blocked.status_code == 400
    assert "dự án" in blocked.json()["detail"]


def test_generator_never_leaks_a_zero_year():
    profile = profiles.normalize({"name": "Aretha Franklin"})
    for kind, day in (("birthday", "2026-03-25"), ("memorial", "2026-08-16"), ("custom", "2026-11-05")):
        event = profiles.make_event(profile, kind, day)
        article = profiles.article_for(profile, event, seed=11)
        script = profiles.script_for(profile, event, article, seed=11)
        assert "0 years" not in article["body"]
        assert "0 years" not in script["overlay_text"]
        assert 700 <= article["word_count"] <= 900
        assert 9 <= script["overlay_words"] <= 15
