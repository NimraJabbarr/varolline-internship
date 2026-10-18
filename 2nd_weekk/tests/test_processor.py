"""Test suite for the csv_processor package."""

import csv
import tempfile
import unittest
from pathlib import Path

from csv_processor.cleaner import clean_row, normalize_date
from csv_processor.pipeline import run_pipeline
from csv_processor.reader import DataReadError, read_csv
from csv_processor.stats import compute_stats
from csv_processor.validator import validate_row

VALID_ROW = {
    "employee_id": "1001",
    "name": "  alice   johnson ",
    "email": "ALICE@Example.COM",
    "age": "29",
    "salary": "$85,000",
    "department": "engineering",
    "join_date": "15/03/2021",
}


def make_row(**overrides):
    row = dict(VALID_ROW)
    row.update(overrides)
    return row


class ReaderTests(unittest.TestCase):
    def test_missing_file_raises_data_read_error(self):
        with self.assertRaises(DataReadError):
            read_csv("does_not_exist.csv")

    def test_empty_file_raises_data_read_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.csv"
            empty.write_text("", encoding="utf-8")
            with self.assertRaises(DataReadError):
                read_csv(empty)

    def test_reads_headers_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
            headers, rows = read_csv(path)
        self.assertEqual(headers, ["a", "b"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["a"], "1")


class CleanerTests(unittest.TestCase):
    def test_clean_row_normalizes_all_fields(self):
        cleaned = clean_row(VALID_ROW)
        self.assertEqual(cleaned["name"], "Alice Johnson")
        self.assertEqual(cleaned["email"], "alice@example.com")
        self.assertEqual(cleaned["salary"], "85000.00")
        self.assertEqual(cleaned["department"], "Engineering")
        self.assertEqual(cleaned["join_date"], "2021-03-15")

    def test_missing_cells_become_empty_strings(self):
        cleaned = clean_row({"employee_id": None, "name": None})
        self.assertEqual(cleaned["employee_id"], "")
        self.assertEqual(cleaned["name"], "")

    def test_normalize_date_accepts_multiple_formats(self):
        self.assertEqual(normalize_date("2021-03-15"), "2021-03-15")
        self.assertEqual(normalize_date("15/03/2021"), "2021-03-15")
        self.assertEqual(normalize_date("not a date"), "not a date")


class ValidatorTests(unittest.TestCase):
    def test_valid_row_passes(self):
        result = validate_row(clean_row(VALID_ROW), row_number=2)
        self.assertTrue(result.is_valid)

    def test_detects_missing_and_invalid_fields(self):
        dirty = clean_row(make_row(name="", email="bad", age="12", salary="-5"))
        result = validate_row(dirty, row_number=3)
        self.assertFalse(result.is_valid)
        flagged = {issue.field for issue in result.issues}
        self.assertEqual(flagged, {"name", "email", "age", "salary"})

    def test_detects_bad_date_and_non_numeric_id(self):
        dirty = clean_row(make_row(employee_id="abc", join_date="2021-13-40"))
        result = validate_row(dirty, row_number=4)
        flagged = {issue.field for issue in result.issues}
        self.assertEqual(flagged, {"employee_id", "join_date"})


class StatsTests(unittest.TestCase):
    def test_statistics_over_valid_records(self):
        records = [
            clean_row(make_row(employee_id="1", salary="60000", age="30", department="Sales")),
            clean_row(make_row(employee_id="2", salary="80000", age="40", department="Sales")),
            clean_row(make_row(employee_id="3", salary="100000", age="50", department="IT")),
        ]
        stats = compute_stats(records, total_rows=5, invalid_rows=1, duplicates_removed=1)
        self.assertEqual(stats.valid_rows, 3)
        self.assertEqual(stats.average_salary, 80000.0)
        self.assertEqual(stats.median_salary, 80000.0)
        self.assertEqual(stats.min_salary, 60000.0)
        self.assertEqual(stats.max_salary, 100000.0)
        self.assertEqual(stats.average_age, 40.0)
        self.assertEqual(stats.headcount_by_department, {"IT": 1, "Sales": 2})

    def test_empty_record_set_does_not_crash(self):
        stats = compute_stats([], total_rows=0, invalid_rows=0, duplicates_removed=0)
        self.assertEqual(stats.valid_rows, 0)
        self.assertEqual(stats.average_salary, 0.0)


class PipelineTests(unittest.TestCase):
    def test_end_to_end_pipeline(self):
        rows = [
            make_row(employee_id="1001"),
            make_row(employee_id="1001"),  # duplicate
            make_row(employee_id="1002", email="broken"),
            make_row(employee_id="1003", salary="95000"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            input_csv = tmp / "in.csv"
            with input_csv.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(VALID_ROW))
                writer.writeheader()
                writer.writerows(rows)
            cleaned_csv = tmp / "out" / "cleaned.csv"
            report = tmp / "out" / "report.txt"

            stats = run_pipeline(str(input_csv), str(cleaned_csv), str(report))

            self.assertEqual(stats.total_rows, 4)
            self.assertEqual(stats.valid_rows, 2)
            self.assertEqual(stats.invalid_rows, 1)
            self.assertEqual(stats.duplicates_removed, 1)

            with cleaned_csv.open(encoding="utf-8") as fh:
                cleaned_rows = list(csv.DictReader(fh))
            self.assertEqual(len(cleaned_rows), 2)
            self.assertEqual({r["employee_id"] for r in cleaned_rows}, {"1001", "1003"})

            report_text = report.read_text(encoding="utf-8")
            self.assertIn("SUMMARY REPORT", report_text)
            self.assertIn("duplicate", report_text.lower())

    def test_pipeline_with_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DataReadError):
                run_pipeline(
                    str(Path(tmp) / "nope.csv"),
                    str(Path(tmp) / "out.csv"),
                    str(Path(tmp) / "report.txt"),
                )


if __name__ == "__main__":
    unittest.main()
