"""Demo mode: made-up view counts, so people can try NerdLore before they get a YouTube API key.

Nothing here comes from YouTube or goes over the network. Each video's view count and upload
date are generated from its id, so the same video always gets the same made-up numbers. They
live only in the app's memory and are never saved, so they can't overwrite or be mistaken for
real view counts. Every page says "made-up views" while demo mode is on.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pandas as pd

from .youtube import VideoStats

SAMPLE_ZIP = Path(__file__).parent / "sample_data" / "hackertube-sample.zip"

# Page text to swap while demo mode is on, longest first so the specific phrases win.
RELABEL = [
    ("YouTube views (from YouTube)", "Made-up views (demo)"),
    ("YOUTUBE VIEWS", "MADE-UP VIEWS"),
    ("YouTube views", "made-up views"),
    ('color:var(--muted)">YOUTUBE<', 'color:var(--muted)">DEMO<'),
    ("uploaded to YouTube (date from YouTube)", "uploaded (made-up dates in demo mode)"),
    ("Uploaded to YouTube", "Uploaded (made up)"),
]


def sample_zip() -> bytes:
    """The small HackerTube sample that ships with the app (see sample_data/NOTICE in the zip)."""
    return SAMPLE_ZIP.read_bytes()


def _unit(digest: bytes, i: int) -> float:
    """A number in (0, 1) taken from four bytes of the digest."""
    return (int.from_bytes(digest[i:i + 4], "big") + 0.5) / 2 ** 32


def fake_stats(videos: pd.DataFrame) -> dict[str, VideoStats]:
    """Made-up view counts and upload dates for each video, the same every time.

    Views are spread over a log scale (hundreds to hundreds of millions) and lean a little
    higher for videos more people on HN recommend, so every zone of the map has videos in it.
    Upload dates fall up to five years before the video's first HN mention.
    """
    out = {}
    for row in videos.itertuples():
        h = hashlib.sha256(f"nerdlore-demo:{row.vid}".encode()).digest()
        normal = math.sqrt(-2 * math.log(_unit(h, 0))) * math.cos(2 * math.pi * _unit(h, 4))
        log_views = 4.2 + 0.09 * min(int(row.recommenders), 25) + 0.95 * normal
        views = int(round(10 ** min(max(log_views, 2.5), 8.6)))
        first = int(row.first_year) if pd.notna(row.first_year) else 2015
        year = max(2006, min(first, 2026) - int(_unit(h, 8) * 6))
        published = f"{year:04d}-{1 + h[12] % 12:02d}-{1 + h[13] % 28:02d}"
        out[row.vid] = VideoStats(vid=row.vid, available=True, views=views, published=published)
    return out


# A strip at the top of every interactive page while demo mode is on.
STRIP = ('<div style="margin:0 0 10px;padding:7px 12px;border-radius:8px;border:1px solid rgba(255,122,61,.55);'
         'background:rgba(255,122,61,.13);color:#ff9a66;font:600 12px/1.4 ui-monospace,SFMono-Regular,Consolas,'
         'monospace;letter-spacing:.06em">&#9679; DEMO &middot; THE VIEW COUNTS AND UPLOAD DATES ON THIS PAGE '
         'ARE MADE UP, NOT FROM YOUTUBE</div>')


def relabel(html: str) -> str:
    """Make an interactive page say "made-up views" instead of "YouTube views", with a demo strip on top."""
    for old, new in RELABEL:
        html = html.replace(old, new)
    return html.replace("<body>", "<body>" + STRIP, 1)
