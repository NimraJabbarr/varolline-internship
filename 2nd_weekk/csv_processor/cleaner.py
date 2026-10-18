"""Normalization of raw rows before validation.

Cleaning rules:
  - Trim whitespace and collapse repeated internal spaces.
  - Names and departments are title-cased.
  - Emails are lower-cased.
  - Numeric fields have currency symbols, commas, and units stripped and
    are rendered in a canonical form ("30" for age, "85000.00" for salary).
  - Dates in any of the accepted input formats are normalized to ISO
    (YYYY-MM-DD). Unparseable values are left untouched so the validator
    can flag them.
"""

from __future__ import annotations

import re
from datetime import datetime

EXPECTED_FIELDS = [
    "employee_id",
    "name",
    "email",
    "age",
    "salary",
    "department",
    "join_date",
]

DATE_INPUT_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y")

_WHITESPACE_RE = re.compile(r"\s+")
_NON_NUMERIC_RE = re.compile(r"[^\d.\-]")


def _title_case(text: str, *, preserve_acronyms: bool = False) -> str:
    words = []
    for word in text.split(" "):
        if preserve_acronyms and word.isupper() and len(word) <= 3:
            words.append(word)
        else:
            words.append(word.capitalize())
    return " ".join(words)


def clean_text(
    value: object, *, title_case: bool = False, preserve_acronyms: bool = False
) -> str:
    if value is None:
        return ""
    cleaned = _WHITESPACE_RE.sub(" ", str(value)).strip()
    if not title_case:
        return cleaned
    return _title_case(cleaned, preserve_acronyms=preserve_acronyms)


def _clean_number(value: object) -> str:
    return _NON_NUMERIC_RE.sub("", clean_text(value))


def clean_age(value: object) -> str:
    text = _clean_number(value)
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def clean_salary(value: object) -> str:
    text = _clean_number(value)
    if not text:
        return ""
    try:
        return f"{float(text):.2f}"
    except ValueError:
        return text


def normalize_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def clean_row(row: dict) -> dict:
    """Return a normalized copy of one raw CSV row."""
    return {
        "employee_id": clean_text(row.get("employee_id")),
        "name": clean_text(row.get("name"), title_case=True),
        "email": clean_text(row.get("email")).lower(),
        "age": clean_age(row.get("age")),
        "salary": clean_salary(row.get("salary")),
        "department": clean_text(
            row.get("department"), title_case=True, preserve_acronyms=True
        ),
        "join_date": normalize_date(row.get("join_date")),
    }
