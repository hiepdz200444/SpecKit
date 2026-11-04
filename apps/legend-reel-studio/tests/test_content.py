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


def test_article_lands_inside_700_900_words_for_every_artist():
    counts = []
    for artist in library.artists_index():
        ev = _event(artist["id"], "birthday")
        for seed in (1, 5, 17):
            article = content.article_for(artist, ev, seed=seed)
            counts.append(article["word_count"])
            assert 700 <= article["word_count"] <= 900, (artist["id"], seed, article["word_count"])
            assert article["in_range"] is True
            assert content.article_stats(article["body"])["in_range"] is True
    assert counts


def test_article_has_every_publishing_field():
    artist = library.get_artist("elvis-presley")
    ev = _event("elvis-presley", "birthday")
    article = content.article_for(artist, ev, seed=3)
    assert article["title"] and len(article["title"]) <= 120
    assert len(article["title_variants"]) >= 3
    assert article["body"].count("https://www.youtube.com/") == 3
    assert "first comment" in article["first_comment"].lower()
    assert len(article["hashtags"]) >= 8
    assert len(article["music_links"]) == 3
    assert article["word_range"] == [700, 900]
    # deterministic for a given seed
    assert content.article_for(artist, ev, seed=3)["body"] == article["body"]


def test_article_stats_flags_out_of_range_bodies():
    short = content.article_stats("only a handful of words here")
    assert short["words"] == 6 and short["in_range"] is False
    long_body = " ".join(["word"] * 950)
    assert content.article_stats(long_body)["in_range"] is False
    ok_body = " ".join(["word"] * 800)
    stats = content.article_stats(ok_body)
    assert stats["in_range"] is True
    assert stats["min"] == 700 and stats["max"] == 900


def test_article_grammar_uses_object_pronouns_correctly():
    for artist_id in ("whitney-houston", "elvis-presley", "prince", "tina-turner"):
        artist = library.get_artist(artist_id)
        ev = _event(artist_id, "memorial")
        for seed in (1, 2, 3, 4, 5):
            body = content.article_for(artist, ev, seed=seed)["body"].lower()
            assert "with she " not in body
            assert "with he " not in body


def test_script_has_text_and_voice_blocks_without_video_plan():
    artist = library.get_artist("freddie-mercury")
    ev = _event("freddie-mercury", "memorial")
    article = content.article_for(artist, ev, seed=2)
    plan = content.script_for(artist, ev, article, seed=2)

    assert "scenes" not in plan
    assert "duration" not in plan
    assert 9 <= plan["overlay_words"] <= 15
    assert plan["overlay_ok"] is True
    assert plan["fb_hook"]
    assert "comment" in plan["caption"].lower()
    assert plan["hashtags"]
    assert "first comment" in plan["first_comment"].lower()
    assert 25 <= content.word_count(plan["voice_script"]) <= 60


def test_normalize_overlay_falls_back_to_a_valid_line():
    artist = library.get_artist("elvis-presley")
    ev = _event("elvis-presley", "birthday")
    assert content.normalize_overlay("too short", artist, ev) != "too short"
    assert 9 <= content.word_count(content.normalize_overlay("too short", artist, ev)) <= 15


def test_checks_flag_bad_copy():
    project = {
        "video_overlay_text": "one two three",
        "caption": "no call to action here",
        "article_title": "ok title",
        "article_body": "tiny body",
        "hashtags": "#music",
        "images": [],
    }
    checks = {c["id"]: c for c in content.engagement_checks(project)}
    assert checks["overlay_words"]["ok"] is False
    assert checks["article_words"]["ok"] is False
    assert checks["comment_cta"]["ok"] is False
    assert checks["images"]["ok"] is False
    assert checks["banner"]["ok"] is False
    assert checks["voice"]["ok"] is False

    project["video_overlay_text"] = "This is a nine word line that runs to fifteen words total"
    project["caption"] = "Full story in the first comment"
    project["article_body"] = " ".join(["word"] * 800)
    project["images"] = [{"id": f"i{i}"} for i in range(20)]
    project["banner_url"] = "/media/images/x/1.jpg"
    project["voice"] = {"url": "/media/voice/x.mp3", "engine": "edge-tts"}
    checks = {c["id"]: c for c in content.engagement_checks(project)}
    assert all(c["ok"] for c in checks.values()), checks


def test_word_count_handles_punctuation_and_contractions():
    assert content.word_count("Don't stop me now, baby!") == 5
    assert content.word_count("  ") == 0
