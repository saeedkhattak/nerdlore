"""Builds the interactive HTML components. View counts are passed through raw, never summarised."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _render(template: Path, data: dict) -> str:
    """Put data into an HTML component's __DATA__ slot."""
    payload = json.dumps(data).replace("</", r"<\/")  # keep titles from closing the <script> tag
    return template.read_text(encoding="utf-8").replace("__DATA__", payload)


def _year(value) -> int | None:
    text = str(value)[:4] if value is not None else ""
    return int(text) if text.isdigit() else None


ZONE_MAP_HTML = Path(__file__).with_name("zone_map.html")
ZONE_BLURBS = {"Hidden gems": "HN keeps recommending it, few people watched",
               "Shared classics": "HN loves it, and so does everyone else",
               "Crowd hits": "lots of views, HN mentions it less",
               "Quiet corner": "fewer recommenders, fewer views"}
ZONE_COLORS = {"Hidden gems": "#a78bfa", "Shared classics": "#e3b341", "Crowd hits": "#3dd6ff",
               "Quiet corner": "#6e7681"}


def zone_map_html(df: pd.DataFrame, zones: pd.Series, many_recs: int, many_views: int,
                  featured: dict[str, list[str]]) -> str:
    """The animated zone map (zone_map.html) filled with this selection's videos. Views are passed through raw."""
    names = list(ZONE_COLORS)
    data = {
        "zones": names, "colors": list(ZONE_COLORS.values()), "blurbs": [ZONE_BLURBS[z] for z in names],
        "recs": int(many_recs), "views": int(many_views), "featured": [featured.get(z, []) for z in names],
        "videos": [{"i": r.vid, "t": r.title, "c": r.channel, "v": int(r.views), "r": int(r.recommenders),
                    "z": names.index(z), "u": r.url} for r, z in zip(df.itertuples(), zones)],
    }
    return _render(ZONE_MAP_HTML, data)


GEMS_HTML = Path(__file__).with_name("gems.html")


def gems_html(gems: pd.DataFrame, hn: dict[str, dict], max_recs: int, max_views: int,
              rank_by: str = "views") -> str:
    """The hidden-gems vault (gems.html) filled with these gems, in order. Views are passed through raw.

    rank_by ("recs" or "views") says which number the order follows, so the cards can highlight it.
    """
    data = {
        "maxRecs": int(max_recs), "maxViews": int(max_views), "rankBy": rank_by,
        "gems": [{"i": r.vid, "t": r.title, "c": r.channel, "u": r.url, "r": int(r.recommenders), "v": int(r.views),
                  "type": r.content_type, "topic": r.primary_topic or "", "why": r.why_hn or "",
                  "q": r.quote or hn.get(r.vid, {}).get("quote", ""), "hn": hn.get(r.vid, {}).get("url", ""),
                  "year": _year(r.published), "fy": _year(r.first_year)} for r in gems.itertuples()],
    }
    return _render(GEMS_HTML, data)


PAIRS_HTML = Path(__file__).with_name("pairs.html")


def pairs_html(pairs: pd.DataFrame) -> str:
    """The "Same praise, different reach" page (pairs.html) filled with analysis.pairs() rows. Views are passed through raw."""
    def side(r, prefix: str) -> dict:
        return {"i": getattr(r, f"{prefix}_vid"), "t": getattr(r, f"{prefix}_title"), "c": getattr(r, f"{prefix}_channel"),
                "u": getattr(r, f"{prefix}_url"), "v": int(getattr(r, f"{prefix}_views")),
                "why": getattr(r, f"{prefix}_why") or "", "type": getattr(r, f"{prefix}_type") or "",
                "year": _year(getattr(r, f"{prefix}_published"))}

    data = {"pairs": [{"r": int(r.recommenders), "hi": side(r, "most_viewed"), "lo": side(r, "least_viewed")}
                      for r in pairs.itertuples()]}
    return _render(PAIRS_HTML, data)


CHANNELS_HTML = Path(__file__).with_name("channels.html")
YEARS_HTML = Path(__file__).with_name("years.html")
JOKES_HTML = Path(__file__).with_name("jokes.html")


def channels_html(channels: pd.DataFrame, top_videos: dict[str, pd.DataFrame]) -> str:
    """The channel explorer (channels.html). HackerTube data only."""
    return _render(CHANNELS_HTML, {"channels": [
        {"name": r.channel, "videos": int(r.videos), "score": float(r.avg_hn_score), "recs": int(r.total_recommenders),
         "url": r.channel_url,
         "top": [{"i": v.vid, "t": v.title, "u": v.url, "r": int(v.recommenders), "type": v.content_type,
                  "fy": _year(v.first_year)} for v in top_videos.get(r.channel, pd.DataFrame()).itertuples()]}
        for r in channels.itertuples()]})


def years_html(df: pd.DataFrame, kinds: str) -> str:
    """The year-by-year time machine (years.html). Views and upload dates are passed through raw."""
    return _render(YEARS_HTML, {"kinds": kinds, "videos": [
        {"i": r.vid, "t": r.title, "c": r.channel, "u": r.url, "r": int(r.recommenders), "v": int(r.views),
         "pub": r.published or "", "uy": _year(r.published), "fy": _year(r.first_year)} for r in df.itertuples()]})


def jokes_html(jokes: pd.DataFrame, years: dict[str, dict[int, int]], threads: dict[str, pd.DataFrame]) -> str:
    """The running-gag browser (jokes.html). HackerTube data only."""
    return _render(JOKES_HTML, {"jokes": [
        {"i": r.vid, "t": r.title, "c": r.channel, "u": r.url, "n": int(r.joke_mentions), "why": r.why_hn or "",
         "years": {str(y): n for y, n in years.get(r.vid, {}).items()},
         "threads": [{"m": m.month, "s": m.story_title, "q": m.quote, "u": m.hn_url}
                     for m in threads.get(r.vid, pd.DataFrame()).itertuples()]}
        for r in jokes.itertuples()]})
