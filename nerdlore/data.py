"""Load HackerTube's public data export (https://hackertube.org/data).

The export is licensed ODC-By 1.0: credit HackerTube and the open-index/hacker-news dataset.
Nothing here touches YouTube data.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from dataclasses import dataclass

import pandas as pd

HACKERTUBE_ZIP_URL = "https://hackertube.org/download/hackertube-data.zip"
MAX_ZIP_BYTES = 100 * 1024 * 1024  # the real export is about 18 MB

REQUIRED_FILES = ("videos.jsonl",)
OPTIONAL_FILES = ("mentions.jsonl",)


class DataError(Exception):
    """The uploaded or downloaded file is not a usable HackerTube export."""


@dataclass
class Dataset:
    videos: pd.DataFrame
    mentions: pd.DataFrame  # empty if the export had no mentions.jsonl


def download_export(url: str = HACKERTUBE_ZIP_URL, timeout: int = 60) -> bytes:
    """Download the HackerTube export zip."""
    req = urllib.request.Request(url, headers={"User-Agent": "nerdlore"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(MAX_ZIP_BYTES + 1)
    if len(data) > MAX_ZIP_BYTES:
        raise DataError("The download is larger than expected for a HackerTube export.")
    return data


def _find(names: list[str], filename: str) -> str | None:
    # Files may sit at the zip root or inside one folder (e.g. hackertube-data/videos.jsonl).
    for name in names:
        if name == filename or name.endswith("/" + filename):
            return name
    return None


def _read_jsonl(zf: zipfile.ZipFile, name: str) -> list[dict]:
    rows = []
    with zf.open(name) as fh:
        for i, line in enumerate(io.TextIOWrapper(fh, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise DataError(f"{name} line {i} is not valid JSON.") from exc
    return rows


def load_export(zip_bytes: bytes) -> Dataset:
    """Read videos.jsonl (and mentions.jsonl if present) from the export zip."""
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise DataError("The file is larger than expected for a HackerTube export.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise DataError("That file is not a zip. Upload hackertube-data.zip from hackertube.org/data.") from exc

    with zf:
        names = zf.namelist()
        for required in REQUIRED_FILES:
            if _find(names, required) is None:
                raise DataError(f"The zip has no {required}. Is this the HackerTube export?")
        videos = _videos_frame(_read_jsonl(zf, _find(names, "videos.jsonl")))
        mentions_name = _find(names, "mentions.jsonl")
        mentions = _mentions_frame(_read_jsonl(zf, mentions_name)) if mentions_name else _mentions_frame([])
    return Dataset(videos=videos, mentions=mentions)


def _videos_frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        raise DataError("videos.jsonl is empty.")
    out = []
    for r in rows:
        if "vid" not in r:
            raise DataError("A row in videos.jsonl has no 'vid' field.")
        hn = r.get("hn") or {}
        quote = r.get("quote") or {}
        out.append({
            "vid": r["vid"],
            "url": r.get("url") or f"https://www.youtube.com/watch?v={r['vid']}",
            "title": r.get("title", ""),
            "channel": r.get("channel", ""),
            "content_type": r.get("content_type", "other"),
            "shelf_life": r.get("shelf_life", ""),
            "primary_topic": r.get("primary_topic", ""),
            "why_hn": r.get("why_hn", ""),
            "quote": quote.get("text", ""),
            "score": float(r.get("score", 0) or 0),
            "recommenders": int(hn.get("recommenders", 0) or 0),
            "strong_recs": int(hn.get("strong_recs", 0) or 0),
            "first_year": hn.get("first_year"),
            "last_year": hn.get("last_year"),
        })
    df = pd.DataFrame(out)
    # Rank by HackerTube's own score (1 = best). Ties share the best rank.
    df["hn_rank"] = df["score"].rank(ascending=False, method="min").astype(int)
    return df


def _mentions_frame(rows: list[dict]) -> pd.DataFrame:
    cols = ["vid", "stance", "month", "story_title", "quote", "hn_url"]
    return pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows], columns=cols)
