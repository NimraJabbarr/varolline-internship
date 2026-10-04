"""Command-line interface.

Exit codes:  0 success | 1 error (bad input, config or output) | 2 bad usage (argparse)
             3 finished, but NO valid rows were found | 130 interrupted
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from csvtool import __version__
from csvtool.config import load_config
from csvtool.errors import CsvToolError, ExportError
from csvtool.exporter import (
    write_cleaned_csv,
    write_json,
    write_rejected_csv,
    write_text,
    write_xlsx,
)
from csvtool.pipeline import PipelineResult, run_pipeline
from csvtool.reader import read_table
from csvtool.reporting import build_summary, render_text

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NO_VALID_ROWS = 3
EXIT_INTERRUPTED = 130

log = logging.getLogger("csvtool")


def _delimiter(value: str) -> str:
    if value == "\\t":
        return "\t"
    if len(value) != 1:
        raise argparse.ArgumentTypeError("delimiter must be a single character (or \\t)")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csvtool",
        description="Validate, clean and summarise a CSV/TSV/JSON file of records.",
    )
    parser.add_argument("input", type=Path, help="input file (.csv, .tsv, .txt or .json)")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("output"),
                        help="folder for the output files (default: ./output)")
    parser.add_argument("-c", "--config", type=Path, default=None,
                        help="rules file (.json / .yaml); built-in defaults if omitted")
    parser.add_argument("--xlsx", action="store_true", help="also write an Excel workbook")
    parser.add_argument("--json-report", action="store_true", help="also write summary as JSON")
    parser.add_argument("--encoding", default="utf-8-sig",
                        help="input encoding (default: utf-8-sig, which also handles a BOM)")
    parser.add_argument("--delimiter", type=_delimiter, default=None,
                        help="CSV delimiter (default: ',' or tab for .tsv)")
    parser.add_argument("--log-file", type=Path, default=None, help="also write logs to this file")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-v", "--verbose", action="store_true", help="show debug logs")
    noise.add_argument("-q", "--quiet", action="store_true", help="only show errors")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def configure_logging(verbose: bool, quiet: bool, log_file: Optional[Path]) -> None:
    level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.INFO
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()
    log.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except OSError as exc:
            raise ExportError(f"cannot open log file {log_file}: {exc}") from exc
    for handler in handlers:
        handler.setFormatter(formatter)
        log.addHandler(handler)


def _print_overview(result: PipelineResult, written: Sequence[Path]) -> None:
    print(
        f"Rows read: {result.total_rows} | valid: {result.valid_count} | "
        f"invalid: {result.invalid_count} | duplicates: {result.duplicate_count}"
    )
    for path in written:
        print(f"  wrote {path}")


def run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    table = read_table(
        args.input, required=cfg.required_fields, encoding=args.encoding, delimiter=args.delimiter
    )
    result = run_pipeline(table, cfg)

    out_dir: Path = args.output_dir
    stem = args.input.stem
    targets = {
        "cleaned": out_dir / f"cleaned_{stem}.csv",
        "rejected": out_dir / f"rejected_{stem}.csv",
        "report": out_dir / f"summary_{stem}.txt",
        "json": out_dir / f"summary_{stem}.json",
        "xlsx": out_dir / f"report_{stem}.xlsx",
    }
    summary = build_summary(result, source=args.input.name)
    written: List[Path] = []
    write_cleaned_csv(targets["cleaned"], result.columns, result.valid)
    written.append(targets["cleaned"])
    write_rejected_csv(targets["rejected"], result.columns, result.rejected)
    written.append(targets["rejected"])
    write_text(targets["report"], render_text(summary))
    written.append(targets["report"])
    if args.json_report:
        write_json(targets["json"], summary)
        written.append(targets["json"])
    if args.xlsx:
        write_xlsx(targets["xlsx"], result, summary)
        written.append(targets["xlsx"])

    if not args.quiet:
        _print_overview(result, written)
    if result.valid_count == 0:
        log.error("no valid rows found; outputs contain headers only")
        return EXIT_NO_VALID_ROWS
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        configure_logging(args.verbose, args.quiet, args.log_file)
        return run(args)
    except CsvToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
    except Exception as exc:  # last-resort guard: never show a raw traceback to the user
        log.debug("unexpected failure", exc_info=True)
        print(f"error: unexpected failure ({type(exc).__name__}: {exc}). Run with -v for details.",
              file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
