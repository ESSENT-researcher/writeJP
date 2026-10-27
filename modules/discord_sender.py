"""
discord_sender.py
Discord Webhook으로 필사 뉴스 + 단어장 Embed를 전송한다.
"""

import time
from datetime import datetime, timedelta, timezone

import requests

DIFFICULTY_LABELS = {
    "beginner":     "入門 🌱",
    "intermediate": "中級 📖",
    "advanced":     "上級 🔥",
}
CATEGORY_LABELS = {
    "world":         "🌏 国際",
    "business":      "💹 経済",
    "domestic":      "🗾 社会",
    "science":       "🔬 科学",
    "sports":        "⚽ スポーツ",
    "entertainment": "🎬 エンタメ",
}
LEVEL_ICONS = {"N1": "🔴", "N2": "🟠", "N3": "🟡", "N4": "🟢", "N5": "🔵"}

COLOR_NEWS  = 0x4A90D9
COLOR_VOCAB = 0xF5A623

DESC_LIMIT = 4000      # Embed description 한도 4096에서 여유
WEBHOOK_TIMEOUT = 15
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
JST = timezone(timedelta(hours=9))


def format_date_jp(now: datetime | None = None) -> str:
    now = now or datetime.now(JST)
    return f"{now.year}年{now.month}月{now.day}日（{WEEKDAYS[now.weekday()]}）"


def _join_lines(lines: list[str], limit: int = DESC_LIMIT) -> str:
    """줄 단위로 합치되 한도를 넘으면 남는 줄을 버리고 '…（略）'을 붙인다."""
    out, size = [], 0
    for i, line in enumerate(lines):
        if size + len(line) + 1 > limit - 10:
            out.append("…（略）")
            break
        out.append(line)
        size += len(line) + 1
    return "\n".join(out)


def build_news_embed(
    sentences:  list[str],
    sources:    list[dict],
    difficulty: str,
    categories: list[str],
    now: datetime | None = None,
) -> dict:
    """필사 문장 Embed. sources는 실제 사용된 기사 목록."""
    cats = " / ".join(CATEGORY_LABELS.get(c, c) for c in categories)

    header = [f"**難易度:** {DIFFICULTY_LABELS.get(difficulty, difficulty)}"
              + ("" if difficulty == "advanced" else f"　**分野:** {cats}")]
    for s in sources:
        header.append(f"**記事:** [{s['title']}]({s['url']})　*{s['source']}*")
    header.append("━━━━━━━━━━━━━━━━━━━━━")

    body = [f"`{i:02d}.` {s}" for i, s in enumerate(sentences, 1)]
    return {
        "title":       f"📰 今日の日本語ニュース｜{format_date_jp(now)}",
        "description": _join_lines(header + body),
        "color":       COLOR_NEWS,
        "footer":      {"text": f"writeJP　•　{len(sentences)}文"},
    }


def build_vocab_embed(vocab_list: list[dict]) -> dict | None:
    """레벨별 단어장 Embed. 단어가 없으면 None."""
    if not vocab_list:
        return None

    lines, counts = [], []
    for level in sorted({v["level"] for v in vocab_list}):
        words = [v for v in vocab_list if v["level"] == level]
        counts.append(f"{level}: {len(words)}語")
        if lines:
            lines.append("")
        lines.append(f"{LEVEL_ICONS.get(level, '⚪')} **{level}**")
        lines += [f"• **{v['word']}**（{v['reading']}）— {v['meaning']}" for v in words]

    return {
        "title":       "📚 今日の単語帳",
        "description": _join_lines(lines),
        "color":       COLOR_VOCAB,
        "footer":      {"text": "　".join(counts)},
    }


def _post(webhook_url: str, payload: dict) -> requests.Response:
    return requests.post(webhook_url, json=payload, timeout=WEBHOOK_TIMEOUT)


def send_to_discord(
    webhook_url: str,
    sentences:   list[str],
    sources:     list[dict],
    difficulty:  str,
    categories:  list[str],
    vocab_list:  list[dict],
) -> bool:
    """뉴스 Embed + 단어장 Embed를 보낸다. 성공하면 True."""
    embeds = [build_news_embed(sentences, sources, difficulty, categories)]
    vocab_embed = build_vocab_embed(vocab_list)
    if vocab_embed:
        embeds.append(vocab_embed)
    payload = {"embeds": embeds}

    try:
        resp = _post(webhook_url, payload)
        if resp.status_code == 429:   # rate limit: 지정된 시간만큼 기다린 뒤 1회 재시도
            wait = float(resp.json().get("retry_after", 2))
            print(f"⏳ rate limit — {wait:.1f}초 후 재시도")
            time.sleep(min(wait, 30))
            resp = _post(webhook_url, payload)

        if resp.status_code in (200, 204):
            print("✅ Discord 전송 완료!")
            return True
        print(f"❌ Discord 전송 실패: {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Discord 전송 오류: {e}")
    return False
