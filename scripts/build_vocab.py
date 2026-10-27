"""
build_vocab.py
JLPT N1~N5 단어 CSV를 내려받아 data/jlpt_vocab.csv 하나로 병합한다.

출처: https://github.com/stephenmk/yomichan-jlpt-vocab (JMdict 기반, 뜻은 영어)

실행:
    python3 scripts/build_vocab.py
"""

import csv
import io
import os
import re
import sys

import requests

BASE_URL = (
    "https://raw.githubusercontent.com/stephenmk/yomichan-jlpt-vocab/"
    "main/original_data/{level}.csv"
)
LEVELS = ["N1", "N2", "N3", "N4", "N5"]  # 어려운 레벨이 먼저 → 같은 (표기, 읽기)가 겹치면 어려운 쪽 채택
OUT_PATH = "data/jlpt_vocab.csv"
MAX_GLOSSES = 3


def split_glosses(definition: str) -> list[str]:
    """쉼표로 뜻을 나누되, 괄호 안의 쉼표는 나누지 않는다."""
    glosses, depth, current = [], 0, []
    for ch in definition:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth <= 0:
            glosses.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    glosses.append("".join(current).strip())
    return [g for g in glosses if g]


def short_meaning(definition: str) -> str:
    """'1. slope, advance, ...' 형태의 긴 뜻을 앞의 몇 개로 줄인다."""
    definition = re.sub(r"^\d+\.\s*", "", definition.strip())
    return ", ".join(split_glosses(definition)[:MAX_GLOSSES])


def fetch_level(level: str) -> list[dict]:
    resp = requests.get(BASE_URL.format(level=level.lower()), timeout=30)
    resp.raise_for_status()
    return list(csv.DictReader(io.StringIO(resp.text)))


def build() -> list[dict]:
    seen = {}
    for level in LEVELS:
        for row in fetch_level(level):
            word = (row["kanji"] or row["kana"]).strip()
            reading = row["kana"].strip()
            # 같은 표기라도 읽기가 다르면 다른 단어다 (認める: みとめる / したためる)
            if not word or (word, reading) in seen:
                continue
            seen[(word, reading)] = {
                "word":    word,
                "reading": reading,
                "meaning": short_meaning(row["waller_definition"]),
                "level":   level,
            }
        print(f"  {level} 처리 완료 (누적 {len(seen)}개)")
    return list(seen.values())


def main() -> int:
    print("📥 JLPT 단어 데이터 내려받는 중...")
    rows = build()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["word", "reading", "meaning", "level"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ {len(rows)}개 단어 저장: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
