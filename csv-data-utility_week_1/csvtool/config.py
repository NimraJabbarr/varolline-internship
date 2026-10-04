"""Validation/cleaning rules, loadable from a JSON or YAML file."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from csvtool.errors import ConfigError

DEFAULT_REQUIRED = ["id", "name", "email", "age", "salary", "department", "join_date"]


@dataclass
class Config:
    """All tunable rules. Defaults work for an employee file."""

    required_fields: List[str] = field(default_factory=lambda: list(DEFAULT_REQUIRED))
    # A row is a duplicate if ANY of these columns repeats a value already accepted.
    unique_keys: List[str] = field(default_factory=lambda: ["id", "email"])
    # Cell values (case-insensitive) that mean "nothing here".
    missing_tokens: List[str] = field(
        default_factory=lambda: ["n/a", "na", "null", "none", "nan", "-", "--", "?"]
    )
    age_min: int = 16
    age_max: int = 100
    salary_min: float = 1.0
    salary_max: float = 10_000_000.0
    # Tried in order. Slash/dash dates are DAY first (10/03/2021 = 10 March 2021).
    date_formats: List[str] = field(
        default_factory=lambda: ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    )
    min_join_year: int = 1950
    # None = any department is accepted.
    allowed_departments: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Config":
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise ConfigError(
                f"unknown config key(s): {', '.join(unknown)}. "
                f"Valid keys: {', '.join(sorted(known))}"
            )
        cfg = cls()
        for key, value in raw.items():
            if key in ("required_fields", "unique_keys"):
                setattr(cfg, key, [s.lower() for s in _str_list(key, value, allow_empty=False)])
            elif key == "missing_tokens":
                setattr(cfg, key, [s.lower() for s in _str_list(key, value, allow_empty=True)])
            elif key == "date_formats":
                cfg.date_formats = _str_list(key, value, allow_empty=False)
            elif key == "allowed_departments":
                if value is None:
                    cfg.allowed_departments = None
                else:
                    cfg.allowed_departments = [
                        " ".join(s.split()).upper()
                        for s in _str_list(key, value, allow_empty=False)
                    ]
            elif key in ("age_min", "age_max", "min_join_year"):
                setattr(cfg, key, _int(key, value))
            else:  # salary_min / salary_max
                setattr(cfg, key, _number(key, value))
        cfg._check_consistency()
        return cfg

    def _check_consistency(self) -> None:
        if self.age_min > self.age_max:
            raise ConfigError("age_min must be <= age_max")
        if self.salary_min > self.salary_max:
            raise ConfigError("salary_min must be <= salary_max")
        probe = date(2000, 1, 2)
        for fmt in self.date_formats:
            try:
                if datetime.strptime(probe.strftime(fmt), fmt).date() != probe:
                    raise ValueError("does not round-trip")
            except ValueError as exc:
                raise ConfigError(f"invalid date format {fmt!r}: {exc}") from exc


def _str_list(name: str, value: Any, allow_empty: bool) -> List[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"'{name}' must be a list of strings")
    cleaned = [v.strip() for v in value]
    if any(not v for v in cleaned):
        raise ConfigError(f"'{name}' must not contain empty strings")
    if not cleaned and not allow_empty:
        raise ConfigError(f"'{name}' must not be empty")
    return cleaned


def _int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"'{name}' must be a whole number")
    return value


def _number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigError(f"'{name}' must be a finite number")
    return float(value)


def load_config(path: Optional[Path]) -> Config:
    """Load rules from ``path`` (.json / .yaml / .yml). ``None`` returns the defaults."""
    if path is None:
        return Config()
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"cannot read config file {path}: {exc}") from exc

    suffix = path.suffix.lower()
    raw: Any
    if suffix == ".json":
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ConfigError("YAML config needs PyYAML: pip install pyyaml") from exc
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
        if raw is None:
            raw = {}
    else:
        raise ConfigError(f"unsupported config type {suffix!r} (use .json, .yaml or .yml)")

    if not isinstance(raw, dict):
        raise ConfigError("config file must contain a key/value mapping at the top level")
    result: Dict[str, Any] = raw
    return Config.from_dict(result)
