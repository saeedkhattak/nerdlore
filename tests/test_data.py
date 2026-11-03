import io
import zipfile

import pytest

from nerdlore.data import DataError, load_export


def test_loads_videos_and_mentions(export_zip):
    ds = load_export(export_zip)
    assert len(ds.videos) == 6
    assert len(ds.mentions) == 2
    top = ds.videos.sort_values("hn_rank").iloc[0]
    assert top["vid"] == "aaaaaaaaaaa" and top["hn_rank"] == 1 and top["recommenders"] == 15


def test_rejects_non_zip():
    with pytest.raises(DataError, match="not a zip"):
        load_export(b"hello")


def test_rejects_zip_without_videos():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "nothing here")
    with pytest.raises(DataError, match="videos.jsonl"):
        load_export(buf.getvalue())


def test_mentions_are_optional(video_rows):
    import json
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("videos.jsonl", "\n".join(json.dumps(r) for r in video_rows))
    ds = load_export(buf.getvalue())
    assert ds.mentions.empty
