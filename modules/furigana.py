"""
furigana.py
문장의 한자에 후리가나를 붙인다. 형태소 분석(fugashi + ipadic)의 읽기를 한자 부분에만 맞춰 붙인다.

    損害賠償を求める  ->  損害賠償(そんがいばいしょう)を求(もと)める
"""

import re

from modules.vocab_analyzer import get_tagger, to_hiragana

_KANJI = r"[一-鿿々〆]"
_RUN = re.compile(rf"({_KANJI}+)|([^一-鿿々〆]+)")
_HAS_KANJI = re.compile(_KANJI)
_DIGITS = re.compile(r"^[0-9０-９]+$")


def annotate_token(surface: str, reading: str) -> str:
    """
    한 토큰에 후리가나를 붙인다. reading은 히라가나.
    오쿠리가나(送り仮名)는 그대로 두고 한자 덩어리에만 읽기를 단다. 읽기를 맞출 수 없으면 토큰 전체에 단다.
    """
    if not _HAS_KANJI.search(surface) or not reading:
        return surface

    runs = _RUN.findall(surface)
    pattern = "".join(
        "(.+?)" if kanji else re.escape(to_hiragana(other)) for kanji, other in runs
    )
    match = re.fullmatch(pattern, reading)
    if not match:
        return f"{surface}({reading})"

    groups = iter(match.groups())
    return "".join(
        f"{kanji}({next(groups)})" if kanji else other for kanji, other in runs
    )


def add_furigana(sentence: str) -> str:
    """문장 전체에 후리가나를 붙인다. 읽기를 알 수 없는 토큰(고유명사 등)은 그대로 둔다."""
    out = []
    prev_surface = ""
    for token in get_tagger()(sentence):
        feature = token.feature
        reading = feature[7] if len(feature) > 7 and feature[7] != "*" else ""
        # 숫자 뒤의 단위(3日, 11月 …)는 ipadic이 읽기를 틀리게 주므로 달지 않는다
        skip = bool(_DIGITS.match(prev_surface))
        text = token.surface if skip else annotate_token(token.surface, to_hiragana(reading))
        out.append(getattr(token, "white_space", "") + text)
        prev_surface = token.surface
    return "".join(out)
