from datetime import date

import content
import library


def _event(artist_id: str, kind: str, ref: date = date(2026, 11, 4)):
    for ev in library.search_events(ref=ref, window=400):
        if ev["artist_id"] == artist_id and ev["kind"] == kind:
            return ev
    raise AssertionError(f"missing event {artist_id}/{kind}")


def test_overlay_candidates_always_9_to_15_words():
    for artist in library.artists_index():
        for kind in ("birthday", "memorial"):
            ev = {
                "kind": kind,
                "date": "2026-01-08",
                "date_label": "January 8",
                "years": 12,
                "age": 70,
                "year": 2026,
            }
            options = content.overlay_candidates(artist, ev)
            assert options, f"no overlay options for {artist['id']}/{kind}"
            for text in options:
                assert 9 <= content.word_count(text) <= 15, text


def test_overlay_for_release_mentions_subject():
    ev = _event("whitney-houston", "release", date(2026, 11, 3))
    options = content.overlay_candidates(library.get_artist("whitney-houston"), ev)
    assert any("I Will Always Love You" in o for o in options)


def test_article_has_every_publishing_field():
    artist = library.get_artist("elvis-presley")
    ev = _event("elvis-presley", "birthday")
    article = content.article_for(artist, ev, seed=3)
    assert article["title"] and len(article["title"]) <= 120
    assert len(article["title_variants"]) >= 3
    assert article["word_count"] > 300
    assert article["body"].count("https://www.youtube.com/") == 3
    assert "first comment" in article["first_comment"].lower()
    assert len(article["hashtags"]) >= 8
    # deterministic for a given seed
    assert content.article_for(artist, ev, seed=3)["body"] == article["body"]


def test_article_grammar_uses_object_pronouns_correctly():
    for artist_id in ("whitney-houston", "elvis-presley", "prince", "tina-turner"):
        artist = library.get_artist(artist_id)
        ev = _event(artist_id, "memorial")
        for seed in (1, 2, 3, 4, 5):
            body = content.article_for(artist, ev, seed=seed)["body"].lower()
            assert "with she " not in body
            assert "with he " not in body


def test_video_plan_structure_and_copy():
    artist = library.get_artist("freddie-mercury")
    ev = _event("freddie-mercury", "memorial")
    article = content.article_for(artist, ev, seed=2)
    plan = content.video_for(artist, ev, article, seed=2)

    assert [s["kind"] for s in plan["scenes"]] == ["hook", "stat", "song", "curiosity", "cta"]
    assert plan["scenes"][0]["start"] == 0
    assert plan["scenes"][-1]["end"] == plan["duration"]
    for a, b in zip(plan["scenes"], plan["scenes"][1:]):
        assert a["end"] == b["start"]

    assert 9 <= plan["overlay_words"] <= 15
    assert plan["scenes"][0]["text"] == plan["overlay_text"]
    assert "comment" in plan["caption"].lower()
    assert plan["hashtags"]


def test_checks_flag_bad_overlay():
    project = {
        "video_overlay_text": "one two three",
        "caption": "no call to action here",
        "article_title": "ok title",
        "hashtags": "#music",
        "audio_choice": "bed",
    }
    checks = {c["id"]: c for c in content.engagement_checks(project)}
    assert checks["overlay_words"]["ok"] is False
    assert checks["comment_cta"]["ok"] is False

    project["video_overlay_text"] = "This is a nine word line that runs to fifteen words total"
    project["caption"] = "Full story in the first comment"
    checks = {c["id"]: c for c in content.engagement_checks(project)}
    assert checks["overlay_words"]["ok"] is True
    assert checks["comment_cta"]["ok"] is True


def test_word_count_handles_punctuation_and_contractions():
    assert content.word_count("Don't stop me now, baby!") == 5
    assert content.word_count("  ") == 0
