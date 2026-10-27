"""
sentence_picker.py
기사 본문에서 필사에 적합한 문장을 고른다. 문장마다 출처 기사를 기록한다.
"""

import re

MIN_CHAR = 15
MAX_CHAR = 120
MAX_CHAR_BEGINNER = 60

# 필사 대상이 아닌 줄 (광고/네비/날짜/출처/설문 등)
EXCLUDE_PATTERNS = [
    r"^(関連|続きを読む|もっと見る|写真|動画|PR|AD)",
    r"^【.{0,10}(速報|関連|写真|動画|PR).{0,10}】",   # 【関連記事】… 등
    r"^(All Rights Reserved|Copyright|©)",
    r"^\d+$",
    r"^[a-zA-Z\s\d]+$",
    r"(\.{3,}|…{2,})",
    r"^(ログイン|会員登録|サインイン)",
    r"https?://",
    r"^出典[：:]",
    r"^\d+/\d+\([月火水木金土日]\)",
    r"^\d{4}年\d{1,2}月\d{1,2}日",
    r"^\s*[-―─━]+\s*$",
    r"^(この記事|関連記事|あわせて読む|有料記事)",
    r"^(Tweet|Share|Line|Facebook)",
    r"^\d+:\d+$",
    r"どのように(感じ|考え)(ます)?か[？?]",
    r"^[※＊\*]",
    r"^[（(].{1,10}[）)][：:]",        # （ブルームバーグ）: 등 통신사 표기
    r"統計に基づく",
    r"(無断転載|配信しています|お問い合わせ|利用規約)",
    r"(有料会員|会員限定|読みいただけ|受信契約|受信料|NHK\s?ONE|放送法)",   # 구독/수신료 안내
]
COMPILED_EXCLUDES = [re.compile(p) for p in EXCLUDE_PATTERNS]

_JAPANESE = re.compile(r"[぀-ヿ一-鿿]")
_ENDS_SENTENCE = re.compile(r"[。！？]$")
_DATELINE = re.compile(r"^【[^】]{1,12}】")   # 【ワシントン時事】 같은 통신사 머리말
_PAIRS = [("「", "」"), ("『", "』"), ("（", "）"), ("(", ")")]


def split_sentences(text: str) -> list[str]:
    """줄바꿈과 문장 종결 부호(。！？)로 분리한다. 닫는 괄호는 앞 문장에 붙인다."""
    sentences = []
    for line in text.split("\n"):
        for piece in re.split(r"(?<=[。！？])(?![」』）)])", line):
            piece = _DATELINE.sub("", piece.strip()).strip()
            if piece:
                sentences.append(piece)
    return sentences


def _brackets_balanced(sentence: str) -> bool:
    return all(sentence.count(o) == sentence.count(c) for o, c in _PAIRS)


def is_valid_sentence(sentence: str, max_char: int = MAX_CHAR) -> bool:
    """필사에 적합한 문장인지 판별한다."""
    # 닫는 괄호가 붙은 경우(…です。」)도 종결로 본다
    stripped = sentence.rstrip("」』）)")
    if not MIN_CHAR <= len(sentence) <= max_char:
        return False
    if not _JAPANESE.search(sentence):
        return False
    if not _ENDS_SENTENCE.search(stripped):   # 제목·캡션 제거
        return False
    if not _brackets_balanced(sentence):      # 인용문이 중간에 잘린 경우 제거
        return False
    return not any(p.search(sentence) for p in COMPILED_EXCLUDES)


def pick_sentences(articles: list[dict], count: int = 17, difficulty: str = "intermediate") -> dict:
    """
    기사 목록에서 필사 문장을 최대 count개 고른다.

    문장이 가장 많이 나오는 기사부터 채우고, 부족하면 다음 기사에서 보완한다.
    한 기사 안에서는 원문 순서를 유지한다.

    Returns:
        {"sentences": [str, ...],
         "sources": [{"title", "url", "source"}, ...]}   # 실제 사용된 기사만
        문장이 없으면 {}
    """
    max_char = MAX_CHAR_BEGINNER if difficulty == "beginner" else MAX_CHAR

    per_article = []
    seen = set()
    for article in articles:
        valid = []
        for s in split_sentences(article.get("text", "")):
            if s not in seen and is_valid_sentence(s, max_char):
                seen.add(s)
                valid.append(s)
        if valid:
            per_article.append((article, valid))

    if not per_article:
        print("⚠️  유효한 문장이 없습니다.")
        return {}

    per_article.sort(key=lambda pair: len(pair[1]), reverse=True)

    sentences, sources = [], []
    for article, valid in per_article:
        take = valid[: count - len(sentences)]
        sentences.extend(take)
        sources.append({
            "title":  article.get("title", ""),
            "url":    article.get("link") or article.get("url", ""),
            "source": article.get("source", ""),
            "feed_url": article.get("url", ""),
        })
        if len(sentences) >= count:
            break

    print(f"✅ {len(sentences)}문장 선별 완료 (기사 {len(sources)}개)")
    return {"sentences": sentences, "sources": sources}
