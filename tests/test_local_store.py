from datetime import datetime, timedelta, timezone

from nerdlore import local_store
from nerdlore.youtube import VideoStats


def test_key_save_load_forget(tmp_path):
    store = tmp_path / "store"
    assert local_store.load_key(store) == ""
    local_store.save_key("  AIza-test \n", store)
    assert local_store.load_key(store) == "AIza-test"
    local_store.forget_key(store)
    assert local_store.load_key(store) == ""
    local_store.forget_key(store)  # forgetting twice is fine


def test_zip_save_load(tmp_path):
    assert local_store.load_zip(tmp_path) is None
    assert not local_store.has_zip(tmp_path)
    local_store.save_zip(b"PK\x03\x04data", tmp_path)
    assert local_store.has_zip(tmp_path)
    assert local_store.load_zip(tmp_path) == b"PK\x03\x04data"


def test_views_round_trip_and_expire_after_30_days(tmp_path):
    fetched = datetime(2026, 1, 1, tzinfo=timezone.utc)
    stats = {"a": VideoStats("a", True, 123, "2014-02-03"), "b": VideoStats("b", False, None)}
    local_store.save_views(stats, (("talk", "lecture"), 5, True), fetched, tmp_path)

    got, filters, when = local_store.load_views(tmp_path, now=fetched + timedelta(days=29))
    assert got == stats and filters == (("talk", "lecture"), 5, True) and when == fetched

    assert local_store.load_views(tmp_path, now=fetched + timedelta(days=31)) is None
    assert not (tmp_path / local_store.VIEWS_FILE).exists()  # deleted, not just hidden


def test_forget_views_and_bad_file(tmp_path):
    (tmp_path / local_store.VIEWS_FILE).write_text("not json", encoding="utf-8")
    assert local_store.load_views(tmp_path) is None
    local_store.save_views({}, ((), 1, False), datetime.now(timezone.utc), tmp_path)
    local_store.forget_views(tmp_path)
    assert local_store.load_views(tmp_path) is None
