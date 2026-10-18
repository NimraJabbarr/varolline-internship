"""End-to-end orchestration: read -> clean -> validate -> dedupe -> report."""

from __future__ import annotations

import logging

from .cleaner import EXPECTED_FIELDS, clean_row
from .reader import read_csv
from .reporter import write_cleaned_csv, write_summary_report
from .stats import SummaryStats, compute_stats
from .validator import validate_row

logger = logging.getLogger(__name__)


def deduplicate(records: list[dict]) -> tuple[list[dict], list[str]]:
    """Drop records whose employee_id was already seen (first one wins)."""
    seen: set[str] = set()
    unique: list[dict] = []
    duplicates: list[str] = []
    for record in records:
        employee_id = record["employee_id"]
        if employee_id in seen:
            duplicates.append(
                f"employee_id {employee_id} ({record['name']}) - duplicate dropped"
            )
            logger.warning("Duplicate employee_id %s dropped", employee_id)
            continue
        seen.add(employee_id)
        unique.append(record)
    return unique, duplicates


def run_pipeline(input_path: str, cleaned_path: str, report_path: str) -> SummaryStats:
    """Run the full processing pipeline and return the resulting stats.

    Raises:
        DataReadError: if the input cannot be read.
    """
    _, raw_rows = read_csv(input_path)

    valid_records: list[dict] = []
    all_issues = []
    invalid_row_numbers: set[int] = set()

    for index, raw_row in enumerate(raw_rows, start=2):  # row 1 is the header
        cleaned = clean_row(raw_row)
        result = validate_row(cleaned, index)
        if result.is_valid:
            valid_records.append(result.data)
        else:
            invalid_row_numbers.add(index)
            all_issues.extend(result.issues)
            for issue in result.issues:
                logger.warning("%s", issue)

    unique_records, duplicates = deduplicate(valid_records)

    stats = compute_stats(
        unique_records,
        total_rows=len(raw_rows),
        invalid_rows=len(invalid_row_numbers),
        duplicates_removed=len(duplicates),
    )

    write_cleaned_csv(unique_records, EXPECTED_FIELDS, cleaned_path)
    write_summary_report(stats, all_issues, duplicates, report_path)
    return stats
