from __future__ import annotations

from pathlib import Path

import pytest
from conftest import SAMPLE_JSON

from csvtool.errors import ReaderError
from csvtool.reader import read_table


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ReaderError, match="not found"):
        read_table(tmp_path / "nope.csv")


def test_directory_is_not_a_file(tmp_path: Path) -> None:
    with pytest.raises(ReaderError, match="not a file"):
        read_table(tmp_path)


def test_empty_file(write) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReaderError, match="empty"):
        read_table(write("e.csv", ""))


def test_header_only(write) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReaderError, match="no data rows"):
        read_table(write("h.csv", "id,name\n"))


def test_only_blank_rows(write) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReaderError, match="no data rows"):
        read_table(write("b.csv", "id,name\n,\n,\n"))


def test_unsupported_extension(write) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReaderError, match="unsupported"):
        read_table(write("x.xlsx", "whatever"))


def test_missing_required_columns(write) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReaderError, match="missing required column.*email"):
        read_table(write("m.csv", "id,name\n1,Ali\n"), required=["id", "email"])


def test_headers_are_normalised_and_bom_is_handled(write) -> None:  # type: ignore[no-untyped-def]
    path = write("bom.csv", "﻿ID , Join Date\n1,2020-01-01\n", encoding="utf-8")
    table = read_table(path)
    assert table.columns == ["id", "join_date"]
    assert table.records[0].data == {"id": "1", "join_date": "2020-01-01"}


def test_duplicate_and_empty_headers(write) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReaderError, match="duplicate column"):
        read_table(write("d.csv", "id,ID\n1,2\n"))
    with pytest.raises(ReaderError, match="empty column"):
        read_table(write("e2.csv", "id,\n1,2\n"))


def test_ragged_rows_are_flagged_not_crashed(write) -> None:  # type: ignore[no-untyped-def]
    table = read_table(write("r.csv", "a,b\n1,2,3\n4\n5,6\n"))
    assert "more cell" in table.records[0].problems[0]
    assert "fewer cell" in table.records[1].problems[0]
    assert table.records[1].data == {"a": "4", "b": ""}
    assert table.records[2].problems == []


def test_quoted_commas_and_multiline_cells(write) -> None:  # type: ignore[no-untyped-def]
    table = read_table(write("q.csv", 'a,b\n"x, y","line1\nline2"\n'))
    assert table.records[0].data == {"a": "x, y", "b": "line1\nline2"}


def test_bad_encoding_gives_friendly_error(write) -> None:  # type: ignore[no-untyped-def]
    path = write("l1.csv", "id,name\n1,José\n", encoding="latin-1")
    with pytest.raises(ReaderError, match="--encoding"):
        read_table(path)
    assert read_table(path, encoding="latin-1").records[0].data["name"] == "José"


def test_unknown_encoding_name(write) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ReaderError, match="unknown encoding"):
        read_table(write("u.csv", "a\n1\n"), encoding="not-a-codec")


def test_tsv_and_custom_delimiter(write) -> None:  # type: ignore[no-untyped-def]
    assert read_table(write("t.tsv", "a\tb\n1\t2\n")).records[0].data == {"a": "1", "b": "2"}
    assert read_table(write("s.csv", "a;b\n1;2\n"), delimiter=";").records[0].data == {"a": "1", "b": "2"}


def test_blank_rows_are_counted_and_line_numbers_are_physical(write) -> None:  # type: ignore[no-untyped-def]
    table = read_table(write("n.csv", "a,b\n1,2\n\n,\n3,4\n"))
    assert table.blank_rows == 2
    assert [r.line for r in table.records] == [2, 5]


def test_json_sample() -> None:
    table = read_table(SAMPLE_JSON)
    assert len(table.records) == 4
    assert table.records[2].data["age"] == ""  # null -> ""
    assert table.records[0].data["id"] == "1"  # number -> string


def test_json_variants_and_errors(write) -> None:  # type: ignore[no-untyped-def]
    wrapped = write("w.json", '{"records": [{"A": 1}, {"B": 2}]}')
    table = read_table(wrapped)
    assert table.columns == ["a", "b"]
    assert table.records[0].data == {"a": "1", "b": ""}
    with pytest.raises(ReaderError, match="invalid JSON"):
        read_table(write("bad.json", "{oops"))
    with pytest.raises(ReaderError, match="list of objects"):
        read_table(write("o.json", '{"x": 1}'))
    with pytest.raises(ReaderError, match="not an object"):
        read_table(write("i.json", "[1, 2]"))
    with pytest.raises(ReaderError, match="duplicate key"):
        read_table(write("k.json", '[{"Name": "a", "name": "b"}]'))
    with pytest.raises(ReaderError, match="no data rows"):
        read_table(write("z.json", "[]"))
