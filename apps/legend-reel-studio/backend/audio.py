"""Tiny procedural music bed so every reel has audio out of the box.

This is intentionally simple: a warm minor pad, a soft pulse and a shaker.
It exists so the operator never publishes a silent reel while they wait for a
licensed track. Uploaded music always wins over this bed.
"""

from __future__ import annotations

import os
import wave

import numpy as np

SR = 44100
NPM = {  # note -> frequency (A4 = 440)
    "A2": 110.00, "C3": 130.81, "E3": 164.81, "A3": 220.00, "A4": 440.00,
    "F2": 87.31, "F3": 174.61, "C4": 261.63,
    "C3b": 123.47, "G2": 98.00, "B2": 123.47, "D3": 146.83, "G3": 196.00,
    "E2": 82.41,
}

# Am - F - C - G, two bars each at 84 BPM (4/4)
PROGRESSION = [
    ["A2", "E3", "A3", "C4"],
    ["F2", "C3", "F3", "A3"],
    ["C3b", "C3", "E3", "G3"],
    ["G2", "B2", "D3", "G3"],
]


def _tone(freq: float, dur: float, detune: float = 0.0) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    f = freq * (1 + detune / 1200.0)
    wave_ = (
        np.sin(2 * np.pi * f * t)
        + 0.28 * np.sin(2 * np.pi * 2 * f * t)
        + 0.12 * np.sin(2 * np.pi * 3 * f * t)
        + 0.05 * np.sin(2 * np.pi * 4 * f * t)
    )
    return wave_.astype(np.float32)


def _env(n: int, attack: float, release: float, sr: int = SR) -> np.ndarray:
    a = max(1, int(attack * sr))
    r = max(1, int(release * sr))
    env = np.ones(n, dtype=np.float32)
    a = min(a, n)
    env[:a] = np.linspace(0, 1, a, dtype=np.float32) ** 1.5
    r = min(r, n)
    env[-r:] = np.linspace(1, 0, r, dtype=np.float32) ** 1.2
    return env


def _lowpass(x: np.ndarray, cutoff: float = 3200.0) -> np.ndarray:
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    out = np.empty_like(x)
    acc = 0.0
    for i in range(x.size):  # short buffers only
        acc += alpha * (x[i] - acc)
        out[i] = acc
    return out


def _delay(x: np.ndarray, seconds: float = 0.36, feedback: float = 0.28, mix: float = 0.22) -> np.ndarray:
    d = int(seconds * SR)
    out = x.copy()
    for tap in range(1, 4):
        idx = tap * d
        if idx >= x.size:
            break
        out[idx:] += x[:-idx] * (feedback ** (tap - 1)) * mix
    return out


def build_bed(duration: float = 24.0, bpm: float = 84.0) -> np.ndarray:
    n = int(SR * duration)
    mix = np.zeros(n, dtype=np.float32)
    beat = 60.0 / bpm
    bar = beat * 4
    chord_len = bar * 2

    # --- pad chords -------------------------------------------------------
    pos = 0.0
    ci = 0
    while pos < duration:
        chord = PROGRESSION[ci % len(PROGRESSION)]
        dur = min(chord_len, duration - pos)
        if dur <= 0.2:
            break
        seg = np.zeros(int(SR * dur), dtype=np.float32)
        for note in chord:
            f = NPM[note]
            voice = _tone(f, dur) * 0.16 + _tone(f, dur, detune=6) * 0.10
            seg += voice.astype(np.float32)
        seg *= _env(seg.size, 0.9, 1.4)
        start = int(pos * SR)
        end = min(n, start + seg.size)
        mix[start:end] += seg[: end - start]
        pos += dur
        ci += 1

    # --- sub bass ---------------------------------------------------------
    pos = 0.0
    ci = 0
    while pos < duration:
        chord = PROGRESSION[ci % len(PROGRESSION)]
        root = NPM[chord[0]] / 2
        dur = min(bar, duration - pos)
        seg = _tone(root, dur) * 0.30
        seg *= _env(seg.size, 0.05, 0.5)
        start = int(pos * SR)
        end = min(n, start + seg.size)
        mix[start:end] += seg[: end - start]
        pos += dur
        ci += 1

    # --- heartbeat kick ---------------------------------------------------
    t_kick = 0.0
    beat_i = 0
    rng = np.random.default_rng(7)
    while t_kick < duration - 0.3:
        if beat_i % 2 == 0:
            kdur = 0.42
            t = np.arange(int(SR * kdur)) / SR
            sweep = 52 + 38 * np.exp(-t * 22)
            k = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-t * 7.5)
            start = int(t_kick * SR)
            end = min(n, start + k.size)
            mix[start:end] += (k[: end - start] * 0.34).astype(np.float32)
        t_kick += beat
        beat_i += 1

    # --- shaker on off-beats ---------------------------------------------
    t_sh = beat / 2
    while t_sh < duration - 0.3:
        sdur = 0.07
        noise = rng.normal(0, 1, int(SR * sdur)).astype(np.float32)
        noise = np.diff(noise, prepend=np.float32(0)) * np.exp(-np.arange(noise.size) / SR * 55)
        start = int(t_sh * SR)
        end = min(n, start + noise.size)
        mix[start:end] += noise[: end - start] * 0.05
        t_sh += beat

    # --- space + tone shaping --------------------------------------------
    wet = _delay(mix, seconds=0.42, feedback=0.3, mix=0.3)
    mix = 0.72 * mix + 0.5 * wet
    mix = _lowpass(mix, cutoff=5200.0)

    # fades (clamped so short beds still work)
    fade_in = min(int(SR * 1.2), n)
    fade_out = min(int(SR * 3.0), n)
    if fade_in > 0:
        mix[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)
    if fade_out > 0:
        mix[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32)

    peak = float(np.max(np.abs(mix))) or 1.0
    mix = (mix / peak) * 0.82
    return np.clip(mix, -1, 1)


def write_bed(path: str, duration: float = 24.0) -> str:
    mono = build_bed(duration)
    # gentle stereo widening via a short haas delay
    d = int(0.012 * SR)
    left = mono.copy()
    right = np.concatenate([np.zeros(d, dtype=np.float32), mono[:-d]])
    stereo = np.stack([left, right], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bed.wav")
    print(write_bed(out, 24.0))
