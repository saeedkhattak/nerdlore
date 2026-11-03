"""Optional saving on the user's own computer, outside the project folder so nothing gets committed.

Saves the user's API key (only when they press Save), the public HackerTube export zip, and the
YouTube view counts from the last run. YouTube's API policy (III.E.4) allows storing those for at most
30 days, so load_views deletes them once they are older than that.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .youtube import VideoStats

STORE_DIR = Path.home() / ".nerdlore"
KEY_FILE = "youtube_api_key.txt"
ZIP_FILE = "hackertube-data.zip"
VIEWS_FILE = "youtube_views.json"
MAX_VIEWS_AGE = timedelta(days=30)


def load_key(store: Path = STORE_DIR) -> str:
    path = store / KEY_FILE
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def save_key(key: str, store: Path = STORE_DIR) -> None:
    store.mkdir(parents=True, exist_ok=True)
    path = store / KEY_FILE
    path.write_text(key.strip(), encoding="utf-8")
    path.chmod(0o600)  # owner only (best effort on Windows)


def forget_key(store: Path = STORE_DIR) -> None:
    (store / KEY_FILE).unlink(missing_ok=True)


def has_zip(store: Path = STORE_DIR) -> bool:
    return (store / ZIP_FILE).exists()


def zip_mtime(store: Path = STORE_DIR) -> float | None:
    path = store / ZIP_FILE
    return path.stat().st_mtime if path.exists() else None


def load_zip(store: Path = STORE_DIR) -> bytes | None:
    path = store / ZIP_FILE
    return path.read_bytes() if path.exists() else None


def save_zip(data: bytes, store: Path = STORE_DIR) -> None:
    store.mkdir(parents=True, exist_ok=True)
    (store / ZIP_FILE).write_bytes(data)


def save_views(stats: dict[str, VideoStats], filters: tuple, fetched_at: datetime, store: Path = STORE_DIR) -> None:
    store.mkdir(parents=True, exist_ok=True)
    data = {"fetched_at": fetched_at.isoformat(), "filters": [list(filters[0]), filters[1], filters[2]],
            "stats": {v: [s.available, s.views, s.published] for v, s in stats.items()}}
    (store / VIEWS_FILE).write_text(json.dumps(data), encoding="utf-8")


def load_views(store: Path = STORE_DIR, now: datetime | None = None
               ) -> tuple[dict[str, VideoStats], tuple, datetime] | None:
    """Return (stats, filters, fetched_at), or None. Deletes the file once it is too old or unreadable."""
    path = store / VIEWS_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        types, min_recs, hide_news = data["filters"]
        stats = {v: VideoStats(v, available, views, published)
                 for v, (available, views, published) in data["stats"].items()}
    except (ValueError, KeyError, TypeError):
        path.unlink(missing_ok=True)
        return None
    if (now or datetime.now(timezone.utc)) - fetched_at > MAX_VIEWS_AGE:
        path.unlink(missing_ok=True)
        return None
    return stats, (tuple(types), int(min_recs), bool(hide_news)), fetched_at


def forget_views(store: Path = STORE_DIR) -> None:
    (store / VIEWS_FILE).unlink(missing_ok=True)
