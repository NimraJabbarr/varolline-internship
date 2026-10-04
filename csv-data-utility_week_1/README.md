# csvtool: CSV / JSON Data Validation, Cleaning & Reporting Utility

A reusable command-line tool that reads a file of records (employees by default), **detects missing,
invalid and duplicate rows**, **cleans and normalises** the good ones, **calculates statistics**, and
exports a **cleaned CSV**, a **rejected-rows CSV** (with the reason for every rejection) and a
**summary report**.

* Pure Python standard library at its core, with no dependencies required.
* Optional extras: Excel export (`openpyxl`) and YAML config files (`pyyaml`).
* Fully type-hinted (`mypy --strict` clean), linted with `ruff`, covered by 120+ `pytest` tests.

---

## 1. Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                                # tool + pytest/mypy/ruff + optional extras
# (or just: pip install -r requirements-dev.txt  and run with  python -m csvtool ...)

python -m csvtool data/sample/employees.csv -o data/output
```

Console output:

```
Rows read: 14 | valid: 6 | invalid: 6 | duplicates: 2
  wrote data/output/cleaned_employees.csv
  wrote data/output/rejected_employees.csv
  wrote data/output/summary_employees.txt
```

(Warnings for every rejected row are printed to stderr; use `-q` to silence them.)

## 2. Usage

```
csvtool INPUT [-o DIR] [-c CONFIG] [--xlsx] [--json-report]
              [--encoding ENC] [--delimiter CHAR] [--log-file FILE] [-v | -q] [--version]
```

| Option | Meaning |
|---|---|
| `INPUT` | `.csv`, `.tsv`, `.txt` (delimited) or `.json` file |
| `-o, --output-dir` | where outputs go (default `./output`, created if missing) |
| `-c, --config` | rules file, `.json` or `.yaml` (see section 5) |
| `--xlsx` | also write `report_<name>.xlsx` (Cleaned / Rejected / Summary sheets) |
| `--json-report` | also write `summary_<name>.json` (machine-readable) |
| `--encoding` | input encoding, default `utf-8-sig` (also copes with a BOM). Try `cp1252` for Excel-on-Windows files |
| `--delimiter` | e.g. `";"` or `"\t"` (default `,`; tab for `.tsv`) |
| `--log-file` | additionally write the log to a file |
| `-v` / `-q` | debug logs / errors only |

Examples:

```bash
python -m csvtool data/sample/employees.json -o out --xlsx --json-report
python -m csvtool data.csv -c config/rules.yaml -o out --log-file out/run.log
python -m csvtool europe.csv --delimiter ";" --encoding cp1252
```

### Exit codes (useful in scripts / CI)

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | error: file missing/empty/unreadable, bad config, cannot write output |
| 2 | bad command-line usage |
| 3 | ran fine but **no valid rows** were found (outputs contain headers only) |
| 130 | interrupted with Ctrl+C |

## 3. What it does (the pipeline)

```
 read  ->  clean  ->  validate  ->  de-duplicate  ->  statistics  ->  export
reader    cleaner    validator      pipeline          stats          exporter / reporting
```

Every input row ends up in **exactly one** bucket: *valid*, *invalid* or *duplicate*
(this invariant is tested).

### Cleaning rules (applied to every row before validation)

| Field | Rule | Example |
|---|---|---|
| all cells | trim, collapse inner whitespace, drop invisible characters | `"  noor   fatima "` -> `Noor Fatima` |
| all cells | "missing" tokens become empty (`N/A`, `null`, `none`, `nan`, `-`, `--`, `?`) | `N/A` -> `` |
| `email` | lower-case | `SARA@Example.COM` -> `sara@example.com` |
| `name` | Title Case | `sara AHMED` -> `Sara Ahmed` |
| `department` | UPPER CASE | `hr` -> `HR` |
| `age` | plain integer | `30.0` -> `30` |
| `salary` | plain number; strips commas and `Rs.`/`PKR`/`$` | `Rs. 60,000` -> `60000` |
| `join_date` | ISO `YYYY-MM-DD` (accepts `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`) | `10/03/2021` -> `2021-03-10` |

Values that cannot be normalised are left alone and then rejected by the validator.
Headers are normalised too (`" Join Date "` -> `join_date`).

### Validation rules

| Check | Rejection code |
|---|---|
| required field empty / column cell missing | `missing_field` |
| `id` must be letters/digits/`_ . -` | `invalid_id` |
| `name` must be letters (any script), spaces, `' . -` | `invalid_name` |
| `email` must be a well-formed address | `invalid_email` |
| `age` must be a whole number in 16-100 | `invalid_age`, `age_out_of_range` |
| `salary` must be a finite number in 1-10,000,000 (`nan`/`inf` rejected) | `invalid_salary`, `salary_out_of_range` |
| `join_date` must be a real calendar date, not in the future, not before 1950 | `invalid_date`, `future_date`, `date_out_of_range` |
| `department` well-formed (and in the allow-list, if configured) | `invalid_department`, `department_not_allowed` |
| row has more/fewer cells than the header | `malformed_row` |
| `id` **or** `email` already used by an accepted row (case-insensitive) | reported as `duplicate` |

A row that fails validation never "claims" an id/email, so a valid later row is **not**
wrongly discarded as a duplicate of a broken earlier one.

### Statistics (in the summary report)

Salary and age: mean, median, min, max, standard deviation, total. Also: headcount and average
salary per department, hires per year, highest-paid employee.

## 4. Output files

| File | Content |
|---|---|
| `cleaned_<name>.csv` | valid, normalised rows (same columns as the input) |
| `rejected_<name>.csv` | every rejected row as originally written, plus `line`, `status` (`invalid`/`duplicate`) and `reason` |
| `summary_<name>.txt` | human-readable report: counts, rejection reasons, statistics, preview of rejected rows |
| `summary_<name>.json` | same information, machine-readable (`--json-report`) |
| `report_<name>.xlsx` | Excel workbook with real numbers/dates (`--xlsx`) |

`line` numbers are physical line numbers in the input (header = line 1), so you can jump straight to the
problem in a text editor. Samples produced from `data/sample/employees.csv` are in `data/output/`.

Safety: all writes are **atomic** (temp file + rename), so a crash never leaves a half-written report,
and your input file is never modified. Cells starting with `= + @` are prefixed with `'` so spreadsheets
can't execute them as formulas (CSV-injection protection).

## 5. Configuration (rules without touching code)

Pass `-c config/rules.json` or `-c config/rules.yaml`. Every key is optional; unknown keys are an error
(so typos are caught). Defaults:

```json
{
  "required_fields": ["id", "name", "email", "age", "salary", "department", "join_date"],
  "unique_keys": ["id", "email"],
  "missing_tokens": ["n/a", "na", "null", "none", "nan", "-", "--", "?"],
  "age_min": 16, "age_max": 100,
  "salary_min": 1, "salary_max": 10000000,
  "date_formats": ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
  "min_join_year": 1950,
  "allowed_departments": null
}
```

Note: slash/dash dates are read **day first** (`10/03/2021` = 10 March). Change `date_formats` if your
data is month first.

## 6. Input formats

* **CSV/TSV**: first row is the header; quoted commas, multi-line cells, BOM and blank lines are handled.
* **JSON**: a list of objects, or `{"records": [...]}`. Numbers and `null` are converted to text first, so
  both formats follow exactly the same rules (see `data/sample/employees.json`).

## 7. Project layout

```
csvtool/
  cli.py        argument parsing, logging setup, exit codes, wiring
  config.py     Config dataclass + JSON/YAML loader with strict validation
  reader.py     CSV/TSV/JSON -> Table of Records (friendly errors for every failure)
  parsing.py    pure helpers: whitespace, int/money/date parsing, email/name checks
  cleaner.py    normalisation rules
  validator.py  per-row checks -> list of Issues
  pipeline.py   clean -> validate -> de-duplicate (no file I/O, easy to test)
  stats.py      statistics
  reporting.py  summary dict + text report
  exporter.py   atomic CSV/TXT/JSON/XLSX writers, formula-injection guard
tests/          pytest suite (one file per module + end-to-end CLI tests)
data/sample/    sample inputs;  data/output/  sample outputs
config/         rules.json, rules.yaml
.github/workflows/ci.yml   GitHub Actions: ruff + mypy + pytest on Python 3.9-3.13
```

Design notes: the pipeline is separated from I/O so every stage is a small testable function; expected
problems raise `CsvToolError` subclasses which the CLI turns into one-line messages (no tracebacks);
the rules live in a config object instead of being hard-coded.

## 8. Development

```bash
pytest -q           # run the tests
ruff check .        # lint
mypy                # strict type check
```

## 9. Known limitations

* The whole file is loaded into memory, which is fine up to roughly a few hundred thousand rows.
* Title-casing is simple: `McDonald` becomes `Mcdonald`.
* The date format list is ordered, so ambiguous dates use the first matching format (day-first by default).
* Only the Python standard library is used for CSV parsing; Excel `.xlsx` *input* is not supported.
