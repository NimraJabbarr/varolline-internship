from __future__ import annotations

from typing import Dict

from conftest import TODAY

from csvtool.cleaner import clean_record
from csvtool.config import Config
from csvtool.validator import validate_record


def codes(row: Dict[str, str], cfg: Config) -> set:  # type: ignore[type-arg]
    return {i.code for i in validate_record(row, cfg, TODAY)}


def test_valid_row_has_no_issues(good_row: Dict[str, str], cfg: Config) -> None:
    assert validate_record(good_row, cfg, TODAY) == []


def test_every_required_field_is_checked(good_row: Dict[str, str], cfg: Config) -> None:
    for name in cfg.required_fields:
        row = dict(good_row, **{name: "  "})
        assert "missing_field" in codes(row, cfg), name


def test_missing_column_entirely_counts_as_missing(good_row: Dict[str, str], cfg: Config) -> None:
    del good_row["email"]
    assert "missing_field" in codes(good_row, cfg)


def test_missing_token_counts_as_missing(good_row: Dict[str, str], cfg: Config) -> None:
    assert "missing_field" in codes(dict(good_row, salary="N/A"), cfg)


def test_each_invalid_value_gets_its_own_code(good_row: Dict[str, str], cfg: Config) -> None:
    cases = {
        "email": ("nope", "invalid_email"),
        "age": ("abc", "invalid_age"),
        "salary": ("abc", "invalid_salary"),
        "join_date": ("2021-02-30", "invalid_date"),
        "name": ("Ali9", "invalid_name"),
        "id": ("a b", "invalid_id"),
        "department": ("123", "invalid_department"),
    }
    for field, (value, code) in cases.items():
        assert code in codes(dict(good_row, **{field: value}), cfg), field


def test_ranges(good_row: Dict[str, str], cfg: Config) -> None:
    assert "age_out_of_range" in codes(dict(good_row, age="-5"), cfg)
    assert "age_out_of_range" in codes(dict(good_row, age="150"), cfg)
    assert "salary_out_of_range" in codes(dict(good_row, salary="0"), cfg)
    assert "salary_out_of_range" in codes(dict(good_row, salary="-10"), cfg)
    assert "future_date" in codes(dict(good_row, join_date="2026-10-04"), cfg)
    assert "date_out_of_range" in codes(dict(good_row, join_date="1900-01-01"), cfg)
    assert codes(dict(good_row, join_date="2026-10-03"), cfg) == set()  # today is allowed


def test_nan_and_inf_salary_are_rejected(good_row: Dict[str, str], cfg: Config) -> None:
    for bad in ("nan", "inf", "-inf", "Infinity"):
        assert codes(dict(good_row, salary=bad), cfg), bad


def test_allowed_departments(good_row: Dict[str, str]) -> None:
    cfg = Config.from_dict({"allowed_departments": ["it", "HR"]})
    assert codes(good_row, cfg) == set()
    assert "department_not_allowed" in codes(dict(good_row, department="Finance"), cfg)


def test_clean_record_rules(cfg: Config) -> None:
    raw = {
        "id": " 1 ",
        "name": "  sara   AHMED ",
        "email": " SARA@Example.COM ",
        "age": "30.0",
        "salary": "Rs. 60,000",
        "department": " human  resources",
        "join_date": "10/03/2021",
        "notes": "N/A",
    }
    assert clean_record(raw, cfg) == {
        "id": "1",
        "name": "Sara Ahmed",
        "email": "sara@example.com",
        "age": "30",
        "salary": "60000",
        "department": "HUMAN RESOURCES",
        "join_date": "2021-03-10",
        "notes": "",
    }


def test_clean_record_leaves_unparseable_values_for_the_validator(cfg: Config) -> None:
    raw = {"age": "abc", "salary": "x", "join_date": "soon", "email": "NOPE"}
    assert clean_record(raw, cfg) == {"age": "abc", "salary": "x", "join_date": "soon", "email": "nope"}


def test_clean_record_does_not_mutate_input(cfg: Config) -> None:
    raw = {"name": " ali "}
    clean_record(raw, cfg)
    assert raw == {"name": " ali "}
