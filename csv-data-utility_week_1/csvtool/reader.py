"""Read CSV/TSV/JSON files into a uniform Table of string records."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from csvtool.errors import ReaderError
from csvtool.parsing import collapse_ws

log = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (".csv", ".tsv", ".txt", ".json")


@dataclass
class Record:
    """One input row. ``line`` is the line (CSV) or item number (JSON) for error messages."""

    line: int
    data: Dict[str, str]
    problems: List[str] = field(default_factory=list)


@dataclass
class Table:
    columns: List[str]
    records: List[Record]
    blank_rows: int = 0


def normalize_header(name: str) -> str:
    """' Join Date ' -> 'join_date'."""
    return collapse_ws(name).lower().replace(" ", "_")


def read_table(
    path: Path,
    required: Sequence[str] = (),
    encoding: str = "utf-8-sig",
    delimiter: Optional[str] = None,
) -> Table:
    """Read ``path`` and return a Table. Raises ReaderError for any input problem."""
    path = Path(path)
    if not path.exists():
        raise ReaderError(f"input file not found: {path}")
    if not path.is_file():
        raise ReaderError(f"input path is not a file: {path}")
    try:
        if path.stat().st_size == 0:
            raise ReaderError(f"input file is empty: {path}")
    except OSError as exc:
        raise ReaderError(f"cannot access {path}: {exc}") from exc

    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            table = _read_json(path, encoding)
        elif suffix in (".csv", ".tsv", ".txt"):
            sep = delimiter or ("\t" if suffix == ".tsv" else ",")
            table = _read_csv(path, encoding, sep)
        else:
            raise ReaderError(
                f"unsupported input type {suffix or '(none)'!r}; "
                f"supported: {', '.join(SUPPORTED_SUFFIXES)}"
            )
    except UnicodeDecodeError as exc:
        raise ReaderError(
            f"cannot decode {path} as {encoding}. Try --encoding cp1252 or --encoding latin-1."
        ) from exc
    except LookupError as exc:  # unknown codec name
        raise ReaderError(f"unknown encoding {encoding!r}") from exc
    except PermissionError as exc:
        raise ReaderError(f"permission denied reading {path}") from exc
    except OSError as exc:
        raise ReaderError(f"cannot read {path}: {exc}") from exc

    missing = [col for col in required if col not in table.columns]
    if missing:
        raise ReaderError(
            f"missing required column(s): {', '.join(missing)}. "
            f"Columns found: {', '.join(table.columns)}"
        )
    if not table.records:
        raise ReaderError(f"{path} has no data rows")
    log.info("read %d row(s) and %d column(s) from %s", len(table.records), len(table.columns), path)
    return table


def _read_csv(path: Path, encoding: str, delimiter: str) -> Table:
    try:
        with path.open("r", encoding=encoding, newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header = next(reader, None)
            if header is None:
                raise ReaderError(f"input file is empty: {path}")
            columns = [normalize_header(h) for h in header]
            if any(not c for c in columns):
                raise ReaderError("header row contains an empty column name")
            duplicates = sorted({c for c in columns if columns.count(c) > 1})
            if duplicates:
                raise ReaderError(f"duplicate column name(s) in header: {', '.join(duplicates)}")

            records: List[Record] = []
            blank = 0
            width = len(columns)
            for cells in reader:
                if all(not collapse_ws(c) for c in cells):
                    blank += 1
                    continue
                problems: List[str] = []
                if len(cells) > width:
                    problems.append(f"row has {len(cells) - width} more cell(s) than the header")
                elif len(cells) < width:
                    problems.append(f"row has {width - len(cells)} fewer cell(s) than the header")
                data = {col: (cells[i] if i < len(cells) else "") for i, col in enumerate(columns)}
                records.append(Record(line=reader.line_num, data=data, problems=problems))
    except csv.Error as exc:
        raise ReaderError(f"malformed CSV in {path}: {exc}") from exc
    return Table(columns=columns, records=records, blank_rows=blank)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _read_json(path: Path, encoding: str) -> Table:
    try:
        with path.open("r", encoding=encoding) as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ReaderError(f"invalid JSON in {path}: {exc}") from exc
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        payload = payload["records"]
    if not isinstance(payload, list):
        raise ReaderError("JSON input must be a list of objects (or {\"records\": [...]})")

    columns: List[str] = []
    records: List[Record] = []
    blank = 0
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ReaderError(f"JSON item {index} is not an object")
        data: Dict[str, str] = {}
        for key, value in item.items():
            col = normalize_header(str(key))
            if not col:
                raise ReaderError(f"JSON item {index} has an empty key")
            if col in data:
                raise ReaderError(f"JSON item {index} has duplicate key {col!r}")
            data[col] = _stringify(value)
            if col not in columns:
                columns.append(col)
        if all(not collapse_ws(v) for v in data.values()):
            blank += 1
            continue
        records.append(Record(line=index, data=data))
    for record in records:  # JSON objects may omit keys; fill so every row has every column
        for col in columns:
            record.data.setdefault(col, "")
    return Table(columns=columns, records=records, blank_rows=blank)
