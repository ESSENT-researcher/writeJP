from modules.state import MAX_KEEP, load_sent_articles, save_sent_articles


def test_missing_or_corrupt_file_is_empty(tmp_path):
    assert load_sent_articles(str(tmp_path / "none.json")) == []
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_sent_articles(str(bad)) == []


def test_save_appends_and_keeps_order(tmp_path):
    path = str(tmp_path / "s.json")
    save_sent_articles(["a", "b"], path)
    save_sent_articles(["c"], path)
    assert load_sent_articles(path) == ["a", "b", "c"]


def test_resent_url_moves_to_latest(tmp_path):
    path = str(tmp_path / "s.json")
    save_sent_articles(["a", "b"], path)
    save_sent_articles(["a"], path)
    assert load_sent_articles(path) == ["b", "a"]


def test_keeps_only_most_recent(tmp_path):
    path = str(tmp_path / "s.json")
    save_sent_articles([str(i) for i in range(MAX_KEEP + 10)], path)
    kept = load_sent_articles(path)
    assert len(kept) == MAX_KEEP
    assert kept[-1] == str(MAX_KEEP + 9) and kept[0] == "10"
