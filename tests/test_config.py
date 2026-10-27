from datetime import date, timedelta

import pytest

from modules.config import ROTATION_START, load_config, resolve_categories

CONFIG = {"categories": ["business", "world", "science"], "rotate_categories": True}


def test_rotates_business_world_science_one_per_day():
    days = [ROTATION_START + timedelta(days=i) for i in range(7)]
    assert [resolve_categories(CONFIG, d) for d in days] == [
        ["business"], ["world"], ["science"], ["business"], ["world"], ["science"], ["business"]]


def test_rotation_also_works_before_start_date():
    assert resolve_categories(CONFIG, ROTATION_START - timedelta(days=1)) == ["science"]


def test_no_rotation_returns_all_categories():
    config = {**CONFIG, "rotate_categories": False}
    assert resolve_categories(config, date(2026, 10, 28)) == ["business", "world", "science"]


def test_single_category_is_returned_as_is():
    assert resolve_categories({"categories": ["world"], "rotate_categories": True}, date(2026, 1, 1)) == ["world"]


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("WRITEJP_DIFFICULTY", raising=False)
    monkeypatch.delenv("WRITEJP_CATEGORIES", raising=False)


def test_shipped_config_matches_requested_setup(clean_env):
    config = load_config("config.json")
    assert config["difficulty"] == "intermediate"
    assert config["sentence_count"] == 8
    assert config["categories"] == ["business", "world", "science"]
    assert config["rotate_categories"] is True
    assert config["vocab_levels"] == ["N3", "N2"]


def test_manual_category_input_disables_rotation(clean_env, monkeypatch):
    monkeypatch.setenv("WRITEJP_CATEGORIES", "science")
    config = load_config("config.json")
    assert config["categories"] == ["science"]
    assert config["rotate_categories"] is False
