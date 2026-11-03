import io
import json
import urllib.error

import pytest

from nerdlore import youtube


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_views_batches_and_marks_missing(monkeypatch):
    calls = []

    def fake_urlopen(url, timeout=30):
        calls.append(url)
        ids = url.split("id=")[1].split("&")[0].split("%2C")
        items = [{"id": i, "statistics": {"viewCount": "123"}, "snippet": {"publishedAt": "2013-04-02T17:00:00Z"}}
                 for i in ids if i != "gone0000000"]
        return _Resp(json.dumps({"items": items}).encode())

    monkeypatch.setattr(youtube.urllib.request, "urlopen", fake_urlopen)
    vids = [f"v{i:010d}" for i in range(60)] + ["gone0000000"]
    out = youtube.fetch_views(vids, "TESTKEY", pause=0)
    assert len(calls) == 2  # 61 ids -> batches of 50 + 11
    assert out["v0000000001"].views == 123 and out["v0000000001"].available
    assert out["v0000000001"].published == "2013-04-02"
    assert out["gone0000000"].available is False and out["gone0000000"].views is None


def test_errors_never_contain_the_key(monkeypatch):
    def fake_urlopen(url, timeout=30):
        body = io.BytesIO(json.dumps({"error": {"errors": [{"reason": "quotaExceeded"}]}}).encode())
        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, body)

    monkeypatch.setattr(youtube.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(youtube.YouTubeError) as exc:
        youtube.fetch_views(["abc"], "SECRETKEY123", pause=0)
    assert "quota" in str(exc.value)
    assert "SECRETKEY123" not in str(exc.value)


def test_empty_key_is_rejected():
    with pytest.raises(youtube.YouTubeError, match="API key"):
        youtube.fetch_views(["abc"], "  ")
