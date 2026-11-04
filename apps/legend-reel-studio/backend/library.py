"""Event discovery over the curated artist library."""

from __future__ import annotations

from datetime import date, timedelta

from seed_artists import ARTISTS, MILESTONES

ARTIST_BY_ID = {a["id"]: a for a in ARTISTS}
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _to_date(s: str) -> date:
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def _label(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}"


def _occurrence(month: int, day: int, ref: date, back: int = 1, forward: int = 1) -> list[date]:
    out = []
    for delta_y in range(-back, forward + 1):
        y = ref.year + delta_y
        try:
            out.append(date(y, month, day))
        except ValueError:  # 29 February
            continue
    return out


def _age_at_death(artist: dict) -> int:
    b, d = _to_date(artist["birth"]), _to_date(artist["death"])
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def _base_event(artist: dict, kind: str, occ: date, ref: date, **extra) -> dict:
    ev = {
        "id": f"{artist['id']}:{kind}:{occ.isoformat()}",
        "artist_id": artist["id"],
        "kind": kind,
        "date": occ.isoformat(),
        "date_label": _label(occ),
        "year": occ.year,
        "days_away": (occ - ref).days,
        "age_at_death": _age_at_death(artist),
    }
    ev.update(extra)
    return ev


def artist_events(artist: dict, ref: date, window: int) -> list[dict]:
    events: list[dict] = []
    b = _to_date(artist["birth"])
    d = _to_date(artist["death"])
    for occ in _occurrence(b.month, b.day, ref):
        away = (occ - ref).days
        if abs(away) <= window:
            age = occ.year - b.year
            events.append(
                _base_event(artist, "birthday", occ, ref, age=age, label_vi=f"Sinh nhật lần thứ {age}")
            )
    for occ in _occurrence(d.month, d.day, ref):
        away = (occ - ref).days
        if abs(away) <= window:
            years = occ.year - d.year
            events.append(
                _base_event(
                    artist, "memorial", occ, ref, years=years,
                    label_vi=f"{years} năm ngày mất",
                )
            )
    return events


def milestone_events(ref: date, window: int) -> list[dict]:
    events = []
    for m in MILESTONES:
        artist = ARTIST_BY_ID.get(m["artist_id"])
        if not artist:
            continue
        md = _to_date(m["date"])
        for occ in _occurrence(md.month, md.day, ref):
            away = (occ - ref).days
            if abs(away) <= window:
                years = occ.year - md.year
                if years <= 0:
                    continue
                ev = _base_event(artist, "release", occ, ref, title=m["subject"], note=m["note"])
                ev.update({"years": years, "label_vi": f"{years} năm: {m['subject']} {m['note']}"})
                events.append(ev)
    return events


def search_events(
    ref: date | None = None,
    window: int = 7,
    q: str = "",
    kinds: list[str] | None = None,
) -> list[dict]:
    ref = ref or date.today()
    kinds = kinds or []
    pool: list[dict] = []
    for artist in ARTISTS:
        pool.extend(artist_events(artist, ref, window))
    pool.extend(milestone_events(ref, window))

    def matches(ev: dict) -> bool:
        artist = ARTIST_BY_ID[ev["artist_id"]]
        if kinds and ev["kind"] not in kinds:
            return False
        if not q:
            return True
        needle = q.lower().strip()
        haystack = " ".join(
            [
                artist["name"],
                artist.get("aka", ""),
                artist["genre"],
                artist["era"],
                artist["hometown"],
                artist.get("legacy", ""),
                ev.get("title", ""),
                " ".join(s["title"] for s in artist["songs"]),
            ]
        ).lower()
        return needle in haystack

    events = [e for e in pool if matches(e)]
    events.sort(key=lambda e: (abs(e["days_away"]), e["days_away"] < 0, e["artist_id"]))
    for ev in events:
        ev["artist"] = _artist_card(ARTIST_BY_ID[ev["artist_id"]])
    return events


def _artist_card(artist: dict) -> dict:
    return {
        "id": artist["id"],
        "name": artist["name"],
        "aka": artist["aka"],
        "genre": artist["genre"],
        "era": artist["era"],
        "hometown": artist["hometown"],
        "birth": artist["birth"],
        "death": artist["death"],
        "wikipedia": artist["wikipedia"],
        "palette": artist["palette"],
        "cover": artist.get("cover", "bg-stage.jpg"),
        "songs": artist["songs"],
        "legacy": artist["legacy"],
        "facts": artist["facts"],
        "pronoun": artist.get("pronoun", "he"),
        "possessive": artist.get("possessive", "his"),
    }


def artists_index() -> list[dict]:
    return [_artist_card(a) for a in ARTISTS]


def get_artist(artist_id: str) -> dict | None:
    a = ARTIST_BY_ID.get(artist_id)
    return _artist_card(a) if a else None


def upcoming_summary(ref: date | None = None, window: int = 14) -> list[dict]:
    return search_events(ref=ref, window=window)[:8]
