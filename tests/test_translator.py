from types import SimpleNamespace

import anthropic
import pytest

from modules import translator
from modules.translator import build_prompt, parse_translations, translate_sentences

SENTENCES = ["一文目です。", "二文目です。", "三文目です。"]


def _client(text=None, stop_reason="end_turn", error=None):
    def create(**kwargs):
        _client.last_kwargs = kwargs
        if error:
            raise error
        content = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)]
        return SimpleNamespace(stop_reason=stop_reason, content=content)

    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))


def test_build_prompt_numbers_sentences():
    assert build_prompt(SENTENCES).splitlines() == ["1|一文目です。", "2|二文目です。", "3|三文目です。"]


def test_parse_orders_by_number_and_fills_gaps():
    assert parse_translations("3|셋\n1|하나", 3) == ["하나", "", "셋"]
    assert parse_translations("설명만 있고 번호가 없음", 3) is None
    assert parse_translations("9|범위 밖", 3) is None


def test_translate_returns_aligned_korean_and_sends_expected_request():
    client = _client("1|첫 번째 문장입니다.\n2|두 번째 문장입니다.\n3|세 번째 문장입니다.")
    assert translate_sentences(SENTENCES, client=client) == [
        "첫 번째 문장입니다.", "두 번째 문장입니다.", "세 번째 문장입니다."]
    kwargs = _client.last_kwargs
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in kwargs["betas"]
    assert kwargs["output_config"] == {"effort": "low"}
    assert "thinking" not in kwargs and "temperature" not in kwargs   # Opus 5.5는 두 값 모두 400
    assert kwargs["messages"][0]["content"].startswith("1|一文目です。")


def test_refusal_or_truncation_returns_none():
    assert translate_sentences(SENTENCES, client=_client("1|x", stop_reason="refusal")) is None
    assert translate_sentences(SENTENCES, client=_client("1|x", stop_reason="max_tokens")) is None


def test_api_errors_return_none_instead_of_raising():
    request = SimpleNamespace(method="POST", url="https://api.anthropic.com/v1/messages")
    for error in (anthropic.APIConnectionError(request=request),):
        assert translate_sentences(SENTENCES, client=_client(error=error)) is None


def test_no_api_key_skips_translation(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert translate_sentences(SENTENCES) is None
    assert translate_sentences([]) is None
