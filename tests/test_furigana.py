from modules.furigana import add_furigana, annotate_token


def test_annotates_only_the_kanji_part_and_keeps_okurigana():
    assert annotate_token("求める", "もとめる") == "求(もと)める"
    assert annotate_token("取り組み", "とりくみ") == "取(と)り組(く)み"


def test_whole_word_and_compound():
    assert annotate_token("損害賠償", "そんがいばいしょう") == "損害賠償(そんがいばいしょう)"


def test_no_kanji_or_no_reading_is_left_alone():
    assert annotate_token("ガソリン", "がそりん") == "ガソリン"
    assert annotate_token("求める", "") == "求める"


def test_falls_back_to_whole_token_when_reading_does_not_align():
    assert annotate_token("求める", "ぜんぜんちがう") == "求める(ぜんぜんちがう)"


def test_sentence_is_annotated_and_text_is_preserved():
    result = add_furigana("政府は懸念を示した。")
    assert result == "政府(せいふ)は懸念(けねん)を示(しめ)した。"


def test_removing_readings_gives_back_the_original_sentence():
    import re
    sentence = "米中間選挙まで1週間。トランプ大統領は（当時26）と述べた。"
    plain = re.sub(r"\([ぁ-ゖー]+\)", "", add_furigana(sentence))
    assert plain == sentence


def test_unit_after_number_gets_no_reading():
    # ipadic은 3日·11月 같은 날짜 단위의 읽기를 틀리게 준다
    assert "(" not in add_furigana("11月3日")
