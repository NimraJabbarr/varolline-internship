from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from csvtool.config import Config

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = ROOT / "data" / "sample" / "employees.csv"
SAMPLE_JSON = ROOT / "data" / "sample" / "employees.json"
TODAY = date(2026, 10, 3)  # fixed so "future date" tests never rot


@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def good_row() -> dict:  # type: ignore[type-arg]
    return {
        "id": "1",
        "name": "Ali Khan",
        "email": "ali@example.com",
        "age": "25",
        "salary": "50000",
        "department": "IT",
        "join_date": "2022-01-15",
    }


@pytest.fixture
def write(tmp_path: Path):  # type: ignore[no-untyped-def]
    def _write(name: str, text: str, encoding: str = "utf-8") -> Path:
        path = tmp_path / name
        path.write_bytes(text.encode(encoding))
        return path

    return _write
