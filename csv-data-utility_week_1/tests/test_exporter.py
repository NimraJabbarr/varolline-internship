from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from conftest import SAMPLE_CSV, TODAY

from csvtool.config import Config
from csvtool.errors import ExportError
from csvtool.exporter import (
    safe_cell,
    write_cleaned_csv,
    write_json,
    write_rejected_csv,
    write_text,
    write_xlsx,
)
from csvtool.pipeline import run_pipeline
from csvtool.reader import read_table
from csvtool.reporting import build_summary, render_text


def _result():  # type: ignore[no-untyped-def]
    return run_pipeline(read_table(SAMPLE_CSV), Config(), TODAY)


def test_safe_cell_blocks_formula_injection_but_keeps_numbers() -> None:
    assert safe_cell("=1+1") == "'=1+1"
    assert safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert safe_cell("+cmd") == "'+cmd"
    assert safe_cell("-1+1") == "'-1+1"
    assert safe_cell("-5") == "-5"
    assert safe_cell("-5.25") == "-5.25"
    assert safe_cell("Ali") == "Ali"
    assert safe_cell("a\x00b") == "ab"


def test_cleaned_csv_roundtrip(tmp_path: Path) -> None:
    result = _result()
    out = tmp_path / "deep" / "nested" / "cleaned.csv"  # parent dirs are created
    write_cleaned_csv(out, result.columns, result.valid)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 6 and rows[1]["name"] == "Sara Ahmed" and rows[1]["join_date"] == "2021-03-10"
    assert list(rows[0].keys()) == result.columns


def test_rejected_csv_keeps_original_values_and_reasons(tmp_path: Path) -> None:
    result = _result()
    out = tmp_path / "rejected.csv"
    write_rejected_csv(out, result.columns, result.rejected)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 8
    bilal = next(r for r in rows if r["id"] == "4")
    assert bilal["status"] == "invalid" and bilal["email"] == "invalid-email"
    assert "invalid email" in bilal["reason"]


def test_report_files(tmp_path: Path) -> None:
    summary = build_summary(_result(), "employees.csv")
    text = render_text(summary)
    assert "Valid (exported)       : 6" in text and "67,166.67" in text and "FINANCE" in text
    write_text(tmp_path / "r.txt", text)
    write_json(tmp_path / "r.json", summary)
    loaded = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert loaded["counts"] == {
        "rows_read": 14, "blank_rows_skipped": 1, "valid": 6, "invalid": 6, "duplicates": 2,
    }
    assert not list(tmp_path.glob("*.tmp"))  # atomic temp files are cleaned up


def test_report_for_zero_valid_rows_does_not_crash() -> None:
    from csvtool.pipeline import PipelineResult
    from csvtool.stats import compute_statistics

    empty = PipelineResult(["id"], 0, 0, [], [], {}, compute_statistics([]))
    assert "No valid rows" in render_text(build_summary(empty, "x.csv"))


def test_xlsx(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    result = _result()
    out = tmp_path / "r.xlsx"
    write_xlsx(out, result, build_summary(result, "employees.csv"))
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["Cleaned", "Rejected", "Summary"]
    cleaned = list(wb["Cleaned"].iter_rows(values_only=True))
    assert cleaned[0][:3] == ("id", "name", "email") and len(cleaned) == 7
    assert cleaned[2][4] == 60000.0 and cleaned[2][3] == 30  # real numbers, not text
    assert str(cleaned[2][6])[:10] == "2021-03-10"
    assert len(list(wb["Rejected"].iter_rows())) == 9


def test_unwritable_destination_raises_export_error(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(ExportError):
        write_text(blocker / "sub" / "r.txt", "x")  # parent is a file, not a directory
