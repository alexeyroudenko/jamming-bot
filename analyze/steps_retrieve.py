#!/usr/bin/env python3
"""Download steps export CSV from storage into analyze/data/steps_export.csv."""

import argparse
import csv
import io
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

DEFAULT_URL = "https://storage.jamming-bot.arthew0.online/export/csv"
DEFAULT_OUT = Path(__file__).resolve().parent / "data" / "steps_export.csv"


def _ensure_csv_field_limit() -> None:
    """Export rows may contain very large fields (e.g. long tag lists)."""
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch CSV export from storage and save locally."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("STEPS_EXPORT_URL", DEFAULT_URL),
        help="Export endpoint, default: %(default)s",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUT,
        help="Output file path, default: %(default)s",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds, default: %(default)s",
    )
    return parser.parse_args()


def _load_step_numbers(csv_path: Path) -> set[int]:
    numbers: set[int] = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = (row.get("number") or "").strip()
            if not raw:
                continue
            try:
                numbers.add(int(float(raw)))
            except ValueError:
                continue
    return numbers


def _backup_path(output: Path) -> Path:
    parent = output.parent
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    candidate = parent / f"steps_export_{stamp}.csv"
    if not candidate.exists():
        return candidate
    for sec in range(60):
        candidate = parent / f"steps_export_{stamp}-{sec:02d}.csv"
        if not candidate.exists():
            return candidate
    return parent / f"steps_export_{stamp}-{datetime.now().strftime('%S')}.csv"


def _iter_rows_from_bytes(data: bytes):
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    yield from reader


def _added_rows_summary(data: bytes, old_numbers: set[int]) -> list[tuple[str, str, str]]:
    """Rows whose number was not in old_numbers: (number, status_code, tags)."""
    added: list[tuple[str, str, str]] = []
    seen: set[int] = set()
    for row in _iter_rows_from_bytes(data):
        raw = (row.get("number") or "").strip()
        if not raw:
            continue
        try:
            n = int(float(raw))
        except ValueError:
            continue
        if n in old_numbers or n in seen:
            continue
        seen.add(n)
        status = (row.get("status_code") or "").strip()
        tags = (row.get("tags") or "").strip()
        added.append((raw, status, tags))
    added.sort(key=lambda t: int(float(t[0])))
    return added


def _print_table(rows: list[tuple[str, str, str]]) -> None:
    headers = ("number", "status_code", "tags")
    col0 = max(len(headers[0]), max((len(r[0]) for r in rows), default=0))
    col1 = max(len(headers[1]), max((len(r[1]) for r in rows), default=0))
    sep = " | "
    line = f"{headers[0]:<{col0}}{sep}{headers[1]:<{col1}}{sep}{headers[2]}"
    print(line)
    print("-" * len(line))
    for num, code, tags in rows:
        print(f"{num:<{col0}}{sep}{code:<{col1}}{sep}{tags}")


def main():
    _ensure_csv_field_limit()
    args = parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    had_previous = output.is_file()
    old_numbers: set[int] = set()
    if had_previous:
        old_numbers = _load_step_numbers(output)

    request = urllib.request.Request(
        args.url,
        headers={"User-Agent": "jamming-bot-analyze-steps-retrieve/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"request failed: {exc.reason}", file=sys.stderr)
        return 1

    if had_previous:
        backup = _backup_path(output)
        output.rename(backup)
        print(f"archived previous export -> {backup}")

    output.write_bytes(data)
    print(f"wrote {len(data)} bytes -> {output}")

    if not had_previous:
        print("no previous steps_export.csv; skip diff (nothing to compare).")
        return 0

    added = _added_rows_summary(data, old_numbers)
    print(f"\nadded steps (not in previous export): {len(added)}")
    if added:
        _print_table(added)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
