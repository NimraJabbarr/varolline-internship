from __future__ import annotations

import statistics

from csvtool.stats import compute_statistics


def test_empty_input() -> None:
    result = compute_statistics([])
    assert result["records"] == 0
    assert result["salary"] is None and result["age"] is None
    assert result["by_department"] == {} and result["highest_paid"] is None


def test_values_match_the_statistics_module() -> None:
    def row(i: str, name: str, salary: str, age: str, dept: str, joined: str) -> dict[str, str]:
        return {"id": i, "name": name, "salary": salary, "age": age, "department": dept, "join_date": joined}

    rows = [
        row("1", "A", "50000", "25", "IT", "2020-01-01"),
        row("2", "B", "60000", "30", "HR", "2020-05-01"),
        row("3", "C", "80000", "41", "IT", "2022-05-01"),
    ]
    result = compute_statistics(rows)
    salaries = [50000.0, 60000.0, 80000.0]
    assert result["salary"]["mean"] == round(statistics.mean(salaries), 2)
    assert result["salary"]["median"] == 60000.0
    assert result["salary"]["min"] == 50000.0 and result["salary"]["max"] == 80000.0
    assert result["salary"]["stdev"] == round(statistics.stdev(salaries), 2)
    assert result["salary"]["total"] == 190000.0
    assert result["age"]["mean"] == 32.0
    assert result["by_department"] == {
        "IT": {"count": 2, "avg_salary": 65000.0},
        "HR": {"count": 1, "avg_salary": 60000.0},
    }
    assert result["hires_by_year"] == {"2020": 2, "2022": 1}
    assert result["highest_paid"] == {"id": "3", "name": "C", "salary": 80000.0}


def test_single_row_has_zero_stdev_and_missing_columns_are_tolerated() -> None:
    result = compute_statistics([{"salary": "100"}])
    assert result["salary"]["stdev"] == 0.0
    assert result["age"] is None and result["by_department"] == {}
