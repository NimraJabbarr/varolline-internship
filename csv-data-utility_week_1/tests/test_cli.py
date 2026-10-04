from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT, SAMPLE_CSV, SAMPLE_JSON

from csvtool.cli import EXIT_ERROR, EXIT_NO_VALID_ROWS, EXIT_OK, main


def test_happy_path_writes_all_default_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out"
    assert main([str(SAMPLE_CSV), "-o", str(out)]) == EXIT_OK
    assert sorted(p.name for p in out.iterdir()) == [
        "cleaned_employees.csv", "rejected_employees.csv", "summary_employees.txt",
    ]
    stdout = capsys.readouterr().out
    assert "valid: 6 | invalid: 6 | duplicates: 2" in stdout
    rows = list(csv.DictReader((out / "cleaned_employees.csv").open(encoding="utf-8")))
    assert [r["id"] for r in rows] == ["1", "2", "6", "7", "8", "13"]


def test_optional_outputs(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl")
    out = tmp_path / "o"
    assert main([str(SAMPLE_CSV), "-o", str(out), "--json-report", "--xlsx", "-q"]) == EXIT_OK
    assert (out / "report_employees.xlsx").is_file()
    assert json.loads((out / "summary_employees.json").read_text(encoding="utf-8"))["counts"]["valid"] == 6


def test_json_input(tmp_path: Path) -> None:
    assert main([str(SAMPLE_JSON), "-o", str(tmp_path), "-q"]) == EXIT_OK
    assert (tmp_path / "cleaned_employees.csv").is_file()


def test_missing_input_file_is_a_clean_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "nope.csv"), "-o", str(tmp_path / "o")]) == EXIT_ERROR
    assert "error: input file not found" in capsys.readouterr().err
    assert not (tmp_path / "o").exists()  # nothing written on failure


def test_bad_config_is_a_clean_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "c.json"
    bad.write_text('{"age_minn": 1}')
    assert main([str(SAMPLE_CSV), "-c", str(bad), "-o", str(tmp_path / "o")]) == EXIT_ERROR
    assert "unknown config key" in capsys.readouterr().err


def test_config_changes_behaviour(tmp_path: Path) -> None:
    cfg = tmp_path / "c.json"
    cfg.write_text('{"allowed_departments": ["IT", "HR"]}')
    out = tmp_path / "o"
    assert main([str(SAMPLE_CSV), "-c", str(cfg), "-o", str(out), "-q"]) == EXIT_OK
    rows = list(csv.DictReader((out / "cleaned_employees.csv").open(encoding="utf-8")))
    assert {r["department"] for r in rows} == {"IT", "HR"}


def test_no_valid_rows_exit_code_and_header_only_outputs(tmp_path: Path, write) -> None:  # type: ignore[no-untyped-def]
    src = write("bad.csv", "id,name,email,age,salary,department,join_date\n1,,,,,,\n")
    out = tmp_path / "o"
    assert main([str(src), "-o", str(out), "-q"]) == EXIT_NO_VALID_ROWS
    assert (out / "cleaned_bad.csv").read_text(encoding="utf-8").strip() == (
        "id,name,email,age,salary,department,join_date"
    )


def test_input_file_is_never_modified(write) -> None:  # type: ignore[no-untyped-def]
    original = "id,name,email,age,salary,department,join_date\n1,ali,A@x.com,30,5,IT,2020-01-01\n"
    src = write("in.csv", original)
    assert main([str(src), "-o", str(src.parent), "-q"]) == EXIT_OK  # outputs next to the input
    assert src.read_text(encoding="utf-8") == original
    assert (src.parent / "cleaned_in.csv").is_file()


def test_unwritable_output_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    blocker = tmp_path / "f"
    blocker.write_text("x")
    assert main([str(SAMPLE_CSV), "-o", str(blocker / "sub"), "-q"]) == EXIT_ERROR
    assert "cannot write" in capsys.readouterr().err


def test_log_file(tmp_path: Path) -> None:
    log = tmp_path / "logs" / "run.log"
    assert main([str(SAMPLE_CSV), "-o", str(tmp_path / "o"), "--log-file", str(log), "-q"]) == EXIT_OK
    # -q means errors only, so the file may be empty, but it must exist
    assert log.is_file()
    assert main([str(SAMPLE_CSV), "-o", str(tmp_path / "o"), "--log-file", str(log)]) == EXIT_OK
    assert "rejected (duplicate)" in log.read_text(encoding="utf-8")


def test_usage_errors_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        main([str(SAMPLE_CSV), "--delimiter", "ab"])
    assert exc.value.code == 2


def test_runs_as_a_real_subprocess(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "csvtool", str(SAMPLE_CSV), "-o", str(tmp_path), "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
