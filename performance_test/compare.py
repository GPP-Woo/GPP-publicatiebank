"""Compare two load test runs side by side.

Takes the ``--csv`` output of two Locust runs (the ``<prefix>_stats.csv`` file, or
just the prefix) and prints, per request, the throughput, failure rate and
response times of both runs and the change between them::

    python performance_test/compare.py results/before results/after

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

type Row = Mapping[str, str]
"""One line of a Locust ``_stats.csv``, by column header."""
type RequestKey = tuple[str, str]
"""``(Type, Name)``, e.g. ``("GET", "/api/v2/publicaties/[uuid]")``."""
type Stats = Mapping[RequestKey, Row]


def load(path: str | os.PathLike[str]) -> dict[RequestKey, Row]:
    file = Path(path)
    if not file.name.endswith("_stats.csv"):
        file = file.with_name(f"{file.name}_stats.csv")
    with file.open(newline="") as f:
        return {(row["Type"], row["Name"]): row for row in csv.DictReader(f)}


def _float(row: Row | None, column: str) -> float | None:
    if row is None or row[column] in ("", "N/A"):
        return None
    return float(row[column])


def _failure_ratio(row: Row | None) -> float | None:
    requests = _float(row, "Request Count")
    if not requests:
        return None
    return (_float(row, "Failure Count") or 0) / requests


class Column(NamedTuple):
    title: str
    source: str | Callable[[Row | None], float | None]
    """A CSV column header, or a function computing the value from the row."""
    format: str
    relative_change: bool

    def value(self, row: Row | None) -> float | None:
        if callable(self.source):
            return self.source(row)
        return _float(row, self.source)


def _fmt(value: float | None, fmt: str) -> str:
    return "-" if value is None else format(value, fmt)


def _change(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return ""
    if a == 0:
        return "" if b == 0 else "new"
    return f"{(b - a) / a:+.0%}"


COLUMNS: Sequence[Column] = [
    Column("req/s", "Requests/s", ".2f", relative_change=False),
    Column("fail", _failure_ratio, ".1%", relative_change=False),
    Column("p50 ms", "50%", ".0f", relative_change=True),
    Column("p95 ms", "95%", ".0f", relative_change=True),
]


def compare(a: Stats, b: Stats, label_a: str, label_b: str) -> list[list[str]]:
    header = ["request"]
    for column in COLUMNS:
        header += [f"{column.title} {label_a}", f"{column.title} {label_b}"]
        if column.relative_change:
            header.append("Δ")
    rows = [header]

    names = list(a) + [name for name in b if name not in a]
    # the totals go last, like in the Locust report
    names.sort(key=lambda name: (name[1] == "Aggregated", name[1], name[0]))
    for name in names:
        row_a, row_b = a.get(name), b.get(name)
        line = [" ".join(part for part in name if part)]
        for column in COLUMNS:
            value_a, value_b = column.value(row_a), column.value(row_b)
            line += [_fmt(value_a, column.format), _fmt(value_b, column.format)]
            if column.relative_change:
                line.append(_change(value_a, value_b))
        rows.append(line)
    return rows


def print_table(rows: Sequence[Sequence[str]]) -> None:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for i, row in enumerate(rows):
        cells = [row[0].ljust(widths[0])]
        cells += [
            cell.rjust(width) for cell, width in zip(row[1:], widths[1:], strict=True)
        ]
        print("  ".join(cells))
        if i == 0:
            print("  ".join("-" * width for width in widths))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two load test runs.")
    parser.add_argument("baseline", help="stats CSV (or --csv prefix) of the first run")
    parser.add_argument(
        "candidate", help="stats CSV (or --csv prefix) of the second run"
    )
    parser.add_argument("--labels", nargs=2, default=("A", "B"), metavar=("A", "B"))
    args = parser.parse_args(argv)
    print_table(compare(load(args.baseline), load(args.candidate), *args.labels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
