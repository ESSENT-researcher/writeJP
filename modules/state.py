"""
state.py
전송한 기사 URL 기록 (중복 방지). 파일은 레포에 커밋되어 실행 간에 유지된다.
"""

import json
import os

SENT_ARTICLES_PATH = "data/sent_articles.json"
MAX_KEEP = 300


def load_sent_articles(path: str = SENT_ARTICLES_PATH) -> list[str]:
    """전송 기록을 오래된 순서로 반환한다. 파일이 없거나 깨져 있으면 빈 목록."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return list(json.load(f).get("sent", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_sent_articles(urls: list[str], path: str = SENT_ARTICLES_PATH) -> None:
    """URL들을 기록에 추가하고 최근 MAX_KEEP개만 남긴다 (순서 보존, 중복 제거)."""
    merged = load_sent_articles(path)
    for url in urls:
        if url in merged:
            merged.remove(url)  # 최신 위치로 이동
        merged.append(url)
    merged = merged[-MAX_KEEP:]

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sent": merged}, f, ensure_ascii=False, indent=2)
        f.write("\n")
