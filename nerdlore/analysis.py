"""Analyses that stay inside YouTube's API rules.

Allowed: showing each video's view count exactly as YouTube returns it, and sorting or
filtering by it. Not allowed (III.E.4.h, III.E.2.b): new metrics calculated from view
counts, such as medians, averages, totals, ratios or scores. So every function here either
uses only HackerTube's data, or passes raw view counts through untouched.
"""

from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd

from .youtube import VideoStats

TALK_TYPES = ("talk", "lecture")
CHANNEL_SEARCH = "https://www.youtube.com/results?sp=EgIQAg%253D%253D&search_query="  # filter: channels


def filter_videos(videos: pd.DataFrame, types: list[str] | tuple[str, ...], min_recommenders: int,
                  hide_news: bool = True) -> pd.DataFrame:
    """HackerTube data only: pick the videos the user wants to look at."""
    df = videos[videos["content_type"].isin(types) & (videos["recommenders"] >= min_recommenders)]
    if hide_news:
        df = df[df["shelf_life"] != "news"]
    return df.copy()


def attach_views(df: pd.DataFrame, stats: dict[str, VideoStats]) -> pd.DataFrame:
    """Add YouTube's raw view count (unchanged) and drop videos YouTube no longer serves."""
    out = df.copy()
    out["views"] = out["vid"].map(lambda v: stats[v].views if v in stats else None)
    out["published"] = out["vid"].map(lambda v: stats[v].published if v in stats else None)
    out["available"] = out["vid"].map(lambda v: stats[v].available if v in stats else False)
    out = out[out["available"] & out["views"].notna()].drop(columns="available")
    out["views"] = out["views"].astype("int64")
    out["uploaded_year"] = pd.to_numeric(out["published"].str[:4], errors="coerce").astype("Int64")
    return out


GEM_RANKINGS = {"recs": "Most HN recommenders", "views": "Fewest YouTube views"}


def hidden_gems(df: pd.DataFrame, min_recs: int = 0, max_views: int | None = None, rank_by: str = "views",
                limit: int | None = 25) -> pd.DataFrame:
    """Videos with at least min_recs HN recommenders and fewer than max_views YouTube views (raw counts).

    rank_by="recs": most HN recommenders first, fewer views breaking ties.
    rank_by="views": fewest views first, more HN recommenders breaking ties.
    """
    rows = df[df["recommenders"] >= min_recs]
    if max_views is not None:
        rows = rows[rows["views"] < max_views]
    if rank_by == "recs":
        rows = rows.sort_values(["recommenders", "views"], ascending=[False, True])
    else:
        rows = rows.sort_values(["views", "recommenders"], ascending=[True, False])
    return rows if limit is None else rows.head(limit)


def pairs(df: pd.DataFrame, min_recommenders: int) -> pd.DataFrame:
    """For each HN recommender count, the most- and least-viewed video with that count.

    Only selects rows by their raw view counts; no ratio or difference is calculated.
    """
    rows = []
    for recs, group in df[df["recommenders"] >= min_recommenders].groupby("recommenders"):
        if len(group) < 2:
            continue
        row = {"recommenders": int(recs)}
        for side, video in (("most_viewed", group.loc[group["views"].idxmax()]),
                            ("least_viewed", group.loc[group["views"].idxmin()])):
            row.update({f"{side}_title": video["title"], f"{side}_channel": video["channel"],
                        f"{side}_views": int(video["views"]), f"{side}_url": video["url"],
                        f"{side}_vid": video["vid"], f"{side}_why": video.get("why_hn", ""),
                        f"{side}_type": video.get("content_type", ""), f"{side}_published": video.get("published")})
        rows.append(row)
    return pd.DataFrame(rows).sort_values("recommenders", ascending=False) if rows else pd.DataFrame()


def trusted_channels(videos: pd.DataFrame, min_videos: int = 10, limit: int = 15) -> pd.DataFrame:
    """HackerTube data only: channels by average HackerTube score."""
    g = videos.groupby("channel").agg(videos=("vid", "count"), avg_hn_score=("score", "mean"),
                                      total_recommenders=("recommenders", "sum"))
    g = g[g["videos"] >= min_videos].sort_values("avg_hn_score", ascending=False).head(limit)
    g["avg_hn_score"] = g["avg_hn_score"].round(2)
    # The export has channel names but no channel IDs, so link a YouTube channel search instead.
    g["channel_url"] = [CHANNEL_SEARCH + quote_plus(name) for name in g.index]
    best = videos.sort_values("score", ascending=False).drop_duplicates("channel").set_index("channel")
    g["best_title"] = best["title"].reindex(g.index)
    g["best_url"] = best["url"].reindex(g.index)
    return g.reset_index()


ZONES = ("Hidden gems", "Shared classics", "Crowd hits", "Quiet corner")


def zone_of(df: pd.DataFrame, many_recs: int, many_views: int) -> pd.Series:
    """Place each video in a zone by two thresholds the user picks (nothing is calculated from views)."""
    loved = df["recommenders"] >= many_recs
    seen = df["views"] >= many_views
    zones = pd.Series("Quiet corner", index=df.index)
    zones[loved & ~seen] = "Hidden gems"
    zones[loved & seen] = "Shared classics"
    zones[~loved & seen] = "Crowd hits"
    return zones


def videos_in_zone(df: pd.DataFrame, zones: pd.Series, zone: str) -> pd.DataFrame:
    """The videos in one zone, in the order that best shows what the zone means."""
    rows = df[zones == zone]
    if zone == "Crowd hits":
        return rows.sort_values(["views", "recommenders"], ascending=[False, False])
    if zone == "Hidden gems":
        return rows.sort_values(["recommenders", "views"], ascending=[False, True])
    return rows.sort_values(["recommenders", "views"], ascending=[False, False])


def hn_inside_jokes(mentions: pd.DataFrame, videos: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    """HackerTube data only: videos HN mentions most often as a joke."""
    if mentions.empty:
        return pd.DataFrame()
    jokes = mentions[mentions["stance"] == "joke"].groupby("vid").agg(
        joke_mentions=("vid", "size"), first_month=("month", "min"), last_month=("month", "max"))
    out = videos.set_index("vid").join(jokes, how="inner").sort_values("joke_mentions", ascending=False)
    cols = ["vid", "title", "channel", "joke_mentions", "first_month", "last_month", "why_hn", "url"]
    return out.reset_index()[cols].head(limit)


def hn_links(mentions: pd.DataFrame, vids: list[str]) -> dict[str, dict]:
    """HackerTube data only: for each video, one HN comment that recommends it (strong ones, with a quote, first)."""
    if mentions.empty:
        return {}
    recs = mentions[mentions["vid"].isin(vids) & mentions["stance"].isin(["strong_rec", "rec"])].copy()
    recs["strong"] = recs["stance"] == "strong_rec"
    recs["has_quote"] = recs["quote"].str.strip() != ""
    recs = recs.sort_values(["strong", "has_quote", "month"], ascending=False).drop_duplicates("vid")
    return {r.vid: {"url": r.hn_url, "thread": r.story_title, "quote": r.quote} for r in recs.itertuples()}


def channel_top_videos(videos: pd.DataFrame, channels: list[str], limit: int = 6) -> dict[str, pd.DataFrame]:
    """HackerTube data only: each channel's best videos by HackerTube score."""
    ranked = videos[videos["channel"].isin(channels)].sort_values("score", ascending=False)
    return {name: group.head(limit) for name, group in ranked.groupby("channel", sort=False)}


def joke_years(mentions: pd.DataFrame, vid: str) -> dict[int, int]:
    """HackerTube data only: how many times a video was posted as a joke in each year."""
    months = mentions[(mentions["vid"] == vid) & (mentions["stance"] == "joke")]["month"]
    years = months.str[:4]
    return {int(y): int(n) for y, n in years[years.str.isdigit()].value_counts().sort_index().items()}


def joke_threads(mentions: pd.DataFrame, vid: str, limit: int = 5) -> pd.DataFrame:
    """HackerTube data only: HN threads where a video was posted as a joke, ones with a quote first."""
    rows = mentions[(mentions["vid"] == vid) & (mentions["stance"] == "joke")].copy()
    rows["has_quote"] = rows["quote"].str.strip() != ""
    rows = rows.sort_values(["has_quote", "month"], ascending=[False, False]).head(limit)
    return rows.sort_values("month")[["month", "story_title", "quote", "hn_url"]]
