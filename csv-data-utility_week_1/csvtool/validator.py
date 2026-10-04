"""Row validation. Pure functions: a row goes in, a list of Issues comes out."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Dict, List, Mapping, Optional

from csvtool.config import Config
from csvtool.parsing import (
    collapse_ws,
    is_missing,
    is_valid_department,
    is_valid_email,
    is_valid_id,
    is_valid_name,
    parse_date,
    parse_int,
    parse_money,
)


@dataclass(frozen=True)
class Issue:
    field: str
    code: str
    message: str


def _show(value: str) -> str:
    text = collapse_ws(value)
    return repr(text if len(text) <= 40 else text[:37] + "...")


def _check_id(value: str, cfg: Config, today: date) -> List[Issue]:
    if is_valid_id(value):
        return []
    return [Issue("id", "invalid_id", f"invalid id {_show(value)} (use letters, digits, _ . -)")]


def _check_name(value: str, cfg: Config, today: date) -> List[Issue]:
    if is_valid_name(value):
        return []
    return [Issue("name", "invalid_name", f"invalid name {_show(value)} (letters only)")]


def _check_email(value: str, cfg: Config, today: date) -> List[Issue]:
    if is_valid_email(value):
        return []
    return [Issue("email", "invalid_email", f"invalid email {_show(value)}")]


def _check_age(value: str, cfg: Config, today: date) -> List[Issue]:
    age = parse_int(value)
    if age is None:
        return [Issue("age", "invalid_age", f"age is not a whole number: {_show(value)}")]
    if not cfg.age_min <= age <= cfg.age_max:
        return [
            Issue(
                "age",
                "age_out_of_range",
                f"age {age} outside {cfg.age_min}-{cfg.age_max}",
            )
        ]
    return []


def _check_salary(value: str, cfg: Config, today: date) -> List[Issue]:
    salary = parse_money(value)
    if salary is None:
        return [Issue("salary", "invalid_salary", f"salary is not a number: {_show(value)}")]
    if not cfg.salary_min <= salary <= cfg.salary_max:
        return [
            Issue(
                "salary",
                "salary_out_of_range",
                f"salary {salary:,.2f} outside {cfg.salary_min:,.2f}-{cfg.salary_max:,.2f}",
            )
        ]
    return []


def _check_department(value: str, cfg: Config, today: date) -> List[Issue]:
    if not is_valid_department(value):
        return [Issue("department", "invalid_department", f"invalid department {_show(value)}")]
    if cfg.allowed_departments is not None:
        if collapse_ws(value).upper() not in cfg.allowed_departments:
            return [
                Issue(
                    "department",
                    "department_not_allowed",
                    f"department {_show(value)} is not in the allowed list",
                )
            ]
    return []


def _check_join_date(value: str, cfg: Config, today: date) -> List[Issue]:
    parsed = parse_date(value, cfg.date_formats)
    if parsed is None:
        return [Issue("join_date", "invalid_date", f"invalid join_date {_show(value)}")]
    if parsed > today:
        return [Issue("join_date", "future_date", f"join_date {parsed.isoformat()} is in the future")]
    if parsed.year < cfg.min_join_year:
        return [
            Issue(
                "join_date",
                "date_out_of_range",
                f"join_date {parsed.isoformat()} is before {cfg.min_join_year}",
            )
        ]
    return []


_CHECKS: Dict[str, Callable[[str, Config, date], List[Issue]]] = {
    "id": _check_id,
    "name": _check_name,
    "email": _check_email,
    "age": _check_age,
    "salary": _check_salary,
    "department": _check_department,
    "join_date": _check_join_date,
}


def validate_record(
    data: Mapping[str, str], cfg: Config, today: Optional[date] = None
) -> List[Issue]:
    """Return every problem found in one row (an empty list means the row is valid)."""
    today = today or date.today()
    issues: List[Issue] = []
    for name in cfg.required_fields:
        if is_missing(data.get(name), cfg.missing_tokens):
            issues.append(Issue(name, "missing_field", f"missing required field '{name}'"))
    for name, check in _CHECKS.items():
        value = data.get(name)
        if value is not None and not is_missing(value, cfg.missing_tokens):
            issues.extend(check(value, cfg, today))
    return issues
