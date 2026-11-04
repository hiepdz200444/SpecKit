"""Text-to-speech for the reel voiceover.

Priority order:
  1. edge-tts — Microsoft Edge neural voices, en-US (mp3, needs internet).
  2. pyttsx3 — offline system voices (Windows SAPI5 / macOS say / Linux espeak).
     pyttsx3 writes WAV; if a system `ffmpeg` happens to be installed the file
     is converted to mp3, otherwise the WAV is delivered as-is.

Nothing here is required for the rest of the studio: when both engines are
missing the API returns a clear Vietnamese error and everything else keeps
working.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import wave
from typing import Any

MAX_CHARS = 4000

NEURAL_VOICES = [
    {"id": "en-US-AriaNeural", "label": "Aria — nữ, ấm, kể chuyện", "gender": "nữ"},
    {"id": "en-US-GuyNeural", "label": "Guy — nam, trầm, kiểu radio", "gender": "nam"},
    {"id": "en-US-JennyNeural", "label": "Jenny — nữ, rõ ràng, trung tính", "gender": "nữ"},
    {"id": "en-US-ChristopherNeural", "label": "Christopher — nam, dày, documentary", "gender": "nam"},
    {"id": "en-US-MichelleNeural", "label": "Michelle — nữ, nhẹ, gần gũi", "gender": "nữ"},
    {"id": "en-US-EricNeural", "label": "Eric — nam, nhanh, podcast", "gender": "nam"},
]
DEFAULT_VOICE = NEURAL_VOICES[0]["id"]


class VoiceError(RuntimeError):
    """Raised with a Vietnamese message that is safe to show in the UI."""


def _edge_available() -> bool:
    try:
        import edge_tts  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def _pyttsx3_available() -> bool:
    try:
        import pyttsx3  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def engines() -> dict[str, bool]:
    return {"edge": _edge_available(), "pyttsx3": _pyttsx3_available(), "ffmpeg": bool(shutil.which("ffmpeg"))}


def clean_text(text: str) -> str:
    value = " ".join((text or "").split())
    if not value:
        raise VoiceError("Chưa có text để tạo voice")
    if len(value) > MAX_CHARS:
        raise VoiceError(f"Text quá dài ({len(value)} ký tự). Giới hạn {MAX_CHARS} ký tự mỗi lần.")
    return value


def voice_dir(data_dir: str, project_id: str) -> str:
    path = os.path.join(data_dir, "voice", project_id)
    os.makedirs(path, exist_ok=True)
    return path


def _edge_save(text: str, voice: str, path: str, timeout: float = 45.0) -> None:
    import edge_tts

    async def run() -> None:
        await edge_tts.Communicate(text, voice).save(path)

    asyncio.run(asyncio.wait_for(run(), timeout=timeout))
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        raise VoiceError("edge-tts không trả về audio")


def _pyttsx3_save(text: str, path: str) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.save_to_file(text, path)
    engine.runAndWait()
    engine.stop()
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        raise VoiceError("pyttsx3 không tạo được file (máy có thể thiếu giọng đọc hệ thống)")


def _to_mp3(src: str, dest: str) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    try:
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", src, "-codec:a", "libmp3lame", "-q:a", "4", dest],
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False
    return os.path.exists(dest) and os.path.getsize(dest) > 1024


def _wav_duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as f:
            frames = f.getnframes()
            rate = f.getframerate() or 1
            return round(frames / rate, 1)
    except Exception:  # noqa: BLE001
        return 0.0


def synthesize(data_dir: str, project_id: str, text: str, voice: str = DEFAULT_VOICE) -> dict[str, Any]:
    """Create a voiceover file and return its metadata (path/ext/engine/bytes)."""
    text = clean_text(text)
    if not any(v["id"] == voice for v in NEURAL_VOICES):
        voice = DEFAULT_VOICE
    folder = voice_dir(data_dir, project_id)
    target = os.path.join(folder, "voiceover")
    for stale in (target + ".mp3", target + ".wav"):
        if os.path.exists(stale):
            os.remove(stale)

    errors: list[str] = []

    if _edge_available():
        try:
            _edge_save(text, voice, target + ".mp3")
            return _result(target + ".mp3", data_dir, "edge-tts", voice, text)
        except Exception as exc:  # noqa: BLE001 - any network/voice failure falls back
            errors.append(f"edge-tts: {exc}")

    if _pyttsx3_available():
        try:
            _pyttsx3_save(text, target + ".wav")
            if _to_mp3(target + ".wav", target + ".mp3"):
                os.remove(target + ".wav")
                return _result(target + ".mp3", data_dir, "pyttsx3 + ffmpeg", voice, text)
            return _result(target + ".wav", data_dir, "pyttsx3", voice, text)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"pyttsx3: {exc}")

    detail = "; ".join(errors) if errors else "không tìm thấy edge-tts hoặc pyttsx3"
    raise VoiceError(
        "Không tạo được voice. Cần internet cho edge-tts, hoặc cài pyttsx3 + giọng hệ thống để chạy offline. "
        f"Chi tiết: {detail}"
    )


def _result(path: str, data_dir: str, engine: str, voice: str, text: str) -> dict[str, Any]:
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    return {
        "path": path,
        "file": os.path.relpath(path, data_dir).replace(os.sep, "/"),
        "engine": engine,
        "voice": voice,
        "ext": ext,
        "bytes": os.path.getsize(path),
        "duration": _wav_duration(path) if ext == "wav" else 0.0,
        "text": text,
    }
