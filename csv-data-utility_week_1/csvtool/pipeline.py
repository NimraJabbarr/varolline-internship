"""The processing pipeline: clean -> validate -> de-duplicate -> statistics (no file I/O)."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from csvtool.cleaner import clean_record
from csvtool.config import Config
from csvtool.errors import ConfigError
from csvtool.parsing import collapse_ws
from csvtool.reader import Record, Table
from csvtool.stats import compute_statistics
from csvtool.validator import Issue, validate_record

log = logging.getLogger(__name__)


@dataclass
class Rejected:
    """A row that did not make it into the cleaned output."""

    record: Record  # the ORIGINAL, uncleaned row
    status: str  # 'invalid' or 'duplicate'
    issues: List[Issue] = field(default_factory=list)
    duplicate_of: Optional[int] = None
    duplicate_key: str = ""

    @property
    def reason(self) -> str:
        if self.status == "duplicate":
            return f"duplicate {self.duplicate_key} (first seen on line {self.duplicate_of})"
        return "; ".join(issue.message for issue in self.issues)


@dataclass
class PipelineResult:
    columns: List[str]
    total_rows: int
    blank_rows: int
    valid: List[Record]  # cleaned rows
    rejected: List[Rejected]
    issue_counts: Dict[str, int]
    stats: Dict[str, Any]

    @property
    def valid_count(self) -> int:
        return len(self.valid)

    @property
    def invalid_count(self) -> int:
        return sum(1 for r in self.rejected if r.status == "invalid")

    @property
    def duplicate_count(self) -> int:
        return sum(1 for r in self.rejected if r.status == "duplicate")


def run_pipeline(table: Table, cfg: Config, today: Optional[date] = None) -> PipelineResult:
    """Process a Table. Every input row ends up in exactly one of: valid, invalid, duplicate."""
    for key in cfg.unique_keys:
        if key not in table.columns:
            raise ConfigError(f"unique key {key!r} is not a column in the input")

    today = today or date.today()
    seen: Dict[Tuple[str, str], int] = {}
    valid: List[Record] = []
    rejected: List[Rejected] = []
    issue_counts: Counter = Counter()  # type: ignore[type-arg]

    for record in table.records:
        cleaned = clean_record(record.data, cfg)
        issues = validate_record(cleaned, cfg, today)
        issues.extend(Issue("*", "malformed_row", problem) for problem in record.problems)

        if issues:
            rejected.append(Rejected(record, "invalid", issues))
            issue_counts.update(issue.code for issue in issues)
            log.warning("line %d rejected (invalid): %s", record.line, rejected[-1].reason)
            continue

        clash = _find_clash(cleaned, cfg.unique_keys, seen)
        if clash is not None:
            key, first_line = clash
            rejected.append(
                Rejected(record, "duplicate", duplicate_of=first_line, duplicate_key=key)
            )
            log.warning("line %d rejected (duplicate): %s", record.line, rejected[-1].reason)
            continue

        for key in cfg.unique_keys:
            value = _norm_key(cleaned.get(key, ""))
            if value:
                seen[(key, value)] = record.line
        valid.append(Record(line=record.line, data=cleaned))

    return PipelineResult(
        columns=list(table.columns),
        total_rows=len(table.records),
        blank_rows=table.blank_rows,
        valid=valid,
        rejected=rejected,
        issue_counts=dict(sorted(issue_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        stats=compute_statistics([r.data for r in valid]),
    )


def _norm_key(value: str) -> str:
    return collapse_ws(value).casefold()


def _find_clash(
    cleaned: Dict[str, str], keys: List[str], seen: Dict[Tuple[str, str], int]
) -> Optional[Tuple[str, int]]:
    for key in keys:
        value = _norm_key(cleaned.get(key, ""))
        if value and (key, value) in seen:
            return key, seen[(key, value)]
    return None
