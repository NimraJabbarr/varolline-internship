


"""Validation of cleaned rows against the employee record schema."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$")
MIN_AGE = 18
MAX_AGE = 70
ISO_DATE_FORMAT = "%Y-%m-%d"


@dataclass
class ValidationIssue:
    row_number: int
    field: str
    message: str

    def __str__(self) -> str:
        return f"Row {self.row_number}: [{self.field}] {self.message}"


@dataclass
class RecordResult:
    row_number: int
    data: dict
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_row(row: dict, row_number: int) -> RecordResult:
    """Validate one cleaned row and collect every issue found."""
    issues: list[ValidationIssue] = []

    def add(field_name: str, message: str) -> None:
        issues.append(ValidationIssue(row_number, field_name, message))

    employee_id = row.get("employee_id", "")
    if not employee_id:
        add("employee_id", "missing employee id")
    elif not employee_id.isdigit():
        add("employee_id", f"non-numeric id {employee_id!r}")

    if not row.get("name"):
        add("name", "missing name")

    email = row.get("email", "")
    if not email:
        add("email", "missing email")
    elif not EMAIL_PATTERN.match(email):
        add("email", f"invalid email {email!r}")

    age_raw = row.get("age", "")
    if not age_raw:
        add("age", "missing age")
    else:
        try:
            age = int(age_raw)
            if not MIN_AGE <= age <= MAX_AGE:
                add("age", f"age {age} outside allowed range {MIN_AGE}-{MAX_AGE}")
        except ValueError:
            add("age", f"age {age_raw!r} is not a number")

    salary_raw = row.get("salary", "")
    if not salary_raw:
        add("salary", "missing salary")
    else:
        try:
            salary = float(salary_raw)
            if salary <= 0:
                add("salary", f"salary {salary:.2f} must be positive")
        except ValueError:
            add("salary", f"salary {salary_raw!r} is not a number")

    if not row.get("department"):
        add("department", "missing department")

    join_date = row.get("join_date", "")
    if not join_date:
        add("join_date", "missing join date")
    else:
        try:
            datetime.strptime(join_date, ISO_DATE_FORMAT)
        except ValueError:
            add("join_date", f"unrecognized date {join_date!r}")

    return RecordResult(row_number=row_number, data=row, issues=issues)
