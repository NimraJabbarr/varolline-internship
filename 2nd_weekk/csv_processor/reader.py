"""Reading of raw CSV input with robust error handling."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DataReadError(Exception):
    """Raised when the input file cannot be read as CSV."""


def read_csv(path: str | Path) -> tuple[list[str], list[dict]]:
    """Read a CSV file and return (headers, rows).

    Rows are returned as dicts keyed by the header names. Missing cells
    become None and surplus cells are kept under the None key so the
    validator can flag malformed rows instead of crashing.

    Raises:
        DataReadError: if the file is missing, empty, or not valid CSV.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise DataReadError(f"Input file not found: {file_path}")
    if file_path.is_dir():
        raise DataReadError(f"Expected a file but found a directory: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise DataReadError(f"Input file is empty: {file_path}")
            headers = [str(h).strip() for h in reader.fieldnames]
            rows = [dict(row) for row in reader]
    except UnicodeDecodeError as exc:
        raise DataReadError(f"File is not valid UTF-8 text: {file_path}") from exc
    except csv.Error as exc:
        raise DataReadError(f"Malformed CSV in {file_path}: {exc}") from exc
    except OSError as exc:
        raise DataReadError(f"Could not read {file_path}: {exc}") from exc

    logger.info("Read %d rows (%d columns) from %s", len(rows), len(headers), file_path)
    return headers, rows
