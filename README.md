# Varolline Internship

Weekly Python projects completed during the Varolline internship. Each week is
a self-contained project in its own folder with its own README, tests, and
setup instructions.

## Projects

| Week | Folder | Description |
|------|--------|-------------|
| Week 1 | [csv-data-utility_week_1](./csv-data-utility_week_1) | CLI tool (`csvtool`) to read, clean, validate, and export CSV/JSON data with configurable rules and summary reports. |
| Week 2 | [2nd_weekk](./2nd_weekk) | Modular CSV data-processing pipeline — reader, cleaner, validator, stats, and reporter with a pure standard-library CLI. |
| Week 3 | [3rd_week](./3rd_week/fastapi_crud) | FastAPI CRUD REST API with SQLite (SQLAlchemy), Pydantic schemas, routers, pytest coverage, and a GitHub Actions CI workflow. |

## Repository structure

```
varolline-internship/
├── csv-data-utility_week_1/   # Week 1 — CSV Data Utility (csvtool package)
├── 2nd_weekk/                 # Week 2 — CSV processing pipeline
├── 3rd_week/                  # Week 3 — FastAPI CRUD API
│   └── fastapi_crud/
├── .github/workflows/         # CI for the Week 3 FastAPI project
└── README.md
```

## Getting started

Each project has its own virtual environment and dependencies. See the README
inside each week's folder for setup, usage, and test instructions.

Quick example (Week 3 API):

```bash
cd 3rd_week/fastapi_crud
pip install -r requirements.txt
uvicorn main:app --reload
```

## CI

A GitHub Actions workflow runs the Week 3 test suite with coverage on every
push and pull request that touches `3rd_week/fastapi_crud`.
