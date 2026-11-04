import os
import subprocess
import wave

import imageio_ffmpeg
import pytest

import audio
import content
import library
import render
from seed_artists import ARTISTS


def _tiny_project(kind="hook"):
    artist = library.get_artist("elvis-presley")
    return {
        "video_plan": {
            "badge": "ON THIS DAY",
            "duration": 1.0,
            "fps": 10,
            "scenes": [
                {"id": "hook", "kind": "hook", "start": 0.0, "end": 0.5, "text": "Elvis would have turned 92 today and this take still lands"},
                {"id": "stat", "kind": "stat", "start": 0.5, "end": 1.0, "text": "92", "sub": "YEARS AGO TODAY"},
            ],
        },
        "banner_image": "",
    }, artist


def test_audio_bed_is_valid_wav(tmp_path):
    out = tmp_path / "bed.wav"
    audio.write_bed(str(out), duration=2.0)
    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 2
        assert wf.getframerate() == 44100
        assert abs(wf.getnframes() / 44100 - 2.0) < 0.05


@pytest.mark.slow
def test_render_produces_vertical_mp4(tmp_path):
    project, artist = _tiny_project()
    out = tmp_path / "reel.mp4"
    poster = tmp_path / "poster.jpg"
    renderer = render.Renderer(project, artist, "noir")
    result = renderer.render(str(out), audio_path="", poster_path=str(poster))

    assert result["frames"] == 10
    assert out.exists() and out.stat().st_size > 5000
    assert poster.exists()

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    probe = subprocess.run([exe, "-i", str(out)], capture_output=True, text=True).stderr
    assert "1080x1920" in probe
    assert "h264" in probe


def test_styles_available():
    assert set(render.STYLES) == {"noir", "vhs", "gold"}
    for style in render.STYLES.values():
        assert len(style["accent"]) == 3


def test_every_artist_can_build_a_scene_overlay():
    # font/text layout must not crash for any name length
    artist = library.get_artist("bb-king")
    scene = {"kind": "hook", "text": "B.B. King would have turned 101 today and this take still lands"}
    rgb, alpha = render.scene_overlay(scene, artist, render.STYLES["gold"], 0, 5)
    assert rgb.size == (render.W, render.H)
    assert alpha.size == (render.W, render.H)


def test_generated_plan_renders_first_frame(tmp_path):
    artist = library.get_artist("tina-turner")
    events = library.search_events(ref=__import__("datetime").date(2026, 11, 26), window=0)
    ev = next(e for e in events if e["artist_id"] == "tina-turner")
    plan = content.video_for(artist, ev, None, seed=4)
    plan["duration"] = 0.4
    plan["fps"] = 10
    for s in plan["scenes"]:
        s["start"] = 0.0
        s["end"] = 0.4
    project = {"video_plan": plan, "banner_image": ""}
    renderer = render.Renderer(project, artist, "vhs")
    img = renderer.frame(0.1)
    assert img.size == (1080, 1920)
