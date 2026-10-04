"""Small, pure parsing helpers shared by the cleaner and the validator."""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from typing import Collection, Optional, Sequence

_WS = re.compile(r"\s+")
_INVISIBLE = re.compile("[​‌‍⁠﻿]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INT = re.compile(r"[+-]?[0-9]+(?:\.0+)?")
_CURRENCY = re.compile(r"^(?:rs\.?|pkr|usd|\$|€|£)\s*", re.IGNORECASE)
_MONEY = re.compile(r"[+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")
_EMAIL = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._%+-]*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
)
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,49}")
_DEPARTMENT = re.compile(r"[^\W\d_][\w &/-]{0,49}")
_LETTER_RUN = re.compile(r"[^\W\d_]+")


def collapse_ws(value: Optional[str]) -> str:
    """Strip invisible characters, trim, and squash runs of whitespace to one space."""
    if value is None:
        return ""
    return _WS.sub(" ", _INVISIBLE.sub("", value)).strip()


def strip_control(value: str) -> str:
    return _CONTROL.sub("", value)


def is_missing(value: Optional[str], tokens: Collection[str] = ()) -> bool:
    """True for None, blanks, or any of the configured 'missing' tokens."""
    text = collapse_ws(value)
    return text == "" or text.lower() in tokens


def parse_int(value: str) -> Optional[int]:
    """'25', '+25', '25.0' -> 25.  Anything else (including '25.5', 'abc') -> None."""
    text = collapse_ws(value)
    if not _INT.fullmatch(text):
        return None
    try:
        return int(text.split(".")[0])
    except ValueError:  # absurdly long digit strings
        return None


def parse_money(value: str) -> Optional[float]:
    """'50000', '60,000', 'Rs. 1,250.50', '$99' -> float.  nan/inf/garbage -> None."""
    text = _CURRENCY.sub("", collapse_ws(value))
    if not _MONEY.fullmatch(text):
        return None
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def format_number(number: float) -> str:
    """50000.0 -> '50000', 61000.5 -> '61000.50'."""
    rounded = round(number, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}"


def parse_date(value: str, formats: Sequence[str]) -> Optional[date]:
    text = collapse_ws(value)
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def is_valid_email(value: str) -> bool:
    text = collapse_ws(value)
    if len(text) > 254 or ".." in text or not _EMAIL.fullmatch(text):
        return False
    return not text.split("@", 1)[0].endswith(".")


def is_valid_id(value: str) -> bool:
    return bool(_ID.fullmatch(collapse_ws(value)))


def is_valid_name(value: str) -> bool:
    """Letters (any script), spaces, apostrophes, dots and hyphens; must start with a letter."""
    text = collapse_ws(value)
    if not 1 <= len(text) <= 100 or not text[0].isalpha():
        return False
    return all(unicodedata.category(ch)[0] in "LM" or ch in " '.-" for ch in text)


def is_valid_department(value: str) -> bool:
    return bool(_DEPARTMENT.fullmatch(collapse_ws(value)))


def title_case(value: str) -> str:
    """'ali KHAN' -> 'Ali Khan', "o'neil" -> "O'Neil", 'anne-marie' -> 'Anne-Marie'."""
    return _LETTER_RUN.sub(lambda m: m.group().capitalize(), value)
