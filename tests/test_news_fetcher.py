from datetime import datetime, timedelta, timezone

from modules.news_fetcher import filter_recent

NOW = datetime(2026, 10, 27, 23, 0, tzinfo=timezone.utc)   # KST 10/28 08:00


def _item(name, hours_ago):
    published = None if hours_ago is None else NOW - timedelta(hours=hours_ago)
    return {"title": name, "url": f"u/{name}", "published": published}


def test_keeps_only_recent_and_sorts_newest_first():
    items = [_item("old", 30), _item("mid", 10), _item("new", 1), _item("edge", 23.9)]
    result = filter_recent(items, 24, now=NOW)
    assert [i["title"] for i in result] == ["new", "mid", "edge"]


def test_excludes_undated_and_far_future_items():
    items = [_item("undated", None), _item("future", -5), _item("ok", 2)]
    assert [i["title"] for i in filter_recent(items, 24, now=NOW)] == ["ok"]


def test_window_is_configurable():
    items = [_item("a", 3), _item("b", 12)]
    assert [i["title"] for i in filter_recent(items, 6, now=NOW)] == ["a"]
