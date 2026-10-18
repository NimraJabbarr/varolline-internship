# CSV Data Processing Utility

A modular Python utility that reads a CSV file of employee records, cleans and
validates the data, computes statistics, and exports a cleaned CSV plus a
human-readable summary report. Pure standard library — no dependencies.

## Project structure

```
csv_processor/
├── reader.py      # safe CSV reading (DataReadError on missing/empty/bad files)
├── cleaner.py     # normalization rules (whitespace, case, currency, dates)
├── validator.py   # per-field validation, collects all issues per row
├── stats.py       # salary/age/department statistics
├── reporter.py    # writes cleaned CSV + summary report
├── pipeline.py    # read -> clean -> validate -> dedupe -> stats -> export
└── cli.py         # argparse command-line interface
data/employees.csv # sample input with deliberate data-quality problems
tests/test_processor.py
main.py            # entry point
```

## Usage

```
python main.py data/employees.csv
python main.py data/employees.csv -o output/cleaned.csv -r output/report.txt -v
```

## Cleaning rules

- Trim and collapse whitespace; title-case names and departments.
- Lower-case emails.
- Strip currency symbols/commas from salary; canonical `85000.00` form.
- Accept dates as `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`, `DD-MM-YYYY`;
  normalize to ISO.

## Validation rules

- `employee_id`: required, numeric, unique (first occurrence wins).
- `name`, `department`: required.
- `email`: required, must match an email pattern.
- `age`: required, integer in 18–70.
- `salary`: required, positive number.
- `join_date`: required, valid ISO date after cleaning.

## Statistics

Average/median/min/max salary, average/min/max age, headcount per department,
plus row accounting (total / valid / invalid / duplicates).

## Tests

```
python -m unittest discover -s tests -v
```
