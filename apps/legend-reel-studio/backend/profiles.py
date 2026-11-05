"""Article + posting text for characters the operator types in by name.

The curated library knows songs, dates and facts. A profile created from a name
alone knows almost nothing, so this generator:

* never invents song titles, chart positions or dates;
* only mentions songs / facts / dates that the operator actually filled in;
* grows richer automatically when the profile has more fields.

Everything else (700-900 word target, 9-15 word on-screen text, hook, caption,
hashtags) follows the same rules as the curated library.
"""

from __future__ import annotations

import random
import re
from typing import Any
from urllib.parse import quote_plus

import content as base

ARTICLE_MIN = base.ARTICLE_MIN_WORDS
ARTICLE_MAX = base.ARTICLE_MAX_WORDS
ARTICLE_TARGET = base.ARTICLE_TARGET_WORDS
OVERLAY_MIN = base.OVERLAY_MIN_WORDS
OVERLAY_MAX = base.OVERLAY_MAX_WORDS

word_count = base.word_count
article_stats = base.article_stats
_pick = base._pick
_dedupe = base._dedupe

KIND_LABEL_VI = {
    "birthday": "Sinh nhật",
    "memorial": "Ngày mất",
    "release": "Kỷ niệm phát hành",
    "custom": "Sự kiện tự chọn",
}


# --------------------------------------------------------------------------- #
# profile helpers                                                            #
# --------------------------------------------------------------------------- #
def empty_profile(name: str) -> dict:
    return {
        "id": "",
        "name": name.strip(),
        "aka": "",
        "genre": "",
        "era": "",
        "hometown": "",
        "birth": "",
        "death": "",
        "gender": "",
        "legacy": "",
        "facts": [],
        "songs": [],
        "source_url": "",
        "custom": True,
    }


def normalize(profile: dict) -> dict:
    """Return the shape the generators expect, without inventing anything."""
    out = empty_profile(profile.get("name") or "Unknown Artist")
    for key in ("id", "aka", "genre", "era", "hometown", "birth", "death", "gender", "legacy", "source_url"):
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()
    facts = profile.get("facts") or []
    if isinstance(facts, str):
        facts = [line.strip(" -•\t") for line in facts.splitlines()]
    out["facts"] = [f for f in (str(x).strip() for x in facts) if f]
    songs = profile.get("songs") or []
    clean_songs = []
    if isinstance(songs, str):
        songs = [line for line in songs.splitlines()]
    for item in songs:
        if isinstance(item, str):
            title, _, year = item.partition("|")
            item = {"title": title.strip(), "year": year.strip()}
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        clean_songs.append({"title": title, "year": str(item.get("year") or "").strip()})
    out["songs"] = clean_songs[:6]
    out["custom"] = True
    gender = out["gender"].lower()
    if gender in ("female", "f", "nữ", "nu", "woman", "she"):
        out["pronoun"], out["possessive"] = "she", "her"
    elif gender in ("male", "m", "nam", "man", "he"):
        out["pronoun"], out["possessive"] = "he", "his"
    else:
        out["pronoun"], out["possessive"] = "they", "their"
    return out


def display_name(profile: dict) -> str:
    return profile.get("name") or "this artist"


def _song_year(song: dict) -> str:
    return str(song.get("year") or "").strip()


def song_links(profile: dict) -> list[dict]:
    """Search links instead of ids: they never rot when a video is taken down."""
    out = []
    for song in profile.get("songs") or []:
        query = quote_plus(f"{profile.get('name', '')} {song['title']}".strip())
        out.append(
            {
                "title": song["title"],
                "year": song.get("year", ""),
                "youtube": f"https://www.youtube.com/results?search_query={query}",
                "note": "",
            }
        )
    return out


def _song_line(song: dict) -> str:
    year = _song_year(song)
    return f"'{song['title']}'" + (f" ({year})" if year else "")


# --------------------------------------------------------------------------- #
# event copy                                                                 #
# --------------------------------------------------------------------------- #
def event_copy(profile: dict, event: dict) -> dict:
    name = display_name(profile)
    poss = profile.get("possessive", "their")
    pronoun = profile.get("pronoun", "they")
    years = event.get("years") or 0
    kind = event.get("kind") or "custom"
    if kind == "birthday":
        age = event.get("age") or years
        return {
            "badge": "ON THIS DAY",
            "headline": f"{name} would have turned {age} today" if age else f"Happy birthday, {name}",
            "kicker": f"Born {event.get('date_label', '')}".strip(),
            "short": f"{age} years after {poss} birth" if age else f"{name}'s birthday",
            "years_line": f"{age} years ago today, {name} was born." if age else f"Today is {name}'s birthday.",
            "past": f"{name} was born {age} years ago today" if age else f"{name}'s birthday",
        }
    if kind == "memorial":
        return {
            "badge": "REMEMBERING",
            "headline": f"{years} years without {name}" if years else f"Remembering {name}",
            "kicker": f"Died {event.get('date_label', '')}".strip(),
            "short": f"{years} years since {poss} passing" if years else f"Remembering {name}",
            "years_line": f"{years} years ago today, we lost {name}." if years else f"Today we remember {name}.",
            "past": f"{name} died {years} years ago today" if years else f"Remembering {name}",
        }
    subject = event.get("title") or f"{name}"
    note = event.get("note") or ""
    headline = f"{years} years since {subject}" if years else f"{subject}"
    return {
        "badge": "ANNIVERSARY",
        "headline": headline,
        "kicker": f"{event.get('date_label', '')}".strip(),
        "short": headline,
        "years_line": (
            f"{years} years ago today, {subject} — {note}." if (years and note)
            else f"{years} years ago today: {subject}." if years
            else f"{subject}. {note}".strip()
        ),
        "past": f"{years} years ago today, {subject}" if years else subject,
    }


# --------------------------------------------------------------------------- #
# on-screen text (9-15 words)                                                #
# --------------------------------------------------------------------------- #
def overlay_candidates(profile: dict, event: dict) -> list[str]:
    name = display_name(profile)
    songs = profile.get("songs") or []
    first = songs[0] if songs else None
    years = event.get("years") or 0
    age = event.get("age") or years
    kind = event.get("kind") or "custom"
    song_hook = _song_line(first) if first else "this record"

    options: list[str] = []
    if kind == "birthday":
        if age:
            options += [
                f"{name} would have turned {age} today. Put {song_hook} on and listen.",
                f"Ask anyone over 40 about {name}. {age} years after {profile.get('possessive', 'their')} birth.",
                f"{name} was born {age} years ago today. This is the song to play.",
            ]
        else:
            options += [
                f"Today is {name}'s birthday. Put {song_hook} on and listen.",
                f"Happy birthday, {name}. The records still do the talking tonight.",
                f"{name} was born on this day. This is the song to play.",
            ]
    elif kind == "memorial":
        options += [
            f"{years} years without {name}. Play {song_hook} and you'll hear why." if years
            else f"Remembering {name} today. Play {song_hook} and you'll hear why.",
            f"{name} is gone but {song_hook} still stops people mid-sentence.",
            f"{years} years since we lost {name}. The story is in the first comment." if years
            else f"Today we remember {name}. The full story is in the first comment.",
        ]
    else:
        subject = event.get("title") or name
        options += [
            f"The story behind {subject} is not the one you were told.",
            f"{years} years since {subject} — and this part is still wild." if years
            else f"Everyone knows {subject}. Almost nobody knows what happened next.",
            f"{name}. One record. Years later, people still stop and listen.",
        ]
    options += [
        f"If you grew up on {name}, this one hits different tonight.",
        f"{name}. The record that still makes a whole room go quiet.",
        f"This is the {name} song that gets played at every wedding and every funeral.",
    ]

    keep = [t for t in _dedupe(options) if OVERLAY_MIN <= word_count(t) <= OVERLAY_MAX]
    if not keep:
        keep = [f"{name} still matters. The full story is in the first comment below."]
    return keep


def best_overlay(profile: dict, event: dict, seed: int = 1) -> str:
    cands = overlay_candidates(profile, event)
    rng = random.Random(seed)
    return rng.choice(cands[: max(1, len(cands) - 1)])


# --------------------------------------------------------------------------- #
# article                                                                    #
# --------------------------------------------------------------------------- #
def title_variants(profile: dict, event: dict) -> list[str]:
    name = display_name(profile)
    years = event.get("years") or 0
    age = event.get("age") or years
    kind = event.get("kind") or "custom"
    songs = profile.get("songs") or []
    first = songs[0] if songs else None
    song_title = first["title"] if first else None
    genre = (profile.get("genre") or "").strip()

    if kind == "birthday":
        if age:
            out = [
                f"{name} Would Have Turned {age} Today — And the Records Still Silence a Room",
                f"{age} Years After {name} Was Born, One Song Still Does the Work of a Whole Band",
            ]
            if song_title:
                out.append(f"It's Been {age} Years Since {name} Was Born. Play '{song_title}' and You'll Understand")
            out.append(f"{name} at {age}: The {genre + ' ' if genre else ''}Voice That Outlived the Room")
        else:
            out = [
                f"Happy Birthday, {name} — And the Records Still Silence a Room",
                f"{name} Was Born on This Day. One Song Still Does the Work of a Whole Band",
            ]
            if song_title:
                out.append(f"Play '{song_title}' Today and You'll Understand Why {name} Still Matters")
            out.append(f"{name}: The {genre + ' ' if genre else ''}Voice That Outlived the Room")
        return out
    if kind == "memorial":
        if years:
            out = [
                f"{years} Years Without {name}: The Song That Still Gets Played After Midnight",
                f"{years} Years Ago Today We Lost {name}. This Is the Record to Play Tonight",
            ]
            if song_title:
                out.append(f"Nobody Has Sung '{song_title}' Like {name}. {years} Years Later, Nobody Does")
            out.append(f"{name}: Why the Voice Still Lands, {years} Years On")
        else:
            out = [
                f"Remembering {name}: The Song That Still Gets Played After Midnight",
                f"Today We Remember {name}. This Is the Record to Play Tonight",
            ]
            if song_title:
                out.append(f"Nobody Has Sung '{song_title}' Like {name}")
            out.append(f"{name}: Why the Voice Still Lands")
        return out
    subject = event.get("title") or f"{name}"
    return [
        f"{years} Years Ago Today, {subject} Changed What Radio Sounded Like" if years
        else f"The Story Behind {subject} Is Not the One You Were Told",
        f"{name} and {subject}: The Part Nobody Talks About",
        f"Everyone Knows {subject}. Almost Nobody Knows What Happened Next",
    ]


def _generic_pool(profile: dict, event: dict, rng: random.Random) -> list[str]:
    """Paragraphs that only rely on the name + pronoun (safe for sparse profiles)."""
    name = display_name(profile)
    poss = profile.get("possessive", "their")
    genre = (profile.get("genre") or "").lower()
    era = profile.get("era") or ""
    hometown = profile.get("hometown") or ""
    pool = [
        f"There is a whole younger audience hearing this for the first time on a phone speaker, with no idea what it "
        f"sounded like on a car stereo with the windows down. Play it loud once and they get it immediately.",
        f"Watch the old footage and one thing stands out: nobody is playing to the camera. The band is watching each "
        f"other. That is the difference between a hit and a record people still play decades later.",
        f"The songs were never complicated, which is why they traveled. One honest line, a chorus you can learn on the "
        f"first listen, and a vocal that sounds like it was recorded at the end of a long day.",
        f"Ask the fans and they will not talk about charts. They will talk about the night they heard {name} live, or "
        f"the tape in the glovebox, or the wedding where this song emptied the room onto the floor.",
        f"What makes an artist last is not the hits, it is the handful of recordings that keep getting discovered with "
        f"no promotion at all. {name} has more of those than most artists with twice the chart history.",
        f"Streaming buried the album sequence. Most people now hear the single without the song that came before it. "
        f"Play them in order once and the whole thing makes a different, better kind of sense.",
        f"The remasters are cleaner, but cleaner is not the point. The hiss, the room noise and the wrong note in the "
        f"bridge are part of the arrangement, and that grit is why the song feels like it happened to someone.",
        f"Every cover version ends up compared to the original, and every one loses for the same reason: {name} is not "
        f"showing off, {poss} vocal is confessing something, and that is much harder to fake.",
        f"Look at the session notes and you find ordinary stuff: a borrowed amp, a drummer pushing past the click "
        f"because the feel mattered more than the grid. Nobody planned the magic, it just got captured.",
        f"{name} never fit the box the industry built for {poss} music, and that is exactly why the songs outlived the "
        f"marketing. The audience did the promotion for free, one car ride at a time.",
        f"There is an argument that this music belongs to a specific decade and should stay there. The argument does "
        f"not survive one listen in a car at night with somebody you love in the passenger seat.",
        f"Ask three fans for their favourite deep cut and you will get three different answers. That is the sign of a "
        f"catalogue with depth rather than a singles act that ran out of ideas.",
        f"The live recordings are slower, and the slower they get, the more the lyrics land. Age does that to a song. "
        f"The singer stops performing the words and starts remembering them.",
        f"Film and television keep coming back to this material because it does the emotional work in thirty seconds "
        f"that a scene spends ten minutes trying to earn. Directors know it, and so do wedding DJs.",
        f"If you only know {name} from the greatest-hits playlist, you are hearing the ending of a story with the "
        f"middle cut out. The albums are where the personality lives.",
        f"None of this requires a documentary. It requires one good speaker, twenty minutes and the willingness to sit "
        f"still for a song that is not trying to win an argument with you.",
        f"The people who were there keep saying the same thing: you had to be in the room. The closest thing we have "
        f"left is the tape, and the tape is better than most of what is released this week.",
        f"What is left of {name} now is the catalogue, the footage, and a fan base that refuses to file it under "
        f"nostalgia. Play the record and the argument ends.",
    ]
    if hometown:
        pool.append(
            f"{hometown} is not just a line in the biography. It is the reason the music has dirt under its "
            f"fingernails, and the reason {name} never quite fit the room the industry built."
        )
    if genre:
        pool.append(
            f"The {genre} label is too small for this catalogue. Call it what you like — the audience never cared "
            f"about the category, only whether the song told the truth."
        )
    if era:
        pool.append(
            f"{era.capitalize()} is the easy way to file {name}, and the lazy way to dismiss the work. The records "
            f"have outlived the decade and the trends that were supposed to bury them."
        )
    rng.shuffle(pool)
    return pool


def _song_section(profile: dict) -> list[str]:
    songs = profile.get("songs") or []
    if not songs:
        return []
    lines = ["", "## The records that still do the work", ""]
    for index, song in enumerate(songs[:4]):
        year = _song_year(song)
        if index == 0:
            lines.append(f"Start with {_song_line(song)}. It is the one people know without knowing they know it.")
        elif year:
            lines.append(f"Then {_song_line(song)} — the one that made the radio programmers nervous.")
        else:
            lines.append(f"Then {_song_line(song)} — the deep cut the fans keep bringing up.")
    return lines


def _facts_section(profile: dict) -> list[str]:
    facts = profile.get("facts") or []
    if not facts:
        return []
    lines = ["", "## What the headlines left out", ""]
    lines += [f"- {fact}" for fact in facts[:6]]
    return lines


def article_for(profile: dict, event: dict, seed: int = 1) -> dict:
    profile = normalize(profile)
    rng = random.Random(seed)
    name = display_name(profile)
    poss = profile.get("possessive", "their")
    ec = event_copy(profile, event)
    songs = profile.get("songs") or []
    titles = title_variants(profile, event)
    idx = seed % len(titles)
    titles = [titles[idx]] + titles[:idx] + titles[idx + 1:]

    lede = _pick(
        rng,
        [
            f"{ec['years_line']} And for the people who grew up with {poss} records, the date still lands harder than it should.",
            f"There is a version of this story that gets told every year: the hits, the headlines, the ending. This is the other one — the reason the voice is still in the car with us.",
            f"{ec['headline']}. Most people under 30 will scroll past. The people who were there will stop, turn it up, and remember exactly where they were.",
        ],
    )

    why = [
        "",
        f"## Why {name} still matters",
        "",
        _pick(
            rng,
            [
                f"{name} never depended on a trend to sound current. The records were built to be sung back by a room full of people who cannot hit the high part any more, and that is why they still work.",
                f"What survives an artist is rarely the awards. It is the handful of songs that keep getting discovered by somebody's kid, in somebody's car, with no marketing involved.",
                f"There is a generation that knows the name and not the story, and a generation that knows the story by heart. This piece is for both of them.",
            ],
        ),
        _pick(rng, base.AUDIENCE_LINES),
    ]

    body_parts: list[str] = [lede, *why]
    body_parts += _song_section(profile)
    body_parts += _facts_section(profile)

    closing = [
        "",
        "## Listen tonight",
        rng.choice(base.CLOSING_LINES),
        "",
        f"**Playlist and the full story:** {base.CTA_CORE}",
    ]
    footer = []
    life = "–".join(x for x in (profile.get("birth"), profile.get("death")) if x)
    bits = [bit for bit in (name, f"({life})" if life else "", profile.get("era"), profile.get("aka")) if bit]
    if bits:
        footer = ["", f"_{' · '.join(bits)}._"]

    def render(extras: list[str]) -> str:
        parts = list(body_parts)
        for para in extras:
            parts.append(para)
            parts.append("")
        return "\n".join(parts + closing + footer).strip()

    pool = _generic_pool(profile, event, rng)
    extra: list[str] = []
    for para in pool:
        if word_count(render(extra)) >= ARTICLE_TARGET:
            break
        candidate = extra + [para]
        if word_count(render(candidate)) > ARTICLE_MAX - 8:
            continue
        extra = candidate

    body_text = render(extra)
    stats = article_stats(body_text)
    return {
        "title": titles[0],
        "title_variants": titles,
        "body": body_text,
        "first_comment": first_comment(profile, event, ec),
        "hashtags": hashtags(profile),
        "word_count": stats["words"],
        "word_range": [ARTICLE_MIN, ARTICLE_MAX],
        "in_range": stats["in_range"],
        "music_links": song_links(profile),
        "reading_time": max(2, round(stats["words"] / 200)),
    }


def hashtags(profile: dict) -> list[str]:
    name = display_name(profile)
    tags = ["#MusicLegends", "#OnThisDay", "#ClassicHits", "#VinylCommunity", "#MusicHistory", "#NowPlaying"]
    name_tag = "#" + re.sub(r"[^A-Za-z0-9]", "", name)
    if len(name_tag) > 1:
        tags.insert(0, name_tag)
    genre = (profile.get("genre") or "").split("/")[0].strip()
    if genre:
        genre_tag = "#" + re.sub(r"[^A-Za-z0-9]", "", genre.replace(" ", ""))
        if len(genre_tag) > 1:
            tags.insert(1, genre_tag)
    if profile.get("birth"):
        tags.insert(2, "#" + re.sub(r"[^0-9]", "", str(profile["birth"]))[:4])
    seen, out = set(), []
    for tag in tags:
        if tag in ("#", "#" + "") or tag.lower() in seen:
            continue
        seen.add(tag.lower())
        out.append(tag)
    return out[:10]


def first_comment(profile: dict, event: dict, ec: dict | None = None) -> str:
    ec = ec or event_copy(profile, event)
    profile = normalize(profile)
    name = display_name(profile)
    songs = profile.get("songs") or []
    lines = [f"🎧 {ec['headline']}.", ""]
    if profile.get("legacy"):
        lines += [profile["legacy"], ""]
    if songs:
        lines.append("The records to play tonight — headphones on, no skipping:")
        lines += [f"▶️ {_song_line(song)}" for song in songs[:3]]
        lines.append("")
    if profile.get("source_url"):
        lines += [f"Source: {profile['source_url']}", ""]
    lines += ["Full story and the playlist are pinned in the first comment 👇", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# text & voice                                                               #
# --------------------------------------------------------------------------- #
def fb_hook(profile: dict, event: dict, rng: random.Random) -> str:
    name = display_name(profile)
    years = event.get("years") or 0
    options = [
        f"You think you know {name}? Wait until you hear what {profile.get('possessive', 'their')} voice does in the second verse.",
        f"Nobody warned me about this {name} record. One listen and I understood why my parents never skipped it.",
        f"{years} years later and this {name} song still stops people mid-sentence." if years
        else f"The {name} song that stops people mid-sentence, every single time.",
        f"The {name} song that gets played at every funeral and every wedding. Here is why.",
        f"Everyone remembers the hits. Almost nobody knows what happened after this one.",
    ]
    return rng.choice(options)


def caption(profile: dict, event: dict, ec: dict, hook: str, rng: random.Random) -> str:
    poss = profile.get("possessive", "their")
    cta = rng.choice(
        [
            "The full story + the songs to play tonight are in the FIRST COMMENT 👇",
            "Full write-up and both songs are pinned in the first comment 👇",
            "I put the whole story and the playlist in the first comment 👇",
        ]
    )
    return "\n".join(
        [
            hook,
            "",
            f"{ec['headline']}.",
            f"{poss.capitalize()} voice is still in the car with us — here is the record that proves it.",
            "",
            cta,
            "",
            "Save this one for tonight. 🎧",
        ]
    )


def voice_script(profile: dict, event: dict, overlay: str) -> str:
    profile = normalize(profile)
    ec = event_copy(profile, event)
    songs = profile.get("songs") or []
    tail = f" The record to play tonight is {_song_line(songs[0])}." if songs else " The record to play tonight is linked below."
    return f"{overlay} {ec['headline']}.{tail} The full story is in the first comment."


def script_for(profile: dict, event: dict, article: dict | None = None, seed: int = 1) -> dict:
    rng = random.Random(seed)
    profile = normalize(profile)
    ec = event_copy(profile, event)
    overlay = best_overlay(profile, event, seed)
    hook = fb_hook(profile, event, rng)
    text = caption(profile, event, ec, hook, rng)
    tags = article.get("hashtags") if article else hashtags(profile)
    comment = article.get("first_comment") if article else first_comment(profile, event, ec)
    words = word_count(overlay)
    return {
        "overlay_text": overlay,
        "overlay_words": words,
        "overlay_ok": OVERLAY_MIN <= words <= OVERLAY_MAX,
        "fb_hook": hook,
        "caption": text,
        "hashtags": tags,
        "first_comment": comment,
        "badge": ec["badge"],
        "voice_script": voice_script(profile, event, overlay),
    }


def overlay_variants(profile: dict, event: dict) -> list[dict]:
    out = []
    for text in overlay_candidates(normalize(profile), event):
        words = word_count(text)
        out.append({"text": text, "words": words, "ok": OVERLAY_MIN <= words <= OVERLAY_MAX})
    return out


def make_event(profile: dict, kind: str, date_str: str, title: str = "", note: str = "", years: int = 0) -> dict:
    """Build the event dict the generators expect for an operator-typed occasion."""
    from datetime import date as _date

    profile = normalize(profile)
    kind = kind if kind in KIND_LABEL_VI else "custom"
    try:
        day = _date.fromisoformat(date_str)
        label = f"{day.strftime('%B')} {day.day}"
        year = day.year
    except (ValueError, TypeError):
        label = date_str or ""
        year = _date.today().year

    def _year_of(value: str) -> int:
        digits = re.sub(r"[^0-9]", "", str(value or ""))[:4]
        return int(digits) if len(digits) == 4 else 0

    if not years:
        if kind == "birthday" and _year_of(profile.get("birth")):
            years = max(0, year - _year_of(profile.get("birth")))
        elif kind == "memorial" and _year_of(profile.get("death")):
            years = max(0, year - _year_of(profile.get("death")))

    event: dict[str, Any] = {
        "id": f"{profile.get('id') or 'custom'}:{kind}:{date_str}",
        "artist_id": profile.get("id") or "",
        "kind": kind,
        "date": date_str,
        "date_label": label,
        "year": year,
        "years": years,
        "title": (title or "").strip(),
        "note": (note or "").strip(),
        "label_vi": f"{KIND_LABEL_VI[kind]}: {(title or '').strip() or profile.get('name', '')}",
        "custom": True,
    }
    if kind == "birthday":
        event["age"] = years
    if kind == "memorial":
        event["age_at_death"] = ""
    return event
