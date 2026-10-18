"""Command-line interface for the CSV processing utility."""

from __future__ import annotations

import argparse
import logging
import sys

from .pipeline import run_pipeline
from .reader import DataReadError

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-processor",
        description="Clean, validate, and summarize a CSV file of employee records.",
    )
    parser.add_argument("input", help="Path to the raw input CSV file")
    parser.add_argument(
        "-o", "--output", default="output/cleaned_employees.csv",
        help="Path for the cleaned CSV output (default: %(default)s)",
    )
    parser.add_argument(
        "-r", "--report", default="output/summary_report.txt",
        help="Path for the summary report (default: %(default)s)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        stats = run_pipeline(args.input, args.output, args.report)
    except DataReadError as exc:
        logger.error("Processing aborted: %s", exc)
        return 1
    except OSError as exc:
        logger.error("Could not write output: %s", exc)
        return 1

    print(
        f"Done: {stats.valid_rows}/{stats.total_rows} valid records "
        f"({stats.invalid_rows} invalid, {stats.duplicates_removed} duplicates removed)."
    )
    print(f"Cleaned CSV : {args.output}")
    print(f"Report      : {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
