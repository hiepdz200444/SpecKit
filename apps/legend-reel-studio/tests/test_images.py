import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as app_module
import images as images_mod

client = TestClient(app_module.app)


def _jpeg(size=(600, 800), colour=(40, 30, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="JPEG")
    return buf.getvalue()


JPEG = _jpeg()


@pytest.fixture()
def project():
    ev = client.get("/api/events?day=2026-11-04&window=400&q=elvis").json()["events"][0]
    return client.post("/api/projects", json={"artist_id": ev["artist_id"], "event": ev}).json()


def _fake_wiki(url, params=None):
    if "rest_v1/page/summary" in url:
        return {
            "title": "Elvis Presley",
            "description": "American singer",
            "originalimage": {"source": "https://upload.wikimedia.org/wiki/lead.jpg", "width": 900, "height": 1200},
            "thumbnail": {"source": "https://upload.wikimedia.org/wiki/lead-thumb.jpg"},
        }
    params = params or {}
    if params.get("list") == "search":
        return {"query": {"search": [{"title": f"File:Elvis {i}.jpg"} for i in range(4)]}}
    if params.get("prop") == "imageinfo":
        pages = {}
        for i, title in enumerate(params["titles"].split("|")):
            pages[str(i)] = {
                "title": title,
                "imageinfo": [
                    {
                        "url": f"https://upload.wikimedia.org/wikipedia/commons/{i}.jpg",
                        "thumburl": f"https://upload.wikimedia.org/wikipedia/commons/{i}-thumb.jpg",
                        "width": 1200,
                        "height": 1500,
                        "mime": "image/jpeg",
                        "extmetadata": {
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                            "Artist": {"value": '<a href="https://commons.wikimedia.org/wiki/User:Jane">Jane Doe</a>'},
                            "ImageDescription": {"value": "Elvis on stage, 1956"},
                        },
                    }
                ],
            }
        return {"query": {"pages": pages}}
    return {}


@pytest.fixture()
def fake_network(monkeypatch):
    monkeypatch.setattr(images_mod, "http_json", _fake_wiki)
    monkeypatch.setattr(images_mod, "http_bytes", lambda url: (JPEG, "image/jpeg"))
    return monkeypatch


def test_suggest_collects_wikipedia_and_commons_with_licences(project, fake_network):
    res = client.get(f"/api/projects/{project['id']}/images/suggest")
    assert res.status_code == 200
    data = res.json()
    assert data["target"] == 20
    assert len(data["images"]) >= 3
    sources = {img["source"] for img in data["images"]}
    assert "wikipedia" in sources and "wikimedia" in sources
    commons = [img for img in data["images"] if img["source"] == "wikimedia"][0]
    assert commons["license"] == "CC BY-SA 4.0"
    assert commons["license_url"].startswith("https://creativecommons.org/")
    assert commons["attribution"] == "Jane Doe"  # html stripped
    assert commons["page_url"].startswith("https://commons.wikimedia.org/wiki/File:")


def test_add_selected_candidates_stores_licence_and_attribution(project, fake_network):
    data = client.get(f"/api/projects/{project['id']}/images/suggest").json()
    picked = data["images"][:2]
    res = client.post(f"/api/projects/{project['id']}/images", json={"images": picked})
    assert res.status_code == 200
    body = res.json()
    assert body["added"] == 2
    project_after = body["project"]
    assert project_after["image_count"] == 2
    stored = project_after["images"][0]
    assert stored["license"]
    assert stored["attribution"]
    assert stored["is_banner"] is True
    # adding the same candidate twice must not duplicate it
    again = client.post(f"/api/projects/{project['id']}/images", json={"images": picked}).json()
    assert again["added"] == 0
    assert again["project"]["image_count"] == 2


def test_import_from_pasted_urls(project, fake_network):
    res = client.post(
        f"/api/projects/{project['id']}/images",
        json={"urls": ["https://i.pinimg.com/736x/ab/cd/ef.jpg", "https://media.gettyimages.com/id/1.jpg"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["added"] == 2
    assert body["errors"] == []
    for img in body["project"]["images"]:
        assert img["source"] == "user"
        assert img["page_url"] in {"https://i.pinimg.com/736x/ab/cd/ef.jpg", "https://media.gettyimages.com/id/1.jpg"}
        assert img["file_url"].endswith(".jpg")


def test_pinterest_pin_page_is_rejected_with_advice(project, fake_network):
    res = client.post(
        f"/api/projects/{project['id']}/images",
        json={"url": "https://www.pinterest.com/pin/1234567890/"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["added"] == 0
    assert "Copy image address" in body["errors"][0]


def test_local_and_non_image_urls_are_rejected(project, fake_network):
    for url in ("http://127.0.0.1:8000/secret.jpg", "file:///etc/passwd", "https://example.com/page.html"):
        res = client.post(f"/api/projects/{project['id']}/images", json={"url": url})
        assert res.json()["added"] == 0
        assert res.json()["errors"]


def test_html_pages_are_not_images(project, monkeypatch):
    monkeypatch.setattr(images_mod, "http_bytes", lambda url: (b"<html></html>", "text/html"))
    res = client.post(f"/api/projects/{project['id']}/images", json={"url": "https://example.com/a.jpg"})
    assert res.json()["added"] == 0
    assert "text/html" in res.json()["errors"][0]


def test_banner_switch_and_zip_attribution(project, fake_network):
    data = client.get(f"/api/projects/{project['id']}/images/suggest").json()
    body = client.post(f"/api/projects/{project['id']}/images", json={"images": data["images"][:3]}).json()
    imgs = body["project"]["images"]
    assert imgs[0]["is_banner"] is True

    switched = client.patch(
        f"/api/projects/{project['id']}/images/{imgs[2]['id']}", json={"is_banner": True}
    ).json()["project"]
    assert switched["banner_url"] == imgs[2]["file_url"]
    flags = {img["id"]: img["is_banner"] for img in switched["images"]}
    assert flags[imgs[2]["id"]] is True
    assert flags[imgs[0]["id"]] is False

    zip_res = client.get(f"/api/projects/{project['id']}/images.zip")
    with zipfile.ZipFile(io.BytesIO(zip_res.content)) as archive:
        names = archive.namelist()
        assert len([n for n in names if n.endswith(".jpg")]) == 3
        assert "ATTRIBUTION.txt" in names
        credit = archive.read("ATTRIBUTION.txt").decode("utf-8")
    assert "CC BY-SA 4.0" in credit
    assert "Jane Doe" in credit


def test_duplicate_copies_images(project, fake_network):
    data = client.get(f"/api/projects/{project['id']}/images/suggest").json()
    client.post(f"/api/projects/{project['id']}/images", json={"images": data["images"][:2]})
    dup = client.post(f"/api/projects/{project['id']}/duplicate").json()
    assert dup["image_count"] == 2
    for img in dup["images"]:
        stored = client.get(img["file_url"])
        assert stored.status_code == 200


def test_delete_project_removes_image_files(project, fake_network):
    data = client.get(f"/api/projects/{project['id']}/images/suggest").json()
    body = client.post(f"/api/projects/{project['id']}/images", json={"images": data["images"][:1]}).json()
    url = body["project"]["images"][0]["file_url"]
    assert client.get(url).status_code == 200
    client.delete(f"/api/projects/{project['id']}")
    assert client.get(url).status_code == 404


def test_invalid_image_id_is_rejected(project):
    # ids must look like our hex ids, so no path tricks can reach the filesystem
    assert client.patch(f"/api/projects/{project['id']}/images/no-such-id", json={"is_banner": True}).status_code == 400
    assert client.delete(f"/api/projects/{project['id']}/images/zzzzzzzz").status_code == 400
    assert client.delete(f"/api/projects/{project['id']}/images/abcdef123456").status_code == 404
