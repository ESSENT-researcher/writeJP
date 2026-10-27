from modules.sentence_picker import is_valid_sentence, pick_sentences, split_sentences


def test_split_keeps_closing_quote_with_sentence():
    assert split_sentences("彼は「行きます。」と言った。次の文です。") == [
        "彼は「行きます。」と言った。", "次の文です。"]


def test_split_on_newline_and_strips_dateline():
    assert split_sentences("【ワシントン時事】米中間選挙まで1週間。\n二行目の文章です。") == [
        "米中間選挙まで1週間。", "二行目の文章です。"]


def test_valid_sentence():
    assert is_valid_sentence("政府は新たな経済対策を発表しました。")


def test_rejects_short_and_long():
    assert not is_valid_sentence("短い文。")
    assert not is_valid_sentence("あ" * 130 + "。")


def test_beginner_has_tighter_limit():
    sentence = "政府は新たな経済対策を発表し、物価高に苦しむ家庭への支援を拡大する方針を明らかにしました。"
    assert is_valid_sentence(sentence)
    assert not is_valid_sentence(sentence, max_char=40)


def test_rejects_headline_without_terminator():
    assert not is_valid_sentence("ニデック創業者ら9人を提訴へ　会計不正で損害賠償")


def test_rejects_unbalanced_quote_and_boilerplate():
    assert not is_valid_sentence("彼は「行きますと言って、そのまま帰ってしまった。")
    assert not is_valid_sentence("有料会員になると会員限定の有料記事もお読みいただけます。")
    assert not is_valid_sentence("【関連記事】ニデックが2025年度の決算を発表した。")
    assert not is_valid_sentence("詳しくは https://example.com をご覧ください。")


def _article(name, sentences):
    return {"title": name, "url": f"feed/{name}", "link": f"link/{name}",
            "source": "test", "text": "\n".join(sentences)}


def test_pick_fills_from_best_article_then_next_and_tracks_sources():
    a = _article("a", [f"記事Aの{i}番目の文章はこのようになっています。" for i in range(3)])
    b = _article("b", [f"記事Bの{i}番目の文章はこのようになっています。" for i in range(5)])
    result = pick_sentences([a, b], count=6)

    assert len(result["sentences"]) == 6
    assert [s["title"] for s in result["sources"]] == ["b", "a"]   # 문장 많은 기사부터
    assert result["sources"][0]["url"] == "link/b"
    assert result["sources"][0]["feed_url"] == "feed/b"


def test_pick_uses_only_needed_articles():
    a = _article("a", [f"記事Aの{i}番目の文章はこのようになっています。" for i in range(5)])
    b = _article("b", [f"記事Bの{i}番目の文章はこのようになっています。" for i in range(5)])
    result = pick_sentences([a, b], count=4)
    assert len(result["sources"]) == 1


def test_pick_dedupes_and_handles_empty():
    dup = "同じ文章が二つの記事に出てくる場合です。"
    result = pick_sentences([_article("a", [dup]), _article("b", [dup])], count=5)
    assert result["sentences"] == [dup]
    assert pick_sentences([_article("x", ["短い"])], count=5) == {}
