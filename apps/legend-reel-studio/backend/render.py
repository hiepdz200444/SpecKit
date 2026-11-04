"""Render a 1080x1920 Facebook Reel from a project.

Frames are composited with Pillow and piped straight into ffmpeg (libx264 +
AAC), which keeps the whole thing dependency-light and fully offline.
"""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from typing import Callable

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
WEB_DIR = os.path.join(APP_DIR, "web")
FONT_DIR = os.path.join(WEB_DIR, "assets", "fonts")
ASSET_DIR = os.path.join(WEB_DIR, "assets")
DATA_DIR = os.path.join(APP_DIR, "data")

W, H = 1080, 1920
FPS = 30
SS = 1.22  # supersampled source scale for ken-burns headroom

STYLES = {
    "noir": {
        "tint": (12, 16, 28),
        "saturation": 0.55,
        "contrast": 1.12,
        "brightness": 0.62,
        "accent": (240, 176, 76),
        "ink": (250, 246, 238),
        "scanlines": False,
        "label": "Noir",
    },
    "vhs": {
        "tint": (26, 10, 32),
        "saturation": 0.78,
        "contrast": 1.06,
        "brightness": 0.64,
        "accent": (255, 92, 148),
        "ink": (245, 240, 255),
        "scanlines": True,
        "label": "VHS",
    },
    "gold": {
        "tint": (40, 24, 10),
        "saturation": 0.9,
        "contrast": 1.05,
        "brightness": 0.68,
        "accent": (232, 190, 110),
        "ink": (252, 244, 226),
        "scanlines": False,
        "label": "Gold",
    },
}


# --------------------------------------------------------------------------- #
# font helpers                                                                #
# --------------------------------------------------------------------------- #
def F(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _font_display(size: int) -> ImageFont.FreeTypeFont:
    return F("Anton-Regular.ttf", size)


def _font_serif(size: int, italic: bool = False) -> ImageFont.FreeTypeFont:
    return F("DMSerifDisplay-Italic.ttf" if italic else "DMSerifDisplay-Regular.ttf", size)


def _font_body(size: int) -> ImageFont.FreeTypeFont:
    return F("Barlow-Regular.ttf", size)


def _font_semibold(size: int) -> ImageFont.FreeTypeFont:
    return F("Barlow-SemiBold.ttf", size)


def _font_bold(size: int) -> ImageFont.FreeTypeFont:
    return F("Barlow-Bold.ttf", size)


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    for block in str(text).split("\n"):
        words = block.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for word in words[1:]:
            trial = f"{cur} {word}"
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_tracked(draw, xy, text, font, fill, tracking=2.0, anchor_center_x=None):
    x, y = xy
    total = sum(draw.textlength(ch, font=font) + tracking for ch in text) - tracking
    if anchor_center_x is not None:
        x = anchor_center_x - total / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return total


def fit_display(draw, text: str, max_w: int, start: int, min_size: int = 54, max_lines: int = 5):
    size = start
    while size >= min_size:
        font = _font_display(size)
        lines = wrap(draw, text.upper(), font, max_w)
        if len(lines) <= max_lines and all(draw.textlength(l, font=font) <= max_w for l in lines):
            return font, lines
        size -= 4
    font = _font_display(min_size)
    return font, wrap(draw, text.upper(), font, max_w)


# --------------------------------------------------------------------------- #
# image prep                                                                  #
# --------------------------------------------------------------------------- #
def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    r = max(w / img.width, h / img.height)
    resized = img.resize((max(1, round(img.width * r)), max(1, round(img.height * r))), Image.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))


def _grade(img: Image.Image, style: dict) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(style["saturation"])
    img = ImageEnhance.Brightness(img).enhance(style["brightness"])
    img = ImageEnhance.Contrast(img).enhance(style["contrast"])
    tint = Image.new("RGB", img.size, style["tint"])
    img = Image.blend(img, tint, 0.35)
    # gentle blue/teal lift in the shadows
    arr = np.asarray(img).astype(np.float32)
    lum = arr.mean(axis=2, keepdims=True) / 255.0
    shadow = (1 - lum) ** 2
    arr[:, :, 2] = np.clip(arr[:, :, 2] + shadow[..., 0] * 12, 0, 255)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 4, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def _vignette_overlay(style: dict) -> Image.Image:
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H * 0.42
    d = np.sqrt(((x - cx) / (W * 0.72)) ** 2 + ((y - cy) / (H * 0.72)) ** 2)
    vig = np.clip(d - 0.35, 0, 1.4) ** 1.5
    alpha = np.clip(vig * 165, 0, 205).astype(np.uint8)

    top = np.clip((210 - y) / 260, 0, 1) * 210
    bottom = np.clip((y - (H - 760)) / 560, 0, 1) ** 1.2 * 235
    alpha = np.clip(alpha + top + bottom, 0, 255).astype(np.uint8)

    overlay = Image.new("RGBA", (W, H), (6, 8, 14, 0))
    overlay.putalpha(Image.fromarray(alpha, mode="L"))

    if style["scanlines"]:
        scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(scan)
        for yy in range(0, H, 4):
            sd.line([(0, yy), (W, yy)], fill=(0, 0, 0, 26))
        overlay = Image.alpha_composite(overlay, scan)
    return overlay


def _page_bg(style: dict) -> Image.Image:
    base = Image.new("RGB", (W, H), (10, 10, 14))
    d = ImageDraw.Draw(base)
    top = tuple(int(c * 0.9) for c in style["tint"])
    for yy in range(H):
        t = yy / H
        col = tuple(int(top[i] + (8 - top[i]) * t) for i in range(3))
        d.line([(0, yy), (W, yy)], fill=col)
    return base


# --------------------------------------------------------------------------- #
# text overlays per scene                                                     #
# --------------------------------------------------------------------------- #
def _base_layer(style: dict) -> Image.Image:
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def _draw_pill(draw, cx, y, text, font, fg, bg, pad_x=26, pad_y=14, tracking=3.2):
    w = sum(draw.textlength(ch, font=font) + tracking for ch in text) - tracking
    x0, x1 = cx - w / 2 - pad_x, cx + w / 2 + pad_x
    draw.rounded_rectangle([x0, y, x1, y + pad_y * 2 + font.size], radius=(pad_y * 2 + font.size) / 2, fill=bg)
    draw_tracked(draw, (x0 + pad_x, y + pad_y - 2), text, font, fg, tracking)
    return y + pad_y * 2 + font.size


def _comment_bubble(draw, box, fill, outline, width=6):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=44, fill=fill, outline=outline, width=width)
    tail = [(x0 + 92, y1 - 4), (x0 + 176, y1 - 4), (x0 + 104, y1 + 66)]
    draw.polygon(tail, fill=fill)
    draw.line([(x0 + 92, y1 - 2), (x0 + 104, y1 + 62), (x0 + 176, y1 - 2)], fill=outline, width=width)
    # mask the seam of the tail with the fill colour
    draw.line([(x0 + 100, y1 - 6), (x0 + 170, y1 - 6)], fill=fill, width=width + 4)


def _arrow_down(draw, cx, cy, size, color):
    draw.polygon(
        [(cx - size * 0.52, cy - size * 0.5), (cx + size * 0.52, cy - size * 0.5), (cx, cy + size * 0.55)],
        fill=color,
    )


def scene_overlay(scene: dict, artist: dict, style: dict, index: int, total: int) -> tuple[Image.Image, Image.Image]:
    """Return (rgb, alpha) for a scene's static text layer."""
    ink = style["ink"]
    accent = style["accent"]
    layer = _base_layer(style)
    d = ImageDraw.Draw(layer)
    cx = W / 2
    name = artist["name"]
    kind = scene.get("kind", "hook")

    if kind == "hook":
        font, lines = fit_display(d, scene["text"], 940, 108, 66, 5)
        lh = int(font.size * 1.06)
        block_h = lh * len(lines)
        y = 900 - block_h / 2
        # accent bar
        d.rounded_rectangle([cx - 60, y - 62, cx + 60, y - 50], radius=6, fill=accent)
        for line in lines:
            w = d.textlength(line, font=font)
            d.text((cx - w / 2, y), line, font=font, fill=ink)
            y += lh
        d.text((cx, y + 46), "", font=_font_body(30), fill=ink)

    elif kind == "stat":
        big = _font_display(300)
        w = d.textlength(scene["text"], font=big)
        d.text((cx - w / 2, 780), scene["text"], font=big, fill=accent)
        sub_font = _font_semibold(40)
        sub_lines = wrap(d, scene.get("sub", ""), sub_font, 880)
        yy = 1140
        for line in sub_lines[:3]:
            draw_tracked(d, (0, yy), line, sub_font, ink, 2.6, anchor_center_x=cx)
            yy += 54
        d.rounded_rectangle([cx - 90, yy + 26, cx + 90, yy + 32], radius=3, fill=accent)

    elif kind == "song":
        label = _font_semibold(30)
        draw_tracked(d, (0, 640), "NOW PLAYING", label, accent, 6.0, anchor_center_x=cx)
        title_font = _font_serif(96, italic=True)
        lines = wrap(d, f"\u201c{scene['text']}\u201d", title_font, 900)
        if len(lines) > 3:
            title_font = _font_serif(78, italic=True)
            lines = wrap(d, f"\u201c{scene['text']}\u201d", title_font, 900)
        yy = 720
        for line in lines:
            w = d.textlength(line, font=title_font)
            d.text((cx - w / 2, yy), line, font=title_font, fill=ink)
            yy += int(title_font.size * 1.18)
        meta = _font_semibold(42)
        draw_tracked(d, (0, yy + 18), scene.get("sub", ""), meta, accent, 3.2, anchor_center_x=cx)
        note_font = _font_body(38)
        note_lines = wrap(d, scene.get("note", ""), note_font, 820)
        ny = yy + 118
        for line in note_lines[:3]:
            w = d.textlength(line, font=note_font)
            d.text((cx - w / 2, ny), line, font=note_font, fill=(ink[0], ink[1], ink[2], 220))
            ny += 48

    elif kind == "curiosity":
        draw_tracked(d, (0, 620), "THE PART NOBODY TELLS YOU", _font_semibold(30), accent, 5.0, anchor_center_x=cx)
        font, lines = fit_display(d, scene["text"], 900, 84, 54, 5)
        # serif reads more like a story hook
        sfont = _font_serif(66, italic=False)
        lines = wrap(d, scene["text"], sfont, 880)
        yy = 760
        for line in lines[:5]:
            w = d.textlength(line, font=sfont)
            d.text((cx - w / 2, yy), line, font=sfont, fill=ink)
            yy += int(sfont.size * 1.25)
        sub = wrap(d, scene.get("sub", ""), _font_semibold(34), 780)
        yy += 40
        for line in sub[:3]:
            draw_tracked(d, (0, yy), line.upper(), _font_semibold(28), accent, 2.6, anchor_center_x=cx)
            yy += 46

    elif kind == "cta":
        # comment bubble mock
        bx0, by0, bx1, by1 = 150, 676, W - 150, 1052
        _comment_bubble(d, (bx0, by0, bx1, by1), (252, 250, 246, 240), accent, 6)
        d.ellipse([bx0 + 58, by0 + 52, bx0 + 112, by0 + 106], fill=accent)
        d.text((bx0 + 130, by0 + 58), "Top comment", font=_font_semibold(38), fill=(26, 26, 32))
        d.rounded_rectangle([bx1 - 236, by0 + 54, bx1 - 58, by0 + 108], radius=27, fill=(232, 228, 220))
        draw_tracked(d, (bx1 - 210, by0 + 70), "PINNED", _font_semibold(24), (110, 104, 96), 3.0)

        inner_w = bx1 - bx0 - 124
        body_font = _font_serif(66)
        while body_font.size > 42 and d.textlength(scene["text"], font=body_font) > inner_w:
            body_font = _font_serif(body_font.size - 4)
        lines = wrap(d, scene["text"], body_font, inner_w)
        yy = by0 + 158
        for line in lines[:2]:
            d.text((bx0 + 62, yy), line, font=body_font, fill=(18, 18, 24))
            yy += int(body_font.size * 1.16)
        d.text((bx0 + 62, yy + 10), scene.get("sub", ""), font=_font_body(42), fill=(74, 74, 86))

        # small tag row inside the bubble
        tag_y = by1 - 84
        for i, label in enumerate(["STORY", "SONG", "PLAYLIST"]):
            tw = d.textlength(label, font=_font_semibold(24)) + 34
            tx = bx0 + 62 + i * 150
            d.rounded_rectangle([tx, tag_y, tx + tw, tag_y + 46], radius=23, fill=(236, 232, 224))
            d.text((tx + 17, tag_y + 10), label, font=_font_semibold(24), fill=(96, 92, 86))

        # the bubble tail already points at the CTA line below
        cta_font, cta_lines = fit_display(d, "READ IT IN THE FIRST COMMENT", 900, 76, 50, 2)
        yy = 1150
        for line in cta_lines:
            w = d.textlength(line, font=cta_font)
            d.text((cx - w / 2, yy), line, font=cta_font, fill=ink)
            yy += int(cta_font.size * 1.04)
        follow = _font_semibold(30)
        draw_tracked(d, (0, yy + 30), "FOLLOW FOR MORE LEGENDS", follow, accent, 4.2, anchor_center_x=cx)

    rgb = layer.convert("RGB")
    alpha = layer.getchannel("A")
    return rgb, alpha


def hud_layer(t: float, duration: float, scene: dict, artist: dict, style: dict, badge: str = "ON THIS DAY") -> tuple[Image.Image, Image.Image]:
    layer = _base_layer(style)
    d = ImageDraw.Draw(layer)
    accent = style["accent"]
    ink = style["ink"]

    # top badge
    font = _font_semibold(30)
    _draw_pill(d, W / 2, 196, badge, font, (10, 10, 14), accent, pad_x=30, pad_y=12, tracking=6.0)

    # progress bar
    bar_x0, bar_y, bar_w = 78, 300, W - 156
    d.rounded_rectangle([bar_x0, bar_y, bar_x0 + bar_w, bar_y + 6], radius=3, fill=(255, 255, 255, 46))
    p = min(1.0, max(0.0, t / duration))
    d.rounded_rectangle([bar_x0, bar_y, bar_x0 + bar_w * p, bar_y + 6], radius=3, fill=accent)

    # footer identity
    name_font = _font_semibold(34)
    draw_tracked(d, (0, 1444), artist["name"].upper(), name_font, ink, 5.0, anchor_center_x=W / 2)
    draw_tracked(d, (0, 1494), artist["genre"].upper(), _font_semibold(22), accent, 3.4, anchor_center_x=W / 2)

    # animated waveform
    bars = 34
    bw, gap = 9, 7
    total_w = bars * bw + (bars - 1) * gap
    x = (W - total_w) / 2
    base = 1624
    for i in range(bars):
        phase = t * 2.4 + i * 0.42
        amp = (0.35 + 0.65 * abs(math.sin(phase))) * (1 - abs(i - bars / 2) / (bars * 0.9))
        h = 14 + amp * 108
        alpha = 210 if i % 2 == 0 else 150
        d.rounded_rectangle([x, base - h / 2, x + bw, base + h / 2], radius=bw / 2, fill=(*accent, alpha))
        x += bw + gap

    return layer.convert("RGB"), layer.getchannel("A")


# --------------------------------------------------------------------------- #
# frame assembly                                                              #
# --------------------------------------------------------------------------- #
class Renderer:
    def __init__(self, project: dict, artist: dict, style_key: str = "noir", logo: str = ""):
        self.project = project
        self.artist = artist
        self.style = STYLES.get(style_key, STYLES["noir"])
        self.plan = project.get("video_plan") or {}
        self.scenes = self.plan.get("scenes") or []
        self.duration = float(self.plan.get("duration") or 24.0)
        self.fps = int(self.plan.get("fps") or FPS)

        src_path = project.get("banner_image") or ""
        if not src_path or not os.path.exists(src_path):
            fallback = os.path.join(ASSET_DIR, artist.get("cover") or "bg-stage.jpg")
            src_path = fallback
        base = Image.open(src_path).convert("RGB")
        self.src = _grade(_cover(base, int(W * SS), int(H * SS)), self.style)
        self.vignette = _vignette_overlay(self.style)
        self.bg = _page_bg(self.style)

        # text layers
        total = len(self.scenes) or 1
        self.text_layers = [
            scene_overlay(s, artist, self.style, i, total) for i, s in enumerate(self.scenes)
        ]
        self._wave_cache = None

    # -- motion ---------------------------------------------------------
    def _bg_frame(self, t: float, scene_index: int) -> Image.Image:
        s = min(max(scene_index, 0), max(0, len(self.scenes) - 1))
        local_start = self.scenes[s]["start"] if self.scenes else 0
        local_end = self.scenes[s]["end"] if self.scenes else self.duration
        span = max(0.001, local_end - local_start)
        p = min(1.0, max(0.0, (t - local_start) / span))
        # alternate zoom direction + drift per scene
        if s % 2 == 0:
            z = 1.05 + 0.10 * p
        else:
            z = 1.15 - 0.10 * p
        cw = int(self.src.width / z)
        ch = int(self.src.height / z)
        drift_x = 0.06 * math.sin(p * math.pi + s)
        drift_y = 0.045 * math.cos(p * math.pi * 0.8 + s * 0.7)
        cx = int((self.src.width - cw) * (0.5 + drift_x))
        cy = int((self.src.height - ch) * (0.42 + drift_y))
        cx = min(max(cx, 0), self.src.width - cw)
        cy = min(max(cy, 0), self.src.height - ch)
        crop = self.src.crop((cx, cy, cx + cw, cy + ch)).resize((W, H), Image.BILINEAR)
        return crop

    def scene_at(self, t: float) -> tuple[int, dict]:
        for i, s in enumerate(self.scenes):
            if s["start"] <= t < s["end"]:
                return i, s
        return (len(self.scenes) - 1 if self.scenes else 0), (self.scenes[-1] if self.scenes else {"kind": "hook", "text": ""})

    def frame(self, t: float) -> Image.Image:
        idx, scene = self.scene_at(t)
        img = self._bg_frame(t, idx)
        img.paste(self.vignette.convert("RGB"), (0, 0), self.vignette.getchannel("A"))

        # scene text with fade + slide
        rgb, alpha = self.text_layers[idx] if idx < len(self.text_layers) else (None, None)
        if rgb is not None:
            local = t - scene["start"]
            fade = min(1.0, max(0.0, local / 0.42))
            if fade < 1.0:
                a = alpha.point(lambda v, f=fade: int(v * f))
            else:
                a = alpha
            dy = int((1 - fade) * 54)
            img.paste(rgb, (0, dy), a)

        hud_rgb, hud_a = hud_layer(t, self.duration, scene, self.artist, self.style, self.plan.get("badge", "ON THIS DAY"))
        img.paste(hud_rgb, (0, 0), hud_a)
        return img

    # -- encode ---------------------------------------------------------
    def render(
        self,
        out_path: str,
        audio_path: str = "",
        poster_path: str = "",
        progress: Callable[[float, int, int], None] | None = None,
    ) -> dict:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        total_frames = int(round(self.duration * self.fps))

        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(self.fps),
            "-i", "-",
        ]
        use_audio = bool(audio_path and os.path.exists(audio_path))
        if use_audio:
            if not audio_path.lower().endswith(".wav"):
                cmd += ["-stream_loop", "-1"]
            cmd += ["-i", audio_path]
            audio_filter = (
                f"atrim=0:{self.duration:.3f},asetpts=N/SR/TB,"
                "afade=t=in:st=0:d=0.9,"
                f"afade=t=out:st={max(0.0, self.duration - 2.2):.3f}:d=2.2,"
                "volume=0.9,alimiter=limit=0.95"
            )
            cmd += ["-filter:a", audio_filter, "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]

        cmd += [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
            "-movflags", "+faststart", "-g", "60",
        ]
        if use_audio:
            cmd += ["-shortest"]
        cmd += [out_path]

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        assert proc.stdin is not None
        poster = None
        try:
            for i in range(total_frames):
                t = i / self.fps
                img = self.frame(t)
                if i == 12:
                    poster = img.copy()
                proc.stdin.write(img.tobytes())
                if progress and (i % 4 == 0 or i == total_frames - 1):
                    progress((i + 1) / total_frames, i + 1, total_frames)
        finally:
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass
            err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
            code = proc.wait()

        if code != 0:
            raise RuntimeError(f"ffmpeg failed ({code}): {err[-1500:]}")

        if poster_path:
            if poster is None:
                poster = self.frame(0)
            poster.convert("RGB").save(poster_path, quality=88, optimize=True)

        return {"path": out_path, "frames": total_frames, "duration": self.duration, "poster": poster_path}


def demo_render(project: dict, artist: dict, out: str, style: str = "noir", audio: str = "") -> dict:
    r = Renderer(project, artist, style)
    return r.render(out, audio_path=audio)


if __name__ == "__main__":
    import json
    import sys
    import time

    from library import get_artist
    from content import article_for, video_for
    from seed_artists import ARTISTS

    artist = get_artist("elvis-presley")
    event = {"kind": "birthday", "date": "2026-01-08", "date_label": "January 8", "year": 2026, "age": 91, "years": 0, "days_away": 0}
    article = article_for(artist, event, 3)
    plan = video_for(artist, event, article, 3)
    project = {
        "video_plan": plan,
        "banner_image": os.path.join(ASSET_DIR, "bg-stage.jpg"),
    }
    t0 = time.time()
    out = os.path.join(tempfile.gettempdir(), "demo-reel.mp4")
    res = demo_render(project, artist, out, "noir", os.path.join(DATA_DIR, "bed.wav"))
    print(res, f"{time.time() - t0:.1f}s", os.path.getsize(out) // 1024, "KB")
