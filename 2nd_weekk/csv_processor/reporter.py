"""Export of the cleaned dataset and a human-readable summary report."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from .stats import SummaryStats
from .validator import ValidationIssue

logger = logging.getLogger(__name__)

MAX_ISSUES_IN_REPORT = 25


def write_cleaned_csv(records: list[dict], fieldnames: list[str], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info("Wrote %d cleaned records to %s", len(records), out)
    return out


def write_summary_report(
    stats: SummaryStats,
    issues: list[ValidationIssue],
    duplicates: list[str],
    path: str | Path,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "=" * 52,
        " CSV DATA PROCESSING - SUMMARY REPORT",
        "=" * 52,
        f"Generated          : {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "--- Row accounting ---",
        f"Total input rows   : {stats.total_rows}",
        f"Valid records      : {stats.valid_rows}",
        f"Invalid rows       : {stats.invalid_rows}",
        f"Duplicates removed : {stats.duplicates_removed}",
        "",
        "--- Salary statistics (valid records) ---",
        f"Average salary     : {stats.average_salary:,.2f}",
        f"Median salary      : {stats.median_salary:,.2f}",
        f"Min salary         : {stats.min_salary:,.2f}",
        f"Max salary         : {stats.max_salary:,.2f}",
        "",
        "--- Age statistics (valid records) ---",
        f"Average age        : {stats.average_age:.1f}",
        f"Youngest           : {stats.youngest_age}",
        f"Oldest             : {stats.oldest_age}",
        "",
        "--- Headcount by department ---",
    ]

    if stats.headcount_by_department:
        for dept, count in stats.headcount_by_department.items():
            lines.append(f"  {dept:<20}: {count}")
    else:
        lines.append("  (no valid records)")

    lines += ["", "--- Validation issues ---"]
    if issues:
        for issue in issues[:MAX_ISSUES_IN_REPORT]:
            lines.append(f"  {issue}")
        if len(issues) > MAX_ISSUES_IN_REPORT:
            lines.append(f"  ... and {len(issues) - MAX_ISSUES_IN_REPORT} more")
    else:
        lines.append("  None - all rows passed validation.")

    lines += ["", "--- Duplicates removed ---"]
    if duplicates:
        lines.extend(f"  {entry}" for entry in duplicates)
    else:
        lines.append("  None.")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Wrote summary report to %s", out)
    return out
