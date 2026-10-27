"""
vocab_analyzer.py
형태소 분석(fugashi + ipadic)으로 문장의 단어를 기본형으로 뽑아 JLPT 단어장과 대조한다.
"""

import re

import fugashi
import ipadic

CONTENT_POS = {"名詞", "動詞", "形容詞"}
SKIP_SUBPOS = {"非自立", "代名詞", "数", "接尾", "副詞可能"}
MAX_PER_LEVEL = 15

_KANJI = re.compile(r"[一-鿿]")
_KATAKANA = re.compile(r"[ァ-ヶ]")
_tagger = None


def get_tagger() -> fugashi.GenericTagger:
    global _tagger
    if _tagger is None:
        _tagger = fugashi.GenericTagger(ipadic.MECAB_ARGS)
    return _tagger


def _is_candidate(base: str) -> bool:
    """한자가 있거나 3자 이상이어야 후보. (ある·する 같은 짧은 가나 단어 노이즈 방지)"""
    return bool(_KANJI.search(base)) or len(base) >= 3


def to_hiragana(text: str) -> str:
    return _KATAKANA.sub(lambda m: chr(ord(m.group()) - 0x60), text)


def extract_words(sentences: list[str]) -> list[tuple[str, str]]:
    """
    문장들에서 명사/동사/형용사의 (기본형, 읽기[히라가나])를 등장 순서대로 추출한다 (중복 포함).
    읽기를 알 수 없으면 빈 문자열.
    """
    tagger = get_tagger()
    words = []
    for sentence in sentences:
        for token in tagger(sentence):
            feature = token.feature
            if feature[0] not in CONTENT_POS or feature[1] in SKIP_SUBPOS:
                continue
            base = feature[6] if len(feature) > 6 and feature[6] != "*" else token.surface
            if _is_candidate(base):
                reading = feature[7] if len(feature) > 7 and feature[7] != "*" else ""
                words.append((base, to_hiragana(reading)))
    return words


def _pick_entry(entries: list[dict], reading: str) -> dict | None:
    """같은 표기의 항목들 중 읽기가 일치하는 것을 고른다. 읽기를 모르면 항목이 하나뿐일 때만 채택."""
    if reading:
        return next((e for e in entries if to_hiragana(e["reading"]) == reading), None)
    return entries[0] if len(entries) == 1 else None


def analyze_vocab(sentences: list[str], vocab_db: dict, levels: list[str]) -> list[dict]:
    """
    문장들에서 vocab_db에 있는 단어를 찾는다. 읽기가 일치하는 항목만 인정하고,
    그 항목의 레벨이 levels에 있을 때만 단어장에 넣는다.

    Returns:
        [{"word", "reading", "meaning", "level"}, ...]
        어려운 레벨(N1)부터, 같은 레벨 안에서는 등장 순서. 레벨당 MAX_PER_LEVEL개까지.
    """
    found = {}
    for word, reading in extract_words(sentences):
        if word in found or word not in vocab_db:
            continue
        entry = _pick_entry(vocab_db[word], reading)
        if entry and entry["level"] in levels:
            found[word] = {"word": word, **entry}

    by_level = sorted(found.values(), key=lambda v: v["level"])  # sorted()는 안정 정렬
    result, counts = [], {}
    for v in by_level:
        if counts.get(v["level"], 0) < MAX_PER_LEVEL:
            counts[v["level"]] = counts.get(v["level"], 0) + 1
            result.append(v)

    print(f"✅ JLPT 단어 {len(result)}개 발견")
    return result
