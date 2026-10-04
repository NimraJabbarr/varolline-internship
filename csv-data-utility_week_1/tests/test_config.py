from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import ROOT

from csvtool.config import Config, load_config
from csvtool.errors import ConfigError


def test_defaults_when_no_path() -> None:
    assert load_config(None) == Config()


def test_shipped_json_config_equals_defaults() -> None:
    assert load_config(ROOT / "config" / "rules.json") == Config()


def test_shipped_yaml_config_equals_defaults() -> None:
    pytest.importorskip("yaml")
    assert load_config(ROOT / "config" / "rules.yaml") == Config()


def test_partial_override(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"age_min": 18, "unique_keys": ["ID"]}))
    cfg = load_config(path)
    assert cfg.age_min == 18 and cfg.unique_keys == ["id"] and cfg.age_max == 100


@pytest.mark.parametrize(
    "payload",
    [
        {"agee_min": 1},  # typo
        {"age_min": "18"},
        {"age_min": True},
        {"age_min": 50, "age_max": 20},
        {"salary_min": float("nan")},
        {"date_formats": ["%Q-bad"]},
        {"date_formats": []},
        {"required_fields": []},
        {"unique_keys": [""]},
        {"allowed_departments": []},
        {"missing_tokens": "n/a"},
    ],
)
def test_invalid_config_values(payload: dict, tmp_path: Path) -> None:  # type: ignore[type-arg]
    path = tmp_path / "c.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ConfigError):
        load_config(path)


def test_bad_files(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(ConfigError, match="invalid JSON"):
        load_config(bad)
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2]")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(arr)
    odd = tmp_path / "c.ini"
    odd.write_text("x=1")
    with pytest.raises(ConfigError, match="unsupported"):
        load_config(odd)
