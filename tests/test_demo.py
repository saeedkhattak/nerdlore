import re

import pytest

from nerdlore import analysis, charts, demo
from nerdlore.data import load_export


@pytest.fixture(scope="module")
def sample():
    return load_export(demo.sample_zip())


def test_fake_stats_are_stable_and_plausible(export_zip):
    videos = load_export(export_zip).videos
    first, again = demo.fake_stats(videos), demo.fake_stats(videos)
    assert first == again  # the same video always gets the same made-up numbers
    for row in videos.itertuples():
        s = first[row.vid]
        assert s.available and 300 <= s.views <= 400_000_000
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", s.published)
        assert 2006 <= int(s.published[:4]) <= row.first_year  # uploaded before HN first linked it


def test_sample_has_something_on_every_page(sample):
    videos, mentions = sample.videos, sample.mentions
    assert len(videos) >= 500
    assert len(analysis.trusted_channels(videos)) == 15
    assert len(analysis.hn_inside_jokes(mentions, videos)) == 15

    df = analysis.attach_views(analysis.filter_videos(videos, analysis.TALK_TYPES, 5), demo.fake_stats(videos))
    assert len(analysis.pairs(df, 5)) >= 5
    assert len(analysis.hidden_gems(df, 5, 100_000)) >= 3
    zones = analysis.zone_of(df, 10, 100_000)
    assert all(len(analysis.videos_in_zone(df, zones, z)) for z in analysis.ZONES)


def test_demo_pages_never_say_youtube_views(sample):
    videos, mentions = sample.videos, sample.mentions
    df = analysis.attach_views(analysis.filter_videos(videos, analysis.TALK_TYPES, 5), demo.fake_stats(videos))
    gems = analysis.hidden_gems(df, 5, 1_000_000)
    zones = analysis.zone_of(df, 10, 100_000)
    featured = {z: list(analysis.videos_in_zone(df, zones, z)["vid"].head(4)) for z in analysis.ZONES}
    pages = [
        charts.gems_html(gems, analysis.hn_links(mentions, list(gems["vid"])), int(df["recommenders"].max()),
                         int(df["views"].max()), "recs"),
        charts.pairs_html(analysis.pairs(df, 5)),
        charts.zone_map_html(df, zones, 10, 100_000, featured),
        charts.years_html(df, "talk / lecture"),
    ]
    for html in pages:
        shown = demo.relabel(html)
        assert "made-up views" in shown.lower()
        assert not re.search(r"youtube views|uploaded to youtube|date from youtube", shown, re.I)
