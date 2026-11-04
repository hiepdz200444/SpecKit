"""Deterministic copy engine: article, on-video text, FB hook, caption, first comment.

No external LLM is required (works offline). Every generator is seeded so a
project always regenerates the same copy unless the seed changes.
"""

from __future__ import annotations

import random
import re
from typing import Any

CTA_CORE = "Full story and the song are in the first comment 👇"

CLOSING_LINES = [
    "Put the record on, turn the lights down, and listen to it the way it was meant to be heard: all the way through, without skipping the long ending.",
    "Play it on something with a real speaker. This is not headphone music, it is kitchen-table music.",
    "If you only listen to one thing tonight, make it the version that was recorded live, when the room was still deciding whether to sing along.",
    "Find the live cut, not the single edit. The difference is the whole reason people still argue about this artist.",
    "Turn it up one notch past comfortable. That is how the record was mixed, and that is how it still works.",
]


def word_count(text: str) -> int:
    return len([ w for w in re.split(r"\s+", (text or "").strip()) if re.search(r"[A-Za-z0-9']", w)])


def _pick(rng: random.Random, options: list[str]) -> str:
    return rng.choice(options)


def _cap(text: str) -> str:
    """Uppercase the first letter, leaving the rest of the string intact."""
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
    return text


def _subject(artist: dict) -> str:
    return artist["name"]


def _last_memorial_year(artist: dict) -> int:
    return int(artist["death"][:4])


def event_copy(artist: dict, event: dict) -> dict:
    """English labels for the event, used across article / video / comment."""
    name = artist["name"]
    pronoun = artist.get("pronoun", "he")
    poss = artist.get("possessive", "his")
    years = event.get("years") or 0
    if event["kind"] == "birthday":
        age = event.get("age") or 0
        return {
            "badge": "ON THIS DAY",
            "headline": f"{name} would have turned {age} today",
            "kicker": f"Born {event['date_label']} \u00b7 {artist['hometown']}",
            "short": f"{age} years after {poss} birth",
            "years_line": f"{age} years ago today, {name} was born in {artist['hometown']}.",
            "past": f"{name} was born {age} years ago today",
            "pronoun": pronoun,
        }
    if event["kind"] == "memorial":
        return {
            "badge": "REMEMBERING",
            "headline": f"{years} years without {name}",
            "kicker": f"Died {event['date_label']} \u00b7 age {event.get('age_at_death', '')}",
            "short": f"{years} years since {poss} passing",
            "years_line": f"{years} years ago today, we lost {name}. {pronoun.capitalize()} was {event.get('age_at_death', '')}.",
            "past": f"{name} died {years} years ago today",
            "pronoun": pronoun,
        }
    note = event.get("note", "")
    subject = event.get("title", "")
    return {
        "badge": "ANNIVERSARY",
        "headline": f"{years} years since {subject}",
        "kicker": f"{event['date_label']} \u00b7 {note}" if note else f"Released {event['date_label']}",
        "short": f"{years} years since {subject}",
        "years_line": f"{years} years ago today, {subject} \u2014 {note}." if note else f"{years} years ago today: {subject}.",
        "past": f"{years} years ago today, {subject}",
        "pronoun": pronoun,
    }


# --------------------------------------------------------------------------- #
# Overlay text: the 9-15 word line burned onto the video.                     #
# --------------------------------------------------------------------------- #
def overlay_candidates(artist: dict, event: dict) -> list[str]:
    name = artist["name"]
    poss = artist.get("possessive", "his")
    pronoun = artist.get("pronoun", "he")
    songs = artist["songs"]
    s1, s2 = songs[0], songs[1] if len(songs) > 1 else songs[0]
    age = event.get("age") or 0
    years = event.get("years") or 0

    options: dict[str, list[str]] = {}
    if event["kind"] == "birthday":
        options = {
            "specific": [
                f"{name} would have turned {age} today. This one song still stops people cold.",
                f"Ask anyone over 40 where they were when {name} sang this. {age} today.",
                f"{age} years after {poss} birth, this {s1['year']} recording still breaks the room.",
                f"Only real {artist['genre']} fans know the story behind this {s1['year']} take.",
                f"{name} was born {age} years ago today. Listen to this and you'll get it.",
                f"{name} at {age}: the {s1['year']} take that still makes grown fans go quiet.",
            ],
            "generic": [
                f"{name}. One song. {age} years later, people still stop and listen.",
                f"If you grew up on {name}, this {s1['year']} recording will hit different tonight.",
            ],
        }
    elif event["kind"] == "memorial":
        options = {
            "specific": [
                f"{years} years without {name}. Put this song on and you'll hear why.",
                f"Nobody has sung '{s1['title']}' like {name} since. {years} years without that voice.",
                f"{years} years ago today, {name} was gone. This song still answers the phone.",
                f"{years} years since we lost {name}. The story is in the first comment.",
                f"{name} is gone {years} years now. This recording still does not feel old.",
            ],
            "generic": [
                f"{name}. One song. {years} years later, people still stop and listen.",
                f"If you grew up on {name}, this {s1['year']} recording will hit different tonight.",
            ],
        }
    else:
        subject = event.get("title", "")
        options = {
            "specific": [
                f"The story behind {subject} is not the one the label told you.",
                f"{years} years since {subject} — and this part is still wild.",
                f"{years} years ago, {subject} landed. One decision changed the whole record.",
                f"Everyone knows {subject}. Almost nobody knows what happened next.",
                f"{subject} turned {years} this week. The detail fans still argue about is this.",
            ],
            "generic": [
                f"{name}. One song. {years} years later, people still stop and listen.",
                f"If you grew up on {name}, this {s1['year']} recording will hit different tonight.",
            ],
        }

    keep = [t for t in _dedupe(options["specific"]) if 9 <= word_count(t) <= 15]
    if len(keep) < 2:
        keep += [t for t in _dedupe(options["generic"]) if 9 <= word_count(t) <= 15]
    return _dedupe(keep)


def overlay_variants(artist: dict, event: dict) -> list[dict]:
    out = []
    for text in overlay_candidates(artist, event):
        out.append({"text": text, "words": word_count(text), "ok": 9 <= word_count(text) <= 15})
    return out


def best_overlay(artist: dict, event: dict, seed: int = 1) -> str:
    cands = overlay_candidates(artist, event)
    if not cands:
        # absolute fallback, guaranteed 9-15 words
        cands = [f"The story behind this {artist['name']} song is in the first comment below."]
    rng = random.Random(seed)
    # prefer the first (event-specific) candidates
    pool = cands[: max(1, len(cands) - 2)] if len(cands) > 3 else cands
    return rng.choice(pool)


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for i in items:
        k = i.strip().lower()
        if k not in seen:
            seen.add(k)
            out.append(i.strip())
    return out


# --------------------------------------------------------------------------- #
# Article                                                                      #
# --------------------------------------------------------------------------- #
def _title_variants(artist: dict, event: dict) -> list[str]:
    name = artist["name"]
    songs = artist["songs"]
    s1, s2 = songs[0], songs[1] if len(songs) > 1 else songs[0]
    age = event.get("age") or 0
    years = event.get("years") or 0
    genre = artist["genre"]

    if event["kind"] == "birthday":
        return [
            f"{name} Would Have Turned {age} Today \u2014 And This {s1['year']} Recording Still Silences a Room",
            f"{age} Years After {possessive(artist)} Birth, One {name} Song Still Does the Work of a Whole Band",
            f"It's Been {age} Years Since {name} Was Born. Play '{s1['title']}' and You'll Understand",
            f"{name} at {age}: The {genre} Song That Outlived Everybody in the Room",
        ]
    if event["kind"] == "memorial":
        return [
            f"{years} Years Without {name}: The Song That Still Gets Played After Midnight",
            f"The Last Thing {name} Ever Recorded \u2014 And Why It's Still Hard to Finish",
            f"Nobody Has Sung '{s1['title']}' Like {name}. {years} Years Later, Nobody Does",
            f"{years} Years Ago Today We Lost {name}. This Is the Record to Play Tonight",
        ]
    return [
        f"{years} Years Ago Today, {event['title']} Changed What Radio Sounded Like",
        f"The Story Behind {event['title']} Is Not the One the Label Told You",
        f"{years} Years Since {event['title']} \u2014 And One Detail Still Doesn't Add Up",
    ]


def possessive(artist: dict) -> str:
    return artist.get("possessive", "his")


def article_for(artist: dict, event: dict, seed: int = 1) -> dict:
    rng = random.Random(seed)
    name = artist["name"]
    poss = possessive(artist)
    pronoun = artist.get("pronoun", "he")
    songs = artist["songs"]
    s1 = songs[0]
    s2 = songs[1] if len(songs) > 1 else songs[0]
    s3 = songs[2] if len(songs) > 2 else songs[0]
    ec = event_copy(artist, event)
    age = event.get("age") or 0
    years = event.get("years") or 0
    titles = _title_variants(artist, event)
    idx = seed % len(titles)
    titles = [titles[idx]] + titles[:idx] + titles[idx + 1:]

    lede = _pick(
        rng,
        [
            f"{ec['years_line']} And for the people who grew up with {poss} records, the date still lands harder than it should.",
            f"There is a version of this story that gets told every year: the hits, the headlines, the tragedy. This is the other one \u2014 the reason {poss} voice is still in the car with us.",
            f"{ec['headline']}. Most people under 30 will scroll past. The people who were there will stop, turn it up, and remember exactly where they were.",
        ],
    )

    body: list[str] = []
    body.append(lede)
    body.append("")

    body.append(f"## Why {name} still matters in {event.get('year', '')}")
    body.append(
        _pick(
            rng,
            [
                f"{name} came out of {artist['hometown']}, and the {artist['genre'].lower()} sound {pronoun} made never really left. {artist['legacy']}",
                f"The story starts in {artist['hometown']}. {artist['legacy']}",
            ],
        )
    )
    body.append(
        f"That is the part the streaming numbers miss. For a whole generation, these records are not nostalgia \u2014 they are the soundtrack of a first car, a first dance, a last drive home."
    )
    body.append("")

    body.append("## The songs that still do the work")
    body.append(
        f"Start with **'{s1['title']}'** ({s1['year']}). {s1['note']} Then **'{s2['title']}'** ({s2['year']}). {s2['note']}"
    )
    body.append("")
    body.append(f"- '{s1['title']}' ({s1['year']}) \u2014 {s1['youtube']}")
    body.append(f"- '{s2['title']}' ({s2['year']}) \u2014 {s2['youtube']}")
    body.append(f"- '{s3['title']}' ({s3['year']}) \u2014 {s3['youtube']}")
    body.append("")
    body.append(
        f"And then there is '{s3['title']}' ({s3['year']}). {s3['note']} It is the one that gets requested at the end of the night, when nobody is trying to be cool any more."
    )
    body.append("")

    body.append("## What the headlines left out")
    for fact in artist["facts"]:
        body.append(f"- {fact}")
    body.append("")

    body.append("## Why people are still listening in " + str(event.get("year", "")))
    body.append(
        _pick(
            rng,
            [
                f"Most of the audience that finds this reel is between 30 and 60. They are not discovering {name} for the first time. They are rediscovering what the record felt like before the world got loud.",
                f"Ask anyone who was there: {name} was never background music. The records were events. Reels like this one are how a new generation gets handed the tape.",
            ],
        )
    )
    body.append(
        f"There is also something else happening. The children of the people who bought these records are now finding them on their own \u2014 and the songs hold up, which is the hardest test of all."
    )
    body.append("")

    body.append("## Listen tonight")
    body.append(rng.choice(CLOSING_LINES))
    body.append("")
    body.append(f"**Playlist and the full story:** {CTA_CORE}")
    body.append("")
    body.append(
        f"_{name} ({artist['birth'][:4]}\u2013{artist['death'][:4]}). {artist['era']}. {artist['aka']}._"
    )
    body_text = "\n".join(body).strip()

    first_comment = _first_comment(artist, event, ec, s1, s2)
    tags = _hashtags(artist)
    return {
        "title": titles[0],
        "title_variants": titles,
        "dek": f"{ec['headline']}. The story, the records, and the reason {poss} voice still shows up in your car.",
        "body": body_text,
        "first_comment": first_comment,
        "hashtags": tags,
        "word_count": len(body_text.split()),
        "reading_time": max(2, round(len(body_text.split()) / 200)),
    }


def _first_comment(artist: dict, event: dict, ec: dict, s1: dict, s2: dict) -> str:
    name = artist["name"]
    lines = [
        f"\U0001F3A7 {ec['headline']}.",
        "",
        f"{artist['legacy']}",
        "",
        f"The two records to play tonight \u2014 headphones on, no skipping:",
        f"\u25B6\uFE0F {s1['title']} ({s1['year']}): {s1['youtube']}",
        f"\u25B6\uFE0F {s2['title']} ({s2['year']}): {s2['youtube']}",
        "",
        f"Full story and the playlist are pinned in the first comment \U0001F447",
        "",
    ]
    return "\n".join(lines)


def _hashtags(artist: dict) -> list[str]:
    base = [
        "#MusicLegends",
        "#OnThisDay",
        "#ClassicHits",
        "#VinylCommunity",
        "#MusicHistory",
        "#RetroMusic",
        "#NowPlaying",
    ]
    name_tag = "#" + re.sub(r"[^A-Za-z0-9]", "", artist["name"])
    genre_tag = "#" + re.sub(r"[^A-Za-z0-9]", "", artist["genre"].split("/")[0].strip().replace(" ", ""))
    out = [name_tag, genre_tag, "#" + artist["birth"][:4]] + base
    seen, tags = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower())
            tags.append(t)
    return tags[:10]


# --------------------------------------------------------------------------- #
# Video plan                                                                  #
# --------------------------------------------------------------------------- #
def video_for(artist: dict, event: dict, article: dict | None = None, seed: int = 1) -> dict:
    rng = random.Random(seed)
    name = artist["name"]
    poss = possessive(artist)
    pronoun = artist.get("pronoun", "he")
    songs = artist["songs"]
    s1, s2 = songs[0], songs[1] if len(songs) > 1 else songs[0]
    age = event.get("age") or 0
    years = event.get("years") or 0
    ec = event_copy(artist, event)

    overlay = best_overlay(artist, event, seed)

    if event["kind"] == "birthday":
        middle_head = f"{age}"
        middle_sub = f"YEARS AGO TODAY, {name.upper()} WAS BORN IN {artist['hometown'].upper()}"
        curiosity = _pick(
            rng,
            [
                "Everyone remembers the voice. Almost nobody knows the rest of the story.",
                "You have heard this song a hundred times. You have never heard this part.",
                "The story behind this recording is longer than the song itself.",
            ],
        )
    elif event["kind"] == "memorial":
        middle_head = f"{years}"
        middle_sub = f"YEARS WITHOUT {name.upper()}"
        curiosity = _pick(
            rng,
            [
                "Everyone remembers how the story ended. Almost nobody remembers this.",
                f"The songs are still everywhere. The story behind them usually is not.",
                f"You know the voice. You probably do not know what it cost {pronoun}.",
            ],
        )
    else:
        middle_head = f"{years}"
        middle_sub = f"YEARS SINCE {event['title'].upper()}"
        curiosity = _pick(
            rng,
            [
                "Everyone knows this record. Almost nobody knows the fight behind it.",
                "You have heard it a thousand times. The story is the part you missed.",
                "The song is famous. The night it was made is not.",
            ],
        )

    scenes = [
        {
            "id": "hook",
            "start": 0.0,
            "end": 3.6,
            "kind": "hook",
            "text": overlay,
            "label": "Hook (chữ trên video)",
        },
        {
            "id": "event",
            "start": 3.6,
            "end": 8.4,
            "kind": "stat",
            "text": middle_head,
            "sub": middle_sub,
            "label": "Sự kiện",
        },
        {
            "id": "song",
            "start": 8.4,
            "end": 13.8,
            "kind": "song",
            "text": s1["title"],
            "sub": f"{s1['year']} \u00b7 {name}",
            "note": s1["note"],
            "label": "Bài nhạc",
        },
        {
            "id": "curiosity",
            "start": 13.8,
            "end": 19.4,
            "kind": "curiosity",
            "text": curiosity,
            "sub": "The full story is pinned in the first comment.",
            "label": "Gây tò mò",
        },
        {
            "id": "cta",
            "start": 19.4,
            "end": 24.0,
            "kind": "cta",
            "text": "Full story + the song",
            "sub": "in the first comment",
            "label": "Kéo xuống comment",
        },
    ]

    hook = _fb_hook(artist, event, s1, rng)
    caption = _caption(artist, event, ec, s1, s2, hook, rng)
    return {
        "badge": ec["badge"],
        "overlay_text": overlay,
        "overlay_words": word_count(overlay),
        "duration": 24.0,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "scenes": scenes,
        "fb_hook": hook,
        "caption": caption,
        "hashtags": article.get("hashtags") if article else _hashtags(artist),
        "first_comment": article.get("first_comment") if article else _first_comment(artist, event, ec, s1, s2),
        "progress_cue": True,
    }


def _fb_hook(artist: dict, event: dict, s1: dict, rng: random.Random) -> str:
    name = artist["name"]
    years = event.get("years") or 0
    options = [
        f"You think you know {name}? The last thing {possessive(artist)} people did was play this song.",
        f"Nobody warned me about this {name} recording. One listen and I understood why my parents never skipped it.",
        f"{years} years later and this {name} song still stops people mid-sentence. Wait for the second verse.",
        f"My dad played this on repeat and I never asked why. Now I know.",
        f"This is the {name} song that gets played at every funeral and every wedding. Here's why.",
        f"Everyone remembers the hits. Almost nobody knows what happened after this one.",
    ]
    return rng.choice(options)


def _caption(artist: dict, event: dict, ec: dict, s1: dict, s2: dict, hook: str, rng: random.Random) -> str:
    name = artist["name"]
    poss = possessive(artist)
    cta_variants = [
        "The full story + the two songs to play tonight are in the FIRST COMMENT \U0001F447",
        "Full write-up and both songs are pinned in the first comment \U0001F447",
        "I put the whole story and the playlist in the first comment \U0001F447",
    ]
    lines = [
        hook,
        "",
        f"{ec['headline']}.",
        f"{poss.capitalize()} voice is still in the car with us \u2014 here's the record that proves it.",
        "",
        rng.choice(cta_variants),
        "",
        f"Save this one for tonight. \U0001F3A7",
    ]
    return "\n".join(lines)


def engagement_checks(project: dict) -> list[dict]:
    """Soft, editable quality gates shown in the UI (not hard blockers)."""
    overlay = project.get("video_overlay_text") or ""
    wc = word_count(overlay)
    caption = project.get("caption") or ""
    title = project.get("article_title") or ""
    return [
        {
            "id": "overlay_words",
            "label": "Chữ trên video 9-15 từ",
            "ok": 9 <= wc <= 15,
            "detail": f"{wc} từ",
        },
        {
            "id": "comment_cta",
            "label": "Có CTA kéo xuống comment",
            "ok": "comment" in (caption + " " + overlay + " " + (project.get("fb_hook") or "")).lower(),
            "detail": "",
        },
        {
            "id": "title_len",
            "label": "Tiêu đề dưới 100 ký tự",
            "ok": 0 < len(title) <= 100,
            "detail": f"{len(title)} ký tự",
        },
        {
            "id": "hashtags",
            "label": "Có hashtag",
            "ok": bool((project.get("hashtags") or "").strip()),
            "detail": "",
        },
        {
            "id": "audio",
            "label": "Có nhạc nền",
            "ok": bool(project.get("audio_choice")),
            "detail": project.get("audio_choice") or "",
        },
    ]


def build_package(project: dict, artist: dict, event: dict) -> dict[str, Any]:
    """Everything the operator needs to publish, in one payload."""
    return {
        "project": project,
        "artist": artist,
        "event": event,
        "article_markdown": _article_markdown(project, artist),
        "caption_full": (project.get("caption") or "") + "\n\n" + (project.get("hashtags") or ""),
    }


def _article_markdown(project: dict, artist: dict) -> str:
    parts = [
        f"# {project.get('article_title', '')}",
        "",
        f"*{project.get('article_dek', '')}*",
        "",
        project.get("article_body", ""),
        "",
        "---",
        f"Banner: {project.get('banner_image', '') or '(chưa có ảnh)'}",
        "",
        "## First comment (pin this)",
        "",
        project.get("first_comment", ""),
    ]
    return "\n".join(parts)
