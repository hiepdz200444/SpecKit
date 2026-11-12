import wave

import pytest
from fastapi.testclient import TestClient

import app as app_module
import voice as voice_mod

client = TestClient(app_module.app)


def _project():
    ev = client.get("/api/events?day=2026-11-04&window=400&q=elvis").json()["events"][0]
    return client.post("/api/projects", json={"artist_id": ev["artist_id"], "event": ev}).json()


def _write_mp3(path: str) -> None:
    with open(path, "wb") as f:
        f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 8192)


def _write_wav(path: str) -> None:
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(22050)
        f.writeframes(b"\x00\x00" * 22050)


def test_voice_list_is_en_us_neural():
    data = client.get("/api/voices").json()
    assert data["default"].startswith("en-US-")
    assert len(data["voices"]) >= 4
    assert all(v["id"].startswith("en-US-") and v["id"].endswith("Neural") for v in data["voices"])
    assert set(data["engines"]) == {"edge", "pyttsx3", "ffmpeg"}


def test_edge_tts_is_preferred(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_edge_save", lambda text, voice, path, timeout=45.0: _write_mp3(path))
    project = _project()
    res = client.post(
        f"/api/projects/{project['id']}/voice",
        json={"text": "Elvis Presley would have turned ninety one today.", "voice": "en-US-AriaNeural"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["voice"]["engine"] == "edge-tts"
    assert body["voice"]["ext"] == "mp3"
    assert body["voice"]["url"].endswith(".mp3")
    assert body["project"]["voice"]["url"] == body["voice"]["url"]
    audio = client.get(body["voice"]["url"])
    assert audio.status_code == 200
    # the player needs a real audio content type
    assert audio.headers["content-type"].startswith("audio/")
    checks = {c["id"]: c for c in body["project"]["checks"]}
    assert checks["voice"]["ok"] is True


def test_falls_back_to_pyttsx3_without_ffmpeg(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)

    def boom(*_a, **_k):
        raise OSError("network down")

    monkeypatch.setattr(voice_mod, "_edge_save", boom)
    monkeypatch.setattr(voice_mod, "_pyttsx3_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_pyttsx3_save", lambda text, path: _write_wav(path))
    monkeypatch.setattr(voice_mod.shutil, "which", lambda _name: None)

    project = _project()
    res = client.post(f"/api/projects/{project['id']}/voice", json={"text": "Offline fallback voice line."})
    assert res.status_code == 200
    voice = res.json()["voice"]
    assert voice["engine"] == "pyttsx3"
    assert voice["ext"] == "wav"
    assert voice["duration"] == pytest.approx(1.0, abs=0.2)


def test_pyttsx3_is_converted_when_ffmpeg_exists(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: False)
    monkeypatch.setattr(voice_mod, "_pyttsx3_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_pyttsx3_save", lambda text, path: _write_wav(path))
    monkeypatch.setattr(voice_mod, "_to_mp3", lambda src, dest: _write_mp3(dest) or True)

    project = _project()
    res = client.post(f"/api/projects/{project['id']}/voice", json={"text": "Converted voice line."})
    assert res.status_code == 200
    assert res.json()["voice"]["engine"] == "pyttsx3 + ffmpeg"
    assert res.json()["voice"]["ext"] == "mp3"


def test_no_engine_returns_clear_vietnamese_error(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: False)
    monkeypatch.setattr(voice_mod, "_pyttsx3_available", lambda: False)
    project = _project()
    res = client.post(f"/api/projects/{project['id']}/voice", json={"text": "Anything at all."})
    assert res.status_code == 400
    assert "edge-tts" in res.json()["detail"]
    assert "pyttsx3" in res.json()["detail"]


def test_empty_text_is_rejected(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_edge_save", lambda *a, **k: _write_mp3(a[2]))
    project = _project()
    res = client.post(f"/api/projects/{project['id']}/voice", json={"text": "   "})
    # falls back to the on-screen text, which exists on a fresh project
    assert res.status_code == 200
    assert res.json()["voice"]["text"]


def test_delete_voice(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_edge_save", lambda text, voice, path, timeout=45.0: _write_mp3(path))
    project = _project()
    made = client.post(f"/api/projects/{project['id']}/voice", json={"text": "Delete me please."}).json()
    assert client.delete(f"/api/projects/{project['id']}/voice").json()["project"]["voice"] == {}
    assert client.get(made["voice"]["url"]).status_code == 404


def test_text_limit(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_edge_save", lambda text, voice, path, timeout=45.0: _write_mp3(path))
    project = _project()
    res = client.post(f"/api/projects/{project['id']}/voice", json={"text": "x" * (voice_mod.MAX_CHARS + 10)})
    assert res.status_code == 400
    assert "quá dài" in res.json()["detail"]


def test_changing_the_voice_produces_a_new_file_and_url(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)

    def fake_edge(text, voice, path, timeout=45.0):
        with open(path, "wb") as f:
            f.write(b"ID3" + voice.encode() + b"\x00" * 1024)

    monkeypatch.setattr(voice_mod, "_edge_save", fake_edge)
    project = _project()
    first = client.post(
        f"/api/projects/{project['id']}/voice",
        json={"text": "Pick a different voice please.", "voice": "en-US-AriaNeural"},
    ).json()["voice"]
    second = client.post(
        f"/api/projects/{project['id']}/voice",
        json={"text": "Pick a different voice please.", "voice": "en-US-GuyNeural"},
    ).json()["voice"]

    assert first["voice"] == "en-US-AriaNeural" and second["voice"] == "en-US-GuyNeural"
    assert first["applied"] is True and second["applied"] is True
    assert first["url"] != second["url"], "URL must change so the browser cannot replay the old take"
    assert first["file"] != second["file"]
    # the old recording is cleaned up, the new one plays
    assert client.get(first["url"]).status_code == 404
    fresh = client.get(second["url"])
    assert fresh.status_code == 200
    assert b"GuyNeural" in fresh.content
    # a re-render of the project keeps the latest take
    stored = client.get(f"/api/projects/{project['id']}").json()["voice"]
    assert stored["url"] == second["url"]


def test_voice_files_are_served_without_caching(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_edge_save", lambda text, voice, path, timeout=45.0: _write_mp3(path))
    project = _project()
    made = client.post(f"/api/projects/{project['id']}/voice", json={"text": "No cache allowed."}).json()["voice"]
    res = client.get(made["url"])
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"


def test_fallback_says_the_chosen_voice_was_not_applied(monkeypatch):
    monkeypatch.setattr(voice_mod, "_edge_available", lambda: True)

    def boom(*_a, **_k):
        raise OSError("network down")

    monkeypatch.setattr(voice_mod, "_edge_save", boom)
    monkeypatch.setattr(voice_mod, "_pyttsx3_available", lambda: True)
    monkeypatch.setattr(voice_mod, "_pyttsx3_save", lambda text, path: _write_wav(path))
    monkeypatch.setattr(voice_mod.shutil, "which", lambda _name: None)

    project = _project()
    voice = client.post(
        f"/api/projects/{project['id']}/voice",
        json={"text": "System voice fallback.", "voice": "en-US-JennyNeural"},
    ).json()["voice"]
    assert voice["engine"] == "pyttsx3"
    assert voice["applied"] is False
    assert voice["requested_voice"] == "en-US-JennyNeural"
    assert "Internet" in voice["note"] and "pyttsx3" in voice["note"]
