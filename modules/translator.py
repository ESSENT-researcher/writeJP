"""
translator.py
필사 문장을 한국어로 번역한다 (Claude API). 실패하거나 키가 없으면 None을 돌려주고,
호출한 쪽은 번역 없이 계속 진행한다 (번역은 부가 기능이라 전송을 막지 않는다).
"""

import os
import re

import anthropic

MODEL = "claude-opus-5-5"
MAX_TOKENS = 8000

SYSTEM_PROMPT = (
    "당신은 일본어 학습자를 위한 일본어→한국어 번역가입니다. "
    "번호가 붙은 일본어 뉴스 문장을 자연스러운 한국어로 번역하세요. "
    "고유명사는 한국에서 쓰는 표기를 따르고, 설명이나 주석은 붙이지 마세요. "
    "출력은 반드시 입력과 같은 개수의 줄이며, 각 줄은 '번호|번역' 형식이어야 합니다."
)

_LINE = re.compile(r"^\s*(\d+)\s*[|｜]\s*(.+?)\s*$", re.MULTILINE)


def build_prompt(sentences: list[str]) -> str:
    return "\n".join(f"{i}|{s}" for i, s in enumerate(sentences, 1))


def parse_translations(text: str, count: int) -> list[str] | None:
    """'번호|번역' 줄들을 문장 순서에 맞춰 정렬한다. 하나도 못 읽으면 None, 빠진 번호는 빈 문자열."""
    found = {int(n): t for n, t in _LINE.findall(text) if 1 <= int(n) <= count}
    if not found:
        return None
    return [found.get(i, "") for i in range(1, count + 1)]


def translate_sentences(sentences: list[str], client: anthropic.Anthropic | None = None) -> list[str] | None:
    """
    문장 목록을 한국어로 번역해 같은 길이의 목록으로 돌려준다.
    키가 없거나 호출이 실패하면 None (사유는 출력만 하고 예외는 던지지 않는다).
    """
    if not sentences:
        return None
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ℹ️  ANTHROPIC_API_KEY가 없어 번역을 건너뜁니다")
            return None
        client = anthropic.Anthropic()

    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",                      # 안전 분류기가 거절하면 서버가 다른 모델로 재시도
            output_config={"effort": "low"},          # 문장 번역에는 깊은 추론이 필요 없다
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_prompt(sentences)}],
        )
    except anthropic.AuthenticationError:
        print("⚠️  번역 실패: ANTHROPIC_API_KEY가 올바르지 않습니다")
        return None
    except anthropic.APIStatusError as e:
        print(f"⚠️  번역 실패: API 오류 {e.status_code}")
        return None
    except anthropic.APIConnectionError:
        print("⚠️  번역 실패: 네트워크 오류")
        return None

    if response.stop_reason != "end_turn":
        print(f"⚠️  번역 실패: 응답이 정상 종료되지 않았습니다 ({response.stop_reason})")
        return None

    text = "".join(block.text for block in response.content if block.type == "text")
    translations = parse_translations(text, len(sentences))
    if translations is None:
        print("⚠️  번역 실패: 응답에서 번역을 읽지 못했습니다")
        return None
    missing = sum(1 for t in translations if not t)
    print(f"✅ 한국어 번역 완료 ({len(sentences) - missing}/{len(sentences)}문장)")
    return translations
