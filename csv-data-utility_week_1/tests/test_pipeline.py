from __future__ import annotations

import pytest
from conftest import SAMPLE_CSV, TODAY

from csvtool.config import Config
from csvtool.errors import ConfigError
from csvtool.pipeline import run_pipeline
from csvtool.reader import read_table


def test_sample_file_exact_expectations(cfg: Config) -> None:
    result = run_pipeline(read_table(SAMPLE_CSV), cfg, TODAY)
    assert (result.total_rows, result.blank_rows) == (14, 1)
    assert (result.valid_count, result.invalid_count, result.duplicate_count) == (6, 6, 2)
    assert [r.data["id"] for r in result.valid] == ["1", "2", "6", "7", "8", "13"]
    # 14 physical data lines: header is line 1, so id=3 is line 4, etc.
    reasons = {r.record.line: (r.status, r.reason) for r in result.rejected}
    assert reasons[4][0] == "invalid" and "name" in reasons[4][1]
    assert reasons[5] == ("duplicate", "duplicate id (first seen on line 2)")
    assert reasons[12] == ("duplicate", "duplicate email (first seen on line 8)")
    assert reasons[14][1].endswith("is in the future")
    # independently hand-calculated from the 6 valid rows
    assert result.stats["salary"]["mean"] == 67166.67
    assert result.stats["salary"]["median"] == 62500.0
    assert result.stats["age"]["mean"] == 33.83
    assert result.stats["by_department"]["HR"] == {"count": 2, "avg_salary": 62500.0}


def test_every_row_lands_in_exactly_one_bucket(cfg: Config) -> None:
    result = run_pipeline(read_table(SAMPLE_CSV), cfg, TODAY)
    assert result.valid_count + len(result.rejected) == result.total_rows
    lines = [r.line for r in result.valid] + [r.record.line for r in result.rejected]
    assert len(lines) == len(set(lines)) == result.total_rows


def test_invalid_first_row_does_not_shadow_a_valid_later_one(write, cfg: Config) -> None:  # type: ignore[no-untyped-def]
    text = (
        "id,name,email,age,salary,department,join_date\n"
        "1,,a@x.com,30,100,IT,2020-01-01\n"  # invalid, must NOT claim id=1 / a@x.com
        "1,Ali,a@x.com,30,100,IT,2020-01-01\n"
    )
    result = run_pipeline(read_table(write("p.csv", text)), cfg, TODAY)
    assert result.valid_count == 1 and result.valid[0].line == 3
    assert result.invalid_count == 1 and result.duplicate_count == 0


def test_duplicates_are_case_and_whitespace_insensitive(write, cfg: Config) -> None:  # type: ignore[no-untyped-def]
    text = (
        "id,name,email,age,salary,department,join_date\n"
        "E1,Ali,a@x.com,30,100,IT,2020-01-01\n"
        "e1 ,Bob,b@x.com,30,100,IT,2020-01-01\n"
        "E2,Cat, A@X.COM ,30,100,IT,2020-01-01\n"
    )
    result = run_pipeline(read_table(write("d.csv", text)), cfg, TODAY)
    assert result.valid_count == 1 and result.duplicate_count == 2


def test_custom_unique_keys(write) -> None:  # type: ignore[no-untyped-def]
    text = (
        "id,name,email,age,salary,department,join_date\n"
        "1,Ali,a@x.com,30,100,IT,2020-01-01\n"
        "2,Bob,a@x.com,30,100,IT,2020-01-01\n"
    )
    cfg = Config.from_dict({"unique_keys": ["id"]})
    assert run_pipeline(read_table(write("k.csv", text)), cfg, TODAY).valid_count == 2


def test_unknown_unique_key_is_a_config_error(write) -> None:  # type: ignore[no-untyped-def]
    table = read_table(write("u.csv", "id,name\n1,Ali\n"))
    cfg = Config.from_dict({"required_fields": ["id"], "unique_keys": ["email"]})
    with pytest.raises(ConfigError, match="unique key"):
        run_pipeline(table, cfg, TODAY)


def test_malformed_rows_are_rejected(write, cfg: Config) -> None:  # type: ignore[no-untyped-def]
    text = (
        "id,name,email,age,salary,department,join_date\n"
        "1,Ali,a@x.com,30,100,IT,2020-01-01,EXTRA\n"
        "2,Bob,b@x.com,30,100,IT\n"
    )
    result = run_pipeline(read_table(write("m.csv", text)), cfg, TODAY)
    assert result.valid_count == 0
    assert "malformed_row" in result.issue_counts


def test_all_invalid_gives_empty_but_well_formed_result(write, cfg: Config) -> None:  # type: ignore[no-untyped-def]
    text = "id,name,email,age,salary,department,join_date\n1,,,,,,\n"
    result = run_pipeline(read_table(write("a.csv", text)), cfg, TODAY)
    assert result.valid_count == 0 and result.stats["records"] == 0


def test_json_input_goes_through_same_rules(cfg: Config) -> None:
    from conftest import SAMPLE_JSON

    result = run_pipeline(read_table(SAMPLE_JSON), cfg, TODAY)
    assert result.valid_count == 3 and result.invalid_count == 1  # id 3 has age null
    maryam = result.valid[1].data
    assert maryam["salary"] == "95000" and maryam["join_date"] == "2019-08-15"
    assert result.valid[0].data["name"] == "Hamza Tariq"
    assert result.valid[0].data["email"] == "hamza@example.com"
