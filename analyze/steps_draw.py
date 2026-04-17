#!/usr/bin/env python3
import csv
import math
import struct
import sys
import zlib
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent / "data" / "steps_export.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "out"

# Timeline strip: column-major step index n → (col, row); col maps to tiles along X.
TIMELINE_TILE_W = 1000
TIMELINE_TILE_H = 128
TIMELINE_N_TILES = 10
# Extended: 100×1000×128 → analyze/timeline/; step presence + B/W vertical patterns (full fill).
TIMELINE_EXT_N_TILES = 100
TIMELINE_EXT_DIR = Path(__file__).resolve().parent / "timeline"


def timeline_capacity(n_tiles: int = TIMELINE_N_TILES) -> int:
    return n_tiles * TIMELINE_TILE_W * TIMELINE_TILE_H


def decode_timeline_pixel_status(r: int, g: int) -> int:
    """
    Recover uint16 from R,G (big-endian). Current timeline strips use grayscale
    presence pixels; use timeline_tile_xy_to_step + CSV for step n / status.
    """
    return (r & 0xFF) * 256 + (g & 0xFF)


def timeline_tile_xy_to_step(tile_idx: int, x: int, y: int, n_tiles: int) -> int:
    """Inverse column-major: pixel (tile,x,y) → step number n."""
    if not (0 <= tile_idx < n_tiles and 0 <= x < TIMELINE_TILE_W and 0 <= y < TIMELINE_TILE_H):
        raise ValueError("coordinates outside strip")
    col = tile_idx * TIMELINE_TILE_W + x
    return col * TIMELINE_TILE_H + y


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


def _empty_timeline_tiles(n_tiles: int) -> list:
    w, h = TIMELINE_TILE_W, TIMELINE_TILE_H
    return [[bytearray(w * 3) for _ in range(h)] for _ in range(n_tiles)]


def _timeline_data_bw_rgb(
    present: bool, x: int, y: int, n: int, tile_idx: int
) -> tuple[int, int, int]:
    """
    Grayscale (R=G=B): step presence like steps_data.png, but every slot is drawn.
    Vertical line / broken-grid phase + horizontal bands of varying density (static-like).
    """
    col_id = n // TIMELINE_TILE_H
    band = min(6, (y * 7) // TIMELINE_TILE_H)
    # Broken vertical alignment between rows
    stagger = (band * 17 + (col_id % 29) * 2 + (tile_idx * 5)) % 9 - 4
    bx = x + stagger
    period = 2 + (col_id % 5) + (band % 3)
    vline = (bx % max(1, period)) == 0

    # Band bias: top darker, lower bands brighter (horizontal strata)
    band_floor = (22, 48, 78, 115, 150, 195, 225)[band]
    h = (n * 2654435761 + x * 1597334677 + y * 2246822519 + tile_idx * 374761393) & 0xFFFFFFFF
    noise = ((h % 127) - 63) // 4

    if present:
        base = min(252, band_floor + 55)
        if vline:
            base = min(255, base + 38)
        v = max(0, min(255, base + noise))
    else:
        base = max(10, band_floor // 5)
        if vline:
            base = min(200, base + 72)
        v = max(0, min(255, base + noise))

    return (v, v, v)


def _rasterize_timeline_data_strip(number_set: set[int], n_tiles: int):
    """
    Full fill: one pixel per step index n in column-major order (same as timeline_tile_xy_to_step).
    Bright vertical texture where CSV has that number; darker banded field elsewhere.
    Returns (tiles, 1, 0).
    """
    w, h = TIMELINE_TILE_W, TIMELINE_TILE_H
    tiles = _empty_timeline_tiles(n_tiles)
    for tile_idx in range(n_tiles):
        for y in range(h):
            row_buf = tiles[tile_idx][y]
            for x in range(w):
                n = timeline_tile_xy_to_step(tile_idx, x, y, n_tiles)
                present = n in number_set
                rr, gg, bb = _timeline_data_bw_rgb(present, x, y, n, tile_idx)
                off = x * 3
                row_buf[off] = rr
                row_buf[off + 1] = gg
                row_buf[off + 2] = bb
    return tiles, 1, 0


def rasterize_statuses_timeline_tiles(numbers, statuses, max_val: int):
    """
    Ten RGB rasters: step presence along column-major strip (same indexing as steps_data n).
    statuses/max_val ignored; kept for call compatibility.
    """
    return _rasterize_timeline_data_strip(set(numbers), TIMELINE_N_TILES)


def rasterize_statuses_timeline_ext_decodable(numbers, statuses, max_val: int):
    """100-tile strip in analyze/timeline/: same data logic, full fill."""
    return _rasterize_timeline_data_strip(set(numbers), TIMELINE_EXT_N_TILES)


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

    cap = timeline_capacity()
    tiles, k, skipped = rasterize_statuses_timeline_tiles(
        numbers, data["statuses"], max_val
    )
    print(
        f"timeline: capacity={cap} slots, step presence (steps_data semantics), "
        f"1 px per step, full fill; k={k}, skipped={skipped}"
    )
    if max_val >= cap:
        print(f"warning: max step {max_val} >= timeline capacity {cap}; strip clips.")
    for i, rows in enumerate(tiles):
        out = OUTPUT_DIR / f"steps_statuses_{i + 1}.png"
        write_rgb_png(out, rows, TIMELINE_TILE_W, TIMELINE_TILE_H)
        print(f"saved:   {out}")

    cap_ext = timeline_capacity(TIMELINE_EXT_N_TILES)
    tiles_ext, k_ext, skipped_ext = rasterize_statuses_timeline_ext_decodable(
        numbers, data["statuses"], max_val
    )
    TIMELINE_EXT_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"timeline_ext: dir={TIMELINE_EXT_DIR}, capacity={cap_ext} slots, "
        f"step presence full fill; k={k_ext}, skipped={skipped_ext}; "
        f"n = timeline_tile_xy_to_step(tile_i,x,y,100)"
    )
    if max_val >= cap_ext:
        print(
            f"warning: max step {max_val} >= extended timeline capacity {cap_ext}."
        )
    for i, rows in enumerate(tiles_ext):
        out = TIMELINE_EXT_DIR / f"steps_statuses_{i + 1}.png"
        write_rgb_png(out, rows, TIMELINE_TILE_W, TIMELINE_TILE_H)
        print(f"saved:   {out}")

    _save_grayscale("steps_tags.png", rasterize_presence_set(data["has_tags"], width, height), width, height)
    _save_grayscale("steps_screenshot.png", rasterize_presence_set(data["has_screenshot"], width, height), width, height)
    _save_grayscale("steps_text.png", rasterize_text_brightness(data["text_lengths"], width, height), width, height)
    _save_grayscale("steps_geo.png", rasterize_presence_set(data["has_geo"], width, height), width, height)


if __name__ == "__main__":
    main()
