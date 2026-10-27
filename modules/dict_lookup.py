"""
dict_lookup.py
data/jlpt_vocab.csv를 메모리 dict로 로딩한다.

같은 표기가 읽기에 따라 여러 항목일 수 있으므로 {표기: [항목, ...]} 형태로 돌려준다.
(레벨 필터링은 읽기를 대조한 뒤에 해야 하므로 여기서는 전체 레벨을 읽는다.)
"""

import csv

VOCAB_CSV = "data/jlpt_vocab.csv"
MEANING_KO_CSV = "data/meaning_ko.csv"   # (표기, 읽기) → 한국어 뜻. 없으면 영어 뜻을 쓴다.

_cache: dict[tuple, dict] = {}


def _load_korean(path: str) -> dict[tuple[str, str], str]:
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            return {(r["word"], r["reading"]): r["meaning_ko"]
                    for r in csv.DictReader(f) if r["meaning_ko"]}
    except FileNotFoundError:
        return {}


def load_vocab_db(path: str = VOCAB_CSV, ko_path: str = MEANING_KO_CSV) -> dict[str, list[dict]]:
    """
    Returns:
        {"単語": [{"reading": str, "meaning": str, "level": str}, ...]}
        meaning은 한국어 뜻이 있으면 한국어, 없으면 영어.
    """
    key = (path, ko_path)
    if key in _cache:
        return _cache[key]

    korean = _load_korean(ko_path)
    db: dict[str, list[dict]] = {}
    translated = 0
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ko = korean.get((row["word"], row["reading"]))
            translated += bool(ko)
            db.setdefault(row["word"], []).append({
                "reading": row["reading"],
                "meaning": ko or row["meaning"],
                "level":   row["level"],
            })

    _cache[key] = db
    total = sum(len(v) for v in db.values())
    print(f"📖 단어 사전 로딩 완료: {total}개, 한국어 뜻 {translated}개")
    return db
