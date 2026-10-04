from __future__ import annotations

import pytest

from csvtool.parsing import (
    collapse_ws,
    format_number,
    is_missing,
    is_valid_department,
    is_valid_email,
    is_valid_id,
    is_valid_name,
    parse_date,
    parse_int,
    parse_money,
    title_case,
)

FORMATS = ["%Y-%m-%d", "%d/%m/%Y"]


def test_collapse_ws_handles_none_tabs_and_invisible_chars() -> None:
    assert collapse_ws(None) == ""
    assert collapse_ws("  a \t b\n c ") == "a b c"
    assert collapse_ws("﻿Ali​") == "Ali"


def test_is_missing() -> None:
    tokens = ["n/a", "null"]
    assert is_missing(None, tokens)
    assert is_missing("   ", tokens)
    assert is_missing("N/A", tokens)
    assert not is_missing("Ali", tokens)
    assert not is_missing("0", tokens)


@pytest.mark.parametrize("text,expected", [("25", 25), ("+25", 25), (" 25.0 ", 25), ("0", 0), ("-5", -5)])
def test_parse_int_ok(text: str, expected: int) -> None:
    assert parse_int(text) == expected


@pytest.mark.parametrize("text", ["25.5", "abc", "", "1e3", "2 5", "nan", "٢٥x"])
def test_parse_int_rejects(text: str) -> None:
    assert parse_int(text) is None


def test_parse_int_huge_digit_string_does_not_crash() -> None:
    parse_int("9" * 6000)  # Python >= 3.11 refuses to convert this; we must not crash either way


@pytest.mark.parametrize(
    "text,expected",
    [("50000", 50000.0), ("60,000", 60000.0), ("Rs. 1,250.50", 1250.5), ("$99", 99.0), ("61000.50", 61000.5)],
)
def test_parse_money_ok(text: str, expected: float) -> None:
    assert parse_money(text) == expected


@pytest.mark.parametrize("text", ["abc", "", "nan", "inf", "-inf", "1e5", "1,00", "12.", "1" * 400])
def test_parse_money_rejects(text: str) -> None:
    assert parse_money(text) is None


def test_format_number() -> None:
    assert format_number(50000.0) == "50000"
    assert format_number(61000.5) == "61000.50"
    assert format_number(10.005 + 0.0001) in ("10.01", "10.00")


def test_parse_date_formats_and_invalid_calendar_dates() -> None:
    assert parse_date("2022-01-15", FORMATS).isoformat() == "2022-01-15"  # type: ignore[union-attr]
    assert parse_date("10/03/2021", FORMATS).isoformat() == "2021-03-10"  # type: ignore[union-attr]
    assert parse_date("2021-02-30", FORMATS) is None
    assert parse_date("not-a-date", FORMATS) is None
    assert parse_date("", FORMATS) is None


@pytest.mark.parametrize("email", ["ali@example.com", "a.b+c@sub.example.co.uk", "x_y@a-b.org"])
def test_valid_emails(email: str) -> None:
    assert is_valid_email(email)


@pytest.mark.parametrize(
    "email",
    ["bad-email", "a@b", "@example.com", "a@@b.com", "a b@c.com", "a..b@c.com", "a.@c.com",
     "a@c.com x", "+x@c.com", "a@-c.com", "a@c.c"],
)
def test_invalid_emails(email: str) -> None:
    assert not is_valid_email(email)


def test_names() -> None:
    assert is_valid_name("Ali Khan")
    assert is_valid_name("O'Neil-Smith Jr.")
    assert is_valid_name("نمرہ")
    assert not is_valid_name("Ali123")
    assert not is_valid_name("=cmd")
    assert not is_valid_name("")
    assert not is_valid_name("A" * 101)


def test_id_and_department() -> None:
    assert is_valid_id("E-001") and not is_valid_id("a b") and not is_valid_id("")
    assert is_valid_department("R&D") and is_valid_department("Human Resources")
    assert not is_valid_department("123") and not is_valid_department("=SUM(A1)")


def test_title_case() -> None:
    assert title_case("ali KHAN") == "Ali Khan"
    assert title_case("o'neil") == "O'Neil"
    assert title_case("anne-marie") == "Anne-Marie"
