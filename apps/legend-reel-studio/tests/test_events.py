from datetime import date

import library


def test_birthday_lands_on_exact_day():
    events = library.search_events(ref=date(2027, 1, 8), window=0, q="Elvis")
    kinds = {(e["artist_id"], e["kind"]) for e in events}
    assert ("elvis-presley", "birthday") in kinds
    bday = next(e for e in events if e["artist_id"] == "elvis-presley" and e["kind"] == "birthday")
    assert bday["age"] == 92  # born 1935
    assert bday["days_away"] == 0
    assert len(bday["artist"]["songs"]) == 3


def test_window_filters_out_far_events():
    events = library.search_events(ref=date(2026, 11, 4), window=0)
    assert all(abs(e["days_away"]) == 0 for e in events)
    wide = library.search_events(ref=date(2026, 11, 4), window=30)
    assert len(wide) >= len(events)


def test_events_sorted_today_first_then_nearest():
    events = library.search_events(ref=date(2026, 11, 4), window=30)
    keys = [(abs(e["days_away"]), e["days_away"] < 0) for e in events]
    assert keys == sorted(keys)


def test_search_matches_song_and_genre():
    elvis = library.search_events(ref=date(2027, 1, 8), window=3, q="can't help falling")
    assert elvis and all(e["artist_id"] == "elvis-presley" for e in elvis)

    country = library.search_events(ref=date(2026, 11, 4), window=365, q="country")
    assert country
    assert any(e["artist_id"] in {"johnny-cash", "kenny-rogers", "glen-campbell", "patsy-cline"} for e in country)


def test_kind_filter():
    events = library.search_events(ref=date(2026, 11, 4), window=365, kinds=["memorial"])
    assert events
    assert {e["kind"] for e in events} == {"memorial"}


def test_leap_day_occurrence_is_safe():
    # 29 February must never raise for non-leap years
    occurrences = library._occurrence(2, 29, date(2027, 1, 1))
    assert all(o.day == 29 and o.month == 2 for o in occurrences)
    assert 2028 in {o.year for o in occurrences}


def test_milestone_events_have_release_copy():
    events = library.search_events(ref=date(2026, 11, 3), window=0, kinds=["release"])
    single = next(e for e in events if e["artist_id"] == "whitney-houston")
    assert single["title"] == "'I Will Always Love You'"
    assert "single" in single["note"]
    assert single["years"] == 34


def test_artist_index_has_expected_shape():
    artists = library.artists_index()
    assert len(artists) >= 25
    for a in artists:
        assert a["birth"] and a["death"]
        assert len(a["songs"]) == 3
        assert a["songs"][0]["youtube"].startswith("https://www.youtube.com/")
