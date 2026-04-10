#!/usr/bin/env python3
import csv
import math
import struct
import sys
import zlib
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent / "data" / "steps_export.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "out"


def _ensure_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def _nonempty(val):
    return val is not None and val.strip() not in ("", "[]", "None")


def read_csv(csv_path):
    _ensure_csv_field_limit()
    numbers = set()
    statuses = {}
    has_tags = set()
    has_screenshot = set()
    text_lengths = {}
    has_geo = set()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("number", "").strip()
            if not raw:
                continue
            try:
                n = int(float(raw))
            except ValueError:
                continue
            numbers.add(n)

            code_raw = row.get("status_code", "").strip()
            try:
                statuses[n] = int(float(code_raw))
            except (ValueError, TypeError):
                statuses[n] = 0

            if _nonempty(row.get("tags")):
                has_tags.add(n)
            if _nonempty(row.get("screenshot_url")):
                has_screenshot.add(n)
            tl = row.get("text_length", "").strip()
            try:
                tl_int = int(float(tl))
                if tl_int > 0:
                    text_lengths[n] = tl_int
            except (ValueError, TypeError):
                pass
            lat = row.get("latitude", "").strip()
            lon = row.get("longitude", "").strip()
            if lat and lon and lat != "None" and lon != "None":
                try:
                    float(lat)
                    float(lon)
                    has_geo.add(n)
                except ValueError:
                    pass

    return {
        "numbers": sorted(numbers),
        "statuses": statuses,
        "has_tags": has_tags,
        "has_screenshot": has_screenshot,
        "text_lengths": text_lengths,
        "has_geo": has_geo,
    }


def choose_dimensions(max_val):
    width = max(1, math.ceil(math.sqrt(max_val + 1)))
    height = max(1, math.ceil((max_val + 1) / width))
    return width, height


def rasterize(numbers, width, height):
    rows = [bytearray(width) for _ in range(height)]
    for n in numbers:
        x = n % width
        y = n // width
        if y < height:
            rows[y][x] = 255
    return rows


def png_chunk(tag, data):
    return (
        struct.pack("!I", len(data))
        + tag
        + data
        + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def rasterize_statuses(numbers, statuses, width, height):
    """RGB rows: white=200, red=404, dark red=other error, black=no data."""
    rows = [bytearray(width * 3) for _ in range(height)]
    for n in numbers:
        x = n % width
        y = n // width
        if y >= height:
            continue
        code = statuses.get(n, 0)
        off = x * 3
        if code == 200:
            rows[y][off] = 255
            rows[y][off + 1] = 255
            rows[y][off + 2] = 255
        elif code == 404:
            rows[y][off] = 255
            rows[y][off + 1] = 0
            rows[y][off + 2] = 0
        else:
            rows[y][off] = 160
            rows[y][off + 1] = 0
            rows[y][off + 2] = 0
    return rows


def rasterize_presence_set(number_set, width, height):
    rows = [bytearray(width) for _ in range(height)]
    for n in number_set:
        x = n % width
        y = n // width
        if y < height:
            rows[y][x] = 255
    return rows


def rasterize_text_brightness(text_lengths, width, height):
    rows = [bytearray(width) for _ in range(height)]
    if not text_lengths:
        return rows
    max_tl = max(text_lengths.values())
    for n, tl in text_lengths.items():
        x = n % width
        y = n // width
        if y < height:
            rows[y][x] = 127 + int(128 * min(tl, max_tl) / max_tl)
    return rows


def write_grayscale_png(path, rows, width, height):
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack("!2I5B", width, height, 8, 0, 0, 0, 0)
    png = [
        b"\x89PNG\r\n\x1a\n",
        png_chunk(b"IHDR", header),
        png_chunk(b"IDAT", zlib.compress(raw, level=9)),
        png_chunk(b"IEND", b""),
    ]
    path.write_bytes(b"".join(png))


def write_rgb_png(path, rows, width, height):
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0)
    png = [
        b"\x89PNG\r\n\x1a\n",
        png_chunk(b"IHDR", header),
        png_chunk(b"IDAT", zlib.compress(raw, level=9)),
        png_chunk(b"IEND", b""),
    ]
    path.write_bytes(b"".join(png))


def _save_grayscale(name, rows, width, height):
    path = OUTPUT_DIR / name
    write_grayscale_png(path, rows, width, height)
    print(f"saved:   {path}")


def main():
    data = read_csv(CSV_PATH)
    numbers = data["numbers"]
    if not numbers:
        raise SystemExit("No numbers found in CSV")

    max_val = numbers[-1]
    width, height = choose_dimensions(max_val)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"numbers: {len(numbers)}, range: {numbers[0]}..{max_val}")
    print(f"image:   {width}x{height}")

    _save_grayscale("steps_data.png", rasterize(numbers, width, height), width, height)

    status_path = OUTPUT_DIR / "steps_statuses.png"
    write_rgb_png(status_path, rasterize_statuses(numbers, data["statuses"], width, height), width, height)
    print(f"saved:   {status_path}")

    _save_grayscale("steps_tags.png", rasterize_presence_set(data["has_tags"], width, height), width, height)
    _save_grayscale("steps_screenshot.png", rasterize_presence_set(data["has_screenshot"], width, height), width, height)
    _save_grayscale("steps_text.png", rasterize_text_brightness(data["text_lengths"], width, height), width, height)
    _save_grayscale("steps_geo.png", rasterize_presence_set(data["has_geo"], width, height), width, height)


if __name__ == "__main__":
    main()
