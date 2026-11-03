from nerdlore import analysis
from nerdlore.data import load_export
from nerdlore.youtube import VideoStats

STATS = {  # made-up counts
    "aaaaaaaaaaa": VideoStats("aaaaaaaaaaa", True, 20_000, "2012-05-01"),
    "bbbbbbbbbbb": VideoStats("bbbbbbbbbbb", True, 20_000_000, "2014-09-30"),
    "ccccccccccc": VideoStats("ccccccccccc", True, 19_000, "2012-01-15"),
    "eeeeeeeeeee": VideoStats("eeeeeeeeeee", True, 5),
    "fffffffffff": VideoStats("fffffffffff", False, None),
}


def _talks(export_zip, min_recs=5, hide_news=True):
    ds = load_export(export_zip)
    return ds, analysis.filter_videos(ds.videos, analysis.TALK_TYPES, min_recs, hide_news)


def test_filter_keeps_talks_and_lectures_only(export_zip):
    _, df = _talks(export_zip)
    assert set(df["vid"]) == {"aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"}  # no music, no news, no 2-rec video


def test_filter_can_show_news(export_zip):
    _, df = _talks(export_zip, hide_news=False)
    assert "eeeeeeeeeee" in set(df["vid"])


def test_views_are_passed_through_unchanged(export_zip):
    _, df = _talks(export_zip)
    out = analysis.attach_views(df, STATS)
    assert dict(zip(out["vid"], out["views"])) == {"aaaaaaaaaaa": 20_000, "bbbbbbbbbbb": 20_000_000,
                                                   "ccccccccccc": 19_000}


def test_unavailable_videos_are_dropped(export_zip):
    ds = load_export(export_zip)
    df = analysis.filter_videos(ds.videos, analysis.TALK_TYPES, 1, True)
    out = analysis.attach_views(df, STATS)
    assert "fffffffffff" not in set(out["vid"])


def test_hidden_gems_sorted_by_fewest_views(export_zip):
    _, df = _talks(export_zip)
    gems = analysis.hidden_gems(analysis.attach_views(df, STATS))
    assert list(gems["vid"]) == ["ccccccccccc", "aaaaaaaaaaa", "bbbbbbbbbbb"]


def test_pairs_pick_rows_without_computing_ratios(export_zip):
    _, df = _talks(export_zip)
    tw = analysis.pairs(analysis.attach_views(df, STATS), 5)
    assert len(tw) == 1
    row = tw.iloc[0]
    assert row["recommenders"] == 15
    assert row["most_viewed_views"] == 20_000_000 and row["least_viewed_views"] == 20_000
    assert not any("ratio" in c or "diff" in c for c in tw.columns)


def test_hackertube_only_tabs(export_zip):
    ds = load_export(export_zip)
    assert analysis.trusted_channels(ds.videos, min_videos=1).iloc[0]["channel"] == "Chan"
    jokes = analysis.hn_inside_jokes(ds.mentions, ds.videos)
    assert list(jokes["title"]) == ["Title ddddddddddd"]
    assert jokes.iloc[0]["joke_mentions"] == 1 and jokes.iloc[0]["first_month"] == "2020-01"
    threads = analysis.joke_threads(ds.mentions, "ddddddddddd")
    assert list(threads.columns) == ["month", "story_title", "quote", "hn_url"] and len(threads) == 1


def test_zones_use_the_users_thresholds(export_zip):
    _, df = _talks(export_zip)
    df = analysis.attach_views(df, STATS)  # a: 15 recs/20k, b: 15 recs/20M, c: 7 recs/19k
    zones = analysis.zone_of(df, many_recs=10, many_views=100_000)
    assert dict(zip(df["vid"], zones)) == {"aaaaaaaaaaa": "Hidden gems", "bbbbbbbbbbb": "Shared classics",
                                           "ccccccccccc": "Quiet corner"}
    assert list(analysis.videos_in_zone(df, zones, "Hidden gems")["vid"]) == ["aaaaaaaaaaa"]
    zones = analysis.zone_of(df, many_recs=16, many_views=10_000)
    assert set(zones) == {"Crowd hits"}
    crowd = analysis.videos_in_zone(df, zones, "Crowd hits")
    assert list(crowd["vid"]) == ["bbbbbbbbbbb", "aaaaaaaaaaa", "ccccccccccc"]  # most views first


def test_zone_map_html_embeds_raw_views_safely(export_zip):
    import json
    from nerdlore import charts
    _, df = _talks(export_zip)
    df = analysis.attach_views(df, STATS)
    df.loc[df["vid"] == "aaaaaaaaaaa", "title"] = "Evil </script><script>alert(1)</script>"
    zones = analysis.zone_of(df, 10, 100_000)
    html = charts.zone_map_html(df, zones, 10, 100_000, {"Hidden gems": ["aaaaaaaaaaa"]})
    assert "__DATA__" not in html and "</script><script>alert" not in html
    payload = html.split("const D = ", 1)[1].split(";\n", 1)[0]
    data = json.loads(payload)
    assert {v["i"]: v["v"] for v in data["videos"]} == {"aaaaaaaaaaa": 20_000, "bbbbbbbbbbb": 20_000_000,
                                                        "ccccccccccc": 19_000}
    assert data["featured"][0] == ["aaaaaaaaaaa"] and data["videos"][0]["t"].startswith("Evil </script>")


def test_hn_links_prefer_strong_recommendations(export_zip):
    import pandas as pd
    mentions = pd.DataFrame([
        {"vid": "a", "stance": "rec", "month": "2020-01", "story_title": "s1", "quote": "", "hn_url": "u1"},
        {"vid": "a", "stance": "strong_rec", "month": "2015-01", "story_title": "s2", "quote": "must watch", "hn_url": "u2"},
        {"vid": "a", "stance": "joke", "month": "2024-01", "story_title": "s3", "quote": "lol", "hn_url": "u3"},
        {"vid": "b", "stance": "joke", "month": "2024-01", "story_title": "s4", "quote": "", "hn_url": "u4"},
    ])
    links = analysis.hn_links(mentions, ["a", "b"])
    assert links == {"a": {"url": "u2", "thread": "s2", "quote": "must watch"}}  # jokes never count


def test_gems_html_embeds_gems_in_order(export_zip):
    import json
    from nerdlore import charts
    _, df = _talks(export_zip)
    gems = analysis.hidden_gems(analysis.attach_views(df, STATS))
    html = charts.gems_html(gems, {"aaaaaaaaaaa": {"url": "https://news.ycombinator.com/item?id=1", "quote": "q"}},
                            15, 20_000_000)
    data = json.loads(html.split("const D = ", 1)[1].split(";\n", 1)[0])
    assert [g["i"] for g in data["gems"]] == ["ccccccccccc", "aaaaaaaaaaa", "bbbbbbbbbbb"]
    a = data["gems"][1]
    assert a["v"] == 20_000 and a["year"] == 2012 and a["fy"] == 2015 and a["hn"].endswith("id=1")
    assert a["q"] == "great talk"  # the video's own HackerTube quote wins over the comment quote


def test_hidden_gems_filters_and_ranking_rule(export_zip):
    _, df = _talks(export_zip)
    df = analysis.attach_views(df, STATS)  # a: 15 recs/20k, b: 15 recs/20M, c: 7 recs/19k
    under = analysis.hidden_gems(df, max_views=100_000, rank_by="recs")
    assert list(under["vid"]) == ["aaaaaaaaaaa", "ccccccccccc"]  # b has too many views; most recs first
    assert list(analysis.hidden_gems(df, max_views=100_000, rank_by="views")["vid"]) == ["ccccccccccc", "aaaaaaaaaaa"]
    assert list(analysis.hidden_gems(df, min_recs=10, max_views=100_000)["vid"]) == ["aaaaaaaaaaa"]


def test_pairs_html_embeds_both_raw_view_counts(export_zip):
    import json
    from nerdlore import charts
    _, df = _talks(export_zip)
    tw = analysis.pairs(analysis.attach_views(df, STATS), 5)
    data = json.loads(charts.pairs_html(tw).split("const D = ", 1)[1].split(";\n", 1)[0])
    (pair,) = data["pairs"]
    assert pair["r"] == 15 and pair["hi"]["i"] == "bbbbbbbbbbb" and pair["lo"]["i"] == "aaaaaaaaaaa"
    assert (pair["hi"]["v"], pair["lo"]["v"]) == (20_000_000, 20_000) and pair["hi"]["year"] == 2014
    assert not any(k in pair for k in ("ratio", "diff"))


def _payload(html: str) -> dict:
    import json
    return json.loads(html.split("const D = ", 1)[1].split(";\n", 1)[0])


def test_channel_explorer_lists_top_videos(export_zip):
    from nerdlore import charts
    ds = load_export(export_zip)
    channels = analysis.trusted_channels(ds.videos, min_videos=1)
    top = analysis.channel_top_videos(ds.videos, list(channels["channel"]), limit=2)
    data = _payload(charts.channels_html(channels, top))
    (chan,) = data["channels"]
    assert chan["name"] == "Chan" and chan["videos"] == 6
    assert [v["i"] for v in chan["top"]] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]  # best HackerTube score first


def test_years_page_carries_both_year_kinds(export_zip):
    from nerdlore import charts
    _, df = _talks(export_zip)
    data = _payload(charts.years_html(analysis.attach_views(df, STATS), "talk / lecture"))
    by_id = {v["i"]: v for v in data["videos"]}
    assert by_id["aaaaaaaaaaa"]["uy"] == 2012 and by_id["aaaaaaaaaaa"]["fy"] == 2015
    assert by_id["bbbbbbbbbbb"]["v"] == 20_000_000 and data["kinds"] == "talk / lecture"


def test_jokes_page_has_years_and_threads(export_zip):
    from nerdlore import charts
    ds = load_export(export_zip)
    jokes = analysis.hn_inside_jokes(ds.mentions, ds.videos)
    years = {v: analysis.joke_years(ds.mentions, v) for v in jokes["vid"]}
    assert years == {"ddddddddddd": {2020: 1}}
    data = _payload(charts.jokes_html(jokes, years, {v: analysis.joke_threads(ds.mentions, v) for v in jokes["vid"]}))
    (joke,) = data["jokes"]
    assert joke["n"] == 1 and joke["years"] == {"2020": 1} and joke["threads"][0]["m"] == "2020-01"
