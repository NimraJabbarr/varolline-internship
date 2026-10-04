"""Turn a PipelineResult into a JSON-friendly summary dict and a readable text report."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from csvtool.pipeline import PipelineResult

PREVIEW_LIMIT = 10
WIDTH = 64


def build_summary(
    result: PipelineResult, source: str, generated_at: Optional[datetime] = None
) -> Dict[str, Any]:
    stamp = (generated_at or datetime.now()).replace(microsecond=0)
    return {
        "source": source,
        "generated_at": stamp.isoformat(),
        "counts": {
            "rows_read": result.total_rows,
            "blank_rows_skipped": result.blank_rows,
            "valid": result.valid_count,
            "invalid": result.invalid_count,
            "duplicates": result.duplicate_count,
        },
        "issue_breakdown": result.issue_counts,
        "statistics": result.stats,
        "rejected_preview": [
            {"line": r.record.line, "status": r.status, "reason": r.reason}
            for r in result.rejected[:PREVIEW_LIMIT]
        ],
        "rejected_total": len(result.rejected),
    }


def _money(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:,.2f}"


def render_text(summary: Dict[str, Any]) -> str:
    counts = summary["counts"]
    stats = summary["statistics"]
    out: List[str] = []
    rule = "=" * WIDTH
    out += [rule, "DATA CLEANING SUMMARY REPORT", rule]
    out += [f"Source file  : {summary['source']}", f"Generated at : {summary['generated_at']}", ""]

    out += ["INPUT / OUTPUT COUNTS", "-" * WIDTH]
    out += [
        f"  Rows read              : {counts['rows_read']}",
        f"  Blank rows skipped     : {counts['blank_rows_skipped']}",
        f"  Valid (exported)       : {counts['valid']}",
        f"  Invalid (rejected)     : {counts['invalid']}",
        f"  Duplicates (rejected)  : {counts['duplicates']}",
        "",
    ]

    out += ["WHY ROWS WERE REJECTED (invalid rows, by issue type)", "-" * WIDTH]
    if summary["issue_breakdown"]:
        for code, n in summary["issue_breakdown"].items():
            out.append(f"  {code:<24}: {n}")
    else:
        out.append("  (none)")
    out.append("")

    out += [f"STATISTICS (on the {stats['records']} valid rows)", "-" * WIDTH]
    if stats["records"] == 0:
        out.append("  No valid rows, so no statistics.")
    else:
        sal, age = stats["salary"], stats["age"]
        if sal:
            out += [
                "  Salary",
                f"    mean    : {_money(sal['mean'])}",
                f"    median  : {_money(sal['median'])}",
                f"    min/max : {_money(sal['min'])} / {_money(sal['max'])}",
                f"    std dev : {_money(sal['stdev'])}",
                f"    total   : {_money(sal['total'])}",
            ]
        if age:
            out += [
                "  Age",
                f"    mean    : {age['mean']:.2f}",
                f"    median  : {age['median']:.2f}",
                f"    min/max : {age['min']:.0f} / {age['max']:.0f}",
            ]
        top = stats["highest_paid"]
        if top:
            out.append(f"  Highest paid : {top['name'] or top['id']} ({_money(top['salary'])})")
        out += ["", "  By department (count, average salary)"]
        for dept, info in stats["by_department"].items():
            out.append(f"    {dept:<16} {info['count']:>4}   {_money(info['avg_salary']):>14}")
        if stats["hires_by_year"]:
            out += ["", "  Hires by join year"]
            for year, n in stats["hires_by_year"].items():
                out.append(f"    {year} : {n}")
    out.append("")

    out += ["REJECTED ROWS (first %d)" % PREVIEW_LIMIT, "-" * WIDTH]
    if summary["rejected_preview"]:
        for item in summary["rejected_preview"]:
            out.append(f"  line {item['line']:<4} [{item['status']}] {item['reason']}")
        extra = summary["rejected_total"] - len(summary["rejected_preview"])
        if extra > 0:
            out.append(f"  ... and {extra} more (see the rejected_*.csv file)")
    else:
        out.append("  (none)")
    out += ["", rule, ""]
    return "\n".join(out)
