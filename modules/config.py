"""
config.py
config.json 로딩, 환경변수 오버라이드, 난이도별 기본값.
"""

import json
import os

DIFFICULTIES = ("beginner", "intermediate", "advanced")

# 난이도 → 기본 단어장 레벨
DEFAULT_VOCAB_LEVELS = {
    "beginner":     ["N5", "N4"],
    "intermediate": ["N3", "N2"],
    "advanced":     ["N2", "N1"],
}

DEFAULTS = {
    "difficulty":     "intermediate",
    "categories":     ["business", "world"],
    "sentence_count": 10,
    "vocab_levels":   None,
    "max_age_hours":  24,
}


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

    if config["difficulty"] not in DIFFICULTIES:
        raise ValueError(
            f"알 수 없는 난이도: {config['difficulty']} (가능: {', '.join(DIFFICULTIES)})"
        )
    if not config["vocab_levels"]:
        config["vocab_levels"] = DEFAULT_VOCAB_LEVELS[config["difficulty"]]
    return config
