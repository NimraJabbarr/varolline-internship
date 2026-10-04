"""Normalisation rules. Values that cannot be normalised are left as-is for the validator."""

from __future__ import annotations

from typing import Dict, Mapping

from csvtool.config import Config
from csvtool.parsing import (
    collapse_ws,
    format_number,
    parse_date,
    parse_int,
    parse_money,
    title_case,
)


def clean_record(data: Mapping[str, str], cfg: Config) -> Dict[str, str]:
    """Return a normalised copy of one row.

    Rules:
      * every cell: trim, collapse inner whitespace, drop invisible characters
      * missing tokens ('N/A', 'null', '-', ...) become ''
      * email -> lowercase;  name -> Title Case;  department -> UPPERCASE
      * age -> plain integer ('25.0' -> '25')
      * salary -> plain number ('Rs. 60,000' -> '60000')
      * join_date -> ISO 'YYYY-MM-DD'
    """
    cleaned: Dict[str, str] = {}
    for key, raw in data.items():
        value = collapse_ws(raw)
        if value.lower() in cfg.missing_tokens:
            value = ""
        if value:
            value = _normalise_field(key, value, cfg)
        cleaned[key] = value
    return cleaned


def _normalise_field(key: str, value: str, cfg: Config) -> str:
    if key == "email":
        return value.lower()
    if key == "name":
        return title_case(value)
    if key == "department":
        return value.upper()
    if key == "age":
        age = parse_int(value)
        return str(age) if age is not None else value
    if key == "salary":
        salary = parse_money(value)
        return format_number(salary) if salary is not None else value
    if key == "join_date":
        parsed = parse_date(value, cfg.date_formats)
        return parsed.isoformat() if parsed is not None else value
    return value
