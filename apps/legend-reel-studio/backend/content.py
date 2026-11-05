"""Deterministic copy engine: article (700-900 words), on-screen text, hook, caption, pin comment.

No external LLM is required (works offline). Every generator is seeded so a
project always regenerates the same copy unless the seed changes.
"""

from __future__ import annotations

import random
import re
from typing import Any

CTA_CORE = "Full story and the song are in the first comment 👇"
ARTICLE_MIN_WORDS = 700
ARTICLE_MAX_WORDS = 900
ARTICLE_TARGET_WORDS = 800
OVERLAY_MIN_WORDS = 9
OVERLAY_MAX_WORDS = 15

CLOSING_LINES = [
    "Put the record on, turn the lights down, and listen to it the way it was meant to be heard: all the way through, without skipping the long ending.",
    "Play it on something with a real speaker. This is not headphone music, it is kitchen-table music.",
    "If you only listen to one thing tonight, make it the version that was recorded live, when the room was still deciding whether to sing along.",
    "Find the live cut, not the single edit. The difference is the whole reason people still argue about this artist.",
    "Turn it up one notch past comfortable. That is how the record was mixed, and that is how it still works.",
]

CONTEXT_LINES = [
    "Radio in those years was a closed door, and this was the sound of somebody leaning on it until it opened.",
    "The charts were built for safe songs. This was not safe, which is exactly why it is still on playlists fifty years later.",
    "Every generation thinks it invented the idea of a song that tells the truth about a room. This record was already doing it.",
    "The production sounds simple now. It was not simple then; it was a band and a producer deciding to leave the mistakes in.",
    "Record stores used to sell this album to people who could not afford a second copy, so they taped it for friends instead.",
]

AUDIENCE_LINES = [
    "Ask anyone who was a teenager when this came out where they were the first time they heard it, and you will get a room, a car, a kitchen, a name.",
    "The people who grew up with these records are between 30 and 60 now. They are not discovering this music, they are handing it forward.",
    "For a whole generation these songs are not nostalgia. They are the soundtrack of a first car, a first dance, a last drive home.",
    "There is a reason this music survives the algorithm: it was written to be remembered, not to be scrolled past.",
    "The children of the people who bought these records are finding them on their own now, and the songs hold up, which is the hardest test of all.",
]

RADIO_LINES = [
    "You can still find the original single, the live take and the radio edit, and they do not sound like the same song.",
    "The version most people know is the single. The version that matters is the one recorded late, when nobody was trying to be perfect.",
    "Session musicians on these records were never credited on the sleeve. Half the sound you remember belongs to them.",
    "The mix was built for AM radio, which is why it still cuts through a phone speaker in a way newer recordings do not.",
    "There is a mono mix, a stereo mix and a live mix, and fans have been arguing about the right one for decades.",
]


def word_count(text: str) -> int:
    """Count words the same way the UI does (tokens containing a letter/digit)."""
    return len([w for w in re.split(r"\s+", (text or "").strip()) if re.search(r"[A-Za-z0-9']", w)])


def article_stats(body: str) -> dict[str, Any]:
    words = word_count(body)
    return {
        "words": words,
        "min": ARTICLE_MIN_WORDS,
        "max": ARTICLE_MAX_WORDS,
        "in_range": ARTICLE_MIN_WORDS <= words <= ARTICLE_MAX_WORDS,
    }


def _pick(rng: random.Random, options: list[str]) -> str:
    return rng.choice(options)


def _cap(text: str) -> str:
    """Uppercase the first letter, leaving the rest of the string intact."""
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
    return text


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for i in items:
        k = i.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(i.strip())
    return out


def possessive(artist: dict) -> str:
    return artist.get("possessive", "his")


def subject_pronoun(artist: dict) -> str:
    return artist.get("pronoun", "he")


def event_copy(artist: dict, event: dict) -> dict:
    """English labels for the event, used across article / on-screen text / comment."""
    name = artist["name"]
    pronoun = artist.get("pronoun", "he")
    poss = artist.get("possessive", "his")
    years = event.get("years") or 0
    if event["kind"] == "birthday":
        age = event.get("age") or 0
        return {
            "badge": "ON THIS DAY",
            "headline": f"{name} would have turned {age} today",
            "kicker": f"Born {event['date_label']} · {artist['hometown']}",
            "short": f"{age} years after {poss} birth",
            "years_line": f"{age} years ago today, {name} was born in {artist['hometown']}.",
            "past": f"{name} was born {age} years ago today",
            "pronoun": pronoun,
        }
    if event["kind"] == "memorial":
        return {
            "badge": "REMEMBERING",
            "headline": f"{years} years without {name}",
            "kicker": f"Died {event['date_label']} · age {event.get('age_at_death', '')}",
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
        "kicker": f"{event['date_label']} · {note}" if note else f"Released {event['date_label']}",
        "short": f"{years} years since {subject}",
        "years_line": f"{years} years ago today, {subject} — {note}." if note else f"{years} years ago today: {subject}.",
        "past": f"{years} years ago today, {subject}",
        "pronoun": pronoun,
    }


# --------------------------------------------------------------------------- #
# On-screen text: the 9-15 word line the operator burns into the reel.        #
# --------------------------------------------------------------------------- #
def overlay_candidates(artist: dict, event: dict) -> list[str]:
    name = artist["name"]
    poss = artist.get("possessive", "his")
    songs = artist["songs"]
    s1 = songs[0]
    age = event.get("age") or 0
    years = event.get("years") or 0

    options: dict[str, list[str]] = {}
    if event["kind"] == "birthday":
        options = {
            "specific": [
                f"{name} would have turned {age} today. This one song still stops people cold.",
                f"Ask anyone over 40 where they were when {name} sang this. {age} today.",
                f"{age} years after {poss} birth, this {s1['year']} recording still breaks the room.",
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

    keep = [t for t in _dedupe(options["specific"]) if OVERLAY_MIN_WORDS <= word_count(t) <= OVERLAY_MAX_WORDS]
    if len(keep) < 2:
        keep += [t for t in _dedupe(options["generic"]) if OVERLAY_MIN_WORDS <= word_count(t) <= OVERLAY_MAX_WORDS]
    return _dedupe(keep)


def overlay_variants(artist: dict, event: dict) -> list[dict]:
    out = []
    for text in overlay_candidates(artist, event):
        wc = word_count(text)
        out.append({"text": text, "words": wc, "ok": OVERLAY_MIN_WORDS <= wc <= OVERLAY_MAX_WORDS})
    return out


def best_overlay(artist: dict, event: dict, seed: int = 1) -> str:
    cands = overlay_candidates(artist, event)
    if not cands:
        cands = [f"The story behind this {artist['name']} song is in the first comment below."]
    rng = random.Random(seed)
    pool = cands[: max(1, len(cands) - 2)] if len(cands) > 3 else cands
    return rng.choice(pool)


def normalize_overlay(text: str, artist: dict, event: dict) -> str:
    """Fallback text when the operator's line falls outside 9-15 words."""
    if OVERLAY_MIN_WORDS <= word_count(text) <= OVERLAY_MAX_WORDS:
        return text
    return best_overlay(artist, event, seed=1)


# --------------------------------------------------------------------------- #
# Article: 700-900 English words, title + body + music links.                 #
# --------------------------------------------------------------------------- #
def _title_variants(artist: dict, event: dict) -> list[str]:
    name = artist["name"]
    songs = artist["songs"]
    s1 = songs[0]
    age = event.get("age") or 0
    years = event.get("years") or 0
    genre = artist["genre"]

    if event["kind"] == "birthday":
        return [
            f"{name} Would Have Turned {age} Today — And This {s1['year']} Recording Still Silences a Room",
            f"{age} Years After {possessive(artist)} Birth, One {name} Song Still Does the Work of a Whole Band",
            f"It's Been {age} Years Since {name} Was Born. Play '{s1['title']}' and You'll Understand",
            f"{name} at {age}: The {genre} Song That Outlived Everybody in the Room",
        ]
    if event["kind"] == "memorial":
        return [
            f"{years} Years Without {name}: The Song That Still Gets Played After Midnight",
            f"The Last Thing {name} Ever Recorded — And Why It's Still Hard to Finish",
            f"Nobody Has Sung '{s1['title']}' Like {name}. {years} Years Later, Nobody Does",
            f"{years} Years Ago Today We Lost {name}. This Is the Record to Play Tonight",
        ]
    return [
        f"{years} Years Ago Today, {event['title']} Changed What Radio Sounded Like",
        f"The Story Behind {event['title']} Is Not the One the Label Told You",
        f"{years} Years Since {event['title']} — And One Detail Still Doesn't Add Up",
    ]


def _filler_pool(artist: dict, event: dict, s1: dict, s2: dict, s3: dict, rng: random.Random) -> list[str]:
    """Extra paragraphs used to land the article inside 700-900 words."""
    name = artist["name"]
    poss = possessive(artist)
    genre = artist["genre"].lower()
    hometown = artist["hometown"]
    era = artist["era"]
    pool: list[str] = []

    for fact in artist.get("facts", []):
        pool.append(
            f"That part of the story gets skipped: {fact} It is the kind of detail that never made the TV version, "
            f"and it is the reason older fans still argue about {name} with the volume up."
        )

    pool += [
        f"There is a whole younger audience now hearing this for the first time on a phone speaker, with no idea what "
        f"the record sounded like on a car stereo with the windows down. Give them the {era} version and they get it.",
        f"{hometown} is not just a line in the biography. It is the reason the {genre} on these records has dirt under "
        f"its fingernails, and it is the reason {name} never quite fit the room the industry built for {poss} music.",
        f"The songwriting was never complicated, which is why it traveled. Three chords, one honest line, and a vocal "
        f"that sounds like it was recorded at the end of a long day instead of the start of a marketing campaign.",
        f"Watch the old footage and one thing stands out: nobody in the band is looking at the camera. They are looking "
        f"at each other. That is the difference between a hit and a record people still play forty years later.",
        f"Every cover version of '{s1['title']}' ends up compared to the original, and every one of them loses for the "
        f"same reason. The vocal is not showing off, it is confessing something, and that is much harder to fake.",
        f"'{s2['title']}' was the one that made the radio programmers nervous and the audience loud. It is also the one "
        f"that still sounds best in a room full of people who know every word and cannot hit the high part anymore.",
        f"The business side of this career is a story of contracts nobody would sign today and royalties that went "
        f"somewhere other than the artist. The music survived all of it, which says something about the music.",
        f"There is a reason this material keeps coming back in films and television: it does the emotional work in "
        f"thirty seconds that a scene spends ten minutes trying to earn. Directors know it, and so do wedding DJs.",
        f"Fans of {name} tend to own the same three records and a story about the night they saw {poss} band live. "
        f"Ask them about that night and you will get a better history of the era than any documentary has managed.",
        f"The remasters are cleaner, but cleaner is not the point. The point is that the hiss and the room noise were "
        f"part of the arrangement, and a little of that grit is what makes the songs feel like they happened to someone.",
        f"Dig into the session notes and you find the ordinary stuff of great records: wrong keys, borrowed amps, a "
        f"drummer playing past the click because the feel mattered more than the grid. Nobody planned the magic.",
        f"For a younger listener, the entry point is usually a sample or a cover rather than the original. Follow that "
        f"thread back far enough and you end up here, with the source recording that still sounds better than the copy.",
        f"The live versions from the later tours are slower, and the slower they get, the more the lyrics land. Age does "
        f"that to a song. The singer stops performing the words and starts remembering them.",
        f"There is an argument that this music belongs to a specific decade and should stay there. The argument does "
        f"not survive one listen in a car at night with somebody you love in the passenger seat.",
        f"Streaming buried the album sequence, so most people now hear the single without the song that came before it. "
        f"Play them in order once and the record makes a different, better kind of sense.",
        f"What makes a legend is not the hits, it is the handful of recordings that keep getting discovered without any "
        f"promotion at all. {name} has more of those than most artists with twice the chart history.",
    ]
    rng.shuffle(pool)
    return pool


def article_for(artist: dict, event: dict, seed: int = 1) -> dict:
    rng = random.Random(seed)
    name = artist["name"]
    poss = possessive(artist)
    pronoun = subject_pronoun(artist)
    songs = artist["songs"]
    s1 = songs[0]
    s2 = songs[1] if len(songs) > 1 else songs[0]
    s3 = songs[2] if len(songs) > 2 else songs[0]
    ec = event_copy(artist, event)
    years = event.get("years") or 0
    titles = _title_variants(artist, event)
    idx = seed % len(titles)
    titles = [titles[idx]] + titles[:idx] + titles[idx + 1:]

    lede = _pick(
        rng,
        [
            f"{ec['years_line']} And for the people who grew up with {poss} records, the date still lands harder than it should.",
            f"There is a version of this story that gets told every year: the hits, the headlines, the tragedy. This is the other one — the reason {poss} voice is still in the car with us.",
            f"{ec['headline']}. Most people under 30 will scroll past. The people who were there will stop, turn it up, and remember exactly where they were.",
        ],
    )

    intro = [
        lede,
        "",
        f"## Why {name} still matters in {event.get('year', '')}",
        _pick(
            rng,
            [
                f"{name} came out of {artist['hometown']}, and the {artist['genre'].lower()} sound {pronoun} made never really left. {artist['legacy']}",
                f"The story starts in {artist['hometown']}. {artist['legacy']}",
            ],
        ),
        _pick(rng, AUDIENCE_LINES),
        "",
        f"## The songs that still do the work",
        f"Start with **'{s1['title']}'** ({s1['year']}). {s1['note']} Then **'{s2['title']}'** ({s2['year']}). {s2['note']}",
        "",
        f"- '{s1['title']}' ({s1['year']}) — {s1['youtube']}",
        f"- '{s2['title']}' ({s2['year']}) — {s2['youtube']}",
        f"- '{s3['title']}' ({s3['year']}) — {s3['youtube']}",
        "",
        f"And then there is '{s3['title']}' ({s3['year']}). {s3['note']} It is the one that gets requested at the end of the night, when nobody is trying to be cool any more.",
        "",
        f"## What the headlines left out",
        *[f"- {fact}" for fact in artist["facts"]],
        "",
    ]

    closing = [
        "",
        "## Listen tonight",
        rng.choice(CLOSING_LINES),
        "",
        f"**Playlist and the full story:** {CTA_CORE}",
        "",
        f"_{name} ({artist['birth'][:4]}–{artist['death'][:4]}). {artist['era']}. {artist['aka']}._",
    ]

    middle = [
        "",
        f"## Why people are still listening in {event.get('year', '')}",
        _pick(
            rng,
            [
                f"Most of the audience that finds this reel is between 30 and 60. They are not discovering {name} for the first time. They are rediscovering what the record felt like before the world got loud.",
                f"Ask anyone who was there: {name} was never background music. The records were events. Reels like this one are how a new generation gets handed the tape.",
            ],
        ),
        _pick(rng, CONTEXT_LINES),
        "",
    ]

    pool = _filler_pool(artist, event, s1, s2, s3, rng)
    extra: list[str] = []

    def render(extras: list[str]) -> str:
        parts: list[str] = []
        for block in intro + middle:
            parts.append(block)
        for para in extras:
            parts.append(para)
            parts.append("")
        parts.extend(closing)
        return "\n".join(parts).strip()

    for para in pool:
        if word_count(render(extra)) >= ARTICLE_TARGET_WORDS:
            break
        candidate = extra + [para]
        if word_count(render(candidate)) > ARTICLE_MAX_WORDS - 8:
            continue
        extra = candidate

    body_text = render(extra)
    stats = article_stats(body_text)
    first_comment = _first_comment(artist, event, ec, s1, s2)
    tags = _hashtags(artist)
    return {
        "title": titles[0],
        "title_variants": titles,
        "body": body_text,
        "first_comment": first_comment,
        "hashtags": tags,
        "word_count": stats["words"],
        "word_range": [ARTICLE_MIN_WORDS, ARTICLE_MAX_WORDS],
        "in_range": stats["in_range"],
        "music_links": artist["songs"],
        "reading_time": max(2, round(stats["words"] / 200)),
    }


def _first_comment(artist: dict, event: dict, ec: dict, s1: dict, s2: dict) -> str:
    lines = [
        f"🎧 {ec['headline']}.",
        "",
        f"{artist['legacy']}",
        "",
        "The two records to play tonight — headphones on, no skipping:",
        f"▶️ {s1['title']} ({s1['year']}): {s1['youtube']}",
        f"▶️ {s2['title']} ({s2['year']}): {s2['youtube']}",
        "",
        "Full story and the playlist are pinned in the first comment 👇",
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
# Text & Voice package: on-screen text, hook, caption, pin comment, narration #
# --------------------------------------------------------------------------- #
def _fb_hook(artist: dict, event: dict, rng: random.Random) -> str:
    name = artist["name"]
    years = event.get("years") or 0
    options = [
        f"You think you know {name}? The last thing {possessive(artist)} people did was play this song.",
        f"Nobody warned me about this {name} recording. One listen and I understood why my parents never skipped it.",
        f"{years} years later and this {name} song still stops people mid-sentence. Wait for the second verse.",
        "My dad played this on repeat and I never asked why. Now I know.",
        f"This is the {name} song that gets played at every funeral and every wedding. Here's why.",
        "Everyone remembers the hits. Almost nobody knows what happened after this one.",
    ]
    return rng.choice(options)


def _caption(artist: dict, event: dict, ec: dict, s1: dict, s2: dict, hook: str, rng: random.Random) -> str:
    poss = possessive(artist)
    cta_variants = [
        "The full story + the two songs to play tonight are in the FIRST COMMENT 👇",
        "Full write-up and both songs are pinned in the first comment 👇",
        "I put the whole story and the playlist in the first comment 👇",
    ]
    lines = [
        hook,
        "",
        f"{ec['headline']}.",
        f"{poss.capitalize()} voice is still in the car with us — here's the record that proves it.",
        "",
        rng.choice(cta_variants),
        "",
        "Save this one for tonight. 🎧",
    ]
    return "\n".join(lines)


def voice_script_for(artist: dict, event: dict, overlay: str, s1: dict) -> str:
    """A ~35 word spoken line the operator can run through TTS as the reel voiceover."""
    name = artist["name"]
    ec = event_copy(artist, event)
    return (
        f"{overlay} {ec['headline']}. The record to play tonight is '{s1['title']}' from {s1['year']}. "
        f"The full story is in the first comment."
    )


def script_for(artist: dict, event: dict, article: dict | None = None, seed: int = 1) -> dict:
    rng = random.Random(seed)
    songs = artist["songs"]
    s1 = songs[0]
    s2 = songs[1] if len(songs) > 1 else songs[0]
    ec = event_copy(artist, event)
    overlay = best_overlay(artist, event, seed)
    hook = _fb_hook(artist, event, rng)
    caption = _caption(artist, event, ec, s1, s2, hook, rng)
    tags = article.get("hashtags") if article else _hashtags(artist)
    first_comment = article.get("first_comment") if article else _first_comment(artist, event, ec, s1, s2)
    overlay_words = word_count(overlay)
    return {
        "overlay_text": overlay,
        "overlay_words": overlay_words,
        "overlay_ok": OVERLAY_MIN_WORDS <= overlay_words <= OVERLAY_MAX_WORDS,
        "fb_hook": hook,
        "caption": caption,
        "hashtags": tags,
        "first_comment": first_comment,
        "badge": ec["badge"],
        "voice_script": voice_script_for(artist, event, overlay, s1),
    }


def engagement_checks(project: dict) -> list[dict]:
    """Soft, editable quality gates shown in the UI (not hard blockers)."""
    overlay = project.get("video_overlay_text") or ""
    caption = project.get("caption") or ""
    title = project.get("article_title") or ""
    stats = article_stats(project.get("article_body") or "")
    images = project.get("images") or []
    voice = project.get("voice") or {}
    return [
        {
            "id": "article_words",
            "label": "Bài báo 700–900 từ",
            "ok": stats["in_range"],
            "detail": f"{stats['words']} từ",
        },
        {
            "id": "title_len",
            "label": "Tiêu đề dưới 100 ký tự",
            "ok": 0 < len(title) <= 100,
            "detail": f"{len(title)} ký tự",
        },
        {
            "id": "overlay_words",
            "label": "Chữ trên video 9–15 từ",
            "ok": OVERLAY_MIN_WORDS <= word_count(overlay) <= OVERLAY_MAX_WORDS,
            "detail": f"{word_count(overlay)} từ",
        },
        {
            "id": "comment_cta",
            "label": "Có CTA kéo xuống comment",
            "ok": "comment" in (caption + " " + overlay + " " + (project.get("fb_hook") or "")).lower(),
            "detail": "",
        },
        {
            "id": "images",
            "label": "Đủ 20 ảnh nghệ sĩ",
            "ok": len(images) >= 20,
            "detail": f"{len(images)}/20 ảnh",
        },
        {
            "id": "banner",
            "label": "Đã chọn ảnh banner",
            "ok": bool(project.get("banner_url") or project.get("banner_image")),
            "detail": "",
        },
        {
            "id": "hashtags",
            "label": "Có hashtag",
            "ok": bool((project.get("hashtags") or "").strip()),
            "detail": "",
        },
        {
            "id": "voice",
            "label": "Đã tạo voice",
            "ok": bool(voice.get("url")),
            "detail": voice.get("engine", ""),
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
    links = project.get("music_links") or []
    link_lines = [f"- {s.get('title', '')} ({s.get('year', '')}): {s.get('youtube', '')}" for s in links]
    images = project.get("images") or []
    attribution = [
        f"- {img.get('title') or img.get('id')} — {img.get('license') or 'không rõ giấy phép'}"
        + (f" — {img.get('attribution')}" if img.get("attribution") else "")
        for img in images
    ]
    parts = [
        f"# {project.get('article_title', '')}",
        "",
        project.get("article_body", ""),
        "",
        "---",
        "",
        "## Music links",
        "",
        *link_lines,
        "",
        "## On-screen text",
        "",
        project.get("video_overlay_text", ""),
        "",
        "## Facebook hook",
        "",
        project.get("fb_hook", ""),
        "",
        "## Caption",
        "",
        project.get("caption", ""),
        "",
        "## Hashtags",
        "",
        project.get("hashtags", ""),
        "",
        "## First comment (pin this)",
        "",
        project.get("first_comment", ""),
    ]
    if attribution:
        parts += ["", "## Image credits", "", *attribution]
    voice = project.get("voice") or {}
    if voice.get("url"):
        parts += ["", f"Voiceover: {voice.get('voice', '')} ({voice.get('engine', '')}) — {voice.get('url', '')}"]
    remake = project.get("remake") or {}
    if remake:
        brief = remake.get("brief") or {}
        parts += [
            "",
            "## Remake brief (from a competitor reel)",
            "",
            f"- Nguồn: {remake.get('platform_label') or remake.get('platform', '')} — {remake.get('url', '')}",
            f"- Điểm nổi bật: {remake.get('score', '')}/100 ({remake.get('tier', '')})",
            f"- Định dạng: {remake.get('format_label') or remake.get('format', '')}",
            f"- Hook gốc: {remake.get('hook', '')}",
            "",
            "### Cấu trúc cần giữ",
            "",
            *[f"- {beat}" for beat in brief.get("beats", [])],
            "",
            "### Nguyên tắc làm lại",
            "",
            *[f"- {rule}" for rule in brief.get("remake_rules", [])],
        ]
    return "\n".join(parts)
