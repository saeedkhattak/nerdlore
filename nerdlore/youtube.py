"""Fetch view counts from the YouTube Data API v3 with the user's own API key.

Policy notes (YouTube API Services Developer Policies):
- View counts are shown exactly as YouTube returns them. Nothing here derives new
  metrics from them or aggregates them (III.E.4.h, III.E.2.b).
- Results live only in the caller's memory; this module never writes them to disk
  (III.E.4.b allows at most 30 days of storage; we store none).
- The key is sent only to googleapis.com over HTTPS and is never logged or returned.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable

API = "https://www.googleapis.com/youtube/v3"
BATCH = 50  # videos.list accepts up to 50 ids per call (1 quota unit each)


class YouTubeError(Exception):
    """A problem talking to the YouTube Data API, with a message safe to show users."""


@dataclass
class VideoStats:
    vid: str
    available: bool
    views: int | None  # None when YouTube hides the count or the video is gone
    published: str | None = None  # upload date as YouTube returns it, YYYY-MM-DD


def _get(endpoint: str, params: dict, api_key: str, timeout: int = 30) -> dict:
    query = urllib.parse.urlencode({**params, "key": api_key})
    try:
        with urllib.request.urlopen(f"{API}/{endpoint}?{query}", timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        # Read YouTube's reason; never echo the URL, it contains the key.
        reason = ""
        try:
            body = json.load(exc)
            reason = body["error"]["errors"][0].get("reason", "")
        except Exception:
            pass
        raise YouTubeError(_friendly(exc.code, reason)) from None
    except urllib.error.URLError:
        raise YouTubeError("Could not reach YouTube. Check your internet connection.") from None


def _friendly(status: int, reason: str) -> str:
    if reason in ("keyInvalid", "badRequest") or status == 400:
        return "YouTube rejected the API key. Check you copied the whole key."
    if reason in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
        return "Your API key has used up today's YouTube quota. Try again tomorrow."
    if reason in ("accessNotConfigured", "ipRefererBlocked", "forbidden") or status == 403:
        return ("YouTube refused the request. Make sure YouTube Data API v3 is enabled "
                "for your key's project and the key is allowed to call it.")
    return f"YouTube returned an error (HTTP {status}). Try again later."


def fetch_views(
    vids: Iterable[str],
    api_key: str,
    on_progress: Callable[[int, int], None] | None = None,
    pause: float = 0.1,
) -> dict[str, VideoStats]:
    """Return {vid: VideoStats} for every id, in batches of 50."""
    if not api_key or not api_key.strip():
        raise YouTubeError("Enter your YouTube API key first.")
    ids = list(dict.fromkeys(vids))
    out: dict[str, VideoStats] = {}
    for start in range(0, len(ids), BATCH):
        chunk = ids[start:start + BATCH]
        data = _get("videos", {"part": "statistics,snippet", "id": ",".join(chunk), "maxResults": BATCH}, api_key.strip())
        got = {item["id"]: item for item in data.get("items", [])}
        for vid in chunk:
            item = got.get(vid)
            if item is None:
                out[vid] = VideoStats(vid, available=False, views=None)
                continue
            raw = item.get("statistics", {}).get("viewCount")
            published = item.get("snippet", {}).get("publishedAt")
            out[vid] = VideoStats(vid, available=True, views=int(raw) if raw is not None else None,
                                  published=published[:10] if published else None)
        if on_progress:
            on_progress(min(start + BATCH, len(ids)), len(ids))
        if pause:
            time.sleep(pause)
    return out


def search_other_uploads(query: str, api_key: str, max_results: int = 5) -> list[dict]:
    """Find other uploads of a talk. Costs about 101 quota units per call.

    Returns [{vid, title, channel, views}] with views exactly as YouTube reports them.
    """
    found = _get("search", {"part": "snippet", "q": query, "type": "video", "maxResults": max_results}, api_key.strip())
    ids = [it["id"]["videoId"] for it in found.get("items", []) if it.get("id", {}).get("videoId")]
    if not ids:
        return []
    data = _get("videos", {"part": "snippet,statistics", "id": ",".join(ids)}, api_key.strip())
    rows = []
    for it in data.get("items", []):
        raw = it.get("statistics", {}).get("viewCount")
        rows.append({
            "vid": it["id"],
            "title": it["snippet"].get("title", ""),
            "channel": it["snippet"].get("channelTitle", ""),
            "views": int(raw) if raw is not None else None,
        })
    return rows
