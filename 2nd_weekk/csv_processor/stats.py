"""Statistics computed over the set of valid, de-duplicated records."""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class SummaryStats:
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    duplicates_removed: int = 0
    average_salary: float = 0.0
    median_salary: float = 0.0
    min_salary: float = 0.0
    max_salary: float = 0.0
    average_age: float = 0.0
    youngest_age: int = 0
    oldest_age: int = 0
    headcount_by_department: dict[str, int] = field(default_factory=dict)


def compute_stats(
    records: list[dict],
    *,
    total_rows: int,
    invalid_rows: int,
    duplicates_removed: int,
) -> SummaryStats:
    """Aggregate statistics over valid records."""
    stats = SummaryStats(
        total_rows=total_rows,
        valid_rows=len(records),
        invalid_rows=invalid_rows,
        duplicates_removed=duplicates_removed,
    )

    if not records:
        return stats

    salaries = [float(r["salary"]) for r in records]
    ages = [int(r["age"]) for r in records]

    stats.average_salary = statistics.mean(salaries)
    stats.median_salary = statistics.median(salaries)
    stats.min_salary = min(salaries)
    stats.max_salary = max(salaries)
    stats.average_age = statistics.mean(ages)
    stats.youngest_age = min(ages)
    stats.oldest_age = max(ages)
    stats.headcount_by_department = dict(
        sorted(Counter(r["department"] for r in records).items())
    )
    return stats
