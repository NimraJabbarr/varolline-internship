"""Statistics over cleaned, valid rows. Tolerates missing columns."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence

from csvtool.parsing import parse_int, parse_money


def _summary(values: Sequence[float]) -> Optional[Dict[str, float]]:
    if not values:
        return None
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 2),
        "median": round(statistics.median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        "total": round(sum(values), 2),
    }


def compute_statistics(rows: Sequence[Mapping[str, str]]) -> Dict[str, Any]:
    """Return JSON-serialisable statistics for ``rows`` (already cleaned and validated)."""
    salaries: List[float] = []
    ages: List[float] = []
    dept_counts: Counter = Counter()  # type: ignore[type-arg]
    dept_salaries: Dict[str, List[float]] = defaultdict(list)
    hires: Counter = Counter()  # type: ignore[type-arg]
    top: Optional[Dict[str, Any]] = None

    for row in rows:
        salary = parse_money(row.get("salary", ""))
        age = parse_int(row.get("age", ""))
        dept = row.get("department", "")
        if salary is not None:
            salaries.append(salary)
            if dept:
                dept_salaries[dept].append(salary)
            if top is None or salary > top["salary"]:
                top = {"id": row.get("id", ""), "name": row.get("name", ""), "salary": salary}
        if age is not None:
            ages.append(age)
        if dept:
            dept_counts[dept] += 1
        year = row.get("join_date", "")[:4]
        if len(year) == 4 and year.isdigit():
            hires[year] += 1

    ordered = sorted(dept_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    by_department = {
        dept: {
            "count": count,
            "avg_salary": round(statistics.fmean(dept_salaries[dept]), 2)
            if dept_salaries.get(dept)
            else None,
        }
        for dept, count in ordered
    }
    return {
        "records": len(rows),
        "salary": _summary(salaries),
        "age": _summary(ages),
        "by_department": by_department,
        "hires_by_year": dict(sorted(hires.items())),
        "highest_paid": top,
    }
