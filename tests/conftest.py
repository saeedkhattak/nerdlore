import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _video(vid, ctype="talk", recs=5, score=5.0, channel="Chan", shelf="evergreen", first=2015):
    return {"vid": vid, "url": f"https://www.youtube.com/watch?v={vid}", "title": f"Title {vid}",
            "channel": channel, "content_type": ctype, "shelf_life": shelf, "score": score,
            "hn": {"recommenders": recs, "strong_recs": 1, "first_year": first, "last_year": 2024},
            "quote": {"text": "great talk"}}


@pytest.fixture
def video_rows():
    return [
        _video("aaaaaaaaaaa", recs=15, score=19.5),
        _video("bbbbbbbbbbb", ctype="lecture", recs=15, score=18.0),
        _video("ccccccccccc", recs=7, score=9.0),
        _video("ddddddddddd", ctype="music", recs=9, score=8.0),
        _video("eeeeeeeeeee", recs=6, score=7.0, shelf="news"),
        _video("fffffffffff", recs=2, score=2.0),
    ]


@pytest.fixture
def export_zip(video_rows):
    mentions = [{"vid": "ddddddddddd", "stance": "joke", "month": "2020-01", "story_title": "s", "quote": "", "hn_url": ""},
                {"vid": "aaaaaaaaaaa", "stance": "rec", "month": "2021-01", "story_title": "s", "quote": "", "hn_url": ""}]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hackertube-data/videos.jsonl", "\n".join(json.dumps(r) for r in video_rows))
        zf.writestr("hackertube-data/mentions.jsonl", "\n".join(json.dumps(r) for r in mentions))
    return buf.getvalue()
