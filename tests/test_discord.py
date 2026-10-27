from datetime import datetime

import pytest

from modules import discord_sender as ds
from modules.config import load_config

SOURCES = [{"title": "題名", "url": "https://example.com/a", "source": "Yahoo"}]
VOCAB = [
    {"word": "懸念", "reading": "けねん", "meaning": "worry", "level": "N1"},
    {"word": "影響", "reading": "えいきょう", "meaning": "influence", "level": "N3"},
]


def test_news_embed_contents():
    embed = ds.build_news_embed(["一文目です。", "二文目です。"], SOURCES, "intermediate",
                                ["business"], now=datetime(2026, 10, 27))
    assert "2026年10月27日（火）" in embed["title"]
    assert "`01.` 一文目です。" in embed["description"]
    assert "[題名](https://example.com/a)" in embed["description"]
    assert len(embed["description"]) <= 4096


def test_news_embed_truncates_by_line_within_limit():
    sentences = [f"長い文章です。{'あ' * 100}" for _ in range(60)]
    desc = ds.build_news_embed(sentences, SOURCES, "intermediate", ["world"])["description"]
    assert len(desc) <= 4096
    assert desc.endswith("…（略）")
    assert all(line.startswith(("`", "**", "━", "…")) for line in desc.splitlines())


def test_vocab_embed_groups_by_level_and_empty_is_none():
    desc = ds.build_vocab_embed(VOCAB)["description"]
    assert desc.index("N1") < desc.index("N3")
    assert "• **懸念**（けねん）— worry" in desc
    assert ds.build_vocab_embed([]) is None


class _Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body, self.text = status, body or {}, str(body)

    def json(self):
        return self._body


def test_send_retries_once_on_rate_limit(monkeypatch):
    responses = iter([_Resp(429, {"retry_after": 0}), _Resp(204)])
    monkeypatch.setattr(ds, "_post", lambda url, payload: next(responses))
    monkeypatch.setattr(ds.time, "sleep", lambda s: None)
    assert ds.send_to_discord("u", ["文です。"], SOURCES, "intermediate", ["world"], VOCAB)


def test_send_reports_failure(monkeypatch):
    monkeypatch.setattr(ds, "_post", lambda url, payload: _Resp(400, {"message": "bad"}))
    assert not ds.send_to_discord("u", ["文です。"], SOURCES, "intermediate", ["world"], [])


def test_config_env_override_and_default_levels(tmp_path, monkeypatch):
    path = tmp_path / "c.json"
    path.write_text('{"difficulty": "intermediate", "vocab_levels": null}', encoding="utf-8")
    monkeypatch.setenv("WRITEJP_DIFFICULTY", "advanced")
    monkeypatch.setenv("WRITEJP_CATEGORIES", "sports, science")
    config = load_config(str(path))
    assert config["difficulty"] == "advanced"
    assert config["categories"] == ["sports", "science"]
    assert config["vocab_levels"] == ["N2", "N1"]


def test_config_rejects_unknown_difficulty(tmp_path, monkeypatch):
    path = tmp_path / "c.json"
    path.write_text('{"difficulty": "expert"}', encoding="utf-8")
    monkeypatch.delenv("WRITEJP_DIFFICULTY", raising=False)
    with pytest.raises(ValueError):
        load_config(str(path))
