import pytest

from modules.dict_lookup import load_vocab_db
from modules.vocab_analyzer import analyze_vocab, extract_words
from scripts.build_vocab import short_meaning, split_glosses


@pytest.fixture
def vocab_csv(tmp_path):
    path = tmp_path / "vocab.csv"
    path.write_text(
        "word,reading,meaning,level\n"
        "懸念,けねん,worry,N1\n"
        "認める,したためる,to write up,N1\n"
        "認める,みとめる,to recognize,N3\n"
        "影響,えいきょう,influence,N3\n"
        "決定,けってい,decision,N3\n"
        "友達,ともだち,friend,N5\n",
        encoding="utf-8",
    )
    return str(path)


@pytest.fixture
def ko_csv(tmp_path):
    path = tmp_path / "ko.csv"
    path.write_text("word,reading,meaning_ko\n影響,えいきょう,영향\n", encoding="utf-8")
    return str(path)


def test_load_groups_entries_by_word_and_prefers_korean(vocab_csv, ko_csv):
    db = load_vocab_db(vocab_csv, ko_csv)
    assert {e["reading"] for e in db["認める"]} == {"したためる", "みとめる"}
    assert db["影響"][0]["meaning"] == "영향"          # 한국어 뜻이 있으면 한국어
    assert db["懸念"][0]["meaning"] == "worry"         # 없으면 영어


def test_load_works_without_korean_file(vocab_csv, tmp_path):
    db = load_vocab_db(vocab_csv, str(tmp_path / "none.csv"))
    assert db["決定"][0]["meaning"] == "decision"


def test_extract_words_returns_base_forms_with_reading():
    words = dict(extract_words(["政府は懸念を示した。", "損害賠償を求める。"]))
    assert words["懸念"] == "けねん"
    assert words["求める"] == "もとめる"
    assert "を" not in words and "は" not in words


def test_extract_words_skips_noise():
    words = dict(extract_words(["これはあるものです。"]))
    assert "ある" not in words      # 짧은 가나 단어
    assert "これ" not in words      # 대명사


def test_analyze_orders_hardest_first_and_dedupes(vocab_csv, ko_csv):
    db = load_vocab_db(vocab_csv, ko_csv)
    result = analyze_vocab(["影響を決定した。", "懸念が影響する。"], db, ["N1", "N3"])
    assert [v["word"] for v in result] == ["懸念", "影響", "決定"]
    assert result[0]["level"] == "N1"


def test_analyze_picks_entry_by_reading(vocab_csv, ko_csv):
    """認める는 문장에서 みとめる로 읽히므로 희귀한 したためる(N1)로 잡히면 안 된다."""
    db = load_vocab_db(vocab_csv, ko_csv)
    result = analyze_vocab(["責任を認める。"], db, ["N1", "N3"])
    assert [(v["word"], v["reading"], v["level"]) for v in result] == [("認める", "みとめる", "N3")]


def test_analyze_filters_by_level_after_matching_reading(vocab_csv, ko_csv):
    db = load_vocab_db(vocab_csv, ko_csv)
    # N1만 요청해도 みとめる(N3)가 したためる(N1)로 둔갑하면 안 된다
    assert analyze_vocab(["責任を認める。"], db, ["N1"]) == []
    assert analyze_vocab(["友達と話す。"], db, ["N3"]) == []


def test_split_glosses_keeps_parenthesised_commas():
    assert split_glosses("to float, to look (sad, glad), to express") == [
        "to float", "to look (sad, glad)", "to express"]


def test_short_meaning_strips_numbering_and_truncates():
    assert short_meaning("1. a, b, c, d, e") == "a, b, c"


def test_shipped_data_is_consistent():
    """배포하는 data/ 파일: 모든 단어에 한국어 뜻이 있고, 사전에 없는 번역이 없어야 한다."""
    import csv

    with open("data/jlpt_vocab.csv", encoding="utf-8", newline="") as f:
        vocab = {(r["word"], r["reading"]) for r in csv.DictReader(f)}
    with open("data/meaning_ko.csv", encoding="utf-8", newline="") as f:
        korean = {(r["word"], r["reading"]): r["meaning_ko"] for r in csv.DictReader(f)}

    assert vocab == set(korean)
    assert all(korean.values())
