"""
config.py
config.json 로딩, 환경변수 오버라이드, 난이도별 기본값.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone

DIFFICULTIES = ("beginner", "intermediate", "advanced")

# 난이도 → 기본 단어장 레벨
DEFAULT_VOCAB_LEVELS = {
    "beginner":     ["N5", "N4"],
    "intermediate": ["N3", "N2"],
    "advanced":     ["N2", "N1"],
}

DEFAULTS = {
    "difficulty":        "intermediate",
    "categories":        ["business", "world", "science"],
    "rotate_categories": True,    # True: 날짜에 따라 하루 한 분야씩 순환, False: 모든 분야를 섞어서 사용
    "sentence_count":    8,
    "vocab_levels":      None,
    "max_age_hours":     24,
}

JST = timezone(timedelta(hours=9))
ROTATION_START = date(2026, 10, 28)   # 이 날이 categories의 첫 번째 분야 차례


def load_config(path: str = "config.json") -> dict:
    """config.json을 읽고 기본값/환경변수 오버라이드를 적용한다."""
    config = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config.update(json.load(f))

    # GitHub Actions 수동 실행 입력
    difficulty = os.environ.get("WRITEJP_DIFFICULTY", "").strip()
    categories = os.environ.get("WRITEJP_CATEGORIES", "").strip()
    if difficulty:
        config["difficulty"] = difficulty
    if categories:
        config["categories"] = [c.strip() for c in categories.split(",") if c.strip()]
        config["rotate_categories"] = False   # 직접 고른 분야는 순환하지 않고 그대로 쓴다

    if config["difficulty"] not in DIFFICULTIES:
        raise ValueError(
            f"알 수 없는 난이도: {config['difficulty']} (가능: {', '.join(DIFFICULTIES)})"
        )
    if not config["vocab_levels"]:
        config["vocab_levels"] = DEFAULT_VOCAB_LEVELS[config["difficulty"]]
    return config


def resolve_categories(config: dict, today: date | None = None) -> list[str]:
    """
    오늘 사용할 분야 목록. rotate_categories가 켜져 있으면 날짜(JST)에 따라
    categories를 하루에 하나씩 순서대로 돌려 쓴다 (예: 경제 → 국제 → 과학 → 경제 …).
    """
    categories = config["categories"]
    if not config.get("rotate_categories") or len(categories) <= 1:
        return categories
    today = today or datetime.now(JST).date()
    return [categories[(today - ROTATION_START).days % len(categories)]]
